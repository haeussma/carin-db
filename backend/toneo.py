# neo4j_upsert.py
# neo4j_upsert.py
from __future__ import annotations

import uuid
from collections import defaultdict

# Import your dataclasses
# from your_module import UpsertNode, UpsertEdge, NodeRef   # <- adjust as needed
from typing import Any, Dict, List, Optional, Tuple

import neo4j
from neo4j import GraphDatabase

# Import your dataclasses
from backend.upsert import UpsertEdge, UpsertNode


class Neo4jUpserter:
    """
    Executes a batch upsert plan against Neo4j.

    - For nodes with a unique key: MERGE by (label, keyProp, keyVal) and SET properties.
    - For nodes without a unique key: CREATE, tag with _batch_id + _temp_id for edge wiring.
    - For edges: MATCH src (by key or by batch+temp), MATCH dst by key,
                 then MERGE or CREATE relationship by type; SET rel properties.
    """

    def __init__(
        self, uri: str, user: str, password: str, database: Optional[str] = None
    ):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database

    def close(self) -> None:
        self.driver.close()

    # -------- public API --------

    def upsert(
        self,
        nodes: List[UpsertNode],
        edges: List[UpsertEdge],
        *,
        create_constraints: bool = True,
        case_insensitive_dst_match: bool = True,
    ) -> None:
        batch_id = str(uuid.uuid4())
        with self.driver.session(database=self.database) as sess:
            if create_constraints:
                self._ensure_constraints(sess, nodes)

            self._upsert_nodes(sess, nodes, batch_id=batch_id)
            self._upsert_edges(
                sess,
                edges,
                batch_id=batch_id,
                case_insensitive_dst_match=case_insensitive_dst_match,
            )

    # -------- constraints --------

    def _ensure_constraints(self, sess, nodes: List[UpsertNode]) -> None:
        """
        Create unique constraints for every (label, keyProp) observed in node refs with a key.
        Safe to run repeatedly (IF NOT EXISTS).
        """
        seen: set[Tuple[str, str]] = set()
        for n in nodes:
            if n.ref.key:
                # In your planner, ref.key has *one* entry (the target's unique field)
                if len(n.ref.key) != 1:
                    continue
                (k, _) = next(iter(n.ref.key.items()))
                seen.add((n.label, k))

        for label, prop in seen:
            cypher = f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:`{label}`) REQUIRE n.`{prop}` IS UNIQUE"
            sess.execute_write(lambda tx: tx.run(cypher).consume())

    # -------- nodes --------

    def _upsert_nodes(self, sess, nodes: List[UpsertNode], *, batch_id: str) -> None:
        keyed_groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        created_groups: Dict[str, List[Dict[str, Any]]] = {}

        for n in nodes:
            if n.ref.key:
                # Expect exactly one unique key
                (k, v) = next(iter(n.ref.key.items()))
                keyed_groups.setdefault((n.label, k), []).append(
                    {"keyVal": v, "props": n.properties or {}}
                )
            else:
                created_groups.setdefault(n.label, []).append(
                    {"temp_id": n.ref.temp_id, "props": n.properties or {}}
                )

        # MERGE keyed
        for (label, key_prop), rows in keyed_groups.items():
            cypher = f"""
            UNWIND $rows AS row
            MERGE (n:`{label}` {{ `{key_prop}`: row.keyVal }})
            SET n += row.props,
                n._lastSeenAt = datetime()
            """
            sess.execute_write(lambda tx: tx.run(cypher, rows=rows).consume())

        # CREATE create-only
        for label, rows in created_groups.items():
            cypher = f"""
            UNWIND $rows AS row
            CREATE (n:`{label}`)
            SET n += row.props,
                n._batch_id = $batch_id,
                n._temp_id  = row.temp_id,
                n._createdAt = datetime()
            """
            sess.execute_write(
                lambda tx: tx.run(cypher, rows=rows, batch_id=batch_id).consume()
            )

    # -------- edges --------

    def _upsert_edges(
        self,
        sess,
        edges: List[UpsertEdge],
        *,
        batch_id: str,
        case_insensitive_dst_match: bool,
    ) -> None:
        # Separate by whether source uses key or temp, and group by (src_label, rel_type, dst_label)
        groups_key_src: Dict[Tuple[str, str, str, str], List[Dict[str, Any]]] = {}
        groups_tmp_src: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}

        for e in edges:
            # destination is always matched by a single key: {on: value}
            (dst_key, dst_val) = next(
                iter(e.dst_ref.key.items())
            )  # planner guarantees it
            if e.src_ref.key:
                (src_key, src_val) = next(iter(e.src_ref.key.items()))
                groups_key_src.setdefault(
                    (e.src_label, src_key, e.rel_type, e.dst_label), []
                ).append(
                    {
                        "srcVal": src_val,
                        "dstKey": dst_key,
                        "dstVal": dst_val,
                        "relProps": e.properties or {},
                        "unique": bool(e.unique),
                    }
                )
            else:
                groups_tmp_src.setdefault(
                    (e.src_label, e.rel_type, e.dst_label), []
                ).append(
                    {
                        "srcTempId": e.src_ref.temp_id,
                        "dstKey": dst_key,
                        "dstVal": dst_val,
                        "relProps": e.properties or {},
                        "unique": bool(e.unique),
                    }
                )

        # Helper to emit either MERGE or CREATE relationship
        def _rel_fragment(unique: bool, rel_type: str) -> str:
            if unique:
                return f"MERGE (src)-[r:`{rel_type}`]->(dst)\nSET r += row.relProps"
            else:
                return f"CREATE (src)-[r:`{rel_type}`]->(dst)\nSET r += row.relProps"

        # --- Source by key ---
        for (src_label, src_key, rel_type, dst_label), rows in groups_key_src.items():
            # Destination match: default to case-insensitive compare if requested.
            dst_match_pred = (
                "toLower(dst[row.dstKey]) = toLower(row.dstVal)"
                if case_insensitive_dst_match
                else "dst[row.dstKey] = row.dstVal"
            )
            cypher = f"""
            UNWIND $rows AS row
            MATCH (src:`{src_label}` {{ `{src_key}`: row.srcVal }})
            MATCH (dst:`{dst_label}`)
            WHERE {dst_match_pred}
            {
                _rel_fragment(True, rel_type)
                if all(r["unique"] for r in rows)
                else _rel_fragment(False, rel_type)
            }
            """
            # If the `unique` flag mixes within the group, we can split rows; to keep it simple,
            # we run twice when mixed:
            uniq_rows = [r for r in rows if r["unique"]]
            non_rows = [r for r in rows if not r["unique"]]
            if uniq_rows:
                sess.execute_write(lambda tx: tx.run(cypher, rows=uniq_rows).consume())
            if non_rows:
                cypher_non = cypher.replace(
                    _rel_fragment(True, rel_type), _rel_fragment(False, rel_type)
                )
                sess.execute_write(
                    lambda tx: tx.run(cypher_non, rows=non_rows).consume()
                )

        # --- Source by temp id (created within this batch) ---
        for (src_label, rel_type, dst_label), rows in groups_tmp_src.items():
            dst_match_pred = (
                "toLower(dst[row.dstKey]) = toLower(row.dstVal)"
                if case_insensitive_dst_match
                else "dst[row.dstKey] = row.dstVal"
            )
            cypher = f"""
            UNWIND $rows AS row
            MATCH (src:`{
                src_label
            }` {{ _batch_id: $batch_id, _temp_id: row.srcTempId }})
            MATCH (dst:`{dst_label}`)
            WHERE {dst_match_pred}
            {
                _rel_fragment(True, rel_type)
                if all(r["unique"] for r in rows)
                else _rel_fragment(False, rel_type)
            }
            """
            uniq_rows = [r for r in rows if r["unique"]]
            non_rows = [r for r in rows if not r["unique"]]
            if uniq_rows:
                sess.execute_write(
                    lambda tx: tx.run(
                        cypher, rows=uniq_rows, batch_id=batch_id
                    ).consume()
                )
            if non_rows:
                cypher_non = cypher.replace(
                    _rel_fragment(True, rel_type), _rel_fragment(False, rel_type)
                )
                sess.execute_write(
                    lambda tx: tx.run(
                        cypher_non, rows=non_rows, batch_id=batch_id
                    ).consume()
                )

    # - Schema

    def get_graph_info_dict(self, *, include_examples: bool = True) -> dict[str, Any]:
        """Return graph schema info: node labels, relationship types, and their properties.

        Args:
            include_examples: If True, include example values for node properties.

        Returns:
            Dictionary with keys: nodes, relationships, relationship_properties.
        """
        return {
            "nodes": self.node_properties(include_examples=include_examples),
            "relationships": self.relationships(),
            "relationship_properties": self.relationship_properties(),
        }

    def relationship_properties(self) -> list[dict[str, Any]]:
        """
        Return relationship types and their properties, excluding internal fields.
        """
        rel_properties_query = """
            CALL apoc.meta.data()
            YIELD label, other, elementType, type, property
            WHERE NOT type = "RELATIONSHIP" AND elementType = "relationship"
            WITH label AS nodeLabels, collect(property) AS properties
            RETURN {type: nodeLabels, properties: properties} AS output
            """
        with self.driver.session() as session:
            response = session.run(rel_properties_query).data()
            results: list[dict[str, Any]] = []
            for record in response:
                output = record["output"]
                filtered_props = [
                    p
                    for p in output["properties"]
                    if p not in {"_batch_id", "_temp_id", "_lastSeenAt"}
                ]
                results.append(
                    {
                        "type": output["type"],
                        "properties": filtered_props,
                    }
                )
            return results

    def relationships(self) -> list[dict[str, Any]]:
        """
        Return source node label, relationship type, and target node label.
        Ignores internal fields like _batch_id and _temp_id.
        """
        rel_query = """
            CALL apoc.meta.data()
            YIELD label, other, elementType, type, property
            WHERE type = "RELATIONSHIP" AND elementType = "node"
            RETURN {source: label, name: property, targets: other} AS output
            """
        with self.driver.session() as session:
            response = session.run(rel_query).data()
            results: list[dict[str, Any]] = []
            for record in response:
                output = record["output"]
                if output["name"] not in {"_batch_id", "_temp_id", "_lastSeenAt"}:
                    results.append(output)
            return results

    def get_db_structure(self, *, include_examples: bool = True) -> dict[str, Any]:
        """Return node and relationship structure, optionally with example data."""
        return {
            "nodes": self.node_properties(include_examples=include_examples),
            "relationships": self.relationships,
        }

    def node_properties(self, *, include_examples: bool = True) -> list[dict[str, Any]]:
        """
        Return node label dicts, each with a name and a list of attribute dicts,
        excluding attributes named '_batch_id', '_temp_id', or '_lastSeenAt'.

        Args:
            include_examples: If True, include example values for each attribute.
        """
        node_query = """
        CALL apoc.meta.nodeTypeProperties()
        YIELD
        nodeType       AS rawLabel,
        propertyName   AS attribute,
        propertyTypes  AS data_types
        // strip the leading ":" and all backticks from rawLabel
        WITH
        replace(substring(rawLabel, 2), "`", "") AS label,
        attribute,
        data_types[0] AS data_type

        // for each declared property, try to find a matching node with a non-null value
        OPTIONAL MATCH (n)
        WHERE label IN labels(n)
            AND n[attribute] IS NOT NULL

        // group per (label,attribute) and collect up to one example
        WITH
        label,
        attribute,
        data_type,
        collect(n[attribute]) AS examples

        RETURN
        label,
        attribute       AS property,
        data_type,
        head(examples)  AS example     // will be NULL if examples=[]
        ORDER BY
        label, property;
        """
        node_dict: dict[str, list[dict[str, Any]]] = defaultdict(list)
        nodes: list[dict[str, Any]] = []
        with self.driver.session() as session:
            response = session.run(node_query).data()
        for entry in response:
            attr_name = entry["property"]
            if attr_name in {"_batch_id", "_temp_id", "_lastSeenAt"}:
                continue
            attr: dict[str, Any] = {"attr_name": attr_name}
            if include_examples:
                attr["example_val"] = _convert_temporal_to_string(entry["example"])
            node_dict[entry["label"]].append(attr)
        for label, attributes in node_dict.items():
            nodes.append({"name": label, "attributes": attributes})
        return nodes


def _convert_temporal_to_string(value: Any) -> Any:
    """Convert Neo4j temporal types to strings for Pydantic compatibility."""
    if isinstance(value, (neo4j.time.DateTime, neo4j.time.Date, neo4j.time.Time)):
        return str(value)
    elif isinstance(value, neo4j.time.Duration):
        return str(value)
    return value


if __name__ == "__main__":
    # get credentials via config

    from rich import print

    from backend.model import GraphSheetModel
    from backend.spreadsheet import load_sheets
    from backend.upsert import UpsertPlanner

    sheets = load_sheets("test_data/genoscope/Genoscope_reaction4.xlsx")

    with open("test_model.json", "r") as f:
        project = GraphSheetModel.model_validate_json(f.read())

    planner = UpsertPlanner(project, sheets)
    nodes, edges = planner.plan()
    print(nodes[-10:])
    print(edges[-10:])
    # print(project)

    from backend.settings import config

    print(config.neo4j_uri, config.neo4j_username, config.neo4j_password)

    upsert = Neo4jUpserter(
        "bolt://localhost:7687", config.neo4j_username, config.neo4j_password
    )
    print(upsert.get_graph_info_dict(include_examples=False))

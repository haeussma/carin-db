from typing import List

import pandas as pd

from backend.models import Relationship


class CypherQueryGenerator:
    @staticmethod
    def generate_set_clause(
        columns: List[str],
    ) -> str:
        set_statements = [f"p.`{col}` = row.`{col}`" for col in columns]
        return ",\n    ".join(set_statements)

    @staticmethod
    def generate_cypher_query(
        df: pd.DataFrame, node_label: str, identifier_column: str, path: str
    ) -> str:
        set_clause = CypherQueryGenerator.generate_set_clause(df.columns)
        return f"""
        UNWIND $data as row
        MERGE (p:{node_label} {{
            {identifier_column}: row.`{identifier_column}`,
            source_path_of_data: '{path}'
        }})
        SET {set_clause}
        """

    @staticmethod
    def generate_relationship_query(
        relationship: Relationship, primary_key: str, path: str
    ) -> str:
        """
        Generates a Cypher query to create relationships between nodes that have the same primary key and source_path_of_data.

        Parameters:
        - relationship: Relationship object defining the relationship to create.
        - primary_key: The primary key column name.
        - path: The source file path (used in 'source_path_of_data' property).

        Returns:
        - str: A Cypher query string to create the relationships.
        """
        return f"""
        MATCH (source:{relationship.source}), (target:{relationship.target})
        WHERE source.{primary_key} = target.{primary_key}
        AND source.source_path_of_data = '{path}'
        AND target.source_path_of_data = '{path}'
        MERGE (source)-[r:{relationship.name}]->(target)
        """

    @staticmethod
    def generate_unify_nodes_query(
        node_label: str,
        primary_key: str,
        path: str,
        attribute_columns: List[str],
    ) -> str:
        """
        Generates a Cypher query to unify nodes with identical attributes
        except for the primary key and source_path_of_data.

        Parameters:
        - node_label: The label of the nodes to unify.
        - primary_key: The primary key column name.
        - path: The source file path.
        - attribute_columns: List of attribute columns to consider for matching.

        Returns:
        - str: A Cypher query string.
        """
        # Exclude primary_key and source_path_of_data from the comparison
        group_by_properties = [
            col
            for col in attribute_columns
            if col not in [primary_key, "source_path_of_data"]
        ]

        # Build the property map for grouping, with backticks around property names
        property_map = ", ".join([f"`{col}`: n.`{col}`" for col in group_by_properties])

        # Use APOC to merge nodes
        return f"""
        MATCH (n:{node_label})
        WITH {{ {property_map} }} AS properties, collect(n) AS nodes
        WHERE size(nodes) > 1
        CALL apoc.refactor.mergeNodes(nodes, {{properties: 'combine', mergeRels: true}})
        YIELD node
        RETURN node
        """

    @staticmethod
    def node_properties():
        return """
            CALL apoc.meta.data()
            YIELD label, other, elementType, type, property
            WHERE NOT type = "RELATIONSHIP" AND elementType = "node"
            WITH label AS nodeLabels, collect(property) AS properties
            RETURN {labels: nodeLabels, properties: properties} AS output
            """

    @staticmethod
    def relationships():
        return """
            CALL apoc.meta.data()
            YIELD label, other, elementType, type, property
            WHERE type = "RELATIONSHIP" AND elementType = "node"
            RETURN {source: label, relationship: property, target: other} AS output
            """

import threading
from collections import defaultdict
from typing import Annotated, Any, List

from fastapi import Depends
from loguru import logger
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

from backend.models.graph_model import Attribute, GraphModel, Node, Relationship
from backend.settings import config


class DatabaseError(Exception):
    """Base exception for database-related errors."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when there are issues connecting to the database."""

    pass


class DatabaseAuthenticationError(DatabaseError):
    """Raised when there are authentication issues."""

    pass


class Database:
    _instance: "Database | None" = None
    _lock = threading.Lock()
    _initialized: bool = False

    def __init__(self, uri: str, username: str, password: str):
        self.uri = uri
        self.username = username
        self.password = password
        self.driver = self._connect()
        self._validate_connection()

    def _connect(self):
        return GraphDatabase.driver(self.uri, auth=(self.username, self.password))

    def _validate_connection(self):
        try:
            with self.driver.session() as s:
                s.run("RETURN 1").single()
            logger.info("Neo4j connection OK")
        except AuthError as e:
            logger.error(f"Neo4j auth failed: {e}")
            raise DatabaseAuthenticationError("Invalid Neo4j username or password.")
        except ServiceUnavailable as e:
            logger.error(f"Neo4j connection failed: {e}")
            raise DatabaseConnectionError("Could not connect to the Neo4j database.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise DatabaseError("An unknown error occurred while connecting to Neo4j.")

    def close(self) -> None:
        if self.driver:
            self.driver.close()

    def execute_query(self, query: str):
        with self.driver.session() as session:
            return session.run(query).data()

    @property
    def get_graph_info_dict(self) -> dict[str, Any]:
        """Returns a dictionary containing the graph schema information
        containing node labels, relationship types, and their properties.
        """
        return dict(
            nodes=self.node_properties,
            relationships=self.relationships,
            relationship_properties=self.relationship_properties,
        )

    @property
    def relationship_properties(self) -> list[dict[str, Any]]:
        """
        Returns a list of dictionaries containing the relationship types and their properties.
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
            return [record["output"] for record in response]

    @property
    def relationships(self) -> list[Relationship]:
        """
        Returns a list of dictionaries containing the source node label,
        relationship type, and target node label.
        """
        rel_query = """
            CALL apoc.meta.data()
            YIELD label, other, elementType, type, property
            WHERE type = "RELATIONSHIP" AND elementType = "node"
            RETURN {source: label, name: property, targets: other} AS output
            """

        with self.driver.session() as session:
            response = session.run(rel_query).data()
            return [Relationship(**record["output"]) for record in response]

    @property
    def get_db_structure(self) -> GraphModel:
        return GraphModel(
            nodes=self.node_properties,
            relationships=self.relationships,
        )

    @property
    def node_properties(self) -> List[Node]:
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

        node_dict = defaultdict(list)
        nodes = []
        with self.driver.session() as session:
            response = session.run(node_query).data()

        # group by label and collect attributes
        for entry in response:
            node_dict[entry["label"]].append(
                Attribute(
                    attr_name=entry["property"],
                    example_val=entry["example"],
                    # attr_type=entry["data_type"],
                )
            )

        # create nodes
        for label, attributes in node_dict.items():
            nodes.append(Node(name=label, attributes=attributes))

        return nodes

    @property
    def node_count(self) -> dict[str, int]:
        query = """
            CALL apoc.meta.stats() YIELD labels
            RETURN labels
        """

        with self.driver.session() as session:
            response = session.run(query).data()

        return response[0]["labels"]


def get_db() -> Database:  # FastAPI dependency
    return Database(config.neo4j_uri, config.neo4j_username, config.neo4j_password)


DB = Annotated[Database, Depends(get_db)]

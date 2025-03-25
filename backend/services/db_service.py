from typing import Any

from loguru import logger
from neo4j import Driver, GraphDatabase
from neo4j.exceptions import (
    AuthError,
    DriverError,
    Neo4jError,
    ServiceUnavailable,
    SessionExpired,
)

from ..models.appconfig import Attribute, GraphModel, Node, Relationship


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
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
    ):
        self.uri = uri
        self.user = user
        self.driver = self.connect(uri, user, password)
        self.validate_connection()

    def connect(self, uri: str, user: str, password: str) -> Driver:
        """Create a Neo4j driver instance."""
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.debug(f"Created Neo4j driver for URI: {uri}")
            return driver
        except Exception as e:
            logger.error(f"Failed to create Neo4j driver: {str(e)}")
            raise DatabaseConnectionError(f"Failed to create Neo4j driver: {str(e)}")

    def validate_connection(self) -> None:
        """Validate the database connection by executing a simple query."""
        try:
            with self.driver.session() as session:
                # Execute a simple query to verify connection
                result = session.run("RETURN 1")
                result.single()
                logger.info("Database connection validated successfully")
        except AuthError as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise DatabaseAuthenticationError(f"Authentication failed: {str(e)}")
        except ServiceUnavailable as e:
            logger.error(f"Database service unavailable: {str(e)}")
            raise DatabaseConnectionError(
                f"Database service unavailable. Please check if:\n"
                f"1. The Neo4j server is running\n"
                f"2. The connection URL is correct\n"
                f"3. The database is accessible from your network\n"
                f"Current URL: {self.uri}"
            )
        except SessionExpired as e:
            logger.error(f"Session expired: {str(e)}")
            raise DatabaseConnectionError(f"Session expired: {str(e)}")
        except DriverError as e:
            logger.error(f"Driver error: {str(e)}")
            raise DatabaseConnectionError(f"Driver error: {str(e)}")
        except Neo4jError as e:
            logger.error(f"Neo4j error: {str(e)}")
            raise DatabaseError(f"Neo4j error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error validating connection: {str(e)}")
            raise DatabaseError(f"Unexpected error validating connection: {str(e)}")

    def close(self) -> None:
        """Close the database connection."""
        try:
            self.driver.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")
            raise DatabaseError(f"Error closing database connection: {str(e)}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

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
    def node_properties(self) -> list[Node]:
        node_query = """
        CALL apoc.meta.nodeTypeProperties()
        YIELD nodeType AS name, propertyName AS attribute, propertyTypes AS data_type
        RETURN name, collect({name: attribute, data_type: data_type[0]}) AS attributes
        """

        with self.driver.session() as session:
            nodes_data = session.run(node_query).data()
            nodes = [
                Node(
                    name=node["name"],
                    attributes=[
                        Attribute(name=attr["name"], data_type=attr["data_type"])
                        for attr in node["attributes"]
                    ],
                )
                for node in nodes_data
            ]

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


if __name__ == "__main__":
    from devtools import pprint

    db = Database(uri="bolt://localhost:7692", user="neo4j", password="12345678")
    pprint(db.node_count)

    # pprint(db.get_db_structure)

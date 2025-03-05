from typing import Any

from neo4j import Driver, GraphDatabase

from .models import Attribute, DBStructure, Node, Relationship


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

    def close(self):
        if self.driver:
            self.driver.close()

    @staticmethod
    def connect(uri: str, user: str, password: str) -> Driver:
        return GraphDatabase.driver(uri, auth=(user, password))

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
    def get_db_structure(self) -> DBStructure:
        return DBStructure(
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

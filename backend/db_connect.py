from neo4j import Driver, GraphDatabase


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

    @property
    def get_graph_info_dict(self) -> dict:
        """Returns a dictionary containing the graph schema information
        containing node labels, relationship types, and their properties.
        """
        return dict(
            nodes=self.node_properties,
            relationships=self.relationships,
            relationship_properties=self.relationship_properties,
        )

    @property
    def node_properties(self) -> list[dict[str, str]]:
        """
        Returns a list of dictionaries containing the node labels and their properties.
        """
        node_properties_query = """
            CALL apoc.meta.data()
            YIELD label, other, elementType, type, property
            WHERE NOT type = "RELATIONSHIP" AND elementType = "node"
            WITH label AS nodeLabels, collect(property) AS properties
            RETURN {labels: nodeLabels, properties: properties} AS output
            """

        with self.driver.session() as session:
            response = session.run(node_properties_query).data()
            return [record["output"] for record in response]

    @property
    def relationship_properties(self) -> list[dict]:
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
    def relationships(self) -> list[dict]:
        """
        Returns a list of dictionaries containing the source node label,
        relationship type, and target node label.
        """
        rel_query = """
            CALL apoc.meta.data()
            YIELD label, other, elementType, type, property
            WHERE type = "RELATIONSHIP" AND elementType = "node"
            RETURN {source: label, relationship: property, target: other} AS output
            """

        with self.driver.session() as session:
            response = session.run(rel_query).data()
            return [record["output"] for record in response]

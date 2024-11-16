import uuid
from typing import List

import pandas as pd
from loguru import logger
from pydantic import BaseModel

from backend.cypher import CypherQueryGenerator
from backend.data_sanity import DataSanityChecker
from backend.db_connect import Database
from backend.exceptions import PrimaryKeyError
from backend.models import Node, Relationship


class Extractor(BaseModel):
    path: str
    db: Database
    primary_key: str
    sheet_names: List[str] = []
    batch_id: str

    def __init__(self, **data):
        data["batch_id"] = str(uuid.uuid4())
        super().__init__(**data)
        self.sheet_names = self.read_sheet_names()

    def read_sheet_names(self) -> List[str]:
        return pd.ExcelFile(self.path).sheet_names

    def read_sheet(self, sheet_name: str) -> pd.DataFrame:
        return pd.read_excel(self.path, sheet_name=sheet_name)

    def extract_file(self):
        for sheet_name in self.sheet_names:
            self.extract_sheet(sheet_name)

    def extract_sheet(self, sheet_name: str):
        df = self.read_sheet(sheet_name)
        if self.primary_key not in df.columns:
            rows = df[df[self.primary_key].isna()].index.tolist()
            raise PrimaryKeyError(self.primary_key, sheet_name, rows, self.path)

        # check data type consistency in each column
        data_checker = DataSanityChecker(
            df=df,
            sheet_name=sheet_name,
            path=self.path,
            primary_key=self.primary_key,
        )
        logger.debug("Sanity checking data types")
        for column in df.columns:
            data_checker.check_data_types(column)

        data_checker.check_primary_key_values_exist_in_all_rows()
        data_checker.check_primary_key_values_unique()

        # Add data to the database
        with self.db.driver.session() as session:
            for _, row in df.iterrows():
                data = row.to_dict()
                node = Node(name=sheet_name, properties=data)
                cypher_query = CypherQueryGenerator.generate_cypher_query(
                    df=df,
                    node_label=node.name,
                    identifier_column=self.primary_key,
                    path=self.path,
                )
                session.write_transaction(self.add_node, node, cypher_query)

        logger.debug(f"Data extracted from sheet {sheet_name} of file {self.path}")

    def add_node(self, tx, node: Node, cypher_query: str):
        tx.run(cypher_query, data=[node.properties])

    def create_relationships(self, relationships: List[Relationship]):
        with self.db.driver.session() as session:
            for relationship in relationships:
                cypher_query = CypherQueryGenerator.generate_relationship_query(
                    relationship, self.primary_key, self.path
                )
                session.run(cypher_query)

    def unify_nodes(self):
        with self.db.driver.session() as session:
            for sheet_name in self.sheet_names:
                df = self.read_sheet(sheet_name)
                attribute_columns = df.columns.tolist()
                cypher_query = CypherQueryGenerator.generate_unify_nodes_query(
                    node_label=sheet_name,
                    primary_key=self.primary_key,
                    path=self.path,
                    attribute_columns=attribute_columns,
                )
                session.run(cypher_query)

    def get_existing_node_labels(self) -> list[str]:
        """Gets all unique labels of nodes in the database."""
        with self.db.driver.session() as session:
            query = CypherQueryGenerator.node_properties()
            result = session.run(query).data()
            labels = set([node["output"]["labels"] for node in result])
            return list(labels)

    def get_node_names_from_sheet_and_db(self) -> list[str]:
        """Gets all unique node names from the sheet and
        extracts all existing nodes from the database."""
        nodes = set(self.get_existing_node_labels() + self.sheet_names)
        return list(nodes)


if __name__ == "__main__":
    db = Database(uri="bolt://localhost:7689", user="neo4j", password="12345678")

    relations = [
        Relationship(name="EXPRESSED_AS", source="Enzyme", target="Biocatalyst"),
        Relationship(
            name="HAS_PHOTOMETRIC_MEASUREMENT", source="Biocatalyst", target="UVvis"
        ),
        Relationship(name="HAS_HPLC_MEASUREMENT", source="Biocatalyst", target="Peak"),
        Relationship(name="ASSAYED", source="Peak", target="Reaction"),
        Relationship(name="ASSAYED", source="UVvis", target="Reaction"),
    ]

    path = "/Users/max/Documents/GitHub/carin-db/data.xlsx"
    ex = Extractor(
        path=path,
        db=db,
        primary_key="position",
    )

    ex.extract_file()
    ex.create_relationships(relations)
    ex.unify_nodes()

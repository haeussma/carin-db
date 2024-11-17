import logging
import uuid
from typing import List

import pandas as pd
from loguru import logger

from backend.cypher import CypherQueryGenerator
from backend.data_sanity import DataSanityChecker
from backend.db_connect import Database
from backend.exceptions import PrimaryKeyError
from backend.models import Node, Relationship


class Extractor:
    def __init__(self, path: str, db: Database, primary_key: str):
        self.path = path
        self.db = db
        self.primary_key = primary_key
        self.sheet_names: List[str] = []
        self.batch_id = str(uuid.uuid4())
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

        # replace all " " with "_" in column names
        df.columns = df.columns.str.replace(" ", "_")

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
        logger.info("Unifying nodes")
        with self.db.driver.session() as session:
            for sheet_name in self.sheet_names:
                logging.debug(f"Unifying nodes for sheet: {sheet_name}")
                df = self.read_sheet(sheet_name)
                attribute_columns = df.columns.tolist()
                attribute_columns = [
                    column.replace(" ", "_") for column in attribute_columns
                ]
                print(attribute_columns)
                cypher_query = CypherQueryGenerator.generate_unify_nodes_query(
                    node_label=sheet_name,
                    primary_key=self.primary_key,
                    path=self.path,
                    attribute_columns=attribute_columns,
                )
                logging.debug(f"Unify nodes query: {cypher_query}")
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

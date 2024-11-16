import uuid
from typing import Any, Dict, List

import pandas as pd
from loguru import logger
from neo4j import GraphDatabase
from pydantic import BaseModel


class Relationship(BaseModel):
    name: str
    source: str
    target: str


class Node(BaseModel):
    name: str
    properties: Dict[str, Any]


class DataSanityChecker:
    def __init__(
        self,
        df: pd.DataFrame,
        sheet_name: str,
        path: str,
        primary_key: str,
    ):
        self.df = df
        self.sheet_name = sheet_name
        self.path = path
        self.primary_key = primary_key

    def check_data_types(self, column: str) -> List[str]:
        """
        Checks the data types of values in a specified column, ignoring empty cells (NaN/None).
        Treats int and float as equivalent for consistency checks.

        Parameters:
        - df (pd.DataFrame): The input DataFrame.
        - column (str): The name of the column to check.
        - sheet_name (str): The name of the sheet being checked.

        Returns:
        - List[str]: A list of unique data types found in the column (excluding empty cells).

        Raises:
        - InconsistentDataError: If more than one data type (other than int/float) is found in non-empty cells.
        """
        non_empty_values = self.df[column][
            pd.notna(self.df[column])
        ]  # Filter out empty cells
        data_types = non_empty_values.apply(lambda x: type(x).__name__).unique()

        # Treat int and float as compatible types
        numeric_types = {"int", "float"}
        data_types_set = set(data_types)

        if len(data_types_set - numeric_types) > 1 or (
            len(data_types_set) > 1 and not data_types_set.issubset(numeric_types)
        ):
            # Identify rows with inconsistent types
            inconsistent_rows = non_empty_values[
                non_empty_values.apply(lambda x: type(x).__name__) != data_types[0]
            ].index.tolist()
            inconsistent_rows = [
                row + 2 for row in inconsistent_rows
            ]  # Convert to 1-indexing
            raise InconsistentDataError(
                column,
                data_types.tolist(),
                self.path,
                self.sheet_name,
                inconsistent_rows,
            )

        return data_types

    def check_primary_key_values_exist_in_all_rows(self):
        """Checks if in all rows of the primary key column there is a value"""
        if not self.df[self.primary_key].notna().all():
            missing_rows = self.df[self.df[self.primary_key].isna()].index.tolist()
            missing_rows = [row + 2 for row in missing_rows]
            raise PrimaryKeyNotFoundInRowError(
                self.primary_key, self.sheet_name, missing_rows, self.path
            )

    def check_primary_key_values_unique(self):
        """Checks if the primary key column has unique values.
        If not raises error giving the rows where the duplicates are found"""
        if not self.df[self.primary_key].is_unique:
            duplicate_rows = self.df[
                self.df[self.primary_key].duplicated(keep=False)
            ].index.tolist()
            duplicate_rows = [row + 2 for row in duplicate_rows]
            raise PrimaryKeyNotUniqueError(
                self.primary_key, self.sheet_name, duplicate_rows, self.path
            )


class Database(BaseModel):
    uri: str
    user: str
    password: str
    driver: Any = None

    def __init__(self, **data):
        super().__init__(**data)
        self.driver = self.connect()

    def connect(self):
        return GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        if self.driver:
            self.driver.close()


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


class InconsistentDataError(Exception):
    def __init__(
        self,
        column: str,
        data_types: List[str],
        path: str,
        sheet_name: str,
        row_indices: List[int],
    ):
        row_info = f" at rows {row_indices}" if row_indices else ""
        super().__init__(
            f"Inconsistent data types found in column '{column}' on sheet '{sheet_name}' in file '{path}': {data_types}{row_info}"
        )


class PrimaryKeyNotFoundInRowError(Exception):
    def __init__(
        self,
        primary_key: str,
        sheet_name: str,
        rows: list[int],
        path: str,
    ):
        super().__init__(
            f"Value for primary key '{primary_key}' not found in column '{primary_key}' in rows {rows} of sheet '{sheet_name}' in file '{path}'"
        )


class PrimaryKeyNotUniqueError(Exception):
    def __init__(
        self,
        primary_key: str,
        sheet_name: str,
        rows: list[int],
        path: str,
    ):
        super().__init__(
            f"Value for primary key '{primary_key}' not unique in column '{primary_key}' in rows {rows} of sheet '{sheet_name}' in file '{path}'"
        )


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
            raise ValueError(
                f"Primary key {self.primary_key} not found in columns {df.columns} of sheet {sheet_name} in file {self.path}"
            )

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

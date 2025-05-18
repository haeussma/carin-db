import uuid
from typing import Dict, List

import pandas as pd
from loguru import logger

from backend.models.error_model import GraphValidationError, GraphValidationResult
from backend.models.model import (
    Column,
    Sheet,
    SheetConnection,
    SheetModel,
    SheetReference,
)
from backend.services.database import Database


class DatabasePopulator:
    """Service for extracting data from spreadsheets to a Neo4j database."""

    def __init__(self, sheets: Dict[str, pd.DataFrame], source_file: str):
        """Initialize the DatabaseExtractor.

        Args:
            sheets: Dictionary mapping sheet names to DataFrames
        """
        self.sheets = sheets
        self.batch_id = str(uuid.uuid4())
        self.source_file = source_file

    def _parse_source_values(self, values: pd.Series) -> List[List[str]]:
        """Parse source values into lists of strings, handling NaN values."""
        result: List[List[str]] = []
        for value in values:
            if pd.isna(value):
                result.append([])
                continue
            cleaned_values = [v.strip() for v in str(value).split(",") if v.strip()]
            result.append(cleaned_values)
        return result

    def _validate_sheet_connections(
        self, sheet_model: SheetModel, connections: List[SheetConnection]
    ) -> GraphValidationResult:
        """Validate all sheet connections and collect any validation errors."""
        validation = GraphValidationResult(
            missing_sheets=[], missing_columns=[], missing_values=[]
        )

        for connection in connections:
            # Check source sheet
            source_sheet = next(
                (
                    sheet
                    for sheet in sheet_model.sheets
                    if sheet.name == connection.source_sheet_name
                ),
                None,
            )
            if source_sheet is None:
                validation.missing_sheets.append(
                    GraphValidationError(
                        error_type="missing_sheet",
                        sheet_name=connection.source_sheet_name,
                        message=f"Sheet '{connection.source_sheet_name}' not found",
                    )
                )
                continue

            # Check target sheet
            target_sheet = next(
                (
                    sheet
                    for sheet in sheet_model.sheets
                    if sheet.name == connection.target_sheet_name
                ),
                None,
            )
            if target_sheet is None:
                validation.missing_sheets.append(
                    GraphValidationError(
                        error_type="missing_sheet",
                        sheet_name=connection.target_sheet_name,
                        message=f"Sheet '{connection.target_sheet_name}' not found",
                    )
                )
                continue

            # Check key in source sheet
            if connection.key not in [col.name for col in source_sheet.columns]:
                validation.missing_columns.append(
                    GraphValidationError(
                        error_type="missing_key",
                        sheet_name=connection.source_sheet_name,
                        message=f"Key '{connection.key}' not found in sheet '{connection.source_sheet_name}'",
                    )
                )

            # Check key in target sheet
            if connection.key not in [col.name for col in target_sheet.columns]:
                validation.missing_columns.append(
                    GraphValidationError(
                        error_type="missing_key",
                        sheet_name=connection.target_sheet_name,
                        message=f"Key '{connection.key}' not found in sheet '{connection.target_sheet_name}'",
                    )
                )

        return validation

    def _validate_sheet_references(
        self, sheet_model: SheetModel, references: List[SheetReference]
    ) -> GraphValidationResult:
        """Validate all sheet references and collect any validation errors."""
        validation = GraphValidationResult(
            missing_sheets=[], missing_columns=[], missing_values=[]
        )

        for reference in references:
            # Check source sheet
            source_sheet = next(
                (
                    sheet
                    for sheet in sheet_model.sheets
                    if sheet.name == reference.source_sheet_name
                ),
                None,
            )
            if source_sheet is None:
                validation.missing_sheets.append(
                    GraphValidationError(
                        error_type="missing_sheet",
                        sheet_name=reference.source_sheet_name,
                        message=f"Sheet '{reference.source_sheet_name}' not found",
                    )
                )
                continue

            # Check target sheet
            target_sheet = next(
                (
                    sheet
                    for sheet in sheet_model.sheets
                    if sheet.name == reference.target_sheet_name
                ),
                None,
            )
            if target_sheet is None:
                validation.missing_sheets.append(
                    GraphValidationError(
                        error_type="missing_sheet",
                        sheet_name=reference.target_sheet_name,
                        message=f"Sheet '{reference.target_sheet_name}' not found",
                    )
                )
                continue

            # Check source column
            if reference.source_column_name not in [
                col.name for col in source_sheet.columns
            ]:
                validation.missing_columns.append(
                    GraphValidationError(
                        error_type="missing_column",
                        sheet_name=reference.source_sheet_name,
                        message=f"Column '{reference.source_column_name}' not found in sheet '{reference.source_sheet_name}'",
                    )
                )
                continue

            # Check target column
            if reference.target_column_name not in [
                col.name for col in target_sheet.columns
            ]:
                validation.missing_columns.append(
                    GraphValidationError(
                        error_type="missing_column",
                        sheet_name=reference.target_sheet_name,
                        message=f"Column '{reference.target_column_name}' not found in sheet '{reference.target_sheet_name}'",
                    )
                )
                continue

            # Check values only if structure is valid
            source_values = self.sheets[reference.source_sheet_name][
                reference.source_column_name
            ]
            source_values_as_lists = self._parse_source_values(source_values)
            target_values = self.sheets[reference.target_sheet_name][
                reference.target_column_name
            ]

            for row_id, values in enumerate(source_values_as_lists):
                if not values:  # Skip empty lists (from NaN values)
                    continue
                missing = [v for v in values if v not in target_values.values]
                if missing:
                    validation.missing_values.append(
                        GraphValidationError(
                            error_type="missing_value",
                            sheet_name=reference.source_sheet_name,
                            message=f"Values {missing} in row {row_id + 2} of column '{reference.source_column_name}' "
                            f"not found in target column '{reference.target_column_name}' of sheet '{reference.target_sheet_name}'",
                        )
                    )

        return validation

    def validate_graph_model(self, db: Database) -> None:
        """Validates that the data in the sheets conforms to the graph model specifications.

        Args:
            db: The database to validate

        Raises:
            ValueError: If validation fails
        """
        # Create a sheet model from the sheets
        sheet_model = SheetModel(
            sheets=[
                Sheet(
                    name=sheet_name,
                    columns=[
                        Column(name=col, data_type="string") for col in df.columns
                    ],
                )
                for sheet_name, df in self.sheets.items()
            ]
        )

        # Collect all validation errors
        reference_validation = self._validate_sheet_references(
            sheet_model, sheet_model.sheet_references
        )
        connection_validation = self._validate_sheet_connections(
            sheet_model, sheet_model.sheet_connections
        )

        # Combine all validation errors
        all_errors = GraphValidationResult(
            missing_sheets=reference_validation.missing_sheets
            + connection_validation.missing_sheets,
            missing_columns=reference_validation.missing_columns
            + connection_validation.missing_columns,
            missing_values=reference_validation.missing_values
            + connection_validation.missing_values,
        )

        # Raise formatted error if any validation failed
        if all_errors.has_errors():
            raise ValueError(all_errors.format_error_message())

    def extract_to_db(self, db: Database, sheet_model: SheetModel) -> None:
        """Extracts the validated data and creates the corresponding graph structure in Neo4j.

        Args:
            db: The database to extract to
            sheet_model: The sheet model to use for extraction
        """
        logger.info("Starting data extraction to database")

        # Build a mapping of sheet name -> primary key using sheet_connections
        primary_keys = {}
        for connection in sheet_model.sheet_connections:
            primary_keys[connection.source_sheet_name] = connection.key
            primary_keys[connection.target_sheet_name] = connection.key

        # Default to first column for sheets without connections
        # for name in self.sheets.keys():
        #     if name not in primary_keys:
        #         df = self.sheets[name]
        #         primary_keys[name] = df.columns[0]

        logger.info(f"Using primary keys: {primary_keys}")

        with db.driver.session() as session:
            # --- Step 1: Create Nodes ---
            for sheet_name, df in self.sheets.items():
                label = sheet_name

                # 1 · detect candidate PK columns
                pk_candidates = [
                    c
                    for c in df.columns
                    if c.isupper() and (c.endswith("_ID") or c.endswith("_KEY"))
                ]

                # 2 · decide PK
                if len(pk_candidates) == 1:
                    pk = pk_candidates[0]
                elif len(pk_candidates) == 0:
                    pk = "_row_uuid"
                    if "_row_uuid" not in df.columns:  # add synthetic UUIDs
                        df["_row_uuid"] = [str(uuid.uuid4()) for _ in range(len(df))]
                    logger.warning(
                        f"Sheet '{sheet_name}' has no PK column, using synthetic '_row_uuid' as PK."
                    )
                else:
                    raise ValueError(
                        f"Sheet '{sheet_name}' has multiple candidate PK columns "
                        f"{pk_candidates}. Keep zero or exactly one."
                    )

                logger.info(f"Creating nodes for '{sheet_name}' (PK = '{pk}')")

                for idx, row in df.iterrows():
                    value = row[pk]
                    if pd.isna(value):
                        logger.warning(
                            f"Skipping row {idx} with NaN PK in '{sheet_name}'"
                        )
                        continue

                    props = row.to_dict()
                    props = {k: v for k, v in props.items() if not pd.isna(v)}

                    cypher = f"MERGE (n:{label} {{{pk}: $value}}) SET n += $props"
                    session.run(cypher, value=value, props=props)

            # --- Step 2: Create Relationships for Sheet Connections ---
            for connection in sheet_model.sheet_connections:
                logger.info(f"Creating relationships for connection: {connection}")
                source_label = connection.source_sheet_name
                target_label = connection.target_sheet_name
                key = connection.key
                source_df = self.sheets[connection.source_sheet_name]
                logger.info(
                    f"Creating relationships for connection: {connection.source_sheet_name} -> {connection.edge_name} -> {connection.target_sheet_name}"
                )

                for _, row in source_df.iterrows():
                    key_value = row[key]
                    # Skip rows with NaN primary keys
                    if pd.isna(key_value):
                        logger.warning(
                            f"Skipping row with NaN key value {key} in sheet {connection.source_sheet_name}"
                        )
                        continue

                    cypher_query = (
                        f"MATCH (s:{source_label} {{{key}: $key_value}}), "
                        f"(t:{target_label} {{{key}: $key_value}}) "
                        f"MERGE (s)-[r:{connection.edge_name.upper()}]->(t)"
                    )
                    logger.debug(
                        f"Executing query: {cypher_query} with key_value={key_value}"
                    )
                    session.run(cypher_query, key_value=key_value)

            # --- Step 3: Create Relationships for Sheet References ---
            for reference in sheet_model.sheet_references:
                logger.info(f"Creating relationships for reference: {reference}")
                source_df = self.sheets[reference.source_sheet_name]
                # Generate a relationship type; here we use the source column name.
                relationship_type = reference.source_column_name.upper()

                logger.info(
                    f"Creating reference relationships: {reference.source_sheet_name}.{reference.source_column_name} -> "
                    f"{reference.target_sheet_name}.{reference.target_column_name}"
                )

                for _, row in source_df.iterrows():
                    source_node_id = row[reference.source_column_name]
                    # Skip rows with NaN primary keys
                    if pd.isna(source_node_id):
                        logger.warning(
                            f"Skipping row with NaN primary key {reference.source_column_name} in sheet {reference.source_sheet_name}"
                        )
                        continue

                    cell_value = row[reference.source_column_name]
                    if pd.isna(cell_value):
                        logger.warning(
                            f"Skipping NaN value in column {reference.source_column_name} for row with pk={source_node_id}"
                        )
                        continue

                    tokens = [
                        v.strip() for v in str(cell_value).split(",") if v.strip()
                    ]

                    if not tokens:
                        logger.warning(
                            f"No valid tokens found in '{cell_value}' for row with pk={source_node_id}"
                        )
                        continue

                    for token in tokens:
                        cypher_query = (
                            f"MATCH (s:{reference.source_sheet_name} {{{reference.source_column_name}: $source_id}}), "
                            f"(t:{reference.target_sheet_name} {{{reference.target_column_name}: $target_value}}) "
                            f"MERGE (s)-[r:{relationship_type}]->(t)"
                        )
                        logger.debug(
                            f"Executing query: {cypher_query} with source_id={source_node_id}, target_value={token}"
                        )
                        session.run(
                            cypher_query,
                            source_id=source_node_id,
                            target_value=token,
                        )

        logger.info("Data extraction completed successfully")

    # def extract_to_database(self, db: Database, graph_model: GraphModel) -> None:
    #     """Validates the data against the graph model and extracts it to the database.

    #     Args:
    #         db: The database to extract to
    #         graph_model: The graph model to use for extraction
    #     """
    #     logger.info(f"Starting extraction process for file: {self.path}")
    #     logger.info(
    #         f"Graph model: {len(graph_model.sheet_connections)} connections, {len(graph_model.sheet_references)} references"
    #     )

    #     try:
    #         # Validate the graph model
    #         self.validate_graph_model(graph_model)
    #         # Extract data to database
    #         self.extract_to_db(db=db, graph_model=graph_model)
    #         logger.info("Extraction completed successfully")
    #     except Exception as e:
    #         logger.error(f"Error during extraction: {str(e)}")
    #         raise

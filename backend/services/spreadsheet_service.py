import os
import uuid
from io import BytesIO
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import UploadFile
from loguru import logger

from ..data_sanity import DataSanityChecker
from ..exceptions import TypeInconsistencyError, TypeInconsistencyLocation
from ..models.appconfig import GraphModel, Node
from ..models.error_model import GraphValidationError, GraphValidationResult
from ..services.config_service import ConfigService
from ..services.db_service import Database


class SpreadsheetService:
    """Service for handling spreadsheet operations including extraction and database upload."""

    UPLOAD_DIR = "uploads"

    def __init__(self):
        """Initialize the SpreadsheetService."""
        # Ensure uploads directory exists
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

    @staticmethod
    async def save_uploaded_file(file: UploadFile) -> str:
        """Save an uploaded file to the uploads directory and return the file path.

        Args:
            file: The uploaded file

        Returns:
            str: Path to the saved file
        """
        file_path = os.path.join(SpreadsheetService.UPLOAD_DIR, str(file.filename))

        # Create uploads directory if it doesn't exist
        os.makedirs(SpreadsheetService.UPLOAD_DIR, exist_ok=True)

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        logger.debug(f"File saved successfully to {file_path}")
        return file_path

    @staticmethod
    def generate_spreadsheet(data: List[Dict[str, Any]]) -> BytesIO:
        """Generate a spreadsheet from the provided data.

        Args:
            data: List of dictionaries representing rows of data

        Returns:
            BytesIO: In-memory file-like object containing the Excel spreadsheet
        """
        if not data:
            logger.warning("No data provided for spreadsheet generation")
            raise ValueError("No data provided for spreadsheet generation")

        # Convert data to pandas DataFrame
        df = pd.DataFrame(data)
        logger.debug(f"Created DataFrame with shape: {df.shape}")

        # Create an Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)

        output.seek(0)
        logger.info("Successfully generated spreadsheet")
        return output

    class SheetExtractor:
        """Handles extraction of sheet data and validation."""

        def __init__(self, path: str):
            """Initialize the SheetExtractor.

            Args:
                path: Path to the Excel file
            """
            self.path = path
            self.batch_id = str(uuid.uuid4())
            self.primary_key: Optional[str] = None

            # Initialize sheets
            self.sheets = self._load_excel_sheets()
            # Clean data
            self._clean_sheet_data()

        def _load_excel_sheets(self) -> Dict[str, pd.DataFrame]:
            """Load all sheets from Excel file into memory.

            Returns:
                Dictionary mapping sheet names to DataFrames
            """
            excel_file = pd.ExcelFile(self.path)
            sheet_names = [str(name) for name in excel_file.sheet_names]
            sheets = {
                name: pd.read_excel(excel_file, sheet_name=name) for name in sheet_names
            }
            excel_file.close()
            return sheets

        def _clean_sheet_data(self) -> None:
            """Clean all string data in sheets by stripping whitespace.

            This method modifies the sheets in place, removing leading and trailing
            whitespace from all string values in all columns.
            """
            for sheet_name, df in self.sheets.items():
                for column in df.columns:
                    # Only clean string (object) columns
                    if df[column].dtype == "object":
                        # Strip whitespace and handle NaN values
                        self.sheets[sheet_name][column] = df[column].apply(
                            lambda x: x.strip() if isinstance(x, str) else x
                        )

        @staticmethod
        def sanitize_label(label: str) -> str:
            """Sanitize a string to be used as a Neo4j node label."""
            return label.replace(" ", "_").replace("-", "_")

        def read_sheet_names(self) -> List[str]:
            """Get a list of sheet names from the Excel file."""
            return [str(name) for name in pd.ExcelFile(self.path).sheet_names]

        def read_sheet(self, sheet_name: str) -> pd.DataFrame:
            """Get a sheet from the cached sheets dictionary."""
            if sheet_name not in self.sheets:
                raise ValueError(f"Sheet '{sheet_name}' not found in Excel file")
            return self.sheets[sheet_name]

        def validate_data_types(self) -> None:
            """Validates data types across all sheets and raises a TypeInconsistencyError if needed."""
            all_inconsistencies = []
            for sheet_name in self.read_sheet_names():
                df = self.read_sheet(sheet_name)
                checker = DataSanityChecker(
                    df=df, sheet_name=sheet_name, path=self.path, primary_key=None
                )
                inconsistencies = checker.get_all_inconsistencies()
                all_inconsistencies.extend(
                    [
                        TypeInconsistencyLocation(
                            sheet_name=inc.sheet_name,
                            column=inc.column,
                            data_types=inc.data_types,
                            rows=inc.rows,
                            path=inc.path,
                        )
                        for inc in inconsistencies
                    ]
                )
            if all_inconsistencies:
                raise TypeInconsistencyError(all_inconsistencies)

        def build_graph_model(self) -> GraphModel:
            """Builds the graph model. Should only be called after validation passes."""
            nodes = []
            for sheet_name in self.read_sheet_names():
                df = self.read_sheet(sheet_name)
                checker = DataSanityChecker(
                    df=df, sheet_name=sheet_name, path=self.path, primary_key=None
                )
                node = Node(name=sheet_name)

                for column in df.columns:
                    data_type = checker.get_column_type(column)
                    node.add_to_attributes(name=column, data_type=data_type)
                nodes.append(node)

            logger.info(f"Extracted and validated {len(nodes)} nodes of GraphModel")
            return GraphModel(
                nodes=nodes,
            )

        def _validate_sheet_connection(
            self, connection: SheetConnection, sheet_model: SheetModel
        ) -> None:
            """Validate a single sheet connection."""
            logger.debug(f"Connection: {connection}")

            source_sheet = next(
                (
                    sheet
                    for sheet in sheet_model.sheets
                    if sheet.name == connection.source_sheet_name
                ),
                None,
            )
            if source_sheet is None:
                raise ValueError(
                    f"Sheet {connection.source_sheet_name} not found in sheet model"
                )
            if connection.key not in [col.name for col in source_sheet.columns]:
                raise ValueError(
                    f"Key {connection.key} not found in sheet {connection.source_sheet_name}"
                )

            target_sheet = next(
                (
                    sheet
                    for sheet in sheet_model.sheets
                    if sheet.name == connection.target_sheet_name
                ),
                None,
            )
            if target_sheet is None:
                raise ValueError(
                    f"Sheet {connection.target_sheet_name} not found in sheet model"
                )
            if connection.key not in [col.name for col in target_sheet.columns]:
                raise ValueError(
                    f"Key {connection.key} not found in sheet {connection.target_sheet_name}"
                )

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
            self, sheet_model: SheetModel, references: List[SheetReferences]
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
                source_values = self.read_sheet(reference.source_sheet_name)[
                    reference.source_column_name
                ]
                source_values_as_lists = self._parse_source_values(source_values)
                target_values = self.read_sheet(reference.target_sheet_name)[
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

        def validate_graph_model(self, graph_model: GraphModel) -> None:
            """Validates that the data in the sheets conforms to the graph model specifications.

            Args:
                graph_model: The graph model to validate

            Raises:
                ValueError: If validation fails
            """
            sheet_model = self.get_sheet_model()

            # Collect all validation errors
            reference_validation = self._validate_sheet_references(
                sheet_model, graph_model.sheet_references
            )
            connection_validation = self._validate_sheet_connections(
                sheet_model, graph_model.sheet_connections
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

        def extract_to_db(self, db: Database, graph_model: GraphModel) -> None:
            """Extracts the validated data and creates the corresponding graph structure in Neo4j.

            Args:
                db: The database to extract to
                graph_model: The graph model to use for extraction
            """
            logger.info("Starting data extraction to database")

            # Build a mapping of sheet name -> primary key using sheet_connections
            primary_keys = {}
            for connection in graph_model.sheet_connections:
                primary_keys[connection.source_sheet_name] = connection.key
                primary_keys[connection.target_sheet_name] = connection.key

            # Default to first column for sheets without connections
            for name in self.sheets.keys():
                if name not in primary_keys:
                    df = self.sheets[name]
                    primary_keys[name] = df.columns[0]

            logger.info(f"Using primary keys: {primary_keys}")

            with db.driver.session() as session:
                # --- Step 1: Create Nodes ---
                for sheet_name, df in self.sheets.items():
                    label = self.sanitize_label(sheet_name)
                    pk = primary_keys[sheet_name]
                    logger.info(
                        f"Creating nodes for sheet {sheet_name} with label {label} and primary key {pk}"
                    )

                    for _, row in df.iterrows():
                        # Skip rows with NaN primary keys
                        if pd.isna(row[pk]):
                            logger.warning(
                                f"Skipping row with NaN primary key in sheet {sheet_name}"
                            )
                            continue

                        props = row.to_dict()
                        # Remove NaN values
                        props = {k: v for k, v in props.items() if not pd.isna(v)}

                        cypher_query = (
                            f"MERGE (n:{label} {{{pk}: $value}}) SET n += $props"
                        )
                        logger.debug(
                            f"Executing query: {cypher_query} with value={props[pk]}"
                        )
                        session.run(cypher_query, value=props[pk], props=props)

                # --- Step 2: Create Relationships for Sheet Connections ---
                for connection in graph_model.sheet_connections:
                    source_label = self.sanitize_label(connection.source_sheet_name)
                    target_label = self.sanitize_label(connection.target_sheet_name)
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
                for reference in graph_model.sheet_references:
                    source_label = self.sanitize_label(reference.source_sheet_name)
                    target_label = self.sanitize_label(reference.target_sheet_name)
                    source_df = self.sheets[reference.source_sheet_name]
                    # Use the source sheet's primary key from our mapping.
                    source_pk = primary_keys[reference.source_sheet_name]
                    # Generate a relationship type; here we use the source column name.
                    relationship_type = reference.source_column_name.upper()

                    logger.info(
                        f"Creating reference relationships: {reference.source_sheet_name}.{reference.source_column_name} -> "
                        f"{reference.target_sheet_name}.{reference.target_column_name}"
                    )

                    for _, row in source_df.iterrows():
                        source_node_id = row[source_pk]
                        # Skip rows with NaN primary keys
                        if pd.isna(source_node_id):
                            logger.warning(
                                f"Skipping row with NaN primary key {source_pk} in sheet {reference.source_sheet_name}"
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
                                f"MATCH (s:{source_label} {{{source_pk}: $source_id}}), "
                                f"(t:{target_label} {{{reference.target_column_name}: $target_value}}) "
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

        def extract_to_database(self, db: Database, graph_model: GraphModel) -> None:
            """Validates the data against the graph model and extracts it to the database.

            Args:
                db: The database to extract to
                graph_model: The graph model to use for extraction
            """
            logger.info(f"Starting extraction process for file: {self.path}")
            logger.info(
                f"Graph model: {len(graph_model.sheet_connections)} connections, {len(graph_model.sheet_references)} references"
            )

            try:
                # Validate the graph model
                self.validate_graph_model(graph_model)
                # Extract data to database
                self.extract_to_db(db=db, graph_model=graph_model)
                logger.info("Extraction completed successfully")
            except Exception as e:
                logger.error(f"Error during extraction: {str(e)}")
                raise

    @staticmethod
    def save_graph_model(graph_model: Dict[str, Any], db_name: str = "default") -> None:
        """Save the graph model to the database configuration.

        Args:
            graph_model: The graph model data
            db_name: The name of the database to save to
        """
        try:
            # Get the database info
            db_info = ConfigService.get_database(db_name)
            if not db_info:
                logger.warning(
                    f"Database {db_name} not found, creating new database configuration"
                )
                # Create a new database configuration
                return

            # Update the database with the graph model
            graph_model_obj = GraphModel(**graph_model)
            db_info.graph_model = graph_model_obj

            # Update the database
            ConfigService.update_database(db_info.name, db_info)
            logger.info(f"Graph model saved to database configuration for {db_name}")
        except Exception as e:
            logger.error(f"Error saving graph model: {str(e)}")
            raise

    @staticmethod
    def load_graph_model(db_name: str = "default") -> Optional[Dict[str, Any]]:
        """Load the graph model from the database configuration.

        Args:
            db_name: The name of the database to load from

        Returns:
            The graph model data or None if not found
        """
        try:
            # Get the database info
            db_info = ConfigService.get_database(db_name)
            if not db_info or not db_info.graph_model:
                logger.warning(f"No graph model found for database {db_name}")
                return None

            # Return the graph model
            return db_info.graph_model.model_dump(mode="json")
        except Exception as e:
            logger.error(f"Error loading graph model: {str(e)}")
            return None

    @staticmethod
    async def process_file(
        file_path: str, graph_model_data: Dict[str, Any], db_name: str = "default"
    ) -> None:
        """Process a file with the given graph model and extract it to the database.

        Args:
            file_path: Path to the file to process
            graph_model_data: The graph model data
            db_name: The name of the database to extract to

        Raises:
            ValueError: If the database is not configured
            HTTPException: If there is an error during processing
        """
        try:
            # Get the database configuration
            db_info = ConfigService.get_database(db_name)
            if not db_info:
                raise ValueError(f"Database {db_name} not configured")

            # Create database connection
            db = Database(
                uri=db_info.uri, user=db_info.username, password=db_info.password
            )
            logger.debug("Database connection established")

            # Create graph model
            graph_model = GraphModel(
                sheet_connections=graph_model_data.get("sheet_connections", []),
                sheet_references=graph_model_data.get("sheet_references", []),
            )

            # Create extractor and process file
            extractor = SpreadsheetService.SheetExtractor(path=file_path)
            extractor.extract_to_database(db=db, graph_model=graph_model)

            # Save graph model to configuration
            SpreadsheetService.save_graph_model(graph_model_data, db_name)

            logger.info("File processed and data extracted to database successfully")
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            raise

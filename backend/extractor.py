import uuid
from typing import List, Optional

import pandas as pd
from loguru import logger

from .data_sanity import DataSanityChecker
from .exceptions import (
    TypeInconsistencyError,
    TypeInconsistencyLocation,
)
from .models.error_model import (
    GraphValidationError,
    GraphValidationResult,
)
from .models.graph_model import GraphModel, SheetConnection, SheetReferences
from .models.sheet_model import Column, Sheet, SheetModel
from .services.db_service import Database


class Extractor:
    def __init__(self, path: str):
        self.path = path
        self.batch_id = str(uuid.uuid4())
        self.primary_key: Optional[str] = None

        # Initialize sheets
        self.sheets = self._load_excel_sheets()
        # Clean data
        self._clean_sheet_data()

    def _load_excel_sheets(self) -> dict[str, pd.DataFrame]:
        """Load all sheets from Excel file into memory.

        Returns:
            Tuple containing:
            - Dictionary mapping sheet names to DataFrames
            - List of sheet names
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
        return [str(name) for name in pd.ExcelFile(self.path).sheet_names]

    def read_sheet(self, sheet_name: str) -> pd.DataFrame:
        """Get a sheet from the cached sheets dictionary."""
        if sheet_name not in self.sheets:
            raise ValueError(f"Sheet '{sheet_name}' not found in Excel file")
        return self.sheets[sheet_name]

    def extract_file(self):
        for sheet_name in self.sheet_names:
            self.extract_sheet(sheet_name)

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

    def build_sheet_model(self) -> SheetModel:
        """Builds the sheet model. Should only be called after validation passes."""
        sheets = []
        for sheet_name in self.read_sheet_names():
        df = self.read_sheet(sheet_name)
            checker = DataSanityChecker(
                df=df, sheet_name=sheet_name, path=self.path, primary_key=None
            )
            columns = []
            for column in df.columns:
                data_type = checker.get_column_type(column)
                columns.append(Column(name=column, data_type=data_type))
            sheet = Sheet(name=sheet_name, columns=columns)
            sheets.append(sheet)
        return SheetModel(sheets=sheets)

    def get_sheet_model(self) -> SheetModel:
        """Gets the sheet model after validating data types."""
        self.validate_data_types()
        return self.build_sheet_model()

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

    def _validate_reference_values(
        self,
        reference: SheetReferences,
        source_values_as_lists: List[List[str]],
        target_values: pd.Series,
    ) -> None:
        """Validate that all source values exist in target values."""
        for row_id, values in enumerate(source_values_as_lists):
            if not values:
                continue
            if any(v not in target_values.values for v in values):
                raise ValueError(
                    f"Value {values} in row {row_id + 2} in source column {reference.source_column_name} "
                    f"of sheet {reference.source_sheet_name} not found in target column {reference.target_column_name} "
                    f"of sheet {reference.target_sheet_name}"
                )

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

    def _validate_sheet_connection(
        self, connection: SheetConnection, sheet_model: SheetModel
    ) -> None:
        """Validate a single sheet connection."""
        logger.debug(f"Connection: {connection}")
        logger.debug(f"Sheet model: {sheet_model}")
        source_sheet = next(
            (
                sheet
                for sheet in sheet_model.sheets
                if sheet.name == connection.source_sheet_name
            ),
            None,
        )
        logger.debug(f"Source sheet: {source_sheet}")
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

    def validate_graph_model(self, graph_model: GraphModel) -> None:
        """
        Validates that the data in the sheets conforms to the graph model specifications.
        Collects all validation errors before raising them.
        """
        sheet_model = self.get_sheet_model()

        import json

        with open("dev_examples/sheet_model.json", "w") as f:
            json.dump(sheet_model.model_dump(), f, indent=2, ensure_ascii=False)

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
        """
        Extracts the validated data and creates the corresponding graph structure in Neo4j.
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
                    props = row.to_dict()
                    cypher_query = f"MERGE (n:{label} {{{pk}: $value}}) SET n += $props"
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
                relationship_type = reference.source_column_name

                logger.info(
                    f"Creating reference relationships: {reference.source_sheet_name}.{reference.source_column_name} -> "
                    f"{reference.target_sheet_name}.{reference.target_column_name}"
                )

                for _, row in source_df.iterrows():
                    source_node_id = row[source_pk]
                    cell_value = row[reference.source_column_name]
                    tokens = [
                        v.strip() for v in str(cell_value).split(",") if v.strip()
                    ]

                    if not tokens:
                        logger.warning(
                            f"No valid tokens found in {cell_value} for row with pk={source_node_id}"
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
                            cypher_query, source_id=source_node_id, target_value=token
                        )

        logger.info("Data extraction completed successfully")

    def new_extract(self, db: Database, graph_model: GraphModel) -> None:
        """
        Validates the data against the graph model and extracts it to the database.
        """
        logger.info(f"Starting extraction process for file: {self.path}")
        logger.info(
            f"Graph model: {len(graph_model.sheet_connections)} connections, {len(graph_model.sheet_references)} references"
        )


if __name__ == "__main__":
    path = "/Users/max/Downloads/EnzymeML_MODAMDH_cyclohexanone.xlsx"
    extractor = Extractor(path=path)

    sheet_connections = [
        SheetConnection(
            source_sheet_name="Reaction",
            target_sheet_name="Biocatalyst",
            edge_name="catalyzed_by",
            key="well_id",
        ),
        SheetConnection(
            source_sheet_name="Reaction",
            target_sheet_name="Peak",
            edge_name="was_assayed_in",
            key="well_id",
        ),
    ]

    sheet_references = [
        SheetReferences(
            source_sheet_name="Reaction",
            source_column_name="has_substrate",
            target_sheet_name="Molecule",
            target_column_name="name",
        ),
        SheetReferences(
            source_sheet_name="Reaction",
            source_column_name="has_product",
            target_sheet_name="Molecule",
            target_column_name="name",
        ),
        SheetReferences(
            source_sheet_name="Reaction",
            source_column_name="has_solvent",
            target_sheet_name="Molecule",
            target_column_name="name",
        ),
        SheetReferences(
            source_sheet_name="Reaction",
            source_column_name="was_sampled",
            target_sheet_name="Sampling",
            target_column_name="name",
        ),
        SheetReferences(
            source_sheet_name="Peak",
            source_column_name="detected_molecule",
            target_sheet_name="Molecule",
            target_column_name="name",
        ),
        SheetReferences(
            source_sheet_name="Biocatalyst",
            source_column_name="is_enzyme",
            target_sheet_name="Enzyme",
            target_column_name="database_id",
        ),
    ]

    model = GraphModel(
        sheet_connections=sheet_connections,
        sheet_references=sheet_references,
    )

    import json

    with open("dev_examples/graph_model.json", "w") as f:
        json.dump(model.model_dump(), f, indent=2, ensure_ascii=False)

    db = Database(
        uri="bolt://localhost:7692",
        user="neo4j",
        password="12345678",
    )

    # test query to check the correct db is connected: get all node names

    extractor.new_extract(db=db, graph_model=model)

    query = "MATCH (n) RETURN DISTINCT labels(n)"
    with db.driver.session() as session:
        result = session.run(query)
        for record in result:
            print(record["labels(n)"])

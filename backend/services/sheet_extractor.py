import uuid
from typing import Dict, List

import pandas as pd

from backend.data_sanity import DataSanityChecker
from backend.exceptions import TypeInconsistencyError, TypeInconsistencyLocation
from backend.models.model import (
    Column,
    Sheet,
    SheetConnection,
    SheetModel,
    SheetReference,
)


class SheetModelBuilder:
    """Cleans and validates sheet data and defined connections and references."""

    def __init__(self, path: str):
        """Initialize the SheetExtractor.

        Args:
            path: Path to the Excel file
        """
        self.path = path
        self.batch_id = str(uuid.uuid4())

        # Initialize sheets
        self.sheets = self._load_excel_sheets()
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
                        lambda x: x.strip().rstrip(",") if isinstance(x, str) else x
                    )

    def validate_spreadsheet_data(self) -> List[TypeInconsistencyLocation]:
        """Validates the data types and consistency within the spreadsheet.

        This method checks for type inconsistencies within each column of each sheet.

        Returns:
            List of type inconsistency locations, empty if no issues found

        Raises:
            No exceptions - collects and returns all inconsistencies
        """
        all_inconsistencies = []
        for sheet_name, df in self.sheets.items():
            checker = DataSanityChecker(df=df, sheet_name=sheet_name, path=self.path)
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
        return all_inconsistencies

    def get_sheets(self) -> List[Sheet]:
        """Get the sheets from the spreadsheet.

        Returns:
            List of sheets
        """
        sheets = []
        for sheet_name, df in self.sheets.items():
            checker = DataSanityChecker(df=df, sheet_name=sheet_name, path=self.path)
            columns = []
            for column in df.columns:
                data_type = checker.get_column_type(column)
                columns.append(Column(name=column, data_type=data_type))
            sheets.append(Sheet(name=sheet_name, columns=columns))

        return sheets

    def validate_relations(
        self,
        sheet_connections: List[SheetConnection],
        sheet_references: List[SheetReference],
    ) -> List[str]:
        """Validates if the defined relations are consistent with the spreadsheet structure.

        This method checks if all referenced sheets and columns exist in the spreadsheet.

        Args:
            sheet_connections: List of sheet connections to validate
            sheet_references: List of sheet references to validate

        Returns:
            List of validation error messages, empty if all valid

        Raises:
            No exceptions - collects and returns all inconsistencies
        """
        errors = []
        # Create a mapping of sheet names to their column sets for quick lookup
        sheets_dict = {
            sheet_name: set(df.columns) for sheet_name, df in self.sheets.items()
        }

        # Validate sheet connections
        for conn in sheet_connections:
            if conn.source_sheet_name not in sheets_dict:
                errors.append(
                    f"Source sheet '{conn.source_sheet_name}' not found for edge '{conn.edge_name}'."
                )
            else:
                if conn.key not in sheets_dict[conn.source_sheet_name]:
                    errors.append(
                        f"Key '{conn.key}' not found in source sheet '{conn.source_sheet_name}' for edge '{conn.edge_name}'."
                    )
            if conn.target_sheet_name not in sheets_dict:
                errors.append(
                    f"Target sheet '{conn.target_sheet_name}' not found for edge '{conn.edge_name}'."
                )
            else:
                if conn.key not in sheets_dict[conn.target_sheet_name]:
                    errors.append(
                        f"Key '{conn.key}' not found in target sheet '{conn.target_sheet_name}' for edge '{conn.edge_name}'."
                    )

        # Validate sheet references
        for ref in sheet_references:
            if ref.source_sheet_name not in sheets_dict:
                errors.append(
                    f"Source sheet '{ref.source_sheet_name}' not found for reference from column '{ref.source_column_name}'."
                )
            else:
                if ref.source_column_name not in sheets_dict[ref.source_sheet_name]:
                    errors.append(
                        f"Column '{ref.source_column_name}' not found in sheet '{ref.source_sheet_name}'."
                    )
            if ref.target_sheet_name not in sheets_dict:
                errors.append(
                    f"Target sheet '{ref.target_sheet_name}' not found for reference to column '{ref.target_column_name}'."
                )
            else:
                if ref.target_column_name not in sheets_dict[ref.target_sheet_name]:
                    errors.append(
                        f"Column '{ref.target_column_name}' not found in sheet '{ref.target_sheet_name}'."
                    )

        return errors

    def build_sheet_model(
        self,
        sheet_connections: List[SheetConnection],
        sheet_references: List[SheetReference],
    ) -> SheetModel:
        """Builds the sheet model based on the excel file and the specified sheet connections and references.

        Args:
            sheet_connections: List of sheet connections
            sheet_references: List of sheet references

        Returns:
            SheetModel

        Raises:
            TypeInconsistencyError: If there are type inconsistencies in the data
            ValueError: If there are validation errors in the sheet model
        """
        # Validate data types and consistency within the spreadsheet
        inconsistencies = self.validate_spreadsheet_data()
        if inconsistencies:
            raise TypeInconsistencyError(inconsistencies)

        # Create sheets with proper data types
        sheets = []
        for sheet_name, df in self.sheets.items():
            checker = DataSanityChecker(df=df, sheet_name=sheet_name, path=self.path)
            columns = []
            for column in df.columns:
                data_type = checker.get_column_type(column)
                columns.append(Column(name=column, data_type=data_type))
            sheets.append(Sheet(name=sheet_name, columns=columns))

        # Create the model
        model = SheetModel(
            sheets=sheets,
            sheet_connections=sheet_connections,
            sheet_references=sheet_references,
        )

        # Validate relations against the model
        errors = self.validate_relations(sheet_connections, sheet_references)
        if errors:
            raise ValueError("Sheet model validation errors:\n" + "\n".join(errors))

        return model

    def validate_sheet_model(self, sheet_model: SheetModel) -> List[str]:
        """Legacy method that validates a sheet model against the loaded spreadsheet.

        This is a convenience method that extracts connections and references from
        the sheet model and passes them to validate_relations.

        Args:
            sheet_model: The sheet model to validate

        Returns:
            List of validation error messages, empty if all valid
        """
        return self.validate_relations(
            sheet_model.sheet_connections, sheet_model.sheet_references
        )

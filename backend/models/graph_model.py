from pydantic import BaseModel

from .appconfig import Column, Sheet, SheetModel


class SheetConnection(BaseModel):
    """
    A connection between two sheets indicated by the same key.
    """

    source_sheet_name: str
    target_sheet_name: str
    edge_name: str
    key: str


class SheetReferences(BaseModel):
    """
    A reference between two columns between two sheets.
    """

    source_sheet_name: str
    source_column_name: str
    target_sheet_name: str
    target_column_name: str

    def find_sheet_in_model(self, sheet_name: str, sheet_model: SheetModel) -> Sheet:
        """Find a sheet by name in the sheet model or raise ValueError if not found."""
        sheet_match = next(
            (sheet for sheet in sheet_model.sheets if sheet.name == sheet_name),
            None,
        )
        if sheet_match is None:
            raise ValueError(f"Sheet {sheet_name} not found in sheet model")
        return sheet_match

    def find_column_in_sheet(self, column_name: str, sheet: Sheet) -> Column:
        """Find a column by name in the sheet or raise ValueError if not found."""
        column_match = next(
            (column for column in sheet.columns if column.name == column_name),
            None,
        )
        if column_match is None:
            raise ValueError(f"Column {column_name} not found in sheet {sheet.name}")
        return column_match

    def compare_to_sheet(self, sheet_model: SheetModel) -> None:
        """Validate that the referenced sheets and columns exist in the sheet model."""
        # Find and validate source sheet and column
        source_sheet = self.find_sheet_in_model(self.source_sheet_name, sheet_model)
        self.find_column_in_sheet(self.source_column_name, source_sheet)

        # Find and validate target sheet and column
        target_sheet = self.find_sheet_in_model(self.target_sheet_name, sheet_model)
        self.find_column_in_sheet(self.target_column_name, target_sheet)


class GraphModel(BaseModel):
    """
    A collection of connections and references between sheets.
    """

    sheet_connections: list[SheetConnection]
    sheet_references: list[SheetReferences]

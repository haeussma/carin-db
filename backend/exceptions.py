# exceptions.py
from dataclasses import asdict, dataclass
from typing import List


@dataclass
class SheetNameError:
    sheet_name: str
    path: str


@dataclass
class ColumnNameError:
    sheet_name: str
    column: str
    path: str


@dataclass
class ColumnTypeInconsistency:
    sheet_name: str
    column: str
    first_inconsistency: int  # 0-based row index
    path: str


class SpreadsheetValidationError(Exception):
    def __init__(
        self,
        sheet_name_errors: List[SheetNameError],
        column_name_errors: List[ColumnNameError],
        column_type_inconsistencies: List[ColumnTypeInconsistency],
    ):
        self.sheet_name_errors = sheet_name_errors
        self.column_name_errors = column_name_errors
        self.column_type_inconsistencies = column_type_inconsistencies
        super().__init__("Spreadsheet validation failed")

    def to_dict(self) -> dict:
        return {
            "error": "spreadsheet_validation",
            "message": str(self),
            "sheet_name_errors": [asdict(e) for e in self.sheet_name_errors],
            "column_name_errors": [asdict(e) for e in self.column_name_errors],
            "column_type_inconsistencies": [
                asdict(e) for e in self.column_type_inconsistencies
            ],
        }

from typing import List

from pydantic import BaseModel


class TypeInconsistency(BaseModel):
    column: str
    sheet_name: str
    data_types: list[str]
    rows: list[int]
    path: str


class GraphValidationError(BaseModel):
    error_type: str
    sheet_name: str
    message: str


class GraphValidationResult(BaseModel):
    missing_sheets: List[GraphValidationError]
    missing_columns: List[GraphValidationError]
    missing_values: List[GraphValidationError]

    def has_errors(self) -> bool:
        return bool(self.missing_sheets or self.missing_columns or self.missing_values)

    def format_error_message(self) -> str:
        messages = []
        if self.missing_sheets:
            messages.append("\nMissing Sheets:")
            for error in self.missing_sheets:
                messages.append(f"  - {error.message}")

        if self.missing_columns:
            messages.append("\nMissing Columns:")
            for error in self.missing_columns:
                messages.append(f"  - {error.message}")

        if self.missing_values:
            messages.append("\nMissing Values:")
            for error in self.missing_values:
                messages.append(f"  - {error.message}")

        return "\n".join(messages)

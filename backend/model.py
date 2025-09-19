from __future__ import annotations

import keyword
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal, Optional, Union

import numpy as np
import pandas as pd
from loguru import logger
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from .exceptions import (
    ColumnNameError,
    ColumnTypeInconsistency,
    SheetNameError,
    SpreadsheetValidationError,
)

# ---------- Validation utilities ----------


def _classify_value(x) -> str:
    """Classify a value by its type for consistency checking."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "na"
    if isinstance(x, (bool, np.bool_)):
        return "bool"
    if isinstance(x, (np.integer, int)) and not isinstance(x, (bool, np.bool_)):
        return "int"
    if isinstance(x, (np.floating, float)):
        return "float"
    if isinstance(x, (pd.Timestamp, datetime)):
        return "datetime"
    if isinstance(x, str):
        return "str"
    return "object"


def first_inconsistency_idx(series: pd.Series) -> int | None:
    """Find the first index where a series has inconsistent types."""
    v = series.dropna()
    if v.empty:
        return None
    cats = v.map(
        lambda x: "number"
        if _classify_value(x) in {"int", "float"}
        else _classify_value(x)
    )
    base = cats.iloc[0]
    mask = cats != base
    if mask.any():
        return int(mask.idxmax())
    return None


def is_valid_name(name: str) -> bool:
    """Check if a name is valid (Python identifier, not keyword)."""
    if keyword.iskeyword(name):
        return False
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name) is not None


# ---------- Enums ----------


class ScalarType(str, Enum):
    STR = "str"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    TIMESTAMP = "timestamp"


class CaseMode(str, Enum):
    SENSITIVE = "sensitive"
    INSENSITIVE = "insensitive"


class OnMissMode(str, Enum):
    ERROR = "error"
    SKIP = "skip"
    CREATE = "create"


# ---------- Simple value objects ----------


class MultiSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sep: str
    trim: bool
    allow_empty: bool


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float
    y: float


# ---------- Properties (discriminated union) ----------


class ValueProperty(BaseModel):
    model_config = ConfigDict(
        extra="forbid", use_enum_values=True, arbitrary_types_allowed=True
    )

    kind: Literal["value"] = "value"
    name: str
    dtype: ScalarType
    unique: bool = False
    # Optional: store validation context for better error reporting
    _sheet_name: Optional[str] = PrivateAttr(default=None)
    _column_data: Optional[pd.Series] = PrivateAttr(default=None)
    _file_path: Optional[str] = PrivateAttr(default=None)

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        """Validate and clean the property name."""
        cleaned = v.strip()
        if not is_valid_name(cleaned):
            raise ValueError(
                f"Invalid property name: '{v}'. Names must be valid Python identifiers and not keywords."
            )
        return cleaned

    @model_validator(mode="after")
    def validate_column_consistency(self) -> "ValueProperty":
        """Validate column type consistency if column data is provided."""
        if self._column_data is not None:
            inc = first_inconsistency_idx(self._column_data)
            if inc is not None:
                sheet_name = self._sheet_name
                file_path = self._file_path
                raise ValueError(
                    f"Column type inconsistency in sheet '{sheet_name}', column '{self.name}' at row {inc + 2} in file {file_path}"
                )
        return self


class RefProperty(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    kind: Literal["ref"] = "ref"
    name: str
    to: str
    on: str
    edge: str
    multi: Optional[MultiSpec] = None
    case: CaseMode
    on_miss: OnMissMode
    unique: bool

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        """Remove leading and trailing whitespace from the name."""
        return v.strip()


PropertyValue = Annotated[
    Union[ValueProperty, RefProperty], Field(discriminator="kind")
]


# ---------- Core graph objects ----------
class SheetNode(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    name: str
    properties: list[PropertyValue]
    position: Optional[Position] = None

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        """Validate and clean the sheet name."""
        cleaned = v.strip()
        if not is_valid_name(cleaned):
            raise ValueError(
                f"Invalid sheet name: '{v}'. Names must be valid Python identifiers and not keywords."
            )
        return cleaned


class GraphSheetModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    project_name: str
    sheets: list[SheetNode] = Field(default_factory=list)
    created_at: datetime
    last_modified: datetime

    @classmethod
    def from_spreadsheet_data(
        cls,
        project_name: str,
        sheets_data: dict[str, pd.DataFrame],
        file_path: str,
    ) -> GraphSheetModel:
        """Create a GraphSheetModel from spreadsheet data, collecting validation errors.

        Args:
            project_name: Name of the project
            sheets_data: Dictionary of sheet name to DataFrame
            file_path: Path to the source file for error reporting

        Returns:
            Tuple of (model, validation_error). If validation_error is not None,
            the model creation failed and should not be used.
        """
        sheet_name_errors = []
        column_name_errors = []
        column_type_inconsistencies = []

        sheets = []

        for sheet_name, df in sheets_data.items():
            try:
                # Try to create the sheet node
                properties: list[PropertyValue] = []

                for col in df.columns:
                    try:
                        # Get series type
                        dtype = cls._get_series_type(df[col])
                        print(f"Column {col} has dtype {dtype}")

                        # Try to create property with validation context
                        prop = ValueProperty(
                            name=str(col),
                            dtype=dtype,
                        )
                        # Set private attributes after creation
                        prop._sheet_name = sheet_name
                        prop._column_data = df[col]
                        prop._file_path = file_path
                        logger.debug(f"Adding property: {prop.name}")
                        properties.append(prop)

                    except ValueError as e:
                        # Check if it's a column name error or type inconsistency
                        error_msg = str(e)
                        print(f"Error: {error_msg}")
                        if "Invalid property name" in error_msg:
                            column_name_errors.append(
                                ColumnNameError(sheet_name, str(col), file_path)
                            )
                        elif "Column type inconsistency" in error_msg:
                            # Extract row number from error message
                            inc = first_inconsistency_idx(df[col])
                            if inc is not None:
                                column_type_inconsistencies.append(
                                    ColumnTypeInconsistency(
                                        sheet_name, str(col), inc + 2, file_path
                                    )
                                )

                # Try to create sheet node
                sheet = SheetNode(name=sheet_name, properties=properties, position=None)
                sheets.append(sheet)

            except ValueError as e:
                # Sheet name validation error

                if "Invalid sheet name" in str(e):
                    sheet_name_errors.append(SheetNameError(sheet_name, file_path))

        # If there are validation errors, return them
        if sheet_name_errors or column_name_errors or column_type_inconsistencies:
            raise SpreadsheetValidationError(
                sheet_name_errors,
                column_name_errors,
                column_type_inconsistencies,
            )

        return cls(
            project_name=project_name,
            created_at=datetime.now(timezone.utc),
            last_modified=datetime.now(timezone.utc),
            sheets=sheets,
        )

    @staticmethod
    def _get_series_type(series: pd.Series) -> ScalarType:
        """Determine the scalar type of a pandas Series."""
        if pd.api.types.is_bool_dtype(series):
            return ScalarType.BOOL
        if pd.api.types.is_datetime64_any_dtype(series):
            return ScalarType.TIMESTAMP
        if pd.api.types.is_integer_dtype(series):
            return ScalarType.INT
        if pd.api.types.is_float_dtype(series) or pd.api.types.is_numeric_dtype(series):
            return ScalarType.FLOAT
        return ScalarType.STR


if __name__ == "__main__":
    from rich import print

    from .spreadsheet import load_sheets

    path = "test_data/genoscope/Genoscope_reaction4.xlsx"
    sheets = load_sheets(path)
    project = GraphSheetModel.from_spreadsheet_data(
        project_name="test", sheets_data=sheets, file_path=path
    )
    print(project)

# spreadsheet.py (only changed bits)
from __future__ import annotations

import keyword
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .exceptions import (
    ColumnNameError,
    ColumnTypeInconsistency,
    SheetNameError,
    SpreadsheetValidationError,
)
from .model import GraphSheetModel, Project, ScalarType, SheetNode, ValueProperty


class Spreadsheet:
    def __init__(self, path: str):
        self.path: Path = Path(path)
        self.sheets: dict[str, pd.DataFrame] = self.load_sheets()
        self.validation_error: SpreadsheetValidationError | None = self.validate()

        # raise an error if the spreadsheet is invalid
        if self.validation_error:
            raise self.validation_error

    def load_sheets(self) -> dict[str, pd.DataFrame]:
        sheets: dict[str, pd.DataFrame] = {}
        with pd.ExcelFile(self.path) as xf:
            for sheet_name in map(str, xf.sheet_names):
                sheets[sheet_name] = xf.parse(sheet_name)
        return sheets

    def validate(self) -> SpreadsheetValidationError | None:
        sheet_name_errors: list[SheetNameError] = []
        column_name_errors: list[ColumnNameError] = []
        column_type_inconsistencies: list[ColumnTypeInconsistency] = []

        path_str = str(self.path)

        # validate sheet names
        for sheet_name, df in self.sheets.items():
            if not is_valid_name(sheet_name):
                sheet_name_errors.append(SheetNameError(sheet_name, path_str))

            # validate column names
            for column in df.columns:
                if not is_valid_name(str(column)):
                    column_name_errors.append(
                        ColumnNameError(sheet_name, str(column), path_str)
                    )

                # validate column types
                inc = first_inconsistency_idx(df[column])
                if inc is not None:
                    column_type_inconsistencies.append(
                        ColumnTypeInconsistency(
                            sheet_name, str(column), inc + 2, path_str
                        )
                    )

        if sheet_name_errors or column_name_errors or column_type_inconsistencies:
            return SpreadsheetValidationError(
                sheet_name_errors, column_name_errors, column_type_inconsistencies
            )
        return None

    def get_series_type(self, series: pd.Series, _sheet_name: str) -> ScalarType:
        if pd.api.types.is_bool_dtype(series):
            return ScalarType.BOOL
        if pd.api.types.is_datetime64_any_dtype(series):
            return ScalarType.TIMESTAMP
        if pd.api.types.is_integer_dtype(series):
            return ScalarType.INT
        if pd.api.types.is_float_dtype(series) or pd.api.types.is_numeric_dtype(series):
            return ScalarType.FLOAT
        return ScalarType.STR

    def to_project(self, project_name: str) -> Project:
        """Convert the spreadsheet to a project.

        Args:
            project_name: The name of the project

        Returns:
            Project
        """
        sheets: list[SheetNode] = []
        for sheet_name, df in self.sheets.items():
            sheet = SheetNode(name=sheet_name, properties=[], position=None)
            for col in df.columns:
                prop = ValueProperty(
                    name=str(col), dtype=self.get_series_type(df[col], sheet_name)
                )
                sheet.properties.append(prop)
            sheets.append(sheet)

        return Project(
            name=project_name,
            model=GraphSheetModel(
                project_name=project_name,
                created_at=datetime.now(timezone.utc),
                sheets=sheets,
            ),
            last_modified=datetime.now(timezone.utc),
        )


# --- utilities ---


def _classify_value(x) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):  # we dropna upstream anyway
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


def type_consistent(series: pd.Series) -> bool:
    v = series.dropna()
    if v.empty:
        return True
    kinds = {
        ("number" if _classify_value(x) in {"int", "float"} else _classify_value(x))
        for x in v
    }
    return len(kinds) == 1


def first_inconsistency_idx(series: pd.Series) -> int | None:
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
    if not isinstance(name, str):
        return False
    if keyword.iskeyword(name):
        return False
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name) is not None


if __name__ == "__main__":
    from rich import print

    path = "test_data/genoscope/test.xlsx"
    project_name = "test"
    try:
        spreadsheet = Spreadsheet(path)
        print(spreadsheet.to_project(project_name))
    except SpreadsheetValidationError as e:
        print(e.to_dict())

        # 2) Direct attribute access
        for err in e.sheet_name_errors:
            print(f"[red]Bad sheet name[/]: {err.sheet_name}  ({err.path})")

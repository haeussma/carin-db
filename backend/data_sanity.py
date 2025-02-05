from dataclasses import dataclass
from typing import List

import pandas as pd

from .exceptions import (
    PrimaryKeyNotFoundInRowError,
    PrimaryKeyNotUniqueError,
)


@dataclass
class TypeInconsistency:
    column: str
    sheet_name: str
    data_types: List[str]
    rows: List[int]
    path: str


class DataSanityChecker:
    def __init__(
        self,
        df: pd.DataFrame,
        sheet_name: str,
        path: str,
        primary_key: str | None,
    ):
        self.df = df
        self.sheet_name = sheet_name
        self.path = path
        self.primary_key = primary_key
        self.inconsistencies: List[TypeInconsistency] = []

    def detect_column_types(self, column: str) -> set[str]:
        """
        Detects the unique data types in a column, ignoring empty cells.
        Returns a set of type names found in the column.
        """
        non_empty_values = self.df[column][pd.notna(self.df[column])]
        return set(non_empty_values.apply(lambda x: type(x).__name__).unique())

    def check_column_type_consistency(self, column: str) -> bool:
        """
        Checks if a column has consistent types, allowing int/float mixing.
        Returns True if types are consistent, False otherwise.
        Also records any inconsistencies found.
        """
        data_types = self.detect_column_types(column)
        numeric_types = {"int", "float"}

        # Check if we have both numeric and non-numeric types
        has_numeric = any(t in numeric_types for t in data_types)
        has_non_numeric = any(t not in numeric_types for t in data_types)

        if has_numeric and has_non_numeric:
            # Find rows with non-numeric types
            non_empty_values = self.df[column][pd.notna(self.df[column])]
            inconsistent_rows = non_empty_values[
                ~non_empty_values.apply(lambda x: type(x).__name__ in numeric_types)
            ].index.tolist()
            inconsistent_rows = [row + 2 for row in inconsistent_rows]

            self.inconsistencies.append(
                TypeInconsistency(
                    column=column,
                    sheet_name=self.sheet_name,
                    data_types=list(data_types),
                    rows=inconsistent_rows,
                    path=self.path,
                )
            )
            return False
        return True

    def get_column_type(self, column: str) -> str:
        """
        Gets the primary type for a column after checking consistency.
        For numeric columns (int/float), always returns 'float'.
        For other columns, returns the first non-numeric type found or falls back to 'str'.
        """
        data_types = self.detect_column_types(column)
        numeric_types = {"int", "float"}

        # If we have any numeric types, treat as float
        if any(t in numeric_types for t in data_types):
            return "float"

        # Otherwise return first type found or fallback to str
        return next(iter(data_types)) if data_types else "str"

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

    def eliminate_space_in_column_names(self):
        """Replace all spaces in column names with underscores"""
        self.df.columns = self.df.columns.str.replace(" ", "_")

    def get_all_inconsistencies(self) -> List[TypeInconsistency]:
        """
        Checks all columns for type inconsistencies and returns a list of all found inconsistencies.
        """
        self.inconsistencies = []  # Clear previous inconsistencies

        for column in self.df.columns:
            self.check_column_type_consistency(column)

        return self.inconsistencies

from dataclasses import dataclass
from typing import List

import pandas as pd


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
    ):
        self.df = df
        self.sheet_name = sheet_name
        self.path = path
        self.inconsistencies: List[TypeInconsistency] = []

    def check_column_type_consistency(self, column: str) -> bool:
        """
        Checks if a column has consistent types, allowing int/float mixing.
        Returns True if types are consistent, False otherwise.
        Also records any inconsistencies found.
        """
        # Get non-empty values and their types
        non_empty_values = self.df[column][pd.notna(self.df[column])]
        data_types = set(non_empty_values.apply(lambda x: type(x).__name__).unique())

        # Define allowed type groups
        numeric_types = {"int", "float"}

        # Check for type inconsistencies
        has_numeric = any(t in numeric_types for t in data_types)
        non_numeric_types = {t for t in data_types if t not in numeric_types}

        # Case 1: Mixing numeric with non-numeric types
        if has_numeric and non_numeric_types:
            # Find rows with non-numeric types
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

        # Case 2: Mixing different non-numeric types
        if len(non_numeric_types) > 1:
            # Find rows with types different from the first non-numeric type
            first_type = next(iter(non_numeric_types))
            inconsistent_rows = non_empty_values[
                ~non_empty_values.apply(lambda x: type(x).__name__ == first_type)
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
        non_empty_values = self.df[column][pd.notna(self.df[column])]
        data_types = set(non_empty_values.apply(lambda x: type(x).__name__).unique())
        numeric_types = {"int", "float"}

        # If we have any numeric types, treat as float
        if any(t in numeric_types for t in data_types):
            return "float"

        # Otherwise return first type found or fallback to str
        return next(iter(data_types)) if data_types else "str"

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


if __name__ == "__main__":
    df = pd.read_excel("test_data/genoscope/test.xlsx", sheet_name="reaction")
    checker = DataSanityChecker(df, "reaction", "test_data/genoscope/test.xlsx")
    print(checker.check_column_type_consistency("success"))
    print(checker.inconsistencies)

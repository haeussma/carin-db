from typing import List

import pandas as pd

from backend.exceptions import (
    InconsistentDataError,
    PrimaryKeyNotFoundInRowError,
    PrimaryKeyNotUniqueError,
)


class DataSanityChecker:
    def __init__(
        self,
        df: pd.DataFrame,
        sheet_name: str,
        path: str,
        primary_key: str,
    ):
        self.df = df
        self.sheet_name = sheet_name
        self.path = path
        self.primary_key = primary_key

    def check_data_types(self, column: str) -> List[str]:
        """
        Checks the data types of values in a specified column, ignoring empty cells (NaN/None).
        Treats int and float as equivalent for consistency checks.

        Parameters:
        - df (pd.DataFrame): The input DataFrame.
        - column (str): The name of the column to check.
        - sheet_name (str): The name of the sheet being checked.

        Returns:
        - List[str]: A list of unique data types found in the column (excluding empty cells).

        Raises:
        - InconsistentDataError: If more than one data type (other than int/float) is found in non-empty cells.
        """
        non_empty_values = self.df[column][
            pd.notna(self.df[column])
        ]  # Filter out empty cells
        data_types = non_empty_values.apply(lambda x: type(x).__name__).unique()

        # Treat int and float as compatible types
        numeric_types = {"int", "float"}
        data_types_set = set(data_types)

        if len(data_types_set - numeric_types) > 1 or (
            len(data_types_set) > 1 and not data_types_set.issubset(numeric_types)
        ):
            # Identify rows with inconsistent types
            inconsistent_rows = non_empty_values[
                non_empty_values.apply(lambda x: type(x).__name__) != data_types[0]
            ].index.tolist()
            inconsistent_rows = [
                row + 2 for row in inconsistent_rows
            ]  # Convert to 1-indexing
            raise InconsistentDataError(
                column,
                data_types.tolist(),
                self.path,
                self.sheet_name,
                inconsistent_rows,
            )

        return data_types

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

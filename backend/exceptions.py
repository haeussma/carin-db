from typing import List


class InconsistentDataError(Exception):
    def __init__(
        self,
        column: str,
        data_types: List[str],
        path: str,
        sheet_name: str,
        row_indices: List[int],
    ):
        row_info = f" at rows {row_indices}" if row_indices else ""
        super().__init__(
            f"Inconsistent data types found in column '{column}' on sheet '{sheet_name}' in file '{path}': {data_types}{row_info}"
        )


class PrimaryKeyNotFoundInRowError(Exception):
    def __init__(
        self,
        primary_key: str,
        sheet_name: str,
        rows: list[int],
        path: str,
    ):
        super().__init__(
            f"Value for primary key '{primary_key}' not found in column '{primary_key}' in rows {rows} of sheet '{sheet_name}' in file '{path}'"
        )


class PrimaryKeyError(Exception):
    def __init__(
        self,
        primary_key: str,
        sheet_name: str,
        rows: list[int],
        path: str,
    ):
        super().__init__(
            f"Primary key '{primary_key}' not found in all sheets '{sheet_name}' in file '{path}'"
        )


class PrimaryKeyNotUniqueError(Exception):
    def __init__(
        self,
        primary_key: str,
        sheet_name: str,
        rows: list[int],
        path: str,
    ):
        super().__init__(
            f"Value for primary key '{primary_key}' not unique in column '{primary_key}' in rows {rows} of sheet '{sheet_name}' in file '{path}'"
        )

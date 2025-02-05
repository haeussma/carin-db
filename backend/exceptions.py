from typing import List

from pydantic import BaseModel


class TypeInconsistencyLocation(BaseModel):
    sheet_name: str
    column: str
    data_types: List[str]
    rows: List[int]
    path: str


class TypeInconsistencyError(Exception):
    def __init__(self, inconsistencies: List[TypeInconsistencyLocation]):
        self.inconsistencies = inconsistencies

    def to_dict(self):
        return {
            "error": "type_inconsistency",
            "message": "Found type inconsistencies in the data",
            "details": [inc.model_dump() for inc in self.inconsistencies],
        }


class PrimaryKeyError(Exception):
    def __init__(self, key: str, sheet: str, rows: List[int], path: str):
        self.key = key
        self.sheet = sheet
        self.rows = rows
        self.path = path

    def to_dict(self):
        return {
            "error": "primary_key_error",
            "message": f"Primary key '{self.key}' error in sheet '{self.sheet}'",
            "details": {
                "key": self.key,
                "sheet": self.sheet,
                "rows": self.rows,
                "path": self.path,
            },
        }


class PrimaryKeyNotFoundInRowError(PrimaryKeyError):
    def to_dict(self):
        base = super().to_dict()
        base["error"] = "primary_key_not_found"
        base["message"] = (
            f"Primary key '{self.key}' not found in rows {self.rows} of sheet '{self.sheet}'"
        )
        return base


class PrimaryKeyNotUniqueError(PrimaryKeyError):
    def to_dict(self):
        base = super().to_dict()
        base["error"] = "primary_key_not_unique"
        base["message"] = (
            f"Primary key '{self.key}' has duplicate values in rows {self.rows} of sheet '{self.sheet}'"
        )
        return base

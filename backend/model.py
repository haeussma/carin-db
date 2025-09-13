from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

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
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    kind: Literal["value"] = "value"
    name: str
    dtype: ScalarType
    unique: bool = False


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


PropertyValue = Annotated[
    Union[ValueProperty, RefProperty], Field(discriminator="kind")
]


# ---------- Core graph objects ----------
class SheetNode(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    name: str
    properties: list[PropertyValue]
    position: Optional[Position] = None


class GraphSheetModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    project_name: str
    created_at: datetime
    sheets: list[SheetNode]


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    name: str
    model: GraphSheetModel
    last_modified: datetime

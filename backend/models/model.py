from pydantic import BaseModel, Field

## Spreadsheet Model


class Column(BaseModel):
    name: str
    data_type: str


class Sheet(BaseModel):
    name: str
    columns: list[Column] = Field(default_factory=list)


class SheetConnection(BaseModel):
    source_sheet_name: str
    target_sheet_name: str
    edge_name: str
    key: str


class SheetReference(BaseModel):
    source_sheet_name: str
    source_column_name: str
    target_sheet_name: str
    target_column_name: str


class SheetModel(BaseModel):
    sheets: list[Sheet] = Field(default_factory=list)
    sheet_connections: list[SheetConnection] = Field(default_factory=list)
    sheet_references: list[SheetReference] = Field(default_factory=list)


## Neo4j Model


class Attribute(BaseModel):
    name: str
    data_type: str


class Node(BaseModel):
    name: str
    attributes: list[Attribute] = Field(default_factory=list)


class Relationship(BaseModel):
    source: str
    name: str
    targets: list[str] = Field(default_factory=list)

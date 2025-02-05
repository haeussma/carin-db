from pydantic import BaseModel


class Column(BaseModel):
    name: str
    data_type: str


class Sheet(BaseModel):
    name: str
    columns: list[Column]


class SheetModel(BaseModel):
    sheets: list[Sheet]

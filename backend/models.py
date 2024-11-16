from typing import Any, Dict

from pydantic import BaseModel


class Relationship(BaseModel):
    name: str
    source: str
    target: str


class Node(BaseModel):
    name: str
    properties: Dict[str, Any]

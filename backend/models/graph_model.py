from pydantic import BaseModel, Field


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


class GraphModel(BaseModel):
    nodes: list[Node] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)

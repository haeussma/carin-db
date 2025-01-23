from pydantic import BaseModel, Field


class Relationship(BaseModel):
    name: str = Field(
        ...,
        description="The name of the relationship",
    )
    source: str = Field(
        ...,
        description="The source node of the relationship",
    )
    targets: list[str] = Field(
        ...,
        description="The target node(s) of the relationship",
    )


class Node(BaseModel):
    name: str = Field(
        ...,
        description="The name of the node",
    )
    properties: list[str] = Field(
        ...,
        description="The properties of the node",
    )


class DBStructure(BaseModel):
    nodes: list[Node] = Field(
        ...,
        description="The nodes in the database",
    )
    relationships: list[Relationship] = Field(
        ...,
        description="The relationships in the database",
    )

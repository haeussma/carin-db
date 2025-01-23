from pydantic import BaseModel, Field


class Relationship(BaseModel):
    name: str = Field(
        ...,
        description="The name of the relationship",
    )
    properties: list[str] = Field(
        ...,
        description="The properties of the relationship",
    )


class DBStructure(BaseModel):
    nodes: list[str] = Field(
        ...,
        description="The nodes in the database",
    )
    relationships: list[Relationship] = Field(
        ...,
        description="The relationships in the database",
    )


class MappingInstruction(BaseModel):
    database_selection: str = Field(
        ...,
        description="Additional information what subset of data from the database to use",
    )
    json_schema: dict = Field(
        ...,
        description="The JSON schema to which the data should be mapped",
    )

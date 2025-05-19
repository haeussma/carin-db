from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator


class Attribute(BaseModel):
    attr_name: str = Field(..., description="Attribute name")
    example_val: Optional[Union[str, int, float]] = Field(
        None,
        description="A sample value (or None if no example exists)",
    )
    # attr_type: str = Field(..., description="Declared data type")

    @field_validator("example_val")
    @classmethod
    def truncate_example(
        cls, v: Optional[Union[str, int, float]]
    ) -> Union[str, int, float, None]:
        if isinstance(v, str) and len(v) > 20:
            return v[:20] + "..."
        return v


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

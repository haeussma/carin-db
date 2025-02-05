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


class Attribute(BaseModel):
    name: str = Field(
        ...,
        description="The name of the attribute",
    )
    data_type: str = Field(
        ...,
        description="The type of the attribute",
    )


class Node(BaseModel):
    name: str = Field(
        ...,
        description="The name of the node",
    )
    attributes: list[Attribute] = Field(
        ...,
        description="The attributes of the node including name and data type",
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


class MissingField(BaseModel):
    data_model_field: str = Field(
        ...,
        description="The name of the data-model field that is not present in the knowledge graph.",
    )
    is_mandatory: bool = Field(
        ...,
        description="True if the data-model field is required.",
    )


class AttributeToNode(BaseModel):
    """One-to-one mapping between a data-model field and a graph node attribute."""

    data_model_field: str = Field(
        ...,
        description="The name of the data-model field.",
    )
    node_name: str = Field(
        ..., description="The graph node label matched to the data-model field."
    )
    node_attribute: str = Field(
        ...,
        description="The node attribute that semantically matches the data-model field.",
    )
    is_mandatory: bool = Field(
        ..., description="True if the data-model field is required."
    )


class ClassToGraph(BaseModel):
    """Maps a single data-model class to its fields in the graph."""

    class_name: str = Field(..., description="Exact name of the data-model class.")
    existing_fields_mapping: list[AttributeToNode] = Field(
        ..., description="Fields that could be matched to node attributes."
    )
    missing_fields_mapping: list[MissingField] = Field(
        ..., description="Fields that had no semantic match in the graph."
    )


class GraphToDataModel(BaseModel):
    """Overall mapping of the data-model classes to the graph."""

    data_model_name: str = Field(..., description="Name of the data model.")
    classes: list[ClassToGraph] = Field(
        ..., description="Mappings for each class in the data model."
    )

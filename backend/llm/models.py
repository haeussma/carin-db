from typing import Literal, Union

from pydantic import BaseModel, Field

# ---- Mapping Between Objects and Database Nodes ----


class NodeAttribute(BaseModel):
    """A node attribute that is mapped to an object attribute."""

    node_name: str = Field(description="The name of the node.")
    node_attr: str = Field(description="The attribute name of the node.")


class AttributeMapping(BaseModel):
    """A mapping of an object attribute to a Neo4j database node attribute."""

    obj_attr_name: str = Field(
        description="The attribute name of the object (mapping target)."
    )
    node_attr: NodeAttribute = Field(
        description="The node attribute that is mapped to the object attribute (mapping source)."
    )


class MappingReport(BaseModel):
    """Report on the mapping of a small molecule to a Neo4j database."""

    object_name: str = Field(
        description="The name of the object to map to (mapping target).",
    )
    mappings: list[AttributeMapping] = Field(
        description="List of individual attribute mappings that were clearly found in the graph.",
    )
    ambiguous_mappings: list[AttributeMapping] = Field(
        description="List of individual attribute mappings that were found in the graph but are ambiguous.",
        default_factory=list,
    )
    mapping_possible: bool = Field(
        description="Whether the mapping is possible. Mandatory attributes are present in the graph.",
    )
    agent_name: str = Field(
        description="The name of the agent that filled the report.",
    )


class Instruction(BaseModel):
    """An instruction to the next agent."""

    agent_name: str = Field(
        description="The name of the agent that should follow the instruction.",
    )
    instruction: str = Field(
        description="The instruction to the agent.",
    )


class EvaluationReport(BaseModel):
    """Report on the mapping of a small molecule to a Neo4j database."""

    report: str = Field(
        description="Short summary of the mapping. Mentions fails and ambiguities of the individual agents.",
    )
    ambiguous_instructions: list[Instruction] = Field(
        description="Instructions to the corresponding agents on what is ambiguous and should be calarified. Might contain mapping suggestions.",
    )
    reports: Union[list[MappingReport], None] = Field(
        description="Reports from the individual agents.",
    )
    next_step: Literal["continue", "clarify", "abort"] = Field(
        description="How to proceed. One of 'continue', 'clarify', 'abort'",
    )


class ClarificationRequest(BaseModel):
    """
    A request to the user to resolve ambiguity on one or more fields.
    """

    object_name: str
    ambiguous_keys: list[str] = Field(
        ..., description="List of attribute names that need clarification"
    )
    # a single natural-language question you want the user to answer
    question: str = Field(
        ..., description="Prompt the user to choose or supply the correct value"
    )

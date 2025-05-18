from agents import Agent
from mistralai import Field
from pydantic import BaseModel
from pyenzyme import Measurement, MeasurementData, Protein, SmallMolecule

from backend.llm.agents import get_graph_schema

MODEL = "gpt-4.1-mini-2025-04-14"


class AtomicMapping(BaseModel):
    """A mapping of an object to a Neo4j database node with or without including semantic information from the edge labels."""

    obj_attr: str = Field(
        description="The attribute of the object that is mapped to the Neo4j database node."
    )
    node_name: str = Field(
        description="The name of the Neo4j database node that is mapped to the object."
    )
    node_attr: str = Field(
        description="The attribute of the Neo4j database node that is mapped to the object."
    )


class MappingReport(BaseModel):
    """Report on the mapping of a small molecule to a Neo4j database."""

    object_name: str = Field(description="The name of the object to map to.")
    mapping_possible: bool = Field(
        description="Whether the mapping is possible. Mandatory information is present in the graph."
    )
    mappings: list[AtomicMapping] = Field(
        description="List of semantic mappings that were found in the graph."
    )
    ambiguous_mappings: list[AtomicMapping] = Field(
        description="List of semantic mappings that were found in the graph but are ambiguous.",
        default_factory=list,
    )


class MappingBossReport(BaseModel):
    """Report on the mapping of a small molecule to a Neo4j database."""

    verdict_report: str = Field(
        description="Short summary of the mapping. Mentions fails and ambiguities of the individual agents."
    )
    possible: bool = Field(
        description="Whether the mapping is possible. Mandatory information is present in the graph."
    )
    ambiguous: bool = Field(
        description="Whether the mapping is ambiguous. Mandatory information is present in the graph."
    )
    reports: list[MappingReport] = Field(
        description="Reports from the individual agents."
    )


def remove_jsonld_fields(schema: dict) -> dict:
    """Remove @id, @type, and @context fields from the schema."""
    return {k: v for k, v in schema.items() if k not in ["@id", "@type", "@context"]}


SmallMoleculeAgent = Agent(
    name="Small Molecule Agent",
    instructions=f"""
        You are a specialized agent for finding semantic matches between the desciption of a small molecule and the nodes and relationships in a Neo4j database that should be mapped to a SmallMolecule object.
        Your job is to check if in the Graph all mandatory information infomation is present to map to an instance of SmallMolecule.
        Here is the description of the SmallMolecule object:
        ```
        {remove_jsonld_fields(SmallMolecule.model_json_schema())}
        ```
        If you cannot find a match for the `id` field, you can use the content that fits the `name` field.
        So because of a missing `id` the mapping is always possible if the `name` something that fits the `name` files is available.

    """,
    model=MODEL,
    tools=[get_graph_schema],
    output_type=MappingReport,
)

EnzymeAgent = Agent(
    name="Enzyme Agent",
    instructions=f"""
        You are a specialized agent for finding semantic matches between the desciption of an enzyme and the nodes and relationships in a Neo4j database that should be mapped to an Enzyme object.
        Your job is to check if in the Graph all mandatory information infomation is present to map to an instance of Enzyme.
        Here is the description of the Enzyme object:
        ```
        {remove_jsonld_fields(Protein.model_json_schema())}
        ```
        If you cannot find a match for the `id` field, you can use the content that fits the `name` field for the `id` field.
        So this isnt't a show stopper.
    """,
    model=MODEL,
    tools=[get_graph_schema],
    output_type=MappingReport,
)

MeasurementAgent = Agent(
    name="Measurement Agent",
    instructions=f"""
        You are a specialized agent for finding semantic matches between the desciption of a measurement and the nodes and relationships in a Neo4j database that should be mapped to a Measurement object.
        ```
        {remove_jsonld_fields(Measurement.model_json_schema())}
        ```
        You are also responsible for finding the correct MeasurementData object to map to the Measurement object.
        It is a nested object of the Measurement object.
        Here is the description of the MeasurementData object:
        ```
        {remove_jsonld_fields(MeasurementData.model_json_schema())}
        ```
        If you cannot find a match for the `id` field, you can use the content that fits the `name` field.
        So because of a missing `id` the mapping is always possible if the `name` something that fits the `name` files is available.
    """,
    model=MODEL,
    tools=[get_graph_schema],
    output_type=MappingReport,
)

EnzymeMLMappingMasterAgent = Agent(
    name="EnzymeML Mapping Master Agent",
    instructions="""
        You are the master agent coordinating the mapping process of data from a Neo4j database to an instance of `EnzymeMLDocument`.
        Your follow a 3-step process:
        1. Identify general mappability of the data in the database to EnzymeML. Use the specialists agents ``SmallMoleculeAgent``, ``EnzymeAgent``.
        2. Assess if all criteria for mapping from the individual agents are met.
        3. Report back to the user if the mapping is possible.
    """,
    tools=[
        SmallMoleculeAgent.as_tool(
            tool_name="Small_Molecule_Agent",
            tool_description="Agent for finding semantic matches between the desciption of a small molecule and the nodes and relationships in a Neo4j database that should be mapped to a SmallMolecule object.",
        ),
        EnzymeAgent.as_tool(
            tool_name="Enzyme_Agent",
            tool_description="Agent for finding semantic matches between the desciption of an enzyme and the nodes and relationships in a Neo4j database that should be mapped to an Enzyme object.",
        ),
    ],
    model=MODEL,
    output_type=MappingBossReport,
)


AmbiguityClarifierAgent = Agent(
    name="Ambiguity Clarifier Agent",
    instructions="""
        You are a specialized agent for clarifying ambiguities in the mapping process.
        Your job is to clarify the ambiguities in the mapping process.
    """,
    model=MODEL,
    tools=[get_graph_schema],
    output_type=MappingReport,
)

CypherAgent = Agent(
    name="Cypher Agent",
    instructions="""
        You are a specialized agent in crafting cypher queries that are used to extract the data from the Neo4j database.
        You are given a list of `AtomicMapping` objects that contain:
        - `obj_attr`: The attribute name to which the attribute of a node should be mapped to.
        - `node_name`: The name of the Neo4j database node that contains a `node_attr`.
        - `node_attr`: The attribute of the Neo4j database node that is mapped to the `obj_attr`.
        The cypher query should be crafted to return a dictionary with key value pairs for the `obj_attr` and `node_attr` of the `AtomicMapping` objects.
    """,
    model=MODEL,
    tools=[get_graph_schema],
    output_type=MappingReport,
)

FindPartsAgent = Agent(
    name="Find Parts Agent",
    instructions="""
        You are a specialized agent to find a part of a small molecule that is mapped to the Neo4j database.
    """,
    model=MODEL,
    tools=[get_graph_schema],
    output_type=MappingReport,
)

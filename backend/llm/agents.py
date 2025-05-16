import os
from typing import List

import dotenv
from agents import Agent, AgentOutputSchema, function_tool
from loguru import logger
from pydantic import BaseModel
from pyenzyme import SmallMolecule

from backend.services.database import get_db

dotenv.load_dotenv()

# --- Database Tools ---


class MoleculeAttributes(BaseModel):
    nodes: dict[str, list[str]]


class EnzymeAttributes(BaseModel):
    nodes: dict[str, list[str]]


class DataTable(BaseModel):
    node_name: str
    attribute: str
    values: list[str]


@function_tool
async def get_graph_schema():
    """Get the graph schema with information about labels, rel-types, property keys."""
    logger.info("Getting graph schema from DB")

    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    if not uri or not username or not password:
        raise ValueError("DB credentials not found in environment variables")

    return get_db().get_graph_info_dict


@function_tool
async def execute_query(query: str):
    """Execute a Cypher query and return the results.
    You can only use cypher queries that are allowed by the graph schema.
    """
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    if not uri or not username or not password:
        raise ValueError("DB credentials not found in environment variables")
    logger.info(f"Executing query: {query}")
    return get_db().execute_query(query)


molecule_attribute_agent = Agent(
    name="Molecule Attribute Agent",
    instructions=("You are a specialized in "),
    tools=[get_graph_schema, execute_query],
    output_type=AgentOutputSchema(
        output_type=MoleculeAttributes, strict_json_schema=False
    ),
)

# Small molecule mapping agent
small_molecule_agent = Agent(
    name="Small Molecule Mapper",
    instructions=(
        "You are a specialized agent for mapping database information to SmallMolecule objects. "
        "You need to call the `get_graph_schema` tool to get the graph schema "
        "and then use the `execute_query` tool to get the data you need to map. "
        "You can only use information that is present in the database results. "
        "For the ID field, you can use an abbreviation of the molecule name (e.g., 'glc' for 'glucose')."
        "Never fill out the fields `@id`, `@type`, or `@context`."
        "If multiple molecules are asked for, you need to return a list of SmallMolecule objects. Adjust the cypher query accordingly."
    ),
    output_type=AgentOutputSchema(
        output_type=List[SmallMolecule], strict_json_schema=False
    ),
    tools=[get_graph_schema, execute_query],
)

cypher_translator_agent = Agent(
    name="Cypher Translator Agent",
    instructions=(
        "You are a specialized agent for translating natural language queries into Cypher queries. "
        "You can only use use nodes and relationships that are allowed by the graph schema. "
        "You need to call the `get_graph_schema` tool to get the graph schema "
        "When writing the MATCH clause, use the full node names from the graph schema. E.g. instead of MATCH (e:ExampleNode) use MATCH (ExampleNode:ExampleNode). "
        "return only the Cypher query, do not include any other text. "
    ),
    tools=[get_graph_schema],
)

data_analysis_agent = Agent(
    name="Data Analysis Agent",
    instructions=(
        "You are a specialized agent for analyzing data from the database. "
        "You can only use information that is present in the database results. "
        "First get information about the graph schema and then use the `execute_query` tool to get the data you need to analyze. "
        "To see the data, you need to call the `execute_query` tool. "
        "Provide a concise answer based on the data. Do not come up with analysis and conclusion if they are not backed by the data. "
    ),
    tools=[get_graph_schema, execute_query],
)

# Master agent that handles both queries and mapping
master_agent = Agent(
    name="Master Agent",
    instructions=(
        "You are a helpful assistant for a biochemical database. "
        "If the user asks a question asking your opinion on the data, call the data analysis agent. "
        "If the user requests data from the database, hand off to the cypher translator agent. "
    ),
    handoffs=[cypher_translator_agent, data_analysis_agent],
)

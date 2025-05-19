from agents import function_tool
from loguru import logger

from ..services.database import get_db

# ---- Agent Tools ----


@function_tool
async def get_graph_schema():
    """Get the graph schema with information about labels, rel-types, property keys."""
    logger.debug("AGENT TOOL CALL: get_graph_schema")
    return get_db().get_graph_info_dict


@function_tool
async def execute_query(query: str):
    """Execute a Cypher query and return the results.
    You can only use cypher queries that are allowed by the graph schema.
    """
    logger.debug(f"AGENT TOOL CALL: execute_query with query: {query}")
    return get_db().execute_query(query)

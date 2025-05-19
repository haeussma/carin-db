from typing import Any

from fastapi import APIRouter
from loguru import logger

from backend.models.graph_model import GraphModel

from ...services.database import DB

router = APIRouter(prefix="/database")


@router.get("/health", tags=["Database"])
async def get_database_health(db: DB) -> dict[str, str]:
    """Get the current status of the database connection."""
    response = db.execute_query("RETURN 'healthy'")
    logger.info(f"Database health check response: {response}")
    return response[0]


@router.get("/status", tags=["Database"])
async def get_database_status(db: DB) -> dict[str, int]:
    """Get the current status of the database connection."""
    return db.node_count


@router.get("/db_structure", tags=["Database"])
async def get_database_structure(db: DB) -> GraphModel:
    """Get the structure of the database."""
    return db.get_db_structure


@router.get("/node_properties", tags=["Database"])
async def get_node_properties(db: DB) -> Any:
    """Get the node properties of the database."""
    return db.node_properties


@router.delete("/delete_all", tags=["Database"])
async def delete_all(db: DB) -> dict[str, str]:
    """Delete all nodes and relationships from the database."""
    query = "MATCH (n) DETACH DELETE n"
    db.execute_query(query)
    return {"message": "All nodes and relationships deleted"}

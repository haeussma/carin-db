# backend/api/routes/database.py
from typing import Any

from fastapi import APIRouter
from loguru import logger

from ..services.database import Database

router = APIRouter(prefix="/database")


@router.get("/health", tags=["Database"])
async def get_database_health(db: Database) -> dict[str, str]:
    logger.debug("Checking database health")
    resp = db.execute_query("RETURN 'healthy' AS status")
    logger.info(f"Database health check response: {resp}")
    return resp[0]


@router.get("/status", tags=["Database"])
async def get_database_status(db: Database) -> dict[str, int]:
    return db.node_count


@router.get("/node_properties", tags=["Database"])
async def get_node_properties(db: Database) -> Any:
    return db.node_properties


@router.delete("/delete_all", tags=["Database"])
async def delete_all(db: Database) -> dict[str, str]:
    db.execute_query("MATCH (n) DETACH DELETE n")
    return {"message": "All nodes and relationships deleted"}

# backend/api/routes/database.py
from typing import Any

from fastapi import APIRouter, Depends
from loguru import logger

from backend.api.routes.deps import get_db
from backend.models.graph_model import GraphModel
from backend.services.database import Database

router = APIRouter(prefix="/database")


@router.get("/health", tags=["Database"])
async def get_database_health(db: Database = Depends(get_db)) -> dict[str, str]:
    resp = db.execute_query("RETURN 'healthy' AS status")
    logger.info(f"Database health check response: {resp}")
    return resp[0]


@router.get("/status", tags=["Database"])
async def get_database_status(db: Database = Depends(get_db)) -> dict[str, int]:
    return db.node_count


@router.get("/db_structure", tags=["Database"])
async def get_database_structure(db: Database = Depends(get_db)) -> GraphModel:
    return db.get_db_structure


@router.get("/node_properties", tags=["Database"])
async def get_node_properties(db: Database = Depends(get_db)) -> Any:
    return db.node_properties


@router.delete("/delete_all", tags=["Database"])
async def delete_all(db: Database = Depends(get_db)) -> dict[str, str]:
    db.execute_query("MATCH (n) DETACH DELETE n")
    return {"message": "All nodes and relationships deleted"}

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from ...services.database_connection import Database as DBService
from .config import get_database_config

router = APIRouter(prefix="/database")


@router.get("/status")
async def get_database_status(request: Request):
    """Get the current status of the database connection."""
    db_info = await get_database_config()
    try:
        db = DBService(
            uri=db_info.uri, user=db_info.username, password=db_info.password
        )

        # Try to connect and get basic info
        return db.node_count
    except Exception as e:
        logger.error(f"Error checking database status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Database connection failed: {str(e)}"
        )


@router.get("/db_structure")
async def get_database_structure(request: Request) -> dict:
    """Get the structure of the database."""
    db_info = await get_database_config()
    try:
        db = DBService(
            uri=db_info.uri, user=db_info.username, password=db_info.password
        )
        return db.get_db_structure.model_dump()
    except Exception as e:
        logger.error(f"Error getting database structure: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get database structure: {str(e)}"
        )


@router.post("/execute_query")
async def execute_database_query(request: Request):
    """Execute a custom Cypher query on the database."""
    data = await request.json()
    query = data.get("query")

    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    db_info = await get_database_config()
    try:
        db = DBService(
            uri=db_info.uri, user=db_info.username, password=db_info.password
        )

        result = db.execute_query(query)
        return {"result": result}

    except Exception as e:
        logger.error(f"Error executing database query: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to execute query: {str(e)}"
        )

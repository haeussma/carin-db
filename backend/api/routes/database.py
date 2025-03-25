from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from ...services.config_service import ConfigService
from ...services.db_service import Database as DBService

router = APIRouter(prefix="/database")


@router.post("/status")
async def get_database_status(request: Request):
    """Get the current status of the database connection."""
    data = await request.json()
    db_name = data.get("db_name")
    try:
        config = ConfigService.load_config()
        if not config.databases:
            return {"status": "not_configured", "message": "No database configured"}

        db_config = [db for db in config.databases if db.name == db_name][0]
        db = DBService(
            uri=db_config.uri, user=db_config.username, password=db_config.password
        )

        # Try to connect and get basic info
        node_count = db.node_count
        return {
            "status": "connected",
            "node_count": node_count,
            "message": "Database connection successful",
        }
    except Exception as e:
        logger.error(f"Error checking database status: {e}")
        return {"status": "error", "message": f"Database connection failed: {str(e)}"}


@router.post("/db_structure")
async def get_database_structure(request: Request) -> dict:
    """Get the structure of the database."""
    data = await request.json()
    db_name = data.get("db_name")
    try:
        db_info = ConfigService.get_db_by_name(db_name)
        if not db_info:
            raise HTTPException(
                status_code=400,
                detail="Database connection settings are not configured",
            )
        db = DBService(
            uri=db_info.uri, user=db_info.username, password=db_info.password
        )
        return db.get_db_structure.model_dump()
    except Exception as e:
        logger.error(f"Error getting database structure: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get database structure: {str(e)}"
        )


@router.post("/query")
async def execute_database_query(request: Request):
    """Execute a custom Cypher query on the database."""
    data = await request.json()
    db_name = data.get("db_name")
    query = data.get("query")

    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    if not db_name:
        raise HTTPException(status_code=400, detail="Database name is required")

    try:
        db_info = ConfigService.get_db_by_name(db_name)
        if not db_info:
            raise HTTPException(
                status_code=400,
                detail="Database connection settings are not configured",
            )

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

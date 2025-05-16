from fastapi import APIRouter

from backend.models.graph_model import GraphModel

from ...services.database import DB

router = APIRouter(prefix="/database")


@router.get("/status")
async def get_database_status(db: DB) -> dict[str, int]:
    """Get the current status of the database connection."""
    return db.node_count


@router.get("/db_structure")
async def get_database_structure(db: DB) -> GraphModel:
    """Get the structure of the database."""
    return db.get_db_structure

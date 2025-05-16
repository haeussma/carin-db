import os
from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi.params import Body
from loguru import logger

from backend.config import Settings, config
from backend.models.model import SheetModel

router = APIRouter(prefix="/config")


@router.post("/database")
async def save_database_config(
    database_config: Settings,
) -> dict:
    """Save database configuration to environment variables and config.

    Args:
        database_config: The new database configuration
        db: Database instance (injected)

    Returns:
        dict: Success message
    """
    logger.info("Saving database configuration")

    # Update the config instance
    config.neo4j_uri = database_config.neo4j_uri
    config.neo4j_username = database_config.neo4j_username
    config.neo4j_password = database_config.neo4j_password

    # Update environment variables
    os.environ["NEO4J_URI"] = database_config.neo4j_uri
    os.environ["NEO4J_USERNAME"] = database_config.neo4j_username
    os.environ["NEO4J_PASSWORD"] = database_config.neo4j_password

    # Update .env file
    with open(".env", "w") as f:
        f.write(f"NEO4J_URI={database_config.neo4j_uri}\n")
        f.write(f"NEO4J_USERNAME={database_config.neo4j_username}\n")
        f.write(f"NEO4J_PASSWORD={database_config.neo4j_password}\n")

    return {"message": "Database configuration updated successfully"}


@router.get("/sheet_model")
async def get_sheet_model() -> SheetModel:
    """Gets sheet model configuration from json file"""
    try:
        with open("sheet_model.json", "r") as f:
            model = SheetModel.model_validate_json(f.read())
        return model
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Sheet model configuration file not found",
                "error": "SHEET_MODEL_NOT_FOUND",
                "suggestion": "Please ensure sheet_model.json exists in the root directory",
            },
        )


@router.post("/sheet_model")
async def save_sheet_model(sheet_model: SheetModel):
    """Saves sheet model configuration to json file"""
    with open("sheet_model.json", "w") as f:
        f.write(sheet_model.model_dump_json(indent=4))


@router.delete("/sheet_model")
async def delete_sheet_model():
    """Deletes sheet model configuration from json file"""
    os.remove("sheet_model.json")


@router.delete("/graph_model")
async def delete_graph_model():
    """Deletes graph model configuration json file"""

    os.remove("graph_model.json")
    return {"message": "Graph model deleted successfully"}


@router.get("/openai")
async def get_openai_config() -> str:
    """Get OpenAI configuration from environment variables."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not found in environment variables")
    return api_key


@router.post("/openai")
async def save_openai_config(openai_api_key: Annotated[str, Body()]):
    """Save OpenAI configuration to environment variables."""

    # Update environment variable
    os.environ["OPENAI_API_KEY"] = openai_api_key

    # Update .env file
    with open(".env", "a") as f:
        f.write(f"\nOPENAI_API_KEY={openai_api_key}\n")

    logger.info("OpenAI configuration updated")
    return {"message": "OpenAI configuration updated successfully"}

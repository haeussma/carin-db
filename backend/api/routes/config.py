import json
import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from pydantic import ValidationError

from ...models.model import DatabaseInfo, GraphModel, SheetModel

router = APIRouter(prefix="/config")

# Load environment variables
load_dotenv()


@router.get("/database")
async def get_database_config() -> DatabaseInfo:
    """Get database configuration from environment variables."""
    try:
        uri = os.getenv("NEO4J_URI")
        username = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")

        if not all([uri, username, password]):
            raise ValueError(
                "Missing required database configuration in environment variables"
            )

        return DatabaseInfo(uri=uri, username=username, password=password)  # type: ignore
    except Exception as e:
        logger.error(f"Error getting database configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database")
async def save_database_config(request: Request):
    """Save database configuration to environment variables."""
    try:
        data = await request.json()
        logger.info(f"Saving database configuration: {data}")

        # Update environment variables
        os.environ["NEO4J_URI"] = data.get("url")
        os.environ["NEO4J_USERNAME"] = data.get("username")
        os.environ["NEO4J_PASSWORD"] = data.get("password")

        # Update .env file
        with open(".env", "w") as f:
            f.write(f"NEO4J_URI={data.get('url')}\n")
            f.write(f"NEO4J_USERNAME={data.get('username')}\n")
            f.write(f"NEO4J_PASSWORD={data.get('password')}\n")

        logger.info("Database configuration updated")
        return {"message": "Database configuration updated successfully"}
    except Exception as e:
        logger.error(f"Error saving database configuration: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


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
async def save_sheet_model(request: Request):
    """Saves sheet model configuration to json file"""
    try:
        logger.debug(f"incoming type: {type(request)}")
        data = await request.json()
        logger.debug(f"Received data type: {type(data)}")
        sheet_model = SheetModel.model_validate(data)
        logger.debug(f"sheet model successfully validated: {type(sheet_model)}")
        with open("sheet_model.json", "w") as f:
            f.write(sheet_model.model_dump_json(indent=4))
    except Exception as e:
        logger.error(f"Error saving sheet model configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sheet_model")
async def delete_sheet_model():
    """Deletes sheet model configuration from json file"""
    try:
        os.remove("sheet_model.json")
    except Exception as e:
        logger.error(f"Error deleting sheet model configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/openai")
async def get_openai_config():
    """Get OpenAI configuration from environment variables."""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        return {"openai_api_key": api_key}
    except Exception as e:
        logger.error(f"Error getting OpenAI configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph_model")
async def get_graph_model() -> GraphModel:
    """Gets graph model configuration from json file"""
    try:
        with open("graph_model.json", "r") as f:
            model = GraphModel.model_validate_json(f.read())
        return model
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Graph model configuration file not found",
                "error": "GRAPH_MODEL_NOT_FOUND",
                "suggestion": "Please ensure graph_model.json exists in the root directory",
            },
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid graph model configuration format",
                "error": "INVALID_GRAPH_MODEL_FORMAT",
                "suggestion": "Please check if graph_model.json contains valid JSON",
            },
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Graph model validation failed",
                "error": "GRAPH_MODEL_VALIDATION_ERROR",
                "errors": e.errors(),
                "suggestion": "Please check if the JSON structure matches the required schema",
            },
        )


@router.post("/graph_model")
async def save_graph_model(request: Request):
    """Saves graph model configuration to json file"""
    try:
        data = await request.json()
        graph_model = GraphModel.model_validate(data)
        with open("graph_model.json", "w") as f:
            f.write(graph_model.model_dump_json())
        return {"message": "Graph model saved successfully"}
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid graph model data",
                "error": "GRAPH_MODEL_VALIDATION_ERROR",
                "errors": e.errors(),
                "suggestion": "Please check if the provided data matches the required schema",
            },
        )
    except Exception as e:
        logger.error(f"Error saving graph model configuration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to save graph model",
                "error": "GRAPH_MODEL_SAVE_ERROR",
                "suggestion": "Please try again or contact support if the problem persists",
            },
        )


@router.delete("/graph_model")
async def delete_graph_model():
    """Deletes graph model configuration json file"""
    try:
        os.remove("graph_model.json")
        return {"message": "Graph model deleted successfully"}
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Graph model configuration file not found",
                "error": "GRAPH_MODEL_NOT_FOUND",
                "suggestion": "The graph model file does not exist",
            },
        )
    except Exception as e:
        logger.error(f"Error deleting graph model configuration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to delete graph model",
                "error": "GRAPH_MODEL_DELETE_ERROR",
                "suggestion": "Please try again or contact support if the problem persists",
            },
        )


@router.post("/openai")
async def save_openai_config(request: Request):
    """Save OpenAI configuration to environment variables."""
    try:
        data = await request.json()
        api_key = data.get("openai_api_key")
        if not api_key:
            raise HTTPException(
                status_code=400, detail={"error": {"message": "API key is required"}}
            )

        # Update environment variable
        os.environ["OPENAI_API_KEY"] = api_key

        # Update .env file
        with open(".env", "a") as f:
            f.write(f"\nOPENAI_API_KEY={api_key}\n")

        logger.info("OpenAI configuration updated")
        return {"message": "OpenAI configuration updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving OpenAI configuration: {str(e)}")
        raise HTTPException(
            status_code=500, detail={"error": {"message": "Failed to save API key"}}
        )

import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from ...models.model import DatabaseInfo

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

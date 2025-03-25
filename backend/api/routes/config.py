from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from ...models.appconfig import DatabaseInfo
from ...services.config_service import ConfigService

router = APIRouter(prefix="/config")


@router.get("/database")
async def get_database_config():
    """Get database configuration."""
    config = ConfigService.load_config()
    if not config.databases:
        logger.warning("No databases configured")
        return {"error": "No databases configured"}
    return config.databases[0].model_dump()


@router.post("/database")
async def save_database_config(request: Request):
    """Save database configuration."""
    try:
        data = await request.json()
        database = DatabaseInfo(
            name=data.get("name", "default"),
            uri=data.get("url"),
            username=data.get("username"),
            password=data.get("password"),
        )
        ConfigService.add_database(database)
        logger.info("Database configuration updated")
        return {"message": "Database configuration updated successfully"}
    except Exception as e:
        logger.error(f"Error saving database configuration: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/openai")
async def get_openai_config():
    """Get OpenAI configuration."""
    api_key = ConfigService.get_openai_key()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"openai_api_key": api_key}


@router.post("/openai")
async def save_openai_config(request: Request):
    """Save OpenAI configuration."""
    try:
        data = await request.json()
        api_key = data.get("openai_api_key")
        if not api_key:
            raise HTTPException(
                status_code=400, detail={"error": {"message": "API key is required"}}
            )

        ConfigService.set_openai_key(api_key)
        logger.info("OpenAI configuration updated")
        return {"message": "OpenAI configuration updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving OpenAI configuration: {str(e)}")
        raise HTTPException(
            status_code=500, detail={"error": {"message": "Failed to save API key"}}
        )


@router.delete("/openai")
async def clear_openai_config():
    """Clear OpenAI configuration."""
    try:
        ConfigService.clear_openai_key()
        logger.info("OpenAI configuration cleared")
        return {"message": "OpenAI configuration cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing OpenAI configuration: {str(e)}")
        raise HTTPException(
            status_code=500, detail={"error": {"message": "Failed to clear API key"}}
        )


# @router.get("/graph-model")
# async def get_graph_model():
#     """Get the graph model configuration."""
#     config = ConfigService.load_config()
#     if not config.databases:
#         return {"error": "No database configured"}
#     db_config = config.databases[0]
#     if not db_config.graph_model:
#         return {"error": "No graph model configured"}
#     return db_config.graph_model


# @router.post("/graph-model")
# async def save_graph_model(request: Request):
#     """Save the graph model configuration."""
#     try:
#         data = await request.json()
#         config = ConfigService.load_config()
#         if not config.databases:
#             raise HTTPException(status_code=400, detail="No database configured")

#         db_config = config.databases[0]
#         db_config.graph_model = GraphModel(**data)
#         ConfigService.update_database(db_config.name, db_config)

#         logger.info("Graph model configuration updated")
#         return {"message": "Graph model configuration updated successfully"}
#     except Exception as e:
#         logger.error(f"Error saving graph model configuration: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail={"error": {"message": f"Failed to save graph model: {str(e)}"}},
#         )

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from ...services.config_service import ConfigService
from ...services.database_connection import Database
from ...services.openai_service import OpenAIService

router = APIRouter()


@router.post("/api/ask")
async def ask(request: Request):
    """Handle ask requests with provided OpenAI API key."""
    body = await request.json()
    db_name = body.get("db_name")
    db_config = ConfigService.get_db_by_name(db_name)
    openai_api_key = ConfigService.get_openai_api_key()

    if not openai_api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": "OpenAI API key is required"}},
        )

    if not db_config:
        raise HTTPException(
            status_code=400,
            detail={"error": {"message": "Database configuration is required"}},
        )

    try:
        # Process the request with OpenAI
        openai_service = OpenAIService(
            openai_api_key=openai_api_key,
            db_service=Database(
                uri=db_config.uri, user=db_config.username, password=db_config.password
            ),
        )

        db = Database(
            uri=db_config.uri, user=db_config.username, password=db_config.password
        )

        response = openai_service.get_cypher(
            question=body["question"], db_info=db.get_db_structure.model_dump()
        )

        logger.info(f"OpenAI cypher query: {response}")
        data = db.execute_query(response)
        logger.info(f"Neo4j data: {data}")

        return {"response": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing ask request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "An unexpected error occurred"}},
        )

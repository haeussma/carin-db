from typing import Annotated

from agents import RunConfig, Runner
from fastapi import APIRouter, Body, HTTPException
from loguru import logger

from backend.llm.agents import master_agent
from backend.services.database import DB

router = APIRouter(prefix="/llm")


@router.post("/ask")
async def ask(question: Annotated[str, Body()], db: DB):
    """Handle ask requests with provided OpenAI API key."""
    try:
        result = await Runner.run(
            master_agent,
            question,
            run_config=RunConfig(
                workflow_name="Database Query", model="gpt-4.1-2025-04-14"
            ),
        )

        if result.last_agent.name == "Cypher Translator Agent":
            logger.info(f"Query from Cypher Translator Agent: {result.final_output}")
            data = db.execute_query(result.final_output)
            return {"model": "data_table", "data": data}

        logger.info(f"Response from agent: {result.last_agent.name}")

        return {"model": "text", "data": result.final_output}

    except Exception as e:
        logger.error(f"Error processing ask request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": f"An unexpected error occurred: {str(e)}"}},
        )


@router.post("/map_enzymeml")
async def map_enzymeml(question: str):
    """Handle ask requests with provided OpenAI API key."""
    try:
        result = await Runner.run(
            master_agent,
            question,
            run_config=RunConfig(
                workflow_name="Database Query", model="gpt-4.1-2025-04-14"
            ),
        )

        logger.info(f"Response from agent: {result.last_agent.name}")
        return result.final_output

    except Exception as e:
        logger.error(f"Error processing ask request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": f"An unexpected error occurred: {str(e)}"}},
        )

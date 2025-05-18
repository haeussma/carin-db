from typing import Annotated

from agents import RunConfig, Runner
from fastapi import APIRouter, Body, HTTPException
from loguru import logger
from neo4j.exceptions import ClientError

from backend.llm.agents import master_agent
from backend.services.database import DB

router = APIRouter(prefix="/llm")


@router.post("/ask", tags=["Chat"])
async def ask(
    question: Annotated[str, Body()],
    db: DB,
    run_count: int = 0,
):
    """Handle ask requests with provided OpenAI API key."""
    try:
        if run_count > 2:
            return {
                "model": "text",
                "data": "I'm sorry, I'm having trouble processing your request. Please try again.",
            }

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

    except ClientError as e:
        run_count += 1
        logger.error(
            f"We Got client error. Retrying for the {run_count} time: {str(e)}"
        )
        new_question = f"""
        The user asked: ```{question}```
        From your previous response, I can see that you tried to execute the following query: ```{result.final_output}```
        This cause the following error: ```{str(e)}```
        Please try to fix the query and execute it again.
        """
        logger.info(f"New question: {new_question}")
        # rerun the agent with error message
        return await ask(new_question, db, run_count)


@router.post("/map_enzymeml", tags=["Chat"])
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

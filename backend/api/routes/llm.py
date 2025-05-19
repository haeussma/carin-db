from typing import Annotated

from agents import Runner
from fastapi import APIRouter, Body
from loguru import logger
from neo4j.exceptions import ClientError

from backend.llm.agents import data_analysis_agent, question_dispatcher_agent
from backend.services.database import DB

router = APIRouter(prefix="/llm")


@router.post("/ask", tags=["Chat"])
async def ask(
    question: Annotated[str, Body()],
    db: DB,
    run_count: int = 0,
) -> dict[str, str]:
    """Handle ask requests with provided OpenAI API key."""
    try:
        if run_count > 2:
            return {
                "model": "text",
                "data": "I'm sorry, I'm having trouble processing your request. Please try again.",
            }

        result = await Runner.run(
            starting_agent=question_dispatcher_agent,
            input=question,
        )

        if result.last_agent.name == data_analysis_agent.name:
            logger.info(
                f"Question answer by {data_analysis_agent.name}: {result.final_output[:20]}..."
            )
            return {"model": "text", "data": result.final_output}

        logger.info(
            f"Question answer by {result.last_agent.name}: {result.final_output[:20]}..."
        )

        return {"model": "data_table", "data": db.execute_query(result.final_output)}

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
        logger.info(f"New question: {new_question[:20]}...")
        # rerun the agent with error message
        return await ask(new_question, db, run_count)

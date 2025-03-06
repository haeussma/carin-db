import logging
from typing import Any, Dict, List, Optional

import instructor
from loguru import logger
from neo4j.exceptions import CypherSyntaxError
from openai import OpenAI
from pydantic import BaseModel, Field

from .services.db_service import Database


class CypherResponse(BaseModel):
    query: str = Field(
        ...,
        description="The cypher query based on the user input",
    )


class Response(BaseModel):
    response: str = Field(
        ...,
        description="The response to the user input",
    )
    export_file: bool = Field(
        False,
        description="Whether the data of the response should be exported to a file",
    )


class Chat:
    def __init__(
        self,
        api_key: str | None = None,
    ):
        self.client: OpenAI = instructor.patch(OpenAI(api_key=api_key))

    def get_cypher(
        self,
        question: str,
        db_info: dict,
        history=None,
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": f"""
                # General Task
                You are a biochemist and Neo4j expert. 
                Your task is to translate the user query into a valid Cypher query to extract the requested data from the database, inline with the provided schema.
                If you cannot generate a Cypher statement based on the provided schema, explain the reason to the user.
            
                ## Database Schema
                Here is all information on the nodes and relationships in the database:
                {db_info}
                
                Use only the provided relationship types and properties.
                Do not use any other relationship types or properties that are not provided.
            
                ## Cypher Query Requirements
                Make sure to return the data using the exact node attribute names from the database, without adding prefixes, transformations, or query-based aliasing. Therefore, use the AS keyword.

                """,
            },
            {"role": "user", "content": question},
        ]
        logger.debug(f"Sending messages to OpenAI: {messages}")

        if history:
            logger.debug(f"Adding history to message: {history}")
            messages.extend(history)

        response = self.client.chat.completions.create(
            model="gpt-4",
            response_model=CypherResponse,
            messages=messages,
        )  # type: ignore

        logger.debug(f"Recieved response: {response}")
        return response.query

    def get_data_from_db(
        self,
        question: str,
        db: Database,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> list[dict[str, Any]]:
        """Get data from the database based on the user question."""

        retry_count = 0
        cypher = self.get_cypher(question, db.get_graph_info_dict, history)
        logging.debug(f"Recieved Cypher query: {cypher}")

        try:
            with db.driver.session() as session:
                result = session.run(cypher).data()
                logging.debug(f"Successfully recieved data: {result}")
                return result
        except CypherSyntaxError as e:
            logger.debug(f"Retrying due to CypherSyntaxError: {e}")
            if not retry_count == 0:
                raise e

            retry_count += 1

            history = [
                {"role": "assistant", "content": cypher},
                {
                    "role": "user",
                    "content": f"""This query returns an error: {str(e)} 
                    Give me a improved query that works without any explanations or apologies""",
                },
            ]

            return self.get_data_from_db(question=question, db=db, history=history)


if __name__ == "__main__":
    # define db
    from devtools import pprint

    from backend.services.db_service import Database

    db = Database(uri="bolt://localhost:7692", user="neo4j", password="12345678")

    q = "Gimme the enzyme ids, position, induction concentration and peak area from the 3 enzymes with the highest peak area."
    chat = Chat()
    pprint(
        chat.get_data_from_db(
            question=q,
            db=db,
        )
    )

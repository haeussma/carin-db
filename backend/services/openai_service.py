from typing import Type, TypeVar

from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from pydantic import BaseModel

from .db_service import Database

T = TypeVar("T", bound=BaseModel)


class OpenAIService:
    def __init__(
        self,
        db_service: Database,
        openai_api_key: str,
        model="gpt-4o-mini",
    ):
        self.db_service: Database = db_service
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model

        self._tools: list[ChatCompletionToolParam] = []

    def add_tool(self, tool_def: ChatCompletionToolParam):
        """
        Register a new function schema in the `_tools` list.
        """
        self._tools.append(tool_def)

    def add_tools(self, tools: list[ChatCompletionToolParam]):
        """
        Register a new function schema in the `_tools` list.
        """
        self._tools.extend(tools)

    @property
    def tools(self) -> list[ChatCompletionToolParam]:
        return self._tools

    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 10000,
        **kwargs,
    ) -> ChatCompletion:
        """
        Helper to call the chat endpoint with a consistent signature.
        (You can unify your usage of 'tools' vs 'functions'.)
        """

        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            # tools=self.tools,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            **kwargs,
        )  # type: ignore

    def parse_data_to_model(
        self,
        messages: list[dict[str, str]],
        response_model: Type[T],
    ) -> T:
        return self.client.beta.chat.completions.parse(
            messages=messages,
            response_format=response_model,
            temperature=0.0,
            model=self.model,
        )  # type: ignore


if __name__ == "__main__":
    import os

    from devtools import pprint

    from .openai_tools import is_congruent_with_schema_tool

    # get openai api key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    print(openai_api_key)

    db = Database(uri="bolt://localhost:7692", user="neo4j", password="12345678")
    service = OpenAIService(db, openai_api_key, "gpt-4")
    # service.add_tool(parse_data_structure_tool)
    service.add_tool(is_congruent_with_schema_tool)

    db_structure = db.get_db_structure

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. Tasked with finding out if the data in a graph database is compliant with a data model.",
        },
        {
            "role": "user",
            "content": f"""
            The data in the graph database is as follows:
            {db_structure.model_dump_json()},
            """,
        },
    ]
    # pprint(service.create_chat_completion(messages))

    pprint(db_structure)

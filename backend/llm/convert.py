import instructor
from db.db_connect import Database
from devtools import pprint
from llm.models import MappingInstruction
from openai import OpenAI

MODEL = "gpt-4o"

client = instructor.patch(OpenAI(), mode=instructor.Mode.MD_JSON)

db = Database(uri="bolt://localhost:7692", user="neo4j", password="12345678")

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_cypher_query",
            "description": "Get a cypher query to extract data that is likely needed to map to the provided JSON schema. Attributes in the database and JSON schema should mean the same thing but can have different names. Context of the node and relationship names should be considered.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The plain cypher query without any comments.",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_query_clarification",
            "description": "Get a clarification on the cypher query to extract data from a Neo4j database for later mapping to a JSON schema. This can be a question which attribute in the db corresponds to a specific attribute in the JSON schema. If a property exists multiple time, this does not need to be clarified.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Suggestions and questions form the system to the user on what to use in the cypher query.",
                    },
                },
                "required": ["question"],
                "additionalProperties": False,
            },
        },
    },
]


def handle_user_prompt(prompt):
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a data assistant tasked to help users with mapping their data from a database to a JSON schema.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_model=MappingInstruction,
    )


def create_neo4j_query(addition_instruction: str, json_schema: dict):
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": f"""
                You are a data assistant tasked to write a cypher query to extract data from a Neo4j database.
                Based on the provided JSON schema, and additional instruction what subset of data to include, 
                write a cypher query that extracts the data from the database.
                
                The database contains the following node and relationships: {db.get_db_structure.model_dump_json()}
                Only use these nodes and relationships to extract the data. If in relevant information is missing in the database,
                ask the user for clarification.

                Make sure to extract all neccessary data to map it to the provided JSON schema. If in doubt if a node or attribute 
                is matching the schema, ask the user for clarification.
                """,
            },
            {
                "role": "user",
                "content": f"Here are additional data subsetting instructions: {addition_instruction} and the JSON schema: {json_schema}",
            },
        ],
        tools=tools,
    )


query: str = """
Get all experimental data where the induction concentration was 1. ans map it to this JSON schema.
{
    "type": "object",
    "properties": {
        "position": {
            "type": "string"
        },
        "peak_area": {
            "type": "number"
        },
        "slope": {
            "type": "number"
        },
        "induction_concentration": {
            "type": "number"
        }
    },
    "required": ["position", "peak_area", "slope", "induction_concentration"],
    "additionalProperties": false
}
"""


r1 = handle_user_prompt(query)
r2 = create_neo4j_query(
    addition_instruction=r1.database_selection, json_schema=r1.json_schema
)


def execute_query(query: str):
    return db.execute_query(query)


pprint(r2)

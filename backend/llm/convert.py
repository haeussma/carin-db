import instructor
from devtools import pprint
from openai import OpenAI

from ..services.db_service import Database
from .models import MappingInstruction

MODEL = "gpt-4"

client = instructor.patch(OpenAI(), mode=instructor.Mode.MD_JSON)

db = Database(uri="bolt://localhost:7692", user="neo4j", password="12345678")

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_cypher_query",
            "description": """Generate a Cypher query to extract data from Neo4j database.
            The query should match the requirements of the JSON schema while considering semantic meaning of attributes.
            Only use node labels and relationships that exist in the database schema.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A valid Cypher query that will return data matching the JSON schema requirements.",
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_query_clarification",
            "description": """Request clarification about mapping database attributes to JSON schema fields.
            Use this when uncertain about attribute correspondence or when multiple candidates exist.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "A specific question about which database attribute corresponds to which JSON schema field.",
                    }
                },
                "required": ["question"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
]


def handle_user_prompt(prompt: str) -> MappingInstruction:
    """Handle user's data mapping request.

    Args:
        prompt: User's request for data mapping

    Returns:
        MappingInstruction: Contains database selection criteria and JSON schema
    """
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": """You are a data assistant that helps users map database data to JSON schemas.
                Your task is to understand the user's requirements and generate appropriate database queries.
                Always validate that required fields in the JSON schema can be satisfied by the database schema.""",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_model=MappingInstruction,
    )  # type: ignore


def create_neo4j_query(addition_instruction: str, json_schema: dict):
    """Create a Neo4j query based on data requirements.

    Args:
        addition_instruction: Additional filtering/selection criteria
        json_schema: Target JSON schema for the data

    Returns:
        OpenAI completion response with query generation
    """
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": f"""You are a Neo4j expert tasked with writing Cypher queries.
                Database Schema: {db.get_db_structure.model_dump_json()}
                
                Guidelines:
                1. Only use existing nodes and relationships
                2. Ensure all required JSON schema fields are mapped
                3. Ask for clarification if attribute mapping is ambiguous
                4. Consider semantic meaning when mapping fields
                """,
            },
            {
                "role": "user",
                "content": f"Data requirements: {addition_instruction}\nJSON schema: {json_schema}",
            },
        ],
        tools=tools,
    )


def execute_query(query: str) -> list:
    """Execute a Cypher query against the Neo4j database.

    Args:
        query: Valid Cypher query string

    Returns:
        list: Query results from Neo4j
    """
    return db.execute_query(query)


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

pprint(r2)

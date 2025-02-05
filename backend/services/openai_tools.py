get_cypher_query_tool = {
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
}

get_query_clarification_tool = {
    "type": "function",
    "function": {
        "name": "get_query_clarification",
        "description": """Request clarification about mapping database attributes to JSON schema fields.
            Use this when uncertain about attribute correspondence or when ambiguous candidates exist.""",
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
}

is_congruent_with_schema_tool = {
    "type": "function",
    "function": {
        "name": "is_congruent_with_schema",
        "description": "Check if available data structure is congruent with a specification text of a data structure.",
        "parameters": {
            "type": "object",
            "properties": {
                "is_congruent": {
                    "type": "boolean",
                    "description": "Whether the data structure is congruent with the specification.",
                },
                "missing_properties": {
                    "type": "array",
                    "description": "List of missing properties in the data structure.",
                    "items": {
                        "type": "string",  # Assuming the missing properties are strings (e.g., property names)
                    },
                },
                "existing_properties": {
                    "type": "array",
                    "description": "List of existing properties in the data structure.",
                    "items": {
                        "type": "string",
                    },
                },
                "explanation": {
                    "type": "string",
                    "description": "Explanation of why the data structure is congruent or not.",
                },
            },
            "required": [
                "is_congruent",
                "missing_properties",
                "existing_properties",
                "explanation",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


parse_data_structure_tool = {
    "type": "function",
    "function": {
        "name": "parse_data_model",
        "description": "Parse the provided data model text or JSON schema and extract the key attributes or nodes/relationships.",
        "parameters": {
            "type": "object",
            "properties": {
                "data_model_text": {
                    "type": "string",
                    "description": "The data model descriptive text or JSON schema that needs to be parsed.",
                }
            },
            "required": ["data_model_text"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}

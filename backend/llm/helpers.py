import inspect
from datetime import datetime
from typing import Callable, get_type_hints


def extract_parameters_schema(func: Callable) -> dict:
    """
    Extracts a parameters schema from a callable using type hints and function signature.

    Args:
        func (Callable): The function to analyze.

    Returns:
        dict: A schema describing the function's parameters.
    """
    if not callable(func):
        raise ValueError("Input must be a callable function or method.")

    # Get function signature and type hints
    signature = inspect.signature(func)
    type_hints = get_type_hints(func)

    # Construct the schema
    properties = {}
    required = []

    for param_name, param in signature.parameters.items():
        if param_name == "self":  # Skip 'self' for methods
            continue

        param_type = type_hints.get(
            param_name, "string"
        )  # Default to 'string' if type is not provided
        param_description = f"The parameter '{param_name}'."
        param_schema = {
            "type": _map_python_type_to_json_type(param_type),
            "description": param_description,
        }

        # Add the parameter to properties
        properties[param_name] = param_schema

        # If the parameter does not have a default, it is required
        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required if required else None,
        "additionalProperties": False,
    }


def _map_python_type_to_json_type(python_type):
    """
    Maps Python types to JSON schema types.

    Args:
        python_type: The Python type to map.

    Returns:
        str: The corresponding JSON schema type.
    """
    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    return type_mapping.get(python_type, "string")  # Default to 'string'


def construct_tool_string(func: Callable) -> dict:
    """
    Constructs a tool string for a callable with metadata.

    Args:
        func (Callable): The function to describe.

    Returns:
        str: A JSON-formatted tool string.
    """
    if not callable(func):
        raise ValueError("Input must be a callable function or method.")

    # Extract the function name, docstring, and parameters schema
    func_name = func.__name__
    docstring = inspect.getdoc(func) or "No description available."
    parameters_schema = extract_parameters_schema(func)

    # Construct the tool dictionary
    return {
        "type": "function",
        "function": {
            "name": func_name,
            "description": docstring.strip(),
            "parameters": parameters_schema,
        },
    }


# Example usage
def get_delivery_date(order_id: str, delivery_date: datetime):
    """
    Get the delivery date for a customer's order.

    Call this whenever you need to know the delivery date,
    for example when a customer asks 'Where is my package'.
    """
    pass


tool_string = construct_tool_string(get_delivery_date)
print(tool_string)

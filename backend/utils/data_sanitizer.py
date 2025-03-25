import math


def sanitize_data(data):
    """Sanitize data by replacing NaN and Infinity values with None."""
    if isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(sanitize_data(item) for item in data)
    elif isinstance(data, dict):
        return {key: sanitize_data(value) for key, value in data.items()}
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None  # Replace NaN and Infinity with None
        else:
            return data
    else:
        return data

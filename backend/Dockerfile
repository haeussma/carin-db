FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry

# Copy only dependency files first from the backend folder
COPY backend/pyproject.toml backend/poetry.lock* ./

# Configure poetry to not create a virtual environment in the container
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-root --no-interaction --no-ansi

# Copy the rest of the application
COPY . .

# Add the current directory to PYTHONPATH
ENV PYTHONPATH=/app

# Create logs directory
RUN mkdir -p /app/logs

# Ensure an empty .env file exists
RUN touch /app/.env

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application with hot reload
CMD ["sh", "-c", "poetry run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app"]

import json
import math
import os
import sys
from contextlib import asynccontextmanager
from io import BytesIO

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger

from .exceptions import TypeInconsistencyError
from .extractor import Extractor
from .fetch_external_api import fetch_uniprot_protein_fasta
from .models.graph_model import GraphModel
from .services.db_service import Database
from .services.openai_service import OpenAIService

ENV_FILE_PATH = "/app/.env"


# -----  Configure logger -----
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
)


# -----  Sanitize data -----
def sanitize_data(data):
    if isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, dict):
        return {key: sanitize_data(value) for key, value in data.items()}
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None  # Replace NaN and Infinity with None
        else:
            return data
    else:
        return data


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up FastAPI application")
    # Create uploads directory if it doesn't exist
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
        logger.info("Created uploads directory")
    yield


app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/upload")
async def upload_spreadsheet(file: UploadFile = File(...)):
    """Uploads the spreadsheet and returns the sheet model after validating data types and data consistency"""

    logger.info(f"Processing upload request for file: {file.filename}")
    try:
        # Save the uploaded file
        upload_dir = "uploads"
        file_path = os.path.join(upload_dir, str(file.filename))
        logger.debug(f"Saving file to {file_path}")

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        logger.debug("File saved successfully")

        extractor = Extractor(path=file_path)
        try:
            model = extractor.get_sheet_model()
            return {
                "status": "success",
                "data": model.model_dump(
                    mode="json"
                ),  # Use model_dump instead of model_dump_json
            }
        except TypeInconsistencyError as e:
            return JSONResponse(status_code=400, content=e.to_dict())
    except Exception as e:
        logger.error(f"Error processing upload request: {str(e)}")
        raise


@app.get("/api/test")
async def test():
    logger.debug("Test endpoint called")
    return {"message": "This is a test message from the backend!"}


@app.post("/api/ask")
async def ask(request: Request):
    """Handle ask requests with provided OpenAI API key."""
    try:
        body = await request.json()
        question = body.get("question", "")

        # Get OpenAI API key from header
        api_key = request.headers.get("X-OpenAI-Key")
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail={"error": {"message": "OpenAI API key is required"}},
            )

        # Initialize the OpenAI client
        try:
            # Create DB service for the OpenAI service with environment variables
            db_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
            db_user = os.environ.get("NEO4J_USER", "neo4j")
            db_password = os.environ.get("NEO4J_PASSWORD", "password")

            db_service = Database(uri=db_uri, user=db_user, password=db_password)
            openai_service = OpenAIService(db_service, api_key)

            # Process the request with OpenAI
            response = openai_service.create_chat_completion(
                [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": question},
                ]
            )

            return {"response": response.choices[0].message.content}
        except Exception as e:
            # Extract the detailed error message from OpenAI exceptions
            error_message = str(e)
            error_data = {}

            if hasattr(e, "response") and hasattr(e.response, "json"):
                try:
                    error_data = e.response.json()
                except:
                    pass

            logger.error(
                f"Error processing ask request: {error_message} - {error_data}"
            )

            status_code = 500
            if "401" in error_message or "invalid_api_key" in error_message:
                status_code = 401

            raise HTTPException(
                status_code=status_code,
                detail=error_data or {"error": {"message": error_message}},
            )

    except HTTPException:
        # Re-raise HTTP exceptions to preserve their status code and detail
        raise
    except Exception as e:
        logger.error(f"Error processing ask request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "An unexpected error occurred"}},
        )


@app.post("/api/generateSpreadsheet")
async def generate_spreadsheet(request: Request):
    try:
        front_payload = await request.json()
        data = front_payload.get("data")
        logger.info("Generating spreadsheet from data")

        if not data:
            logger.warning("No data provided for spreadsheet generation")
            return {"error": "No data provided"}

        # Convert data to pandas DataFrame
        df = pd.DataFrame(data)
        logger.debug(f"Created DataFrame with shape: {df.shape}")

        # Create an Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)

        output.seek(0)
        logger.info("Successfully generated spreadsheet")

        headers = {"Content-Disposition": 'attachment; filename="data.xlsx"'}
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )
    except Exception as e:
        logger.error(f"Error generating spreadsheet: {str(e)}")
        raise


@app.post("/api/process_file")
async def process_file(
    file: UploadFile = File(...),
    data: str = Form(...),
):
    """Process the uploaded file with the provided graph model configuration."""
    logger.info(f"Processing file {file.filename} with graph model data")
    try:
        # Save the uploaded file
        upload_dir = "uploads"
        file_path = os.path.join(upload_dir, str(file.filename))

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        logger.debug("File saved successfully")

        # Parse the graph model data
        model_data = json.loads(data)
        graph_model = GraphModel(
            sheet_connections=model_data["sheet_connections"],
            sheet_references=model_data["sheet_references"],
        )
        logger.debug("Graph model parsed successfully", graph_model)

        # Initialize database connection
        db_settings = get_db_settings()
        db = Database(
            uri=db_settings["url"],
            user=db_settings["username"],
            password=db_settings["password"],
        )
        logger.debug("Database connection established")

        # Process the file using the extractor
        extractor = Extractor(path=file_path)
        extractor.new_extract(db=db, graph_model=graph_model)
        logger.info("File processed and data extracted to database successfully")

        return {
            "status": "success",
            "message": "File processed and data extracted to database successfully",
        }
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": str(e),
            },
        )


@app.post("/api/proteins")
async def fetch_proteins(request: Request):
    try:
        payload = await request.json()
        uniprot_ids = payload.get("uniprot_ids", [])

        if not isinstance(uniprot_ids, list):
            return {"error": "uniprot_ids must be a list of strings"}, 400

        if not uniprot_ids:
            return {"error": "No UniProt IDs provided"}, 400

        logger.info(f"Fetching sequences for {len(uniprot_ids)} proteins")
        sequences = await fetch_uniprot_protein_fasta(uniprot_ids)

        return {"sequences": sequences}
    except Exception as e:
        logger.error(f"Error fetching protein sequences: {str(e)}")
        raise


# -----  Environment variables -----
@app.post("/api/save_openai_key")
async def save_openai_key(request: Request):
    """Save OpenAI API key to environment file."""
    try:
        payload = await request.json()
        api_key = payload.get("api_key")

        if not api_key:
            raise HTTPException(
                status_code=400, detail={"error": {"message": "API key is required"}}
            )

        # Read existing .env values
        env_data = {}
        if os.path.exists(ENV_FILE_PATH):
            with open(ENV_FILE_PATH, "r") as f:
                for line in f:
                    key, _, value = line.strip().partition("=")
                    env_data[key] = value

        # Update or add new values
        env_data["OPENAI_API_KEY"] = api_key

        # Write back to .env file
        with open(ENV_FILE_PATH, "w") as f:
            f.writelines(f"{key}={value}\n" for key, value in env_data.items())

        return {"message": "API key saved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving OpenAI API key: {str(e)}")
        raise HTTPException(
            status_code=500, detail={"error": {"message": "Failed to save API key"}}
        )


@app.get("/api/get_openai_key")
async def get_openai_key():
    """Retrieve the OpenAI API Key from .env file."""
    if not os.path.exists(ENV_FILE_PATH):
        return {"error": "No API key found"}, 404

    with open(ENV_FILE_PATH, "r") as f:
        for line in f:
            if line.startswith("OPENAI_API_KEY="):
                return {"api_key": line.split("=", 1)[1].strip()}

    return {"error": "API key not found"}, 404


# -----  Database settings -----
@app.get("/api/get_db_settings")
async def get_db_settings():
    # Read existing .env file
    env_lines = []
    if os.path.exists(ENV_FILE_PATH):
        with open(ENV_FILE_PATH, "r") as f:
            env_lines = f.readlines()

    url = username = password = None

    # Update or add OPENAI_API_KEY
    for line in env_lines:
        if line.startswith("NEO4J_URI="):
            url = line.split("=", 1)[1].strip()
        if line.startswith("NEO4J_USER="):
            username = line.split("=", 1)[1].strip()
        if line.startswith("NEO4J_PASSWORD="):
            password = line.split("=", 1)[1].strip()

    if not all([url, username, password]):
        logger.warning("Database settings not found")

    return {
        "url": url,
        "username": username,
        "password": password,
    }


@app.post("/api/save_db_settings")
async def save_db_settings(request: Request):
    """Update or create Neo4j database settings in .env."""
    payload = await request.json()
    new_values = {
        "NEO4J_URI": payload.get("url"),
        "NEO4J_USER": payload.get("username"),
        "NEO4J_PASSWORD": payload.get("password"),
    }

    # Read existing .env values
    env_data = {}
    if os.path.exists(ENV_FILE_PATH):
        with open(ENV_FILE_PATH, "r") as f:
            for line in f:
                key, _, value = line.strip().partition("=")
                env_data[key] = value

    # Update or add new values
    env_data.update({k: v for k, v in new_values.items() if v is not None})

    # Write back to .env file
    with open(ENV_FILE_PATH, "w") as f:
        f.writelines(f"{key}={value}\n" for key, value in env_data.items())

    return {"message": "Neo4j settings updated successfully"}


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting uvicorn server")
    uvicorn.run(app, host="0.0.0.0", port=8000)

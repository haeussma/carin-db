import json
import math
import os
import sys
from contextlib import asynccontextmanager
from io import BytesIO

import pandas as pd
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger

from .chat import Chat
from .exceptions import TypeInconsistencyError
from .extractor import Extractor
from .fetch_external_api import fetch_uniprot_protein_fasta
from .models.graph_model import GraphModel
from .services.db_service import Database

# Configure logger
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
)

# Database configuration
DB_HOST = os.getenv("DATABASE_HOST", "neo4j")  # Use service name from docker-compose
DB_PORT = os.getenv("DATABASE_PORT", "7687")  # Use internal Neo4j port
DB_USER = os.getenv("NEO4J_USER", "neo4j")
DB_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")
DB_URI = f"bolt://{DB_HOST}:{DB_PORT}"


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
    try:
        front_payload = await request.json()
        question = front_payload.get("question")
        api_key = request.headers.get("X-OpenAI-Key")

        if not api_key:
            logger.error("No OpenAI API key provided")
            return {"error": "OpenAI API key is required"}, 401

        logger.info(f"Received question: {question}")

        db = Database(uri=DB_URI, user=DB_USER, password=DB_PASSWORD)
        logger.debug("Connected to database")

        chat = Chat(api_key=api_key)
        data = chat.get_data_from_db(question, db)
        logger.debug(f"Raw data from database: {data}")

        sanitized_data = sanitize_data(data)
        logger.debug(f"Sanitized data: {sanitized_data}")

        return {"result": sanitized_data}
    except Exception as e:
        logger.error(f"Error processing ask request: {str(e)}")
        raise


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
        db = Database(uri=DB_URI, user=DB_USER, password=DB_PASSWORD)
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


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting uvicorn server")
    uvicorn.run(app, host="0.0.0.0", port=8000)

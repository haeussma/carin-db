import json
import math
import os
import sys
from io import BytesIO

import pandas as pd
from chat import Chat
from extractor import Database, Extractor
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger
from models import Relationship

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


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up FastAPI application")
    # Create uploads directory if it doesn't exist
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
        logger.info("Created uploads directory")


@app.post("/api/upload")
async def upload_spreadsheet(file: UploadFile = File(...)):
    logger.info(f"Processing upload request for file: {file.filename}")
    try:
        # Save the uploaded file
        db = Database(uri=DB_URI, user=DB_USER, password=DB_PASSWORD)
        logger.debug(f"Connected to database at {DB_URI}")

        upload_dir = "uploads"
        file_path = os.path.join(upload_dir, file.filename)
        logger.debug(f"Saving file to {file_path}")

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        logger.debug("File saved successfully")

        extractor = Extractor(path=file_path, db=db, primary_key="ID")
        nodes = extractor.get_node_names_from_sheet_and_db()
        logger.info(f"Successfully processed file. Found nodes: {nodes}")
        return nodes
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        raise


@app.post("/api/chat")
async def chat(message: str, to_file: bool):
    logger.info(f"Received chat request: {message[:50]}...")
    return {"response": "AI response goes here"}


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
    primary_key: str = Form(...),
    file: UploadFile = File(...),
    relationships: str = Form(None),
):
    logger.info(f"Processing file: {file.filename}")
    logger.debug(f"Primary key: {primary_key}")
    logger.debug(f"Relationships: {relationships}")

    try:
        # Save the uploaded file
        upload_dir = "uploads"
        file_path = os.path.join(upload_dir, file.filename)
        logger.debug(f"Saving file to {file_path}")

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        logger.debug("File saved successfully")

        if relationships:
            relationships = json.loads(relationships)
            parsed_relationships = [Relationship(**rel) for rel in relationships]
            logger.debug(f"Parsed relationships: {parsed_relationships}")

        # Initialize database connection
        db = Database(uri=DB_URI, user=DB_USER, password=DB_PASSWORD)
        logger.info("Connected to database")

        # Process the file
        ex = Extractor(path=file_path, db=db, primary_key=primary_key)
        ex.extract_file()
        ex.create_relationships(parsed_relationships)
        ex.unify_nodes()

        logger.info(f"File processed successfully: {file.filename}")
        return {"message": "File processed successfully", "file_name": file.filename}
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting uvicorn server")
    uvicorn.run(app, host="0.0.0.0", port=8000)

import json
import math
import os
from io import BytesIO

import pandas as pd
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger

from backend.chat import Chat
from backend.extractor import Database, Extractor
from backend.models import Relationship


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


@app.post("/api/upload")
async def upload_spreadsheet(file: UploadFile = File(...)):
    # Save the uploaded file
    db = Database(uri="bolt://localhost:7689", user="neo4j", password="12345678")
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    extractor = Extractor(path=file_path, db=db, primary_key="ID")
    nodes = extractor.get_node_names_from_sheet_and_db()
    return nodes


@app.post("/api/chat")
async def chat(message: str, to_file: bool):
    return {"response": "AI response goes here"}


@app.get("/api/test")
async def test():
    return {"message": "This is a test message from the backend!"}


@app.post("/api/ask")
async def ask(request: Request):
    front_payload = await request.json()
    question = front_payload.get("question")
    logger.debug(f"Received question: {question}")

    db = Database(uri="bolt://localhost:7689", user="neo4j", password="12345678")

    chat = Chat()
    data = chat.get_data_from_db(question, db)
    logger.debug(f"Data before flattening: {data}")

    # Flatten the data by extracting the first (and only) value from each item
    # data = [next(iter(item.values())) for item in data]
    logger.debug(f"Data after flattening: {data}")

    data = sanitize_data(data)
    logger.debug(f"Sanitized data: {data}")

    return {"result": data}


@app.post("/api/generateSpreadsheet")
async def generate_spreadsheet(request: Request):
    front_payload = await request.json()
    data = front_payload.get("data")
    if not data:
        return {"error": "No data provided"}

    # Convert data to pandas DataFrame
    df = pd.DataFrame(data)

    # Create an Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
        # No need to call writer.save() here

    output.seek(0)  # Rewind the buffer

    # Prepare response
    headers = {"Content-Disposition": 'attachment; filename="data.xlsx"'}
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.post("/api/process_file")
async def process_file(
    primary_key: str = Form(...),
    file: UploadFile = File(...),
    relationships: str = Form(None),
):
    logger.info(f"Processing file: {file.filename}")
    logger.debug(f"Primary key: {primary_key}")
    logger.debug(f"Relationships: {relationships}")

    # Save the uploaded file
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    file_path = os.path.join(upload_dir, file.filename)
    logger.debug(f"Adding file to {file_path}")
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    logger.debug(f"File saved to {file_path}")

    if relationships:
        relationships = json.loads(relationships)
        print(relationships)
        parsed_relationships = [Relationship(**rel) for rel in relationships]
    logger.debug(f"Relationships: {parsed_relationships}")

    # print status message
    logger.info(f"File saved to {file_path}")

    # Parse relationships string into Relationship objects
    # parsed_relationships = [
    #     Relationship(
    #         name=rel.split(":")[0].strip(),
    #         source=rel.split(":")[1].strip(),
    #         target=rel.split(":")[2].strip(),
    #     )
    #     for rel in relationships.split(",")
    # ]

    # Initialize and execute the Extractor
    db = Database(
        uri="bolt://localhost:7689", user="neo4j", password="12345678"
    )  # Update with your actual credentials
    # log status message for successful connection
    logger.info(f"Connected to the database {db.driver}")
    ex = Extractor(
        path=file_path,
        db=db,
        primary_key=primary_key,
    )
    ex.extract_file()
    ex.create_relationships(parsed_relationships)
    ex.unify_nodes()

    return {"message": "File processed successfully", "file_name": file.filename}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

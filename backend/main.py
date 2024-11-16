import json
import os

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.extractor import Database, Extractor
from backend.models import Relationship

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
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    return {"message": "File uploaded successfully", "file_name": file.filename}


@app.post("/api/chat")
async def chat(message: str):
    # Implement your chat logic here
    return {"response": "AI response goes here"}


@app.get("/api/test")
async def test():
    return {"message": "This is a test message from the backend!"}


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

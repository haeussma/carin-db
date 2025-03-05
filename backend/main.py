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
        logger.debug(f"Received model data: {model_data}")

        graph_model = GraphModel(
            sheet_connections=model_data["sheet_connections"],
            sheet_references=model_data["sheet_references"],
        )
        logger.debug(f"Graph model parsed successfully: {graph_model}")
        # write model data to file
        with open("graph_model.json", "w") as f:
            json.dump(graph_model.model_dump(mode="json"), f)

        # Initialize database connection
        db_settings = await get_db_settings()
        logger.debug(f"Database settings: \n{db_settings}")
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
        error_message = str(e)
        logger.error(f"Error processing file: {error_message}")

        # Return a more detailed error response
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Error processing file",
                "detail": error_message,
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
    """Save OpenAI API key to environment variables."""
    try:
        payload = await request.json()
        api_key = payload.get("api_key")

        if not api_key:
            raise HTTPException(
                status_code=400, detail={"error": {"message": "API key is required"}}
            )

        # Set environment variable directly
        os.environ["OPENAI_API_KEY"] = api_key
        logger.info("OpenAI API key saved to environment variables")

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
    """Retrieve the OpenAI API Key from environment variables."""
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        return {"error": "API key not found"}, 404

    return {"api_key": api_key}


# -----  Database settings -----
@app.get("/api/get_db_settings")
async def get_db_settings():
    """Get database settings from environment variables."""
    url = os.environ.get("NEO4J_URI")
    username = os.environ.get("NEO4J_USER")
    password = os.environ.get("NEO4J_PASSWORD")

    if not all([url, username, password]):
        logger.warning("Database settings not found in environment variables")

    return {
        "url": url,
        "username": username,
        "password": password,
    }


@app.post("/api/save_db_settings")
async def save_db_settings(request: Request):
    """Update Neo4j database settings in environment variables."""
    payload = await request.json()

    # Update environment variables with new values
    if payload.get("url") is not None:
        os.environ["NEO4J_URI"] = payload.get("url")

    if payload.get("username") is not None:
        os.environ["NEO4J_USER"] = payload.get("username")

    if payload.get("password") is not None:
        os.environ["NEO4J_PASSWORD"] = payload.get("password")

    logger.info("Neo4j settings updated in environment variables")
    return {"message": "Neo4j settings updated successfully"}


# Helper function to get database settings directly
def _get_db_settings_direct():
    url = os.environ.get("NEO4J_URI")
    username = os.environ.get("NEO4J_USER")
    password = os.environ.get("NEO4J_PASSWORD")

    # Docker container networking fix:
    # If we detect localhost in the URL and we're running in Docker,
    # replace it with the proper container service name
    if url and "localhost" in url:
        # Check if we're running in Docker
        if os.path.exists("/.dockerenv"):
            # Replace localhost with neo4j service name and use internal port
            docker_url = url.replace("localhost", "neo4j")
            # Ensure we're using the internal port 7687, not the exposed 7692
            if ":7692" in docker_url:
                docker_url = docker_url.replace(":7692", ":7687")
            logger.info(
                f"Docker environment detected. Changed Neo4j URL from {url} to {docker_url}"
            )
            url = docker_url

    return {
        "url": url,
        "username": username,
        "password": password,
    }


@app.get("/api/get_node_count")
async def get_node_count():
    try:
        db_settings = _get_db_settings_direct()

        # Check if we have valid database settings
        if not all(
            [db_settings["url"], db_settings["username"], db_settings["password"]]
        ):
            return {
                "error": "Database connection settings are not configured. Please set them in Settings."
            }

        try:
            db = Database(
                uri=db_settings["url"],
                user=db_settings["username"],
                password=db_settings["password"],
            )
            return db.node_count
        except Exception as conn_err:
            # Handle specific connection errors with helpful messages
            error_str = str(conn_err)

            if "Connection refused" in error_str:
                port = "7687"  # Default Neo4j port
                # Try to extract port from URL if possible
                if db_settings["url"] and ":" in db_settings["url"]:
                    port = db_settings["url"].split(":")[-1]

                # Check if we're in Docker environment
                is_docker = os.path.exists("/.dockerenv")

                if is_docker and "localhost" in db_settings["url"]:
                    return {
                        "error": f"Cannot connect to Neo4j database. Docker networking issue detected.\n\n"
                        f"When using Docker, you should connect to the Neo4j container using the service name:\n"
                        f"• Change connection URL from '{db_settings['url']}' to 'neo4j:7687'\n"
                        f"• Or update your .env file with: NEO4J_URI=bolt://neo4j:7687"
                    }
                else:
                    return {
                        "error": f"Cannot connect to Neo4j database at port {port}. Please ensure that:\n\n"
                        f"1. Neo4j server is running\n"
                        f"2. The configured URL ({db_settings['url']}) is correct\n"
                        f"3. No firewall is blocking the connection"
                    }
            elif (
                "authentication failure" in error_str.lower()
                or "unauthorized" in error_str.lower()
            ):
                return {
                    "error": "Authentication failed. Please check your Neo4j username and password in Settings."
                }
            else:
                # Return general connection error
                return {"error": f"Database connection error: {str(conn_err)}"}

    except Exception as e:
        logger.error(f"Error getting node count: {e}")
        return {"error": f"Failed to get node count: {str(e)}"}


# If you had a clear_openai_key function, update it as well
@app.post("/api/clear_openai_key")
async def clear_openai_key():
    """Clear the OpenAI API key from environment variables."""
    try:
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
            logger.info("OpenAI API key removed from environment variables")

        return {"message": "API key cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing OpenAI API key: {str(e)}")
        raise HTTPException(
            status_code=500, detail={"error": {"message": "Failed to clear API key"}}
        )


@app.get("/api/load_graph_model")
def load_graph_model():
    """Loads a `GraphModel` from file.
    Returns empty dict if file does not exist."""
    try:
        # Use absolute path to ensure file is found regardless of where the server is started
        file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "graph_model.json"
        )
        logger.info(f"Loading graph model from: {file_path}")

        with open(file_path, "r") as f:
            data = json.load(f)
            logger.info(f"Loaded graph model: {data}")
            return data
    except FileNotFoundError:
        logger.info("No graph model file found")
        return {}


@app.post("/api/save_graph_model")
async def save_graph_model(request: Request):
    """Saves a `GraphModel` to file."""
    try:
        data = await request.json()
        logger.info(f"Saving graph model: {data}")

        # Use absolute path to ensure file is saved in a consistent location
        file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "graph_model.json"
        )
        logger.info(f"Saving graph model to: {file_path}")

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        return {"status": "success", "message": "Graph model saved successfully"}
    except Exception as e:
        logger.error(f"Error saving graph model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Failed to save graph model: {str(e)}",
            },
        )


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting uvicorn server")
    uvicorn.run(app, host="0.0.0.0", port=8000)

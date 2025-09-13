import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger

from backend.routes.projects import PROJECT_DIR

from ..exceptions import SpreadsheetValidationError
from ..spreadsheet import Spreadsheet

router = APIRouter(prefix="/spreadsheet")

# Define uploads directory relative to project root
UPLOAD_DIR = Path("uploads")


# convenience method so save uploaded file to temporary directory and return the path
async def write_temp_file(file: UploadFile) -> str:
    """Saves the uploaded file to the temporary directory and returns the path."""
    temp_dir = tempfile.mkdtemp()
    path = Path(temp_dir) / str(file.filename)
    logger.debug(f"Saving temporary file to: {path}")
    with open(path, "wb") as buffer:
        content = await file.read()
        if not content:
            raise ValueError("Uploaded file is empty")
        buffer.write(content)
    logger.debug(f"Temporary file saved successfully at: {path}")
    return str(path)


@router.post("/upload", tags=["Spreadsheet"])
async def upload_spreadsheet(file: UploadFile = File(...)):
    """Uploads the spreadsheet and returns the file path.

    Returns:
        str: The absolute path to the uploaded file
    """
    try:
        if not file:
            raise ValueError("No file provided")

        logger.info(f"Processing upload request for file: {file.filename}")

        # Ensure upload directory exists
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # Create file path using Path for consistent handling
        file_path = UPLOAD_DIR / str(file.filename)

        logger.debug(f"Saving file to: {file_path}")

        # Save the file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            if not content:
                raise ValueError("Uploaded file is empty")
            buffer.write(content)

        logger.info(f"File saved successfully at: {file_path}")
        # Return plain path without quotes
        return str(file_path)

    except ValueError as e:
        logger.error(f"Upload validation error: {str(e)}")
        raise HTTPException(
            status_code=400, detail={"status": "error", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Error uploading file: {str(e)}"},
        )


@router.post("/upload-schema", tags=["Spreadsheet"])
async def upload_schema(project_name: str, file: UploadFile = File(...)) -> None:
    """Uploads the schema, validates it, and saves the project."""
    path = await write_temp_file(file)
    try:
        spreadsheet = Spreadsheet(path)
        project = spreadsheet.to_project(project_name)

        # Save the project to the backend
        with open(PROJECT_DIR / f"{project_name}.json", "w") as f:
            f.write(project.model_dump_json(indent=4))
        logger.info(f"Saved imported project: {PROJECT_DIR / f'{project_name}.json'}")

    except SpreadsheetValidationError as e:
        logger.error(f"Spreadsheet validation error: {e}")
        raise HTTPException(status_code=422, detail=e.to_dict())

    finally:
        Path(path).unlink()

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger

from backend.model import GraphSheetModel
from backend.routes.projects import PROJECT_DIR

from ..exceptions import SpreadsheetValidationError
from ..spreadsheet import load_sheets

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


@router.post("/upload-schema", tags=["Spreadsheet"])
async def upload_schema(project_name: str, file: UploadFile = File(...)) -> None:
    """Uploads the schema, validates it, and saves the project."""
    path = await write_temp_file(file)
    sheets = load_sheets(path)
    try:
        project = GraphSheetModel.from_spreadsheet_data(project_name, sheets, path)
        # Save the project to the backend
        with open(PROJECT_DIR / f"{project_name}.json", "w") as f:
            f.write(project.model_dump_json(indent=4))
        logger.info(
            f"💾 Saved imported project: {PROJECT_DIR / f'{project_name}.json'}"
        )

    except SpreadsheetValidationError as e:
        logger.error(f"Spreadsheet validation error: {e}")
        raise HTTPException(status_code=422, detail=e.to_dict())

    finally:
        Path(path).unlink()

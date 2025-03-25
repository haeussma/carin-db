import json

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger

from ...exceptions import TypeInconsistencyError
from ...services.spreadsheet_service import SpreadsheetService

router = APIRouter(prefix="/spreadsheet")


@router.post("/upload")
async def upload_spreadsheet(file: UploadFile = File(...)):
    """Uploads the spreadsheet and returns the file path"""
    logger.info(f"Processing upload request for file: {file.filename}")
    try:
        # Save the uploaded file
        file_path = await SpreadsheetService.save_uploaded_file(file)
        logger.debug(f"File saved to {file_path}")

        return {
            "status": "success",
            "file_path": file_path,
        }
    except Exception as e:
        logger.error(f"Error processing upload request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": f"Error processing upload request: {str(e)}"}},
        )


@router.post("/validate")
async def validate_spreadsheet(file_path: str):
    """Validates the spreadsheet and returns the sheet model after checking data types and consistency"""
    logger.info(f"Validating spreadsheet at path: {file_path}")
    try:
        # Extract sheet model
        extractor = SpreadsheetService.SheetExtractor(path=file_path)
        model = extractor.get_sheet_model()

        return {
            "status": "success",
            "data": model.model_dump(mode="json"),
        }
    except TypeInconsistencyError as e:
        return JSONResponse(status_code=400, content=e.to_dict())
    except Exception as e:
        logger.error(f"Error validating spreadsheet: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": f"Error validating spreadsheet: {str(e)}"}},
        )


@router.post("/generate")
async def generate_spreadsheet(request: Request):
    """Generate a spreadsheet from provided data."""
    try:
        payload = await request.json()
        data = payload.get("data", [])

        if not data:
            logger.warning("No data provided for spreadsheet generation")
            return JSONResponse(status_code=400, content={"error": "No data provided"})

        # Generate spreadsheet using the service
        output = SpreadsheetService.generate_spreadsheet(data)

        headers = {"Content-Disposition": 'attachment; filename="data.xlsx"'}
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )
    except Exception as e:
        logger.error(f"Error generating spreadsheet: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": f"Error generating spreadsheet: {str(e)}"}},
        )


@router.post("/process")
async def process_file(
    file: UploadFile = File(...),
    data: str = Form(...),
    db_name: str = Form("default"),
):
    """Process the uploaded file with the provided graph model configuration."""
    logger.info(f"Processing file {file.filename} with graph model data")
    try:
        # Save the uploaded file
        file_path = await SpreadsheetService.save_uploaded_file(file)
        logger.debug(f"File saved to {file_path}")

        # Parse the graph model data
        model_data = json.loads(data)
        logger.debug(f"Received model data: {model_data}")

        # Process the file using the spreadsheet service
        await SpreadsheetService.process_file(file_path, model_data, db_name)

        return {
            "status": "success",
            "message": "File processed and data extracted to database successfully",
        }
    except ValueError as e:
        error_message = str(e)
        logger.error(f"Validation error processing file: {error_message}")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Error processing file",
                "detail": error_message,
            },
        )
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error processing file: {error_message}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Error processing file",
                "detail": error_message,
            },
        )


@router.get("/model")
async def get_graph_model(db_name: str = "default"):
    """Get the graph model for a database."""
    try:
        model = SpreadsheetService.load_graph_model(db_name)
        if not model:
            return {"model": {}}
        return {"model": model}
    except Exception as e:
        logger.error(f"Error loading graph model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": f"Error loading graph model: {str(e)}"}},
        )


@router.post("/model")
async def save_graph_model(request: Request, db_name: str = "default"):
    """Save a graph model for a database."""
    try:
        data = await request.json()
        SpreadsheetService.save_graph_model(data, db_name)
        return {"status": "success", "message": "Graph model saved successfully"}
    except Exception as e:
        logger.error(f"Error saving graph model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": f"Error saving graph model: {str(e)}"}},
        )

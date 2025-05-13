from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from loguru import logger

from ...exceptions import TypeInconsistencyError
from ...models.appconfig import SheetModel
from ...services.config_service import ConfigService
from ...services.sheet_extractor import SheetModelBuilder
from ...services.spreadsheet_service import SpreadsheetService

router = APIRouter(prefix="/spreadsheet")


@router.post("/upload")
async def upload_spreadsheet(file: UploadFile = File(...)):
    """Uploads the spreadsheet and returns the file path and sheet model"""
    logger.info(f"Processing upload request for file: {file.filename}")

    spreadsheet_service = SpreadsheetService()
    try:
        path = await spreadsheet_service.save_uploaded_file(file)
        logger.debug(f"File saved to {path}")

        builder = SheetModelBuilder(path=path)
        builder.validate_spreadsheet_data()
        sheets = builder.get_sheets()

        logger.info(
            f"Spreadsheet uploaded and content validated successfully to {path}"
        )
        return {
            "status": "success",
            "file_path": path,
            "sheets": sheets,
        }
    except TypeInconsistencyError as e:
        return JSONResponse(status_code=400, content=e.to_dict())
    except Exception as e:
        logger.error(f"Error processing upload request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": f"Error processing upload request: {str(e)}"}},
        )


@router.post("/process")
async def process_spreadsheet(
    request: Request,
):
    """Upload and process a spreadsheet with the provided graph model configuration.

    This endpoint combines upload and process into a single operation.
    """
    logger.info("Processing spreadsheet")
    try:
        data = await request.json()
        file_path = data.get("file_path")
        sheet_model = data.get("sheet_model")

        # Process the file using the spreadsheet service
        db_info = ConfigService.get_first_database()
        spreadsheet_service = SpreadsheetService()
        spreadsheet_service.save_sheet_model(
            path=file_path,
            sheet_connections=sheet_model.get("sheet_connections", []),
            sheet_references=sheet_model.get("sheet_references", []),
            db_uri=db_info.uri,
        )
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
async def get_graph_model():
    """Get the graph model for a database."""

    spreadsheet_service = SpreadsheetService()

    # Get the first database
    try:
        model = spreadsheet_service.load_sheet_model()
    except ValueError:
        return {"model": {}}
    return {"model": model}


@router.post("/model")
async def save_graph_model(request: Request):
    """Save a graph model for a database."""
    try:
        logger.debug("Initializing save graph model")
        data = await request.json()
        db_info = ConfigService.get_first_database()
        logger.debug(f"Database info: {db_info}")

        service = SpreadsheetService()
        service.save_sheet_model(
            path=data.get("file_path"),
            sheet_connections=data.get("sheet_connections"),
            sheet_references=data.get("sheet_references"),
            db_uri=db_info.uri,
        )
        logger.debug(f"Graph model {data} saved successfully")
        return {"status": "success", "message": "Graph model saved successfully"}
    except Exception as e:
        logger.error(f"Error saving graph model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": f"Error saving graph model: {str(e)}"}},
        )


@router.delete("/model")
async def delete_graph_model():
    """Delete the graph model for a database."""
    spreadsheet_service = SpreadsheetService()
    spreadsheet_service.delete_sheet_model()
    return {"status": "success", "message": "Graph model deleted successfully"}


# @router.post("/generate")
# async def generate_spreadsheet(request: Request):
#     """Generate a spreadsheet from provided data."""
#     try:
#         payload = await request.json()
#         data = payload.get("data", [])

#         if not data:
#             logger.warning("No data provided for spreadsheet generation")
#             return JSONResponse(status_code=400, content={"error": "No data provided"})

#         # Generate spreadsheet using the service
#         output = SpreadsheetService.generate_spreadsheet(data)

#         headers = {"Content-Disposition": 'attachment; filename="data.xlsx"'}
#         return StreamingResponse(
#             output,
#             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#             headers=headers,
#         )
#     except Exception as e:
#         logger.error(f"Error generating spreadsheet: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail={"error": {"message": f"Error generating spreadsheet: {str(e)}"}},
#         )


if __name__ == "__main__":
    import asyncio

    from ...models.appconfig import SheetReferences

    data_path = "test_data/lilly_data.xlsx"

    # dummy sheet model
    sheet_references = [
        SheetReferences(
            source_sheet_name="Reaction",
            source_column_name="reaction_id",
            target_sheet_name="Measurement",
            target_column_name="has_reaction",
        )
    ]
    sheet_model = SheetModel(
        sheet_connections=[],
        sheet_references=[],
    )

    # test process endpoint
    asyncio.run(process_spreadsheet(request=Request(scope={})))

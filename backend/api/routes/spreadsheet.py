import os
from io import BytesIO
from pathlib import Path
from typing import Annotated, Any, Dict, List

import pandas as pd
from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger
from pydantic import BaseModel

from backend.models.model import SheetModel
from backend.services.database import DB
from backend.services.database_populator import DatabasePopulator
from backend.services.sheet_extractor import SheetModelBuilder

router = APIRouter(prefix="/spreadsheet")

# Define uploads directory relative to project root
UPLOAD_DIR = Path("uploads")


class SpreadsheetRequest(BaseModel):
    data: List[Dict[str, Any]]


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


@router.post("/validate_spreadsheet", tags=["Spreadsheet"])
async def validate_spreadsheet(path: str):
    """Validates a spreadsheet and returns its structure.

    Returns:
        On success: {
            "status": "success",
            "file_path": str,
            "sheets": List[Sheet]
        }
        On validation error: {
            "status": "error",
            "type_inconsistencies": List[TypeInconsistencyLocation],
            "message": str
        }
    """
    try:
        if not path:
            raise ValueError("No file path provided")

        # Strip quotes and decode URL-encoded characters
        path = path.strip('"').strip("'")

        # Check if absolute path exists
        if os.path.isabs(path) and os.path.exists(path):
            file_path = path
        # If not absolute and not at uploads/ prefix
        elif not path.startswith("uploads/") and not path.startswith("/"):
            # Try with uploads/ prefix
            file_path = os.path.join("uploads", path)
        else:
            file_path = path

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at path: {file_path}")

        builder = SheetModelBuilder(path=file_path)
        validation_errors = builder.validate_spreadsheet_data()

        if validation_errors:
            logger.warning(f"Found {len(validation_errors)} type inconsistencies")
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "type_inconsistencies": [
                        error.model_dump() for error in validation_errors
                    ],
                    "message": "Type inconsistencies found in spreadsheet",
                },
            )

        sheets = builder.get_sheets()
        logger.info(f"Spreadsheet validated successfully: {file_path}")

        return {"status": "success", "file_path": file_path, "sheets": sheets}

    except FileNotFoundError as e:
        logger.error(f"File not found error: {str(e)}")
        raise HTTPException(
            status_code=404, detail={"status": "error", "message": str(e)}
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400, detail={"status": "error", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Error validating spreadsheet: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Error validating spreadsheet: {str(e)}",
            },
        )


@router.post("/process", tags=["Spreadsheet"])
async def process_spreadsheet(
    file_path: Annotated[str, Body()],
    db: DB,
):
    """Reads a spreadsheet and populates the database with the data.
    According to the sheet model, the data is mapped to the database.
    """
    try:
        logger.info("Processing spreadsheet")

        if not file_path:
            raise ValueError("No file path provided")

        # Strip quotes from the path if present
        file_path = file_path.strip('"').strip("'")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at path: {file_path}")

        # get sheet model from file
        try:
            with open("uploads/sheet_model.json", "r") as f:
                sheet_model = SheetModel.model_validate_json(f.read())
        except FileNotFoundError:
            raise ValueError("Sheet model not found. Please save the model first.")
        except Exception as e:
            raise ValueError(f"Error reading sheet model: {str(e)}")

        logger.info(f"Process using file path: {file_path}")

        logger.debug(f"sheet model received with keys: {sheet_model.__dict__.keys()}")

        # Populate DB
        # load sheets from file
        builder = SheetModelBuilder(path=file_path)
        sheets = builder.sheets
        db_populator = DatabasePopulator(
            sheets=sheets,
            source_file=file_path,
        )
        db_populator.extract_to_db(db, sheet_model)

        # Return success
        return {"message": "Spreadsheet processed successfully"}

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400, detail={"status": "error", "message": str(e)}
        )
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise HTTPException(
            status_code=404, detail={"status": "error", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Error processing spreadsheet: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Error processing spreadsheet: {str(e)}",
            },
        )


@router.post("/generate", tags=["Spreadsheet"])
async def generate_spreadsheet(request: SpreadsheetRequest):
    logger.info("Generating spreadsheet from data")

    if not request.data:
        logger.warning("No data provided for spreadsheet generation")
        raise HTTPException(status_code=400, detail="No data provided")

    # Convert data to pandas DataFrame
    df = pd.DataFrame(request.data)
    logger.debug(f"Created DataFrame with shape: {df.shape}")

    # Create an Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")

        # Get the workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets["Data"]

        # Add some formatting
        header_format = workbook.add_format(
            {
                "bold": True,
                "text_wrap": True,
                "valign": "top",
                "bg_color": "#D9E1F2",
                "border": 1,
            }
        )

        # Write the column headers with the defined format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            # Set column width based on content
            max_length = max(df[value].astype(str).apply(len).max(), len(str(value)))
            worksheet.set_column(col_num, col_num, max_length + 2)

    output.seek(0)
    logger.info("Successfully generated spreadsheet")

    headers = {
        "Content-Disposition": 'attachment; filename="data.xlsx"',
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )

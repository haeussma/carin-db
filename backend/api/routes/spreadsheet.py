import os
from io import BytesIO
from pathlib import Path
from typing import Annotated, Any, Dict, List

import pandas as pd
from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger
from pydantic import BaseModel

from backend.api.routes.deps import get_db
from backend.models.model import SheetModel
from backend.services.database import Database
from backend.services.database_populator import DatabasePopulator
from backend.services.spreadsheet_validator import SpreadsheetValidator

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

        builder = SpreadsheetValidator(path=file_path)
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


# 3. Update the /process endpoint to include compatibility check:


@router.post("/process", tags=["Spreadsheet"])
async def process_spreadsheet(
    file_path: Annotated[str, Body()],
    db: Annotated[Database, Depends(get_db)],
    force_process: Annotated[bool, Body()] = False,
):
    """
    Reads a spreadsheet and populates the database with the data.
    If force_process=False, will check compatibility first.
    """
    try:
        logger.info("Processing spreadsheet")

        if not file_path:
            raise ValueError("No file path provided")

        file_path = file_path.strip('"').strip("'")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at path: {file_path}")

        # Load and validate spreadsheet
        builder = SpreadsheetValidator(path=file_path)
        validation_errors = builder.validate_spreadsheet_data()

        if validation_errors:
            raise ValueError("Spreadsheet has validation errors")

        # Check compatibility unless forced
        if not force_process:
            from backend.services.schema_compatibility_checker import (
                SchemaCompatibilityChecker,
            )

            compatibility_checker = SchemaCompatibilityChecker(db)
            compatibility_result = compatibility_checker.check_compatibility(
                builder.get_sheets()
            )

            if (
                not compatibility_result.is_compatible
                and not compatibility_result.can_auto_resolve
            ):
                return {
                    "status": "compatibility_check_required",
                    "message": "Schema compatibility issues found",
                    "compatibility_result": {
                        "compatible": compatibility_result.is_compatible,
                        "can_auto_resolve": compatibility_result.can_auto_resolve,
                        "resolution_summary": compatibility_result.resolution_summary,
                        "mismatches": [
                            {
                                "sheet_name": m.sheet_name,
                                "type": m.mismatch_type,
                                "message": m.message,
                            }
                            for m in compatibility_result.mismatches
                        ],
                    },
                    "suggestion": "Review the changes above. If acceptable, call this endpoint again with force_process=true",
                }

        # Continue with existing processing logic...
        try:
            with open("uploads/sheet_model.json", "r") as f:
                sheet_model = SheetModel.model_validate_json(f.read())
        except FileNotFoundError:
            raise ValueError("Sheet model not found. Please save the model first.")
        except Exception as e:
            raise ValueError(f"Error reading sheet model: {str(e)}")

        logger.info(f"Process using file path: {file_path}")

        # Populate DB
        sheets = builder.sheets
        db_populator = DatabasePopulator(
            sheets=sheets,
            source_file=file_path,
        )
        db_populator.extract_to_db(db, sheet_model)

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


# 2. Update the spreadsheet route: api/routes/spreadsheet.py

# Add this new endpoint before the existing /process endpoint:


@router.post("/check_compatibility", tags=["Spreadsheet"])
async def check_spreadsheet_compatibility(
    file_path: Annotated[str, Body()],
    db: Annotated[Database, Depends(get_db)],
):
    """
    Check if a spreadsheet is compatible with existing graph schema.
    Returns compatibility status and any required changes.
    """
    try:
        if not file_path:
            raise ValueError("No file path provided")

        file_path = file_path.strip('"').strip("'")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at path: {file_path}")

        # Load and validate spreadsheet
        validator = SpreadsheetValidator(path=file_path)
        validation_errors = validator.validate_spreadsheet_data()

        if validation_errors:
            raise ValueError("Spreadsheet has validation errors. Fix these first.")

        sheets = validator.get_sheets()

        # Check compatibility with existing schema
        from backend.services.schema_compatibility_checker import (
            SchemaCompatibilityChecker,
        )

        compatibility_checker = SchemaCompatibilityChecker(db)
        result = compatibility_checker.check_compatibility(sheets)

        return {
            "compatible": result.is_compatible,
            "can_auto_resolve": result.can_auto_resolve,
            "resolution_summary": result.resolution_summary,
            "mismatches": [
                {
                    "sheet_name": m.sheet_name,
                    "type": m.mismatch_type,
                    "message": m.message,
                    "column_name": m.column_name,
                    "expected": m.expected,
                    "actual": m.actual,
                }
                for m in result.mismatches
            ],
        }

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
        logger.error(f"Error checking compatibility: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Error checking compatibility: {str(e)}",
            },
        )

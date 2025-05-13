import os
from typing import Any, Dict

from fastapi import UploadFile

from ..models.appconfig import (
    SheetConnection,
    SheetModel,
    SheetReferences,
)
from ..services.config_service import ConfigService
from .sheet_model_builder import SheetModelBuilder


class SpreadsheetService:
    """Service for handling spreadsheet operations including extraction and database upload."""

    UPLOAD_DIR = "uploads"

    def __init__(self):
        """Initialize the SpreadsheetService."""
        # Ensure uploads directory exists
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

    @staticmethod
    async def save_uploaded_file(file: UploadFile) -> str:
        """Save an uploaded file to the uploads directory and return the file path.

        Args:
            file: The uploaded file

        Returns:
            str: Path to the saved file
        """
        file_path = os.path.join(SpreadsheetService.UPLOAD_DIR, str(file.filename))

        # Create uploads directory if it doesn't exist
        os.makedirs(SpreadsheetService.UPLOAD_DIR, exist_ok=True)

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        return file_path

    def delete_sheet_model(self) -> None:
        db_info = ConfigService.get_first_database()
        db_info.sheet_model = None
        ConfigService.update_database(db_info.uri, db_info)

    def load_sheet_model(self) -> SheetModel:
        db_info = ConfigService.get_first_database()
        if not db_info.sheet_model:
            raise ValueError(
                f"Database with URI {db_info.uri} does not have a sheet model yet, upload a spreadsheet first"
            )
        return db_info.sheet_model

    def save_sheet_model(
        self,
        path: str,
        sheet_connections: list[SheetConnection],
        sheet_references: list[SheetReferences],
        db_uri: str,
    ) -> None:
        db_info = ConfigService.get_db_by_uri(db_uri)

        sheet_model = SheetModelBuilder(path=path).build_sheet_model(
            sheet_connections=sheet_connections, sheet_references=sheet_references
        )
        db_info.sheet_model = sheet_model
        ConfigService.update_database(db_uri, db_info)

    @staticmethod
    async def process_file(
        file_path: str, graph_model_data: Dict[str, Any], db_uri: str = "default"
    ) -> None:
        """Process a file with the given graph model and extract it to the database.

        Args:
            file_path: Path to the file to process
            graph_model_data: The graph model data
            db_uri: The URI of the database to extract to

        Raises:
            ValueError: If the database is not configured
            HTTPException: If there is an error during processing
        """
        pass

    # @staticmethod
    # def generate_spreadsheet(data: List[Dict[str, Any]]) -> BytesIO:
    #     """Generate a spreadsheet from the provided data.

    #     Args:
    #         data: List of dictionaries representing rows of data

    #     Returns:
    #         BytesIO: In-memory file-like object containing the Excel spreadsheet
    #     """
    #     if not data:
    #         logger.warning("No data provided for spreadsheet generation")
    #         raise ValueError("No data provided for spreadsheet generation")

    #     # Convert data to pandas DataFrame
    #     df = pd.DataFrame(data)
    #     logger.debug(f"Created DataFrame with shape: {df.shape}")

    #     # Create an Excel file in memory
    #     output = BytesIO()
    #     with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
    #         df.to_excel(writer, index=False)

    #     output.seek(0)
    #     logger.info("Successfully generated spreadsheet")
    #     return output


if __name__ == "__main__":
    sheet_references = [
        SheetReferences(
            source_sheet_name="Reaction",
            source_column_name="reaction_id",
            target_sheet_name="Measurement",
            target_column_name="has_reaction",
        )
    ]
    path = "test_data/genoscope/test.xlsx"

    service = SpreadsheetService()

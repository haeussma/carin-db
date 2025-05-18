import os

from fastapi import APIRouter, HTTPException

from backend.models.model import SheetModel

router = APIRouter(prefix="/config")

SHEET_MODEL_PATH = os.path.join("uploads", "sheet_model.json")


@router.get("/sheet_model", tags=["Config"])
async def get_sheet_model() -> SheetModel:
    """Gets sheet model configuration from json file in uploads directory"""
    # check if file exists
    if not os.path.exists(SHEET_MODEL_PATH):
        raise HTTPException(
            status_code=404,
            detail="Sheet model configuration file not found",
        )
    with open(SHEET_MODEL_PATH, "r") as f:
        model = SheetModel.model_validate_json(f.read())
    return model


@router.post("/sheet_model", tags=["Config"])
async def save_sheet_model(sheet_model: SheetModel):
    """Saves sheet model configuration to json file in uploads directory"""
    # Ensure uploads directory exists
    os.makedirs(os.path.dirname(SHEET_MODEL_PATH), exist_ok=True)

    with open(SHEET_MODEL_PATH, "w") as f:
        f.write(sheet_model.model_dump_json(indent=4))


@router.delete("/sheet_model", tags=["Config"])
async def delete_sheet_model():
    """Deletes sheet model configuration from json file in uploads directory"""
    os.remove(SHEET_MODEL_PATH)

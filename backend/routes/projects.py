from pathlib import Path

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import ValidationError

from ..model import GraphSheetModel

router = APIRouter(prefix="/projects", tags=["Projects"])

PROJECT_DIR = Path("projects")


def ensure_project_dir():
    if not PROJECT_DIR.is_dir():
        PROJECT_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Created uploads directory")


@router.get("/load", tags=["Projects"], response_model=list[GraphSheetModel])
def load_projects() -> list[GraphSheetModel]:
    ensure_project_dir()  # Ensure the projects directory exists
    logger.info(f"🔍 LOAD PROJECTS CALLED - Loading from {PROJECT_DIR.absolute()}")

    projects = []
    json_files = list(PROJECT_DIR.rglob("*.json"))
    logger.info(
        f"🔍 Found {len(json_files)} JSON files: {[f.name for f in json_files]}"
    )

    for file in json_files:
        try:
            project = GraphSheetModel.model_validate_json(file.read_text())
            projects.append(project)
            logger.info(f"✅ Loaded project: {project.project_name}")
        except Exception as e:
            # read the file and print the contents {e}")
            logger.error(f"❌ Failed to load project from {file}: {e}")

    logger.info(f"🔍 Returning {len(projects)} projects")
    return projects


@router.get("/{project_name}", tags=["Projects"], response_model=GraphSheetModel)
def get_project(project_name: str) -> GraphSheetModel:
    file = PROJECT_DIR / f"{project_name}.json"
    if not file.is_file():
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        json_text = file.read_text(encoding="utf-8")
        return GraphSheetModel.model_validate_json(json_text)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())


@router.post("/{project_name}", tags=["Projects"])
def save_project(project: GraphSheetModel) -> None:
    logger.info(f"🔍 SAVE PROJECT CALLED - Project name: {project.project_name}")
    logger.info(f"🔍 Project data: {project.model_dump()}")

    ensure_project_dir()  # Ensure the projects directory exists
    file = PROJECT_DIR / f"{project.project_name}.json"

    try:
        file.write_text(project.model_dump_json(indent=4), encoding="utf-8")
        logger.info(f"✅ Project {project.project_name} written to {file}")
        logger.info(f"✅ File exists after write: {file.exists()}")
        logger.info(
            f"✅ File size: {file.stat().st_size if file.exists() else 'N/A'} bytes"
        )
    except Exception as e:
        logger.error(f"❌ Failed to write project {project.project_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save project: {e}")


@router.delete("/{project_name}", tags=["Projects"])
def delete_project(project_name: str) -> None:
    file = PROJECT_DIR / f"{project_name}.json"
    if not file.is_file():
        raise HTTPException(status_code=404, detail="Project not found")
    file.unlink()
    logger.info(f"Project {project_name} deleted")

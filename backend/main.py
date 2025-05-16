import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .api.routes import config, database, llm, spreadsheet


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Starting up FastAPI application")
    # Create uploads directory if it doesn't exist
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
        logger.info("Created uploads directory")
    yield
    logger.info("Shutting down FastAPI application")


app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config.router, prefix="/api")
app.include_router(database.router, prefix="/api")
app.include_router(spreadsheet.router, prefix="/api")
app.include_router(llm.router, prefix="/api")


@app.get("/test")
async def test():
    """Test endpoint."""
    return {"message": "This is a test message from the backend!"}


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting uvicorn server")
    uvicorn.run(app, host="0.0.0.0", port=8000)

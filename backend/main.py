from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.services.database import Database
from backend.settings import config as cfg

from .api.routes import chat, config, database, llm, spreadsheet


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up FastAPI application")

    if not os.path.exists("uploads"):
        os.makedirs("uploads")
        logger.info("Created uploads directory")

    try:
        yield
    finally:
        logger.info("DB connection closed")
        logger.info("Shutting down FastAPI application")


def db():
    db = Database.from_config(cfg)
    try:
        yield db
    finally:
        db.close()


app = FastAPI(
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config.router, prefix="/api")
app.include_router(database.router, prefix="/api")
app.include_router(spreadsheet.router, prefix="/api")
app.include_router(llm.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting uvicorn server")
    uvicorn.run(app, host="0.0.0.0", port=8000)

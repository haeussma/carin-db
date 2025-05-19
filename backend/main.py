import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TypedDict

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.llm.orchestrator import AgentOrchestrator

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


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


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


class WebSocketMessage(TypedDict):
    type: str
    content: str


@dataclass
class ChatState:
    orchestrator: AgentOrchestrator = field(default_factory=AgentOrchestrator)
    turn_count: int = 0
    max_turns: int = 3  # Limit the number of turns to prevent infinite loops


@app.websocket("/llm_chat")
async def llm_chat(websocket: WebSocket):
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")

        chat_state = ChatState()

        while True:
            try:
                # Check turn limit
                if chat_state.turn_count >= chat_state.max_turns:
                    logger.warning(f"Maximum turns ({chat_state.max_turns}) exceeded")
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "content": f"Maximum number of turns ({chat_state.max_turns}) exceeded. Please start a new conversation.",
                            }
                        )
                    )
                    await websocket.close(code=1000)
                    break

                # Receive message from client
                raw_message = await websocket.receive_text()
                message: WebSocketMessage = json.loads(raw_message)
                logger.info(f"Received message from client: {message}")

                # Run evaluation using orchestrator
                reports = await chat_state.orchestrator.evaluate(message["content"])
                chat_state.turn_count += 1
                logger.info(f"Received reports: {reports}")

                # Send response back to client
                response = {
                    "type": "final",
                    "content": str(reports.report),
                }
                await websocket.send_text(json.dumps(response))
                logger.info(f"Sent response: {response}")

                # Close the connection after sending final response
                await websocket.close(code=1000)
                break

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON message: {str(e)}")
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "content": "Invalid message format. Please send a valid JSON message.",
                        }
                    )
                )
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "content": f"Sorry, there was an error processing your message. {str(e)}",
                        }
                    )
                )

    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        logger.info("WebSocket connection closed")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting uvicorn server")
    uvicorn.run(app, host="0.0.0.0", port=8000)

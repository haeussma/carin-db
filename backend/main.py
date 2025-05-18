import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TypedDict

from agents import (
    InputGuardrailTripwireTriggered,
    MaxTurnsExceeded,
    OutputGuardrailTripwireTriggered,
    Runner,
    RunResult,
)
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .api.routes import config, database, llm, spreadsheet
from .llm.enzymeml_agent import (
    AmbiguityClarifierAgent,
    EnzymeMLMappingMasterAgent,
    MappingBossReport,
)


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


class WebSocketMessage(TypedDict):
    type: str
    content: str


@dataclass
class ChatState:
    current_run: Optional[RunResult] = None
    context: Optional[Dict[str, Any]] = field(default_factory=dict)
    turn_count: int = 0
    max_turns: int = 5  # Limit the number of turns to prevent infinite loops


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

                # Initialize or continue the agent run
                try:
                    if chat_state.current_run is None:
                        # Start new run
                        chat_state.current_run = await Runner.run(
                            starting_agent=EnzymeMLMappingMasterAgent,
                            input=message["content"],
                            context=chat_state.context,
                            max_turns=chat_state.max_turns,
                        )
                        logger.info(
                            f"Starting new of {chat_state.current_run.last_agent.name}"
                        )
                        chat_state.turn_count += 1
                    else:
                        logger.error(
                            f"Continuing existing run of {chat_state.current_run.last_agent.name}"
                        )
                        # Continue existing run
                        chat_state.current_run = await Runner.run(
                            starting_agent=EnzymeMLMappingMasterAgent,
                            input=message["content"],
                            context=chat_state.context,
                            previous_response_id=chat_state.current_run.last_response_id,
                            max_turns=chat_state.max_turns,
                        )

                except MaxTurnsExceeded as e:
                    logger.error(f"Agent exceeded maximum turns: {str(e)}")
                    # dump error to json
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "content": f"Agent exceeded maximum turns: {str(e)}",
                            }
                        )
                    )
                    await websocket.close(code=1000)
                    break

                except (
                    InputGuardrailTripwireTriggered,
                    OutputGuardrailTripwireTriggered,
                ) as e:
                    logger.error(f"Agent triggered guardrail: {str(e)}")
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "content": f"Failed to complete mapping: {str(e)}",
                            }
                        )
                    )
                    await websocket.close(code=1000)
                    break

                except Exception as e:
                    logger.error(f"Agent error: {str(e)}")
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "content": f"An unknown error occurred while processing your request: {str(e)}",
                            }
                        )
                    )
                    await websocket.close(code=1000)
                    break

                chat_state.turn_count += 1

                # Process the response
                if chat_state.current_run.final_output:
                    if isinstance(
                        chat_state.current_run.final_output, MappingBossReport
                    ):
                        response = {
                            "type": "final",
                            "content": str(
                                chat_state.current_run.final_output.verdict_report
                            ),
                        }

                        boss_response: MappingBossReport = (
                            chat_state.current_run.final_output
                        )
                        if boss_response.ambiguous:
                            logger.info(
                                f"Ambiguous mapping, calling ambiguity clarifier. Context: {chat_state.context}"
                            )
                            # call ambiguity clarifier agent
                            chat_state.current_run = await Runner.run(
                                starting_agent=AmbiguityClarifierAgent,
                                input=message["content"],
                                context=chat_state.context,
                                previous_response_id=chat_state.current_run.last_response_id,
                            )
                    else:
                        # Agent needs more input or tool execution
                        response = {
                            "type": "intermediate",
                            "content": str(chat_state.current_run.last_response_id),
                            "needs_input": "true",
                        }

                # Send response back to client
                await websocket.send_text(json.dumps(response))
                logger.info(f"Sent response: {response}")

                # If we got a final response, close the connection
                if response["type"] == "final":
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

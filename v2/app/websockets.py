import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from app.auth.auth_dependencies import ActiveUserWsDep
from app.agents.supervisor import Supervisor
from app.schemas import WebSocketMessage, RequestModel
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages WebSocket connections, ensuring a single, authenticated connection per user.
    """
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """
        Accepts a new WebSocket connection and registers it, ensuring only one connection per user.
        """
        await websocket.accept()
        if user_id in self.active_connections:
            # Gracefully close the existing connection before establishing a new one.
            await self.active_connections[user_id].close(code=1000, reason="New connection established")
            logger.warning(f"Closing existing WebSocket connection for user {user_id} to establish a new one.")
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, user_id: str):
        """
        Removes a WebSocket connection from the active pool.
        """
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_to_client(self, user_id: str, message: Dict[str, Any]):
        """
        Sends a JSON message to a specific client.
        """
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
        else:
            logger.warning(f"Attempted to send message to disconnected user: {user_id}")

    async def send_error(self, user_id: str, error_message: str):
        """
        Sends a standardized error message to a client.
        """
        await self.send_to_client(user_id, {"type": "error", "payload": {"message": error_message}})

manager = WebSocketManager()
websockets_router = APIRouter()

def get_agent_supervisor(request: Request) -> Supervisor:
    return request.app.state.agent_supervisor

@websockets_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    user: ActiveUserWsDep, 
    supervisor: Supervisor = Depends(get_agent_supervisor)
):
    """
    The primary WebSocket endpoint for handling client communication.
    - Establishes and authenticates the connection.
    - Handles incoming messages and routes them to the agent supervisor.
    - Manages the connection lifecycle and cleans up on disconnect.
    """
    await manager.connect(websocket, user.id)
    try:
        while True:
            try:
                # Set a timeout to prevent connections from hanging indefinitely.
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300)
                
                if data == 'ping':
                    await websocket.send_text('pong')
                    continue

                try:
                    message = WebSocketMessage.parse_raw(data)
                    if message.type == "analysis_request":
                        request_model = RequestModel.parse_obj(message.payload)
                        # Asynchronously run the agent to avoid blocking the WebSocket.
                        asyncio.create_task(
                            supervisor.run(request_model.model_dump(), request_model.id, stream_updates=True)
                        )
                    else:
                        logger.warning(f"Received unknown message type: {message.type}")
                        await manager.send_error(user.id, f"Unknown message type: {message.type}")

                except json.JSONDecodeError:
                    logger.error("Failed to decode JSON from WebSocket message.")
                    await manager.send_error(user.id, "Invalid JSON format.")
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    await manager.send_error(user.id, "An internal error occurred while processing the message.")

            except asyncio.TimeoutError:
                # Send a pong to keep the connection alive if no message is received.
                await websocket.send_text('pong')
            except WebSocketDisconnect:
                logger.info(f"WebSocket gracefully disconnected for user {user.id}")
                break  # Exit the loop to allow cleanup.
            except Exception as e:
                logger.error(f"An unexpected error occurred in the WebSocket connection for user {user.id}: {e}", exc_info=True)
                break # Exit and cleanup on unexpected errors.

    finally:
        manager.disconnect(user.id)
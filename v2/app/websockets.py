
import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from app.auth.auth_dependencies import ActiveUserWsDep
from app.agents.supervisor import Supervisor
from app.schemas import WebSocketMessage, RequestModel
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        logger.info(f"WebSocket connected for user {client_id}")

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        logger.info(f"WebSocket disconnected for user {client_id}")

    async def broadcast_to_client(self, client_id: str, message: Dict[str, Any]):
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                await connection.send_json(message)

manager = WebSocketManager()

websockets_router = APIRouter()

def get_agent_supervisor(request: Request) -> Supervisor:
    return request.app.state.agent_supervisor

@websockets_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user: ActiveUserWsDep, supervisor: Supervisor = Depends(get_agent_supervisor)):
    await manager.connect(websocket, user.id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                if data == 'ping':
                    await websocket.send_text('pong')
                    continue

                try:
                    message = WebSocketMessage.parse_raw(data)
                    if message.type == "analysis_request":
                        request_model = RequestModel.parse_obj(message.payload)
                        try:
                            await supervisor.run(request_model.model_dump(), request_model.id, stream_updates=True)
                        except Exception as e:
                            logger.error(f"Error running agent: {e}", exc_info=True)
                            await manager.broadcast_to_client(user.id, {"error": "Error processing your request."})
                    else:
                        logger.warning(f"Received unknown message type: {message.type}")

                except json.JSONDecodeError:
                    logger.error("Failed to decode JSON from WebSocket message.")
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    await manager.broadcast_to_client(user.id, {"error": "Internal server error."})

            except asyncio.TimeoutError:
                await websocket.send_text('pong') # Keep connection alive
                continue
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user.id}")
    except Exception as e:
        logger.error(f"WebSocket connection failed for user {user.id}: {e}", exc_info=True)
    finally:
        manager.disconnect(websocket, user.id)

@websockets_router.websocket("/dev")
async def dev_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json({"echo": data})
    except WebSocketDisconnect:
        logger.info("Dev WebSocket disconnected")


import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from app.auth.auth_dependencies import ActiveUserWsDep
from app.websocket_manager import manager
from app.agents.supervisor import Supervisor
from app.schemas import WebSocketMessage, RequestModel
from app.logging_config import central_logger

router = APIRouter()

def get_agent_supervisor(request: Request) -> Supervisor:
    return request.app.state.agent_supervisor

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user: ActiveUserWsDep, supervisor: Supervisor = Depends(get_agent_supervisor)):
    await manager.connect(websocket, user.id)
    logger = central_logger.get_logger(__name__)
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
                        await supervisor.run(request_model.model_dump(), request_model.id, stream_updates=True)
                    else:
                        logger.warning(f"Received unknown message type: {message.type}")

                except json.JSONDecodeError:
                    logger.error("Failed to decode JSON from WebSocket message.")
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    await manager.broadcast_to_client(user.id, {"error": "Internal server error."})

            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user.id}")
    finally:
        manager.disconnect(websocket, user.id)

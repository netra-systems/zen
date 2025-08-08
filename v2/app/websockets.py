
import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from app.auth.auth_dependencies import ActiveUserWsDep
from app.agents.supervisor import Supervisor
from app.schemas import WebSocketMessage, RequestModel, AnalysisRequest, WebSocketError
from app.ws_manager import manager

logger = logging.getLogger(__name__)

websockets_router = APIRouter()

def get_agent_supervisor(request: Request) -> Supervisor:
    return request.app.state.agent_supervisor

@websockets_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    user: ActiveUserWsDep, 
    supervisor: Supervisor = Depends(get_agent_supervisor)
):
    await manager.connect(websocket, user.id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300)
                
                if data == 'ping':
                    await websocket.send_text('pong')
                    continue

                try:
                    message = WebSocketMessage.parse_raw(data)
                    if message.type == "analysis_request":
                        request_model = RequestModel.parse_obj(message.payload)
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
                    await manager.send_error(user.id, f"An internal error occurred while processing your request: {e}")

            except asyncio.TimeoutError:
                await websocket.send_text('pong')
            except WebSocketDisconnect:
                logger.info(f"WebSocket gracefully disconnected for user {user.id}")
                break
            except Exception as e:
                logger.error(f"An unexpected error occurred in the WebSocket connection for user {user.id}: {e}", exc_info=True)
                break

    finally:
        manager.disconnect(user.id)

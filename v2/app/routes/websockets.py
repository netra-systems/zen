from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request, Query
import logging
import json
import asyncio
from ..schemas import WebSocketMessage, AnalysisRequest, RequestModel, User
from ..auth.auth_dependencies import get_current_user_ws
from ..agents.supervisor import Supervisor
from ..dependencies import get_agent_supervisor
from ..ws_manager import manager

router = APIRouter()

logger = logging.getLogger(__name__)

async def handle_analysis_request(user: User, message: WebSocketMessage, supervisor: Supervisor):
    try:
        analysis_request = AnalysisRequest(**message.payload)
        await supervisor.start_agent(str(user.id), analysis_request)
    except Exception as e:
        logger.error(f"Error handling analysis request for user {user.id}: {e}", exc_info=True)
        await manager.send_error(str(user.id), f"Failed to start analysis: {e}")

async def handle_unknown_message(user: User, message: WebSocketMessage):
    logger.warning(f"Unknown message type for user {user.id}: {message.type}")
    await manager.send_error(str(user.id), f"Unknown message type: {message.type}")

@router.websocket("/ws/v1/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    user_id: str,
    user: User = Depends(get_current_user_ws),
    supervisor: Supervisor = Depends(get_agent_supervisor)
):
    if user is None:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, user)
    logger.info(f"WebSocket connected for user {user.id}")

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=300)
                if data == {"type": "ping"}:
                    await websocket.send_json({"type": "pong"})
                    continue
                
                message = WebSocketMessage.parse_obj(data)
                
                if message.type == "analysis_request":
                    await handle_analysis_request(user, message, supervisor)
                else:
                    await handle_unknown_message(user, message)

            except asyncio.TimeoutError:
                await websocket.send_json({"type": "pong"}) # Keep alive
            except WebSocketDisconnect:
                logger.info(f"WebSocket gracefully disconnected for user {user.id}")
                break
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from user {user.id}")
                await manager.send_error(str(user.id), "Invalid JSON format")
            except Exception as e:
                logger.error(f"An unexpected error occurred in the WebSocket connection for user {user.id}: {e}", exc_info=True)
                await manager.send_error(str(user.id), "An unexpected error occurred.")
                break
    finally:
        manager.disconnect(user, websocket)
        logger.info(f"WebSocket connection closed for user {user.id}")

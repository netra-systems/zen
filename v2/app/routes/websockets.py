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

async def handle_analysis_request(user_id: str, message: WebSocketMessage, supervisor: Supervisor):
    try:
        analysis_request = AnalysisRequest(**message.payload)
        await supervisor.start_agent(user_id, analysis_request)
    except Exception as e:
        logger.error(f"Error handling analysis request for user {user_id}: {e}", exc_info=True)
        await manager.send_error(user_id, f"Failed to start analysis: {e}")

async def handle_unknown_message(user_id: str, message: WebSocketMessage):
    logger.warning(f"Unknown message type for user {user_id}: {message.type}")
    await manager.send_error(user_id, f"Unknown message type: {message.type}")

@router.websocket("/ws/v1/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    user_id: str,
    supervisor: Supervisor = Depends(get_agent_supervisor)
):
    await manager.connect(websocket, user_id)
    logger.info(f"WebSocket connected for user {user_id}")

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=300)
                if data == {"type": "ping"}:
                    await websocket.send_text('pong')
                    continue
                
                message = WebSocketMessage.parse_obj(data)
                
                if message.type == "analysis_request":
                    await handle_analysis_request(user_id, message, supervisor)
                else:
                    await handle_unknown_message(user_id, message)

            except asyncio.TimeoutError:
                await websocket.send_text('pong') # Keep alive
            except WebSocketDisconnect:
                logger.info(f"WebSocket gracefully disconnected for user {user_id}")
                break
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from user {user_id}")
                await manager.send_error(user_id, "Invalid JSON format")
            except Exception as e:
                logger.error(f"An unexpected error occurred in the WebSocket connection for user {user_id}: {e}", exc_info=True)
                await manager.send_error(user_id, "An unexpected error occurred.")
                break
    finally:
        manager.disconnect(user_id, websocket)
        logger.info(f"WebSocket connection closed for user {user_id}")
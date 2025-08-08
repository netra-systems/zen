from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request, Query
import logging
import json
import asyncio
from app.schemas import WebSocketMessage, AnalysisRequest, RequestModel, User
from app.auth.auth_dependencies import get_current_user_ws
from app.agents.supervisor import Supervisor
from app.dependencies import get_agent_supervisor
from app.ws_manager import manager

websockets_router = APIRouter()

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

@websockets_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    token: str = Query(...),
    supervisor: Supervisor = Depends(get_agent_supervisor)
):
    try:
        user = await get_current_user_ws(token, websocket)
        if not user:
            await websocket.close(code=1008, reason="Invalid token")
            return
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}", exc_info=True)
        await websocket.close(code=1008, reason="Authentication failed")
        return

    await manager.connect(websocket, user.id)
    logger.info(f"WebSocket connected for user {user.id}")

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=300)
                if data == {"type": "ping"}:
                    await websocket.send_text('pong')
                    continue
                
                message = WebSocketMessage.parse_obj(data)
                
                if message.type == "analysis_request":
                    await handle_analysis_request(user.id, message, supervisor)
                else:
                    await handle_unknown_message(user.id, message)

            except asyncio.TimeoutError:
                await websocket.send_text('pong') # Keep alive
            except WebSocketDisconnect:
                logger.info(f"WebSocket gracefully disconnected for user {user.id}")
                break
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from user {user.id}")
                await manager.send_error(user.id, "Invalid JSON format")
            except Exception as e:
                logger.error(f"An unexpected error occurred in the WebSocket connection for user {user.id}: {e}", exc_info=True)
                await manager.send_error(user.id, "An unexpected error occurred.")
                break
    finally:
        manager.disconnect(user.id, websocket)
        logger.info(f"WebSocket connection closed for user {user.id}")

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from pydantic import ValidationError
from app.auth.auth_dependencies import ActiveUserWsDep
from app.agents.supervisor import Supervisor
from app.schemas import WebSocketMessage, AnalysisRequest, RequestModel
from app.ws_manager import manager

logger = logging.getLogger(__name__)

websockets_router = APIRouter()

def get_agent_supervisor(request: Request) -> Supervisor:
    return request.app.state.agent_supervisor

async def handle_analysis_request(user_id: str, message: WebSocketMessage, supervisor: Supervisor):
    if isinstance(message.payload, AnalysisRequest):
        request_model = message.payload.request_model
        asyncio.create_task(
            supervisor.run(request_model.model_dump(), request_model.id, stream_updates=True)
        )
    else:
        await manager.send_error(user_id, "Invalid payload for analysis_request")

async def handle_unknown_message(user_id: str, message: WebSocketMessage):
    logger.warning(f"Received unknown message type: {message.type}")
    await manager.send_error(user_id, f"Unknown message type: {message.type}")

async def handle_validation_error(user_id: str, e: ValidationError):
    logger.error(f"WebSocket validation error for user {user_id}: {e}")
    errors = e.errors()
    error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in errors]
    await manager.send_error(user_id, f"Invalid message format: {', '.join(error_messages)}")

async def handle_message(user_id: str, data: dict, supervisor: Supervisor):
    try:
        message = WebSocketMessage.parse_obj(data)
        if message.type == "analysis_request":
            await handle_analysis_request(user_id, message, supervisor)
        else:
            await handle_unknown_message(user_id, message)

    except ValidationError as e:
        await handle_validation_error(user_id, e)
    except json.JSONDecodeError:
        await manager.send_error(user_id, "Invalid JSON format")
    except Exception as e:
        logger.error(f"Error processing message for user {user_id}: {e}", exc_info=True)
        await manager.send_error(user_id, "An internal error occurred.")

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
                data = await asyncio.wait_for(websocket.receive_json(), timeout=300)
                if data == 'ping':
                    await websocket.send_text('pong')
                    continue
                await handle_message(user.id, data, supervisor)

            except asyncio.TimeoutError:
                await websocket.send_text('pong') # Keep alive
            except WebSocketDisconnect:
                logger.info(f"WebSocket gracefully disconnected for user {user.id}")
                break
            except Exception as e:
                logger.error(f"An unexpected error occurred in the WebSocket connection for user {user.id}: {e}", exc_info=True)
                break

    finally:
        manager.disconnect(user.id)
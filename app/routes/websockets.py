from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from app.ws_manager import manager
from app.logging_config import central_logger
from app.routes.utils.websocket_helpers import (
    accept_websocket_connection, extract_app_services,
    authenticate_websocket_user, receive_message_with_timeout, handle_pong_message,
    parse_json_message, validate_and_handle_message, process_agent_message,
    check_connection_alive, cleanup_websocket_connection
)
import asyncio
import time

logger = central_logger.get_logger(__name__)
router = APIRouter()

async def _handle_none_message() -> bool:
    """Handle None message case."""
    return True

async def _process_valid_message(user_id_str: str, data: str, agent_service) -> bool:
    """Process validated message through agent service."""
    await process_agent_message(user_id_str, data, agent_service)
    return True

async def _handle_validated_message(
    user_id_str: str, websocket: WebSocket, message, data: str, agent_service
) -> bool:
    """Handle message after validation."""
    if not await validate_and_handle_message(user_id_str, websocket, message, manager):
        return True
    return await _process_valid_message(user_id_str, data, agent_service)

async def _handle_parsed_message(
    user_id_str: str, websocket: WebSocket, message, data: str, agent_service
) -> bool:
    """Handle parsed message validation and processing."""
    if message is None:
        return await _handle_none_message()
    return await _handle_validated_message(user_id_str, websocket, message, data, agent_service)

async def _process_single_message(user_id_str: str, websocket: WebSocket, agent_service):
    """Process a single WebSocket message."""
    data = await receive_message_with_timeout(websocket)
    message = await parse_json_message(data, user_id_str, manager)
    if await handle_pong_message(data, user_id_str, websocket, manager):
        return True
    return await _handle_parsed_message(user_id_str, websocket, message, data, agent_service)

async def _handle_message_timeout(conn_info, user_id_str: str) -> bool:
    """Handle message processing timeout."""
    return check_connection_alive(conn_info, user_id_str, manager)

async def _try_process_single_message(
    user_id_str: str, websocket: WebSocket, agent_service
) -> bool:
    """Try to process single message."""
    await _process_single_message(user_id_str, websocket, agent_service)
    return True

async def _process_message_with_timeout_handling(
    user_id_str: str, websocket: WebSocket, conn_info, agent_service
) -> bool:
    """Process single message with timeout handling."""
    try:
        return await _try_process_single_message(user_id_str, websocket, agent_service)
    except asyncio.TimeoutError:
        return await _handle_message_timeout(conn_info, user_id_str)

async def _handle_message_loop(user_id_str: str, websocket: WebSocket, conn_info, agent_service):
    """Handle the main message processing loop."""
    while True:
        continue_loop = await _process_message_with_timeout_handling(
            user_id_str, websocket, conn_info, agent_service
        )
        if not continue_loop:
            break

async def _handle_websocket_disconnect(e: WebSocketDisconnect, user_id_str: str, websocket: WebSocket):
    """Handle WebSocket disconnect."""
    logger.info(f"WebSocket disconnected for user {user_id_str}: {e.code} - {e.reason}")
    reason = e.reason or "Client disconnect"
    await manager.disconnect_user(user_id_str, websocket, code=e.code, reason=reason)

def _is_websocket_connected(websocket: WebSocket) -> bool:
    """Check if WebSocket is connected."""
    return hasattr(websocket, 'application_state') and websocket.application_state == WebSocketState.CONNECTED

async def _handle_websocket_error(e: Exception, user_id_str: str, websocket: WebSocket):
    """Handle WebSocket error."""
    logger.error(f"WebSocket error for user {user_id_str}: {e}", exc_info=True)
    if _is_websocket_connected(websocket):
        await manager.disconnect_user(user_id_str, websocket, code=1011, reason="Server error")

async def _setup_websocket_auth(websocket: WebSocket):
    """Setup WebSocket authentication."""
    token = await accept_websocket_connection(websocket)
    security_service, agent_service = extract_app_services(websocket)
    user_id_str = await authenticate_websocket_user(websocket, token, security_service)
    return user_id_str, agent_service

async def _finalize_websocket_connection(user_id_str: str, websocket: WebSocket):
    """Finalize WebSocket connection setup."""
    conn_info = await manager.connect_user(user_id_str, websocket)
    logger.info(f"WebSocket connection established for user {user_id_str}")
    return conn_info

async def _establish_websocket_connection(websocket: WebSocket):
    """Establish and authenticate WebSocket connection."""
    user_id_str, agent_service = await _setup_websocket_auth(websocket)
    conn_info = await _finalize_websocket_connection(user_id_str, websocket)
    return user_id_str, conn_info, agent_service

async def _handle_disconnect_exception(e: WebSocketDisconnect, user_id_str: str, websocket: WebSocket):
    """Handle WebSocket disconnect exception."""
    if user_id_str:
        await _handle_websocket_disconnect(e, user_id_str, websocket)

async def _handle_general_exception(e: Exception, user_id_str: str, websocket: WebSocket):
    """Handle general WebSocket exception."""
    logger.error(f"Error in WebSocket connection: {e}", exc_info=True)
    if user_id_str:
        await _handle_websocket_error(e, user_id_str, websocket)

async def _handle_websocket_exceptions(e: Exception, user_id_str: str, websocket: WebSocket):
    """Handle various WebSocket exceptions."""
    if isinstance(e, WebSocketDisconnect):
        await _handle_disconnect_exception(e, user_id_str, websocket)
    elif isinstance(e, ValueError):
        return  # Authentication errors - connection already closed
    else:
        await _handle_general_exception(e, user_id_str, websocket)

async def _run_websocket_session(websocket: WebSocket):
    """Run WebSocket session with connection and message handling."""
    user_id_str, conn_info, agent_service = await _establish_websocket_connection(websocket)
    await _handle_message_loop(user_id_str, websocket, conn_info, agent_service)
    return user_id_str

async def _execute_websocket_session(websocket: WebSocket):
    """Execute WebSocket session with error handling."""
    user_id_str = None
    try:
        user_id_str = await _run_websocket_session(websocket)
    except Exception as e:
        await _handle_websocket_exceptions(e, user_id_str, websocket)
    return user_id_str

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint handler."""
    user_id_str = await _execute_websocket_session(websocket)
    if user_id_str:
        await cleanup_websocket_connection(user_id_str, websocket, manager)
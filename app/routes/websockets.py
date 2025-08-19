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
from app.websocket.error_recovery_handler import get_error_recovery_handler
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
    # CRITICAL FIX: Always process through agent service regardless of manager result
    # The manager handles WebSocket-level concerns (ping/pong, routing, etc)
    # But messages still need to go to the agent service for actual processing
    
    # Let manager handle WebSocket-specific messages (ping/pong, etc)
    manager_handled = await validate_and_handle_message(user_id_str, websocket, message, manager)
    
    # If it's a ping or other system message, manager handles it completely
    if message.get("type") in ["ping", "pong", "auth"]:
        return True
    
    # For user messages, ALWAYS forward to agent service
    logger.info(f"[CRITICAL FIX] Processing message through agent service: {message.get('type')}")
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
    logger.info(f"[WS MESSAGE] Waiting for message from user {user_id_str}")
    data = await receive_message_with_timeout(websocket)
    logger.info(f"[WS MESSAGE] Received raw data from {user_id_str}: {data[:100] if data else 'None'}")
    message = await parse_json_message(data, user_id_str, manager)
    logger.info(f"[WS MESSAGE] Parsed message from {user_id_str}: {message}")
    if await handle_pong_message(data, user_id_str, websocket, manager):
        logger.info(f"[WS MESSAGE] Handled pong from {user_id_str}")
        return True
    logger.info(f"[WS MESSAGE] Processing message type: {message.get('type') if message else 'None'}")
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
    logger.info(f"[MESSAGE LOOP] Starting message loop for user {user_id_str}")
    message_count = 0
    while True:
        message_count += 1
        logger.info(f"[MESSAGE LOOP] Waiting for message #{message_count} from {user_id_str}")
        continue_loop = await _process_message_with_timeout_handling(
            user_id_str, websocket, conn_info, agent_service
        )
        if not continue_loop:
            logger.info(f"[MESSAGE LOOP] Exiting loop for {user_id_str} after {message_count} messages")
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
    """Handle WebSocket error with recovery attempt."""
    logger.error(f"WebSocket error for user {user_id_str}: {e}", exc_info=True)
    
    # Find connection info for error recovery
    conn_info = await manager.connection_manager.find_connection(user_id_str, websocket)
    reconnection_token = None
    
    if conn_info:
        # Attempt error recovery
        error_handler = get_error_recovery_handler()
        reconnection_token = await error_handler.handle_error(e, conn_info)
        
    if _is_websocket_connected(websocket):
        # Disconnect with potential reconnection token
        await manager.disconnect_user(
            user_id_str, websocket, code=1011, reason="Server error",
            agent_state={"reconnection_token": reconnection_token} if reconnection_token else None
        )

async def _setup_websocket_auth(websocket: WebSocket):
    """Setup WebSocket authentication."""
    logger.info("[WEBSOCKET AUTH] Starting authentication")
    token = await accept_websocket_connection(websocket)
    logger.info(f"[WEBSOCKET AUTH] Token: {token[:20] if token else 'None'}...")
    security_service, agent_service = extract_app_services(websocket)
    logger.info(f"[WEBSOCKET AUTH] Services found: security={security_service is not None}, agent={agent_service is not None}")
    user_id_str = await authenticate_websocket_user(websocket, token, security_service)
    logger.info(f"[WEBSOCKET AUTH] Authenticated user: {user_id_str}")
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
    logger.info("[WEBSOCKET CONNECTED] New WebSocket connection received at /ws endpoint")
    user_id_str = await _execute_websocket_session(websocket)
    if user_id_str:
        logger.info(f"[WEBSOCKET CLEANUP] Cleaning up connection for user {user_id_str}")
        await cleanup_websocket_connection(user_id_str, websocket, manager)
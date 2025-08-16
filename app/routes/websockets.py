from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from app.ws_manager import manager
from app.logging_config import central_logger
from app.db.postgres import get_async_db
from app.routes.utils.websocket_helpers import (
    accept_websocket_connection, extract_app_services,
    authenticate_websocket_user, receive_message_with_timeout, handle_pong_message,
    parse_json_message, validate_and_handle_message, process_agent_message,
    check_connection_alive, cleanup_websocket_connection
)
import asyncio
import json
import time

logger = central_logger.get_logger(__name__)
router = APIRouter()

async def _validate_websocket_token(websocket: WebSocket) -> str:
    """Validate WebSocket token from query params."""
    token = websocket.query_params.get("token")
    if not token:
        logger.error("No token provided in query parameters")
        await websocket.close(code=1008, reason="No token provided")
        raise ValueError("No token provided")
    return token

async def _accept_websocket_connection(websocket: WebSocket) -> str:
    """Accept WebSocket connection and validate token."""
    await websocket.accept()
    return await _validate_websocket_token(websocket)

async def _get_app_services(websocket: WebSocket):
    """Extract services from app state."""
    app = websocket.app
    security_service = app.state.security_service
    agent_service = app.state.agent_service
    return security_service, agent_service

async def _decode_token_payload(security_service, token: str):
    """Decode and validate token payload."""
    payload = security_service.decode_access_token(token)
    if payload is None:
        logger.error("Token payload is invalid")
        raise ValueError("Invalid token")
    return payload

async def _extract_user_id(payload: dict) -> str:
    """Extract user ID from token payload."""
    user_id = payload.get("sub")
    if user_id is None:
        logger.error("User ID not found in token payload")
        raise ValueError("Invalid token")
    logger.info(f"Attempting to authenticate user with ID: {user_id}")
    return user_id

async def _fetch_user_with_retry(security_service, db_session, user_id: str):
    """Fetch user with retry logic."""
    try:
        return await security_service.get_user_by_id(db_session, user_id)
    except Exception as db_error:
        logger.error(f"Database error while fetching user {user_id}: {db_error}")
        await db_session.rollback()
        return await security_service.get_user_by_id(db_session, user_id)

async def _handle_legacy_email_lookup(security_service, db_session, user_id: str, user):
    """Handle legacy email-based token lookup."""
    if user is None and "@" in user_id:
        logger.warning(f"Token contains email {user_id} instead of user ID, attempting email lookup")
        user = await security_service.get_user(db_session, user_id)
    return user

async def _check_user_exists_and_debug(db_session, user_id: str, payload: dict, user):
    """Check if user exists and provide debug info."""
    if user is None:
        logger.error(f"User with ID {user_id} not found in database")
        logger.debug(f"Token payload: {payload}")
        await _log_empty_database_warning(db_session)
        raise ValueError("User not found")

async def _log_empty_database_warning(db_session):
    """Log warning if database is empty."""
    from sqlalchemy import select, func
    from app.db.models_postgres import User
    user_count_result = await db_session.execute(select(func.count()).select_from(User))
    user_count = user_count_result.scalar()
    if user_count == 0:
        logger.warning("Database has no users. Run 'python create_test_user.py' to create a test user.")

async def _validate_user_active(user) -> str:
    """Validate user is active and return user ID string."""
    if not user.is_active:
        logger.error(f"User {user.id} is not active")
        raise ValueError("User not active")
    return str(user.id)

async def _get_and_validate_user(
    security_service, db_session, user_id: str, payload: dict
) -> str:
    """Get user and validate with legacy lookup support."""
    user = await _fetch_user_with_retry(security_service, db_session, user_id)
    user = await _handle_legacy_email_lookup(security_service, db_session, user_id, user)
    await _check_user_exists_and_debug(db_session, user_id, payload, user)
    return await _validate_user_active(user)

async def _authenticate_websocket_user(websocket: WebSocket, token: str, security_service) -> str:
    """Authenticate WebSocket user and return user ID string."""
    payload = await _decode_token_payload(security_service, token)
    user_id = await _extract_user_id(payload)
    async with get_async_db() as db_session:
        return await _get_and_validate_user(security_service, db_session, user_id, payload)

async def _receive_message_with_timeout(websocket: WebSocket) -> str:
    """Receive WebSocket message with timeout."""
    return await asyncio.wait_for(
        websocket.receive_text(),
        timeout=30  # 30 second timeout for heartbeat
    )

async def _handle_pong_message(data: str, user_id_str: str, websocket: WebSocket) -> bool:
    """Handle pong responses."""
    if data == "pong":
        await manager.handle_pong(user_id_str, websocket)
        return True
    return False

async def _parse_json_message(data: str, user_id_str: str):
    """Parse JSON message and handle errors."""
    try:
        return json.loads(data) if isinstance(data, str) else data
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON received from user {user_id_str}: {data[:100]}")
        await manager.send_error(user_id_str, "Invalid JSON message format")
        return None


async def _process_agent_message(user_id_str: str, data: str, agent_service):
    """Process message through agent service."""
    async with get_async_db() as db_session:
        await agent_service.handle_websocket_message(user_id_str, data, db_session)


async def _handle_none_message() -> bool:
    """Handle None message case."""
    return True

async def _process_valid_message(
    user_id_str: str, data: str, agent_service
) -> bool:
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

async def _process_message_by_type(
    user_id_str: str, websocket: WebSocket, message, data: str, agent_service
) -> bool:
    """Process message based on type."""
    return await _handle_validated_message(
        user_id_str, websocket, message, data, agent_service
    )

async def _handle_parsed_message(
    user_id_str: str, websocket: WebSocket, message, data: str, agent_service
) -> bool:
    """Handle parsed message validation and processing."""
    if message is None:
        return await _handle_none_message()
    return await _process_message_by_type(
        user_id_str, websocket, message, data, agent_service
    )

async def _process_single_message(user_id_str: str, websocket: WebSocket, agent_service):
    """Process a single WebSocket message."""
    data = await receive_message_with_timeout(websocket)
    
    # Parse JSON first, then check for ping
    message = await parse_json_message(data, user_id_str, manager)
    if message and isinstance(message, dict) and message.get("type") == "ping":
        await websocket.send_json({"type": "pong", "timestamp": time.time()})
        return True
    
    # Handle other message types    
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
        if not await _process_message_with_timeout_handling(
            user_id_str, websocket, conn_info, agent_service
        ):
            break

async def _handle_websocket_disconnect(e: WebSocketDisconnect, user_id_str: str, websocket: WebSocket):
    """Handle WebSocket disconnect."""
    logger.info(f"WebSocket disconnected for user {user_id_str}: {e.code} - {e.reason}")
    await manager.disconnect_user(user_id_str, websocket, code=e.code, reason=e.reason or "Client disconnect")

async def _handle_websocket_error(e: Exception, user_id_str: str, websocket: WebSocket):
    """Handle WebSocket error."""
    logger.error(f"WebSocket error for user {user_id_str}: {e}", exc_info=True)
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
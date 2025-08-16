"""WebSocket route specific utilities."""

import asyncio
import json
import time
from typing import Dict, Any, Optional, Tuple
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select, func
from app.db.postgres import get_async_db
from app.logging_config import central_logger
from app.routes.utils.validators import validate_token_payload, validate_user_id_in_payload, validate_user_active

logger = central_logger.get_logger(__name__)


async def validate_websocket_token(websocket: WebSocket) -> str:
    """Validate WebSocket token from query params."""
    token = websocket.query_params.get("token")
    if not token:
        logger.error("No token provided in query parameters")
        await websocket.close(code=1008, reason="No token provided")
        raise ValueError("No token provided")
    return token


async def accept_websocket_connection(websocket: WebSocket) -> str:
    """Accept WebSocket connection and validate token."""
    await websocket.accept()
    return await validate_websocket_token(websocket)


def extract_app_services(websocket: WebSocket) -> Tuple[Any, Any]:
    """Extract services from app state."""
    app = websocket.app
    return app.state.security_service, app.state.agent_service


async def decode_token_payload(security_service, token: str) -> Dict:
    """Decode and validate token payload."""
    payload = security_service.decode_access_token(token)
    return validate_token_payload(payload)


async def fetch_user_with_retry(security_service, db_session, user_id: str):
    """Fetch user with retry logic."""
    try:
        return await security_service.get_user_by_id(db_session, user_id)
    except Exception as db_error:
        logger.error(f"Database error while fetching user {user_id}: {db_error}")
        await db_session.rollback()
        return await security_service.get_user_by_id(db_session, user_id)


async def handle_legacy_email_lookup(security_service, db_session, user_id: str, user):
    """Handle legacy email-based token lookup."""
    if user is None and "@" in user_id:
        logger.warning(f"Token contains email {user_id}, attempting email lookup")
        user = await security_service.get_user(db_session, user_id)
    return user


async def log_empty_database_warning(db_session):
    """Log warning if database is empty."""
    from app.db.models_postgres import User
    user_count_result = await db_session.execute(select(func.count()).select_from(User))
    user_count = user_count_result.scalar()
    if user_count == 0:
        logger.warning("Database has no users. Run 'python create_test_user.py'")


async def check_user_exists_and_debug(db_session, user_id: str, payload: dict, user):
    """Check if user exists and provide debug info."""
    if user is None:
        logger.error(f"User with ID {user_id} not found in database")
        logger.debug(f"Token payload: {payload}")
        await log_empty_database_warning(db_session)
        raise ValueError("User not found")


async def get_and_validate_user(
    security_service, db_session, user_id: str, payload: dict
) -> str:
    """Get user and validate with legacy lookup support."""
    user = await fetch_user_with_retry(security_service, db_session, user_id)
    user = await handle_legacy_email_lookup(security_service, db_session, user_id, user)
    await check_user_exists_and_debug(db_session, user_id, payload, user)
    return validate_user_active(user)


async def authenticate_websocket_user(websocket: WebSocket, token: str, security_service) -> str:
    """Authenticate WebSocket user and return user ID string."""
    payload = await decode_token_payload(security_service, token)
    user_id = validate_user_id_in_payload(payload)
    async with get_async_db() as db_session:
        return await get_and_validate_user(security_service, db_session, user_id, payload)


async def receive_message_with_timeout(websocket: WebSocket) -> str:
    """Receive WebSocket message with timeout."""
    return await asyncio.wait_for(
        websocket.receive_text(),
        timeout=30  # 30 second timeout for heartbeat
    )


async def handle_pong_message(data: str, user_id_str: str, websocket: WebSocket, manager) -> bool:
    """Handle pong responses."""
    if data == "pong":
        await manager.handle_pong(user_id_str, websocket)
        return True
    return False


async def parse_json_message(data: str, user_id_str: str, manager):
    """Parse JSON message and handle errors."""
    try:
        return json.loads(data) if isinstance(data, str) else data
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON received from user {user_id_str}: {data[:100]}")
        await manager.send_error(user_id_str, "Invalid JSON message format")
        return None


async def _handle_ping_message(message, websocket: WebSocket) -> bool:
    """Handle ping message and return True if handled."""
    if isinstance(message, dict) and message.get("type") == "ping":
        await _send_pong_response(websocket)
        return True
    return False

async def _handle_with_manager(user_id_str: str, websocket: WebSocket, message, manager) -> bool:
    """Handle message with manager."""
    if not await manager.handle_message(user_id_str, websocket, message):
        return False
    return True

async def validate_and_handle_message(user_id_str: str, websocket: WebSocket, message, manager) -> bool:
    """Validate message and handle with manager."""
    if await _handle_ping_message(message, websocket):
        return True
    return await _handle_with_manager(user_id_str, websocket, message, manager)


async def _send_pong_response(websocket: WebSocket) -> None:
    """Send pong response to ping message."""
    pong_message = {"type": "pong", "timestamp": time.time()}
    await websocket.send_json(pong_message)


async def process_agent_message(user_id_str: str, data: str, agent_service):
    """Process message through agent service."""
    async with get_async_db() as db_session:
        await agent_service.handle_websocket_message(user_id_str, data, db_session)


def check_connection_alive(conn_info, user_id_str: str, manager) -> bool:
    """Check if connection is alive."""
    if not manager.connection_manager.is_connection_alive(conn_info):
        logger.warning(f"Connection timeout for user {user_id_str}")
        return False
    return True


async def cleanup_websocket_connection(user_id_str: str, websocket: WebSocket, manager):
    """Ensure connection cleanup happens."""
    if user_id_str and user_id_str in manager.connection_manager.active_connections:
        connections = manager.connection_manager.active_connections.get(user_id_str, [])
        if any(conn.websocket == websocket for conn in connections):
            await manager.disconnect_user(user_id_str, websocket)
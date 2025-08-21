"""WebSocket heartbeat utility functions.

Contains utility functions for ping/pong operations and heartbeat calculations.
"""

import time
from typing import Dict, Any
from datetime import datetime, timezone

from netra_backend.app.core.json_utils import prepare_websocket_message
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def create_ping_message() -> Dict[str, Any]:
    """Create ping message payload."""
    return {
        "type": "ping",
        "timestamp": time.time(),
        "system": True
    }


def calculate_response_time(conn_info) -> float:
    """Calculate time since last response."""
    now = datetime.now(timezone.utc)
    last_response_time = conn_info.last_pong or conn_info.last_ping
    return (now - last_response_time).total_seconds()


def is_response_timeout(time_since_response: float, timeout_seconds: int) -> bool:
    """Check if response timeout exceeded."""
    return time_since_response > timeout_seconds


def increment_missed_counter(missed_heartbeats: Dict[str, int], connection_id: str) -> int:
    """Increment and return missed heartbeat counter."""
    missed_count = missed_heartbeats.get(connection_id, 0) + 1
    missed_heartbeats[connection_id] = missed_count
    return missed_count


def log_missed_heartbeat(connection_id: str, missed_count: int, max_missed: int) -> None:
    """Log missed heartbeat information."""
    logger.debug(f"Connection {connection_id} missed heartbeat {missed_count}/{max_missed}")


def should_handle_timeout(missed_count: int, max_missed_heartbeats: int) -> bool:
    """Check if timeout should be handled."""
    return missed_count >= max_missed_heartbeats


def validate_connection_for_ping(conn_info, connection_manager):
    """Validate connection is ready for ping."""
    if not connection_manager.is_connection_alive(conn_info):
        raise ConnectionError("WebSocket not in connected state")
    validate_websocket_state(conn_info)


def validate_websocket_state(conn_info) -> None:
    """Validate WebSocket connection state."""
    from starlette.websockets import WebSocketState
    if conn_info.websocket.client_state != WebSocketState.CONNECTED:
        raise ConnectionError("WebSocket already closed")


async def perform_ping_send(conn_info, ping_message: Dict[str, Any]) -> None:
    """Perform actual ping message sending."""
    prepared_message = prepare_websocket_message(ping_message)
    await conn_info.websocket.send_json(prepared_message)


def is_connection_closed_error(error: Exception) -> bool:
    """Check if error indicates connection is closed."""
    error_msg = str(error).lower()
    return 'close' in error_msg or 'disconnect' in error_msg


def log_connection_closed(connection_id: str, error: Exception) -> None:
    """Log connection closed message."""
    logger.debug(f"Connection closed for {connection_id}: {error}")


def is_connection_closed_ping_error(error: Exception) -> bool:
    """Check if ping error indicates closed connection."""
    error_msg = str(error).lower()
    return 'close' in error_msg or 'disconnect' in error_msg


def handle_closed_connection_ping_error(connection_id: str, error: Exception) -> None:
    """Handle ping error for closed connection."""
    logger.debug(f"Connection closed for {connection_id}, stopping heartbeat")
    raise ConnectionError(f"Connection closed: {error}")


def handle_general_ping_error(connection_id: str, error: Exception) -> None:
    """Handle general ping error."""
    logger.debug(f"Failed to send ping to {connection_id}: {error}")
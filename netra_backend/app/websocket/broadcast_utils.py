"""WebSocket broadcast utility functions.

Contains utility functions for message preparation, validation, and result creation.
"""

import time
from typing import Dict, Any, Union, List, Tuple

from netra_backend.app.schemas.registry import WebSocketMessage
from netra_backend.app.schemas.websocket_message_types import ServerMessage, BroadcastResult
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def prepare_broadcast_message(message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> Union[WebSocketMessage, ServerMessage, Dict[str, Any]]:
    """Prepare message for broadcast by adding timestamp if needed."""
    if isinstance(message, dict) and "timestamp" not in message:
        message["timestamp"] = time.time()
    return message


def validate_user_connections(user_id: str, connections: List) -> bool:
    """Validate that user has active connections."""
    if not connections:
        logger.debug(f"No active connections for user {user_id}")
        return False
    return True


def validate_room_connections(room_id: str, connection_ids: List[str]) -> bool:
    """Validate that room has connections."""
    if not connection_ids:
        logger.debug(f"Room {room_id} does not exist or is empty")
        return False
    return True


def extract_message_type(message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> str:
    """Extract message type from message object."""
    return message.get("type", "unknown") if isinstance(message, dict) else "unknown"


def create_broadcast_result(successful_sends: int, failed_sends: int, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
    """Create broadcast result object."""
    message_type = extract_message_type(message)
    total_connections = successful_sends + failed_sends
    return _build_broadcast_result(successful_sends, failed_sends, total_connections, message_type)

def _build_broadcast_result(successful: int, failed: int, total: int, message_type: str) -> BroadcastResult:
    """Build broadcast result with given parameters."""
    return BroadcastResult(
        successful=successful,
        failed=failed,
        total_connections=total,
        message_type=message_type
    )


def create_room_broadcast_result(successful_sends: int, failed_sends: int, total_connections: int, 
                               message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
    """Create broadcast result for room broadcast."""
    message_type = extract_message_type(message)
    return _build_broadcast_result(successful_sends, failed_sends, total_connections, message_type)


def update_broadcast_counters(success: bool, should_remove: bool, successful_sends: int, 
                            failed_sends: int, connections_to_remove: list, user_id: str, conn_info) -> Tuple[int, int, list]:
    """Update broadcast counters based on send result."""
    successful_sends, failed_sends = _update_send_counters(success, successful_sends, failed_sends)
    connections_to_remove = _update_removal_list(should_remove, connections_to_remove, user_id, conn_info)
    return successful_sends, failed_sends, connections_to_remove

def _update_send_counters(success: bool, successful_sends: int, failed_sends: int) -> Tuple[int, int]:
    """Update success and failure counters."""
    if success:
        successful_sends += 1
    else:
        failed_sends += 1
    return successful_sends, failed_sends

def _update_removal_list(should_remove: bool, connections_to_remove: list, user_id: str, conn_info) -> list:
    """Update connections removal list."""
    if should_remove:
        connections_to_remove.append((user_id, conn_info))
    return connections_to_remove


def update_user_broadcast_counters(success: bool, should_remove: bool, successful_sends: int, 
                                 connections_to_remove: list, conn_info) -> Tuple[int, list]:
    """Update user broadcast counters."""
    if success:
        successful_sends += 1
    elif should_remove:
        connections_to_remove.append(conn_info)
    return successful_sends, connections_to_remove


def update_room_broadcast_counters(success: bool, should_remove: bool, successful_sends: int, 
                                 failed_sends: int, connections_to_remove: list, conn_id: str) -> Tuple[int, int, list]:
    """Update room broadcast counters."""
    successful_sends, failed_sends = _update_send_counters(success, successful_sends, failed_sends)
    connections_to_remove = _update_room_removal_list(should_remove, connections_to_remove, conn_id)
    return successful_sends, failed_sends, connections_to_remove

def _update_room_removal_list(should_remove: bool, connections_to_remove: list, conn_id: str) -> list:
    """Update room connections removal list."""
    if should_remove:
        connections_to_remove.append(conn_id)
    return connections_to_remove


def log_broadcast_completion(successful_sends: int, failed_sends: int) -> None:
    """Log broadcast completion status."""
    if failed_sends > 0:
        logger.warning(f"Broadcast completed: {successful_sends} successful, {failed_sends} failed")


def create_empty_room_broadcast_result() -> BroadcastResult:
    """Create empty broadcast result for invalid room."""
    return BroadcastResult(successful=0, failed=0, total_connections=0, message_type="unknown")


def get_broadcast_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Get broadcast-specific statistics."""
    return {
        "total_broadcasts": stats["total_broadcasts"],
        "successful_sends": stats["successful_sends"],
        "failed_sends": stats["failed_sends"]
    }
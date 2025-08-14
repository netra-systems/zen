"""WebSocket Manager Broadcasting - Message broadcasting and room management.

This module handles WebSocket message broadcasting operations including sending to threads,
rooms, and all connected users with proper validation and error handling.
All functions are ≤8 lines as per CLAUDE.md requirements.
"""

from typing import Dict, Any, Union, List

from app.logging_config import central_logger
from app.schemas.registry import WebSocketMessage
from app.schemas.websocket_message_types import ServerMessage, BroadcastResult
from app.ws_manager_core import WebSocketManagerCore

logger = central_logger.get_logger(__name__)


class WebSocketBroadcastingManager:
    """Manages WebSocket broadcasting operations."""

    def __init__(self, core: WebSocketManagerCore) -> None:
        """Initialize with core manager reference."""
        self.core = core

    async def send_to_thread(self, thread_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Send message to all users in a specific thread/room."""
        validated_message = self._prepare_message(message)
        if validated_message is None:
            return False
        return await self._broadcast_to_room(thread_id, validated_message)

    async def _broadcast_to_room(self, thread_id: str, validated_message: Dict[str, Any]) -> bool:
        """Broadcast validated message to all users in room."""
        room_connections = self.core.room_manager.get_room_connections(thread_id)
        if not room_connections:
            return False
        return await self._send_to_room_users(room_connections, validated_message)

    async def _send_to_room_users(self, room_connections: List[str], validated_message: Dict[str, Any]) -> bool:
        """Send message to all users in room connection list."""
        success_count = 0
        for user_id in room_connections:
            if await self._send_to_single_user(user_id, validated_message):
                success_count += 1
        return success_count > 0

    async def _send_to_single_user(self, user_id: str, validated_message: Dict[str, Any]) -> bool:
        """Send message to single user with messaging manager."""
        from app.ws_manager_messaging import WebSocketMessagingManager
        messaging = WebSocketMessagingManager(self.core)
        return await messaging.send_to_user(user_id, validated_message)

    async def broadcast_to_all(self, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
        """Broadcast message to all connected users."""
        validated_message = self._prepare_message(message)
        if validated_message is None:
            return self._create_failed_broadcast_result()
        return await self._execute_global_broadcast(validated_message)

    def _create_failed_broadcast_result(self) -> BroadcastResult:
        """Create broadcast result for failed validation."""
        return BroadcastResult(
            successful=0, failed=0, total_connections=0, message_type="invalid"
        )

    async def _execute_global_broadcast(self, validated_message: Dict[str, Any]) -> BroadcastResult:
        """Execute broadcast to all users and update stats."""
        result = await self.core.broadcast_manager.broadcast_to_all(validated_message)
        self.core.increment_stat("total_messages_sent", result.successful)
        return result

    def _prepare_message(self, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare and validate message for broadcasting."""
        from app.ws_manager_messaging import WebSocketMessagingManager
        messaging = WebSocketMessagingManager(self.core)
        return messaging._prepare_message(message)

    async def broadcast_to_job(self, job_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Send message to all users connected to a specific job."""
        return await self.send_to_thread(job_id, message)

    async def join_room(self, user_id: str, room_id: str) -> None:
        """Add user to a specific room for broadcasting."""
        self.core.room_manager.join_room(user_id, room_id)

    async def leave_room(self, user_id: str, room_id: str) -> None:
        """Remove user from a specific room."""
        self.core.room_manager.leave_room(user_id, room_id)

    async def leave_all_rooms(self, user_id: str) -> None:
        """Remove user from all rooms."""
        self.core.room_manager.leave_all_rooms(user_id)

    def get_room_connections(self, room_id: str) -> List[str]:
        """Get all user connections in a specific room."""
        return self.core.room_manager.get_room_connections(room_id)

    def get_user_rooms(self, user_id: str) -> List[str]:
        """Get all rooms that a user is connected to."""
        return self.core.room_manager.get_user_rooms(user_id)
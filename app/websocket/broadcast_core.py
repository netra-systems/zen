"""Core WebSocket broadcasting functionality.

Main entry point for WebSocket message broadcasting operations.
"""

from typing import Dict, List, Any, Union

from app.logging_config import central_logger
from app.schemas.registry import WebSocketMessage
from app.schemas.websocket_message_types import ServerMessage, BroadcastResult
from app.websocket.connection import ConnectionInfo, ConnectionManager
from app.websocket.room_manager import RoomManager
from app.websocket.broadcast_executor import BroadcastExecutor
from app.websocket import broadcast_utils as utils

logger = central_logger.get_logger(__name__)


class BroadcastManager:
    """Manages broadcasting messages to WebSocket connections."""
    
    def __init__(self, connection_manager: ConnectionManager, room_manager: RoomManager = None):
        """Initialize broadcast manager."""
        self.connection_manager = connection_manager
        self.room_manager = self._init_room_manager(room_manager)
        self.executor = BroadcastExecutor(connection_manager)
        self._stats = self._init_broadcast_stats()
    
    def _init_room_manager(self, room_manager: RoomManager = None) -> RoomManager:
        """Initialize room manager instance."""
        return room_manager if room_manager is not None else RoomManager(self.connection_manager)
    
    def _init_broadcast_stats(self) -> Dict[str, int]:
        """Initialize broadcast statistics."""
        return {
            "total_broadcasts": 0,
            "successful_sends": 0,
            "failed_sends": 0
        }

    async def broadcast_to_all(self, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
        """Broadcast a message to all connected users."""
        prepared_message = utils.prepare_broadcast_message(message)
        result = await self.executor.execute_all_broadcast(prepared_message)
        self._update_broadcast_stats(result.successful_sends, result.failed_sends)
        return result

    async def broadcast_to_user(self, user_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Broadcast a message to all connections for a specific user."""
        connections = self.connection_manager.get_user_connections(user_id)
        if not utils.validate_user_connections(user_id, connections):
            return False
        successful_sends = await self.executor.execute_user_broadcast(user_id, connections, message)
        return successful_sends > 0

    async def broadcast_to_room(self, room_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
        """Broadcast a message to all connections in a room."""
        connection_ids = self.room_manager.get_room_connections(room_id)
        if not utils.validate_room_connections(room_id, connection_ids):
            return utils.create_empty_room_broadcast_result()
        result = await self.executor.execute_room_broadcast(room_id, connection_ids, message)
        return result

    def _update_broadcast_stats(self, successful_sends: int, failed_sends: int) -> None:
        """Update broadcast statistics."""
        self._stats["total_broadcasts"] += 1
        self._stats["successful_sends"] += successful_sends
        self._stats["failed_sends"] += failed_sends

    # Delegate room management methods
    def create_room(self, room_id: str) -> bool:
        """Create a new room."""
        return self.room_manager.create_room(room_id)

    def delete_room(self, room_id: str) -> bool:
        """Delete a room."""
        return self.room_manager.delete_room(room_id)

    def join_room(self, connection_id: str, room_id: str) -> bool:
        """Add a connection to a room."""
        return self.room_manager.join_room(connection_id, room_id)

    def leave_room(self, connection_id: str, room_id: str) -> bool:
        """Remove a connection from a room."""
        return self.room_manager.leave_room(connection_id, room_id)

    def leave_all_rooms(self, connection_id: str):
        """Remove a connection from all rooms."""
        self.room_manager.leave_all_rooms(connection_id)

    def get_room_connections(self, room_id: str):
        """Get connections in a room."""
        return self.room_manager.get_room_connections(room_id)

    def get_connection_rooms(self, connection_id: str):
        """Get rooms for a connection."""
        return self.room_manager.get_connection_rooms(connection_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get broadcast and room statistics."""
        room_stats = self.room_manager.get_stats()
        broadcast_stats = utils.get_broadcast_stats(self._stats)
        return {**broadcast_stats, **room_stats}
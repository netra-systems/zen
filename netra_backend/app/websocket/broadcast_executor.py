"""WebSocket Broadcast Execution Engine.

Handles the actual execution of broadcast operations to connections.
"""

import asyncio
from typing import Any, Dict, List, Tuple, Union

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.registry import WebSocketMessage
from netra_backend.app.schemas.websocket_message_types import (
    BroadcastResult,
    ServerMessage,
)
from netra_backend.app.websocket import broadcast_utils as utils
from netra_backend.app.websocket.connection import ConnectionInfo, ConnectionManager

logger = central_logger.get_logger(__name__)


class BroadcastExecutor:
    """Executes broadcast operations to WebSocket connections."""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    async def execute_all_broadcast(self, prepared_message) -> BroadcastResult:
        """Execute broadcast to all connections."""
        connections_snapshot = await self._create_connections_snapshot()
        successful_sends, failed_sends, dead_connections = await self._broadcast_to_connections(connections_snapshot, prepared_message)
        await self._cleanup_dead_connections(dead_connections)
        utils.log_broadcast_completion(successful_sends, failed_sends)
        return utils.create_broadcast_result(successful_sends, failed_sends, prepared_message)

    async def execute_user_broadcast(self, user_id: str, connections: List[ConnectionInfo], message) -> int:
        """Execute broadcast to user connections."""
        prepared_message = utils.prepare_broadcast_message(message)
        successful_sends, dead_connections = await self._broadcast_to_user_connections(user_id, connections, prepared_message)
        await self._cleanup_user_dead_connections(user_id, dead_connections)
        return successful_sends

    async def execute_room_broadcast(self, room_id: str, connection_ids: List[str], message) -> BroadcastResult:
        """Execute broadcast to room connections."""
        prepared_message = utils.prepare_broadcast_message(message)
        successful_sends, failed_sends, invalid_connections = await self._broadcast_to_room_connections(room_id, connection_ids, prepared_message)
        return utils.create_room_broadcast_result(successful_sends, failed_sends, len(connection_ids), prepared_message)

    async def _create_connections_snapshot(self) -> List[Tuple[str, ConnectionInfo]]:
        """Create snapshot of all active connections under lock."""
        async with self.connection_manager._connection_lock:
            connections_snapshot = []
            for user_id, connections in self.connection_manager.active_connections.items():
                for conn_info in connections:
                    connections_snapshot.append((user_id, conn_info))
            return connections_snapshot

    async def _broadcast_to_connections(self, connections_snapshot: List[Tuple[str, ConnectionInfo]], message) -> Tuple[int, int, List[Tuple[str, ConnectionInfo]]]:
        """Broadcast message to all connections in snapshot."""
        successful_sends = 0
        failed_sends = 0
        connections_to_remove = []
        return await self._process_connection_batch(connections_snapshot, message, successful_sends, failed_sends, connections_to_remove)
    
    async def _process_connection_batch(self, connections_snapshot, message, successful_sends: int, failed_sends: int, connections_to_remove) -> Tuple[int, int, List[Tuple[str, ConnectionInfo]]]:
        """Process batch of connections for broadcast."""
        for user_id, conn_info in connections_snapshot:
            success, should_remove = await self._send_to_single_connection(user_id, conn_info, message)
            successful_sends, failed_sends, connections_to_remove = utils.update_broadcast_counters(
                success, should_remove, successful_sends, failed_sends, connections_to_remove, user_id, conn_info)
        return successful_sends, failed_sends, connections_to_remove

    async def _send_to_single_connection(self, user_id: str, conn_info: ConnectionInfo, message) -> Tuple[bool, bool]:
        """Send message to single connection and determine if cleanup needed."""
        try:
            from netra_backend.app.websocket.broadcast_sender import BroadcastSender
            sender = BroadcastSender(self.connection_manager)
            success = await sender.send_to_connection(conn_info, message)
            return self._handle_connection_result(success, conn_info)
        except Exception as e:
            return self._handle_connection_error(user_id, conn_info, e)

    def _handle_connection_result(self, success: bool, conn_info: ConnectionInfo) -> Tuple[bool, bool]:
        """Handle result of single connection send attempt."""
        if success:
            conn_info.message_count += 1
            return True, False
        else:
            should_remove = not self.connection_manager.is_connection_alive(conn_info)
            return False, should_remove

    def _handle_connection_error(self, user_id: str, conn_info: ConnectionInfo, error: Exception) -> Tuple[bool, bool]:
        """Handle error during single connection send."""
        logger.error(f"Unexpected error broadcasting to {user_id} ({conn_info.connection_id}): {error}")
        conn_info.error_count += 1
        return False, False

    async def _cleanup_dead_connections(self, connections_to_remove: List[Tuple[str, ConnectionInfo]]) -> None:
        """Clean up dead connections identified during broadcast."""
        for user_id, conn_info in connections_to_remove:
            conn_info.is_closing = True
            await self.connection_manager._disconnect_internal(
                user_id, conn_info.websocket, code=1001, reason="Connection lost during broadcast"
            )

    async def _broadcast_to_user_connections(self, user_id: str, connections: List[ConnectionInfo], message) -> Tuple[int, List[ConnectionInfo]]:
        """Broadcast message to user's connections."""
        successful_sends = 0
        connections_to_remove = []
        return await self._process_user_connections(connections, message, successful_sends, connections_to_remove)
    
    async def _process_user_connections(self, connections: List[ConnectionInfo], message, successful_sends: int, connections_to_remove) -> Tuple[int, List[ConnectionInfo]]:
        """Process user connections for broadcast."""
        for conn_info in connections:
            success, should_remove = await self._send_to_user_connection(conn_info, message)
            successful_sends, connections_to_remove = utils.update_user_broadcast_counters(
                success, should_remove, successful_sends, connections_to_remove, conn_info)
        return successful_sends, connections_to_remove

    async def _send_to_user_connection(self, conn_info: ConnectionInfo, message) -> Tuple[bool, bool]:
        """Send message to user connection with error handling."""
        try:
            from netra_backend.app.websocket.broadcast_sender import BroadcastSender
            sender = BroadcastSender(self.connection_manager)
            success = await sender.send_to_connection(conn_info, message)
            return self._handle_user_connection_result(success, conn_info)
        except Exception as e:
            return self._handle_user_connection_error(conn_info, e)

    def _handle_user_connection_result(self, success: bool, conn_info: ConnectionInfo) -> Tuple[bool, bool]:
        """Handle result of user connection send attempt."""
        if success:
            conn_info.message_count += 1
            return True, False
        else:
            should_remove = not self.connection_manager.is_connection_alive(conn_info)
            return False, should_remove

    def _handle_user_connection_error(self, conn_info: ConnectionInfo, error: Exception) -> Tuple[bool, bool]:
        """Handle error during user connection send."""
        logger.error(f"Error sending to connection {conn_info.connection_id}: {error}")
        conn_info.error_count += 1
        return False, False

    async def _cleanup_user_dead_connections(self, user_id: str, connections_to_remove: List[ConnectionInfo]) -> None:
        """Clean up dead connections for user."""
        for conn_info in connections_to_remove:
            conn_info.is_closing = True
            await self.connection_manager._disconnect_internal(
                user_id, conn_info.websocket, code=1001, reason="Connection lost"
            )

    async def _broadcast_to_room_connections(self, room_id: str, connection_ids: List[str], message) -> Tuple[int, int, List[str]]:
        """Broadcast message to all connections in room."""
        successful_sends = 0
        failed_sends = 0
        connections_to_remove = []
        return await self._process_room_connections(room_id, connection_ids, message, successful_sends, failed_sends, connections_to_remove)
    
    async def _process_room_connections(self, room_id: str, connection_ids: List[str], message, successful_sends: int, failed_sends: int, connections_to_remove: List[str]) -> Tuple[int, int, List[str]]:
        """Process room connections for broadcast."""
        for conn_id in connection_ids:
            success, should_remove = await self._send_to_room_connection(room_id, conn_id, message)
            successful_sends, failed_sends, connections_to_remove = utils.update_room_broadcast_counters(
                success, should_remove, successful_sends, failed_sends, connections_to_remove, conn_id)
        return successful_sends, failed_sends, connections_to_remove

    async def _send_to_room_connection(self, room_id: str, conn_id: str, message) -> Tuple[bool, bool]:
        """Send message to room connection with validation."""
        conn_info = self.connection_manager.get_connection_by_id(conn_id)
        if not conn_info:
            return False, True
        return await self._execute_room_connection_send(room_id, conn_id, conn_info, message)
    
    async def _execute_room_connection_send(self, room_id: str, conn_id: str, conn_info: ConnectionInfo, message) -> Tuple[bool, bool]:
        """Execute send to room connection with error handling."""
        try:
            from netra_backend.app.websocket.broadcast_sender import BroadcastSender
            sender = BroadcastSender(self.connection_manager)
            success = await sender.send_to_connection(conn_info, message)
            return self._handle_room_connection_result(success, conn_info)
        except Exception as e:
            return self._handle_room_connection_error(room_id, conn_id, e)

    def _handle_room_connection_result(self, success: bool, conn_info: ConnectionInfo) -> Tuple[bool, bool]:
        """Handle result of room connection send attempt."""
        if success:
            conn_info.message_count += 1
            return True, False
        else:
            should_remove = not self.connection_manager.is_connection_alive(conn_info)
            return False, should_remove

    def _handle_room_connection_error(self, room_id: str, conn_id: str, error: Exception) -> Tuple[bool, bool]:
        """Handle error during room connection send."""
        logger.error(f"Error sending to connection {conn_id} in room {room_id}: {error}")
        return False, False
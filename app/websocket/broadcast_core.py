"""Core WebSocket broadcasting functionality.

Handles broadcasting messages to multiple connections efficiently and reliably.
"""

import asyncio
from typing import Dict, List, Any, Union, Tuple

from starlette.websockets import WebSocketState

from app.logging_config import central_logger
from app.schemas.registry import WebSocketMessage
from app.schemas.websocket_message_types import ServerMessage, BroadcastResult
from app.core.json_utils import prepare_websocket_message
from .connection import ConnectionInfo, ConnectionManager
from .room_manager import RoomManager
from . import broadcast_utils as utils

logger = central_logger.get_logger(__name__)


class BroadcastManager:
    """Manages broadcasting messages to WebSocket connections."""
    
    def __init__(self, connection_manager: ConnectionManager, room_manager: RoomManager = None):
        """Initialize broadcast manager.
        
        Args:
            connection_manager: Connection manager instance
            room_manager: Optional room manager instance (creates new one if None)
        """
        self.connection_manager = connection_manager
        self.room_manager = self._init_room_manager(room_manager)
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
        """Broadcast a message to all connected users.
        
        Args:
            message: Message to broadcast
            
        Returns:
            BroadcastResult with send statistics
        """
        prepared_message = utils.prepare_broadcast_message(message)
        return await self._execute_all_broadcast(prepared_message)
    
    async def _execute_all_broadcast(self, prepared_message) -> BroadcastResult:
        """Execute broadcast to all connections."""
        connections_snapshot = await self._create_connections_snapshot()
        successful_sends, failed_sends, dead_connections = await self._broadcast_to_connections(connections_snapshot, prepared_message)
        await self._cleanup_broadcast_dead_connections(dead_connections)
        self._update_broadcast_stats(successful_sends, failed_sends)
        utils.log_broadcast_completion(successful_sends, failed_sends)
        return utils.create_broadcast_result(successful_sends, failed_sends, prepared_message)

    async def broadcast_to_user(self, user_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Broadcast a message to all connections for a specific user.
        
        Args:
            user_id: User to send message to
            message: Message to send
            
        Returns:
            True if message was sent to at least one connection
        """
        connections = self.connection_manager.get_user_connections(user_id)
        if not utils.validate_user_connections(user_id, connections):
            return False
        return await self._execute_user_broadcast(user_id, connections, message)
    
    async def _execute_user_broadcast(self, user_id: str, connections: List[ConnectionInfo], message) -> bool:
        """Execute broadcast to user connections."""
        prepared_message = utils.prepare_broadcast_message(message)
        successful_sends, dead_connections = await self._broadcast_to_user_connections(user_id, connections, prepared_message)
        await self._cleanup_user_dead_connections(user_id, dead_connections)
        return successful_sends > 0

    async def broadcast_to_room(self, room_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
        """Broadcast a message to all connections in a room.
        
        Args:
            room_id: Room to broadcast to
            message: Message to broadcast
            
        Returns:
            BroadcastResult with send statistics
        """
        connection_ids = self.room_manager.get_room_connections(room_id)
        if not utils.validate_room_connections(room_id, connection_ids):
            return utils.create_empty_room_broadcast_result()
        return await self._execute_room_broadcast(room_id, connection_ids, message)
    
    async def _execute_room_broadcast(self, room_id: str, connection_ids: List[str], message) -> BroadcastResult:
        """Execute broadcast to room connections."""
        prepared_message = utils.prepare_broadcast_message(message)
        successful_sends, failed_sends, invalid_connections = await self._broadcast_to_room_connections(room_id, connection_ids, prepared_message)
        self._cleanup_room_invalid_connections(invalid_connections)
        return utils.create_room_broadcast_result(successful_sends, failed_sends, len(connection_ids), prepared_message)

    async def _create_connections_snapshot(self) -> List[Tuple[str, ConnectionInfo]]:
        """Create snapshot of all active connections under lock."""
        async with self.connection_manager._connection_lock:
            connections_snapshot = []
            for user_id, connections in self.connection_manager.active_connections.items():
                for conn_info in connections:
                    connections_snapshot.append((user_id, conn_info))
            return connections_snapshot

    async def _broadcast_to_connections(self, connections_snapshot: List[Tuple[str, ConnectionInfo]], message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> Tuple[int, int, List[Tuple[str, ConnectionInfo]]]:
        """Broadcast message to all connections in snapshot."""
        successful_sends = 0
        failed_sends = 0
        connections_to_remove = []
        return await self._process_connection_batch(connections_snapshot, message, successful_sends, failed_sends, connections_to_remove)
    
    async def _process_connection_batch(self, connections_snapshot: List[Tuple[str, ConnectionInfo]], message, successful_sends: int, failed_sends: int, connections_to_remove: List[Tuple[str, ConnectionInfo]]) -> Tuple[int, int, List[Tuple[str, ConnectionInfo]]]:
        """Process batch of connections for broadcast."""
        for user_id, conn_info in connections_snapshot:
            success, should_remove = await self._send_to_single_connection(user_id, conn_info, message)
            successful_sends, failed_sends, connections_to_remove = utils.update_broadcast_counters(
                success, should_remove, successful_sends, failed_sends, connections_to_remove, user_id, conn_info)
        return successful_sends, failed_sends, connections_to_remove

    async def _send_to_single_connection(self, user_id: str, conn_info: ConnectionInfo, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> Tuple[bool, bool]:
        """Send message to single connection and determine if cleanup needed."""
        try:
            success = await self._send_to_connection(conn_info, message)
            return self._handle_single_connection_result(success, conn_info)
        except Exception as e:
            return self._handle_single_connection_error(user_id, conn_info, e)

    def _handle_single_connection_result(self, success: bool, conn_info: ConnectionInfo) -> Tuple[bool, bool]:
        """Handle result of single connection send attempt."""
        if success:
            conn_info.message_count += 1
            return True, False
        else:
            should_remove = not self.connection_manager.is_connection_alive(conn_info)
            return False, should_remove

    def _handle_single_connection_error(self, user_id: str, conn_info: ConnectionInfo, error: Exception) -> Tuple[bool, bool]:
        """Handle error during single connection send."""
        logger.error(f"Unexpected error broadcasting to {user_id} ({conn_info.connection_id}): {error}")
        conn_info.error_count += 1
        return False, False

    async def _cleanup_broadcast_dead_connections(self, connections_to_remove: List[Tuple[str, ConnectionInfo]]) -> None:
        """Clean up dead connections identified during broadcast."""
        for user_id, conn_info in connections_to_remove:
            # Mark connection as closing before cleanup
            conn_info.is_closing = True
            await self.connection_manager._disconnect_internal(
                user_id, conn_info.websocket, code=1001, reason="Connection lost during broadcast"
            )

    def _update_broadcast_stats(self, successful_sends: int, failed_sends: int) -> None:
        """Update broadcast statistics."""
        self._stats["total_broadcasts"] += 1
        self._stats["successful_sends"] += successful_sends
        self._stats["failed_sends"] += failed_sends

    async def _broadcast_to_user_connections(self, user_id: str, connections: List[ConnectionInfo], message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> Tuple[int, List[ConnectionInfo]]:
        """Broadcast message to user's connections."""
        successful_sends = 0
        connections_to_remove = []
        return await self._process_user_connections(connections, message, successful_sends, connections_to_remove)
    
    async def _process_user_connections(self, connections: List[ConnectionInfo], message, successful_sends: int, connections_to_remove: List[ConnectionInfo]) -> Tuple[int, List[ConnectionInfo]]:
        """Process user connections for broadcast."""
        for conn_info in connections:
            success, should_remove = await self._send_to_user_connection(conn_info, message)
            successful_sends, connections_to_remove = utils.update_user_broadcast_counters(
                success, should_remove, successful_sends, connections_to_remove, conn_info)
        return successful_sends, connections_to_remove

    async def _send_to_user_connection(self, conn_info: ConnectionInfo, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> Tuple[bool, bool]:
        """Send message to user connection with error handling."""
        try:
            success = await self._send_to_connection(conn_info, message)
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
            # Mark connection as closing before cleanup
            conn_info.is_closing = True
            await self.connection_manager._disconnect_internal(
                user_id, conn_info.websocket, code=1001, reason="Connection lost"
            )

    async def _broadcast_to_room_connections(self, room_id: str, connection_ids: List[str], message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> Tuple[int, int, List[str]]:
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

    async def _send_to_room_connection(self, room_id: str, conn_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> Tuple[bool, bool]:
        """Send message to room connection with validation."""
        conn_info = self.connection_manager.get_connection_by_id(conn_id)
        if not conn_info:
            return False, True
        return await self._execute_room_connection_send(room_id, conn_id, conn_info, message)
    
    async def _execute_room_connection_send(self, room_id: str, conn_id: str, conn_info: ConnectionInfo, message) -> Tuple[bool, bool]:
        """Execute send to room connection with error handling."""
        try:
            success = await self._send_to_connection(conn_info, message)
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

    def _cleanup_room_invalid_connections(self, connections_to_remove: List[str]) -> None:
        """Clean up invalid connections from room."""
        for conn_id in connections_to_remove:
            self.room_manager.leave_all_rooms(conn_id)

    async def _send_to_connection(self, conn_info: ConnectionInfo, message: Union[Dict[str, Any], Any]) -> bool:
        """Send a message to a specific connection.
        
        Args:
            conn_info: Connection to send to
            message: Message to send
            
        Returns:
            True if message was sent successfully
        """
        if not self._is_connection_ready(conn_info):
            return False
        return await self._execute_connection_send(conn_info, message)
    
    async def _execute_connection_send(self, conn_info: ConnectionInfo, message) -> bool:
        """Execute connection send with comprehensive error handling."""
        try:
            return await self._perform_message_send(conn_info, message)
        except (RuntimeError, ConnectionError) as e:
            self._handle_connection_error(conn_info, e)
            return False
        except Exception as e:
            self._handle_unexpected_error(conn_info, e)
            return False

    def _is_connection_ready(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection is ready for sending."""
        if not self._check_connection_not_closing(conn_info):
            return False
        return self._check_websocket_states(conn_info)
    
    def _check_connection_not_closing(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection is not marked as closing."""
        if conn_info.is_closing:
            logger.debug(f"Connection {conn_info.connection_id} is closing, skipping send")
            return False
        return True
    
    def _check_websocket_states(self, conn_info: ConnectionInfo) -> bool:
        """Check WebSocket client and application states."""
        ws_state = conn_info.websocket.client_state
        app_state = conn_info.websocket.application_state
        return self._validate_connection_states(conn_info, ws_state, app_state)
    
    def _validate_connection_states(self, conn_info: ConnectionInfo, ws_state, app_state) -> bool:
        """Validate WebSocket connection states."""
        if not self._check_client_state(conn_info, ws_state):
            return False
        return self._check_application_state(conn_info, app_state)
    
    def _check_client_state(self, conn_info: ConnectionInfo, ws_state) -> bool:
        """Check WebSocket client state."""
        if ws_state != WebSocketState.CONNECTED:
            logger.debug(f"Connection {conn_info.connection_id} not in CONNECTED state: {ws_state.name}")
            return False
        return True
    
    def _check_application_state(self, conn_info: ConnectionInfo, app_state) -> bool:
        """Check WebSocket application state."""
        if app_state != WebSocketState.CONNECTED:
            logger.debug(f"Connection {conn_info.connection_id} application state not connected: {app_state.name}")
            return False
        return True

    async def _perform_message_send(self, conn_info: ConnectionInfo, message: Union[Dict[str, Any], Any]) -> bool:
        """Perform actual message sending."""
        prepared_message = prepare_websocket_message(message)
        await conn_info.websocket.send_json(prepared_message)
        return True

    def _handle_connection_error(self, conn_info: ConnectionInfo, error: Exception) -> None:
        """Handle connection-related errors."""
        error_msg = str(error)
        self._log_connection_error(conn_info, error, error_msg)
    
    def _log_connection_error(self, conn_info: ConnectionInfo, error: Exception, error_msg: str) -> None:
        """Log connection error with appropriate level."""
        if self._is_close_related_error(error_msg):
            self._log_close_error(conn_info, error, error_msg)
        else:
            logger.warning(f"Error sending to connection {conn_info.connection_id}: {error}")
    
    def _is_close_related_error(self, error_msg: str) -> bool:
        """Check if error is related to connection closing."""
        return ("Cannot call \"send\" once a close message has been sent" in error_msg or
                "Cannot call" in error_msg or "close" in error_msg.lower())
    
    def _log_close_error(self, conn_info: ConnectionInfo, error: Exception, error_msg: str) -> None:
        """Log connection close related errors."""
        if "Cannot call \"send\" once a close message has been sent" in error_msg:
            logger.debug(f"Connection {conn_info.connection_id} already closing, skipping send")
        else:
            logger.debug(f"Connection {conn_info.connection_id} closed: {error}")

    def _handle_unexpected_error(self, conn_info: ConnectionInfo, error: Exception) -> None:
        """Handle unexpected errors during message sending."""
        logger.error(f"Unexpected error sending to connection {conn_info.connection_id}: {error}")

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
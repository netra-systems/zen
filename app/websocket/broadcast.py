"""Core WebSocket broadcasting functionality.

Handles broadcasting messages to multiple connections efficiently and reliably.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Union

from starlette.websockets import WebSocketState

from app.logging_config import central_logger
from app.schemas.registry import WebSocketMessage
from app.schemas.websocket_message_types import ServerMessage, BroadcastResult
from app.core.json_utils import prepare_websocket_message, safe_json_dumps
from .connection import ConnectionInfo, ConnectionManager
from .room_manager import RoomManager

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
        self.room_manager = room_manager if room_manager is not None else RoomManager(connection_manager)
        self._stats = {
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
        successful_sends = 0
        failed_sends = 0
        connections_to_remove = []
        
        # Add timestamp if not present
        if isinstance(message, dict) and "timestamp" not in message:
            message["timestamp"] = time.time()
        
        # Use lock to prevent race conditions during broadcast
        async with self.connection_manager._connection_lock:
            # Create snapshot of connections to avoid modification during iteration
            connections_snapshot = []
            for user_id, connections in self.connection_manager.active_connections.items():
                for conn_info in connections:
                    connections_snapshot.append((user_id, conn_info))
        
        # Send to all connections outside of lock to avoid blocking
        for user_id, conn_info in connections_snapshot:
            try:
                success = await self._send_to_connection(conn_info, message)
                if success:
                    successful_sends += 1
                    conn_info.message_count += 1
                else:
                    failed_sends += 1
                    if not self.connection_manager.is_connection_alive(conn_info):
                        connections_to_remove.append((user_id, conn_info))
            except Exception as e:
                logger.error(f"Unexpected error broadcasting to {user_id} ({conn_info.connection_id}): {e}")
                conn_info.error_count += 1
                failed_sends += 1
        
        # Clean up dead connections
        for user_id, conn_info in connections_to_remove:
            await self.connection_manager._disconnect_internal(
                user_id, conn_info.websocket, code=1001, reason="Connection lost during broadcast"
            )
        
        # Update statistics
        self._stats["total_broadcasts"] += 1
        self._stats["successful_sends"] += successful_sends
        self._stats["failed_sends"] += failed_sends
        
        if failed_sends > 0:
            logger.warning(f"Broadcast completed: {successful_sends} successful, {failed_sends} failed")
        
        return BroadcastResult(
            successful=successful_sends,
            failed=failed_sends,
            total_connections=successful_sends + failed_sends,
            message_type=message.get("type", "unknown") if isinstance(message, dict) else "unknown"
        )
    
    async def broadcast_to_user(self, user_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Broadcast a message to all connections for a specific user.
        
        Args:
            user_id: User to send message to
            message: Message to send
            
        Returns:
            True if message was sent to at least one connection
        """
        connections = self.connection_manager.get_user_connections(user_id)
        if not connections:
            logger.debug(f"No active connections for user {user_id}")
            return False
        
        # Add timestamp if not present
        if isinstance(message, dict) and "timestamp" not in message:
            message["timestamp"] = time.time()
        
        successful_sends = 0
        connections_to_remove = []
        
        for conn_info in connections:
            try:
                success = await self._send_to_connection(conn_info, message)
                if success:
                    successful_sends += 1
                    conn_info.message_count += 1
                else:
                    if not self.connection_manager.is_connection_alive(conn_info):
                        connections_to_remove.append(conn_info)
            except Exception as e:
                logger.error(f"Error sending to connection {conn_info.connection_id}: {e}")
                conn_info.error_count += 1
        
        # Clean up dead connections
        for conn_info in connections_to_remove:
            await self.connection_manager._disconnect_internal(
                user_id, conn_info.websocket, code=1001, reason="Connection lost"
            )
        
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
        if not connection_ids:
            logger.debug(f"Room {room_id} does not exist or is empty")
            return BroadcastResult(successful=0, failed=0, total_connections=0, message_type="unknown")
        
        successful_sends = 0
        failed_sends = 0
        connections_to_remove = []
        
        # Add timestamp if not present
        if isinstance(message, dict) and "timestamp" not in message:
            message["timestamp"] = time.time()
        
        for conn_id in connection_ids:
            conn_info = self.connection_manager.get_connection_by_id(conn_id)
            if not conn_info:
                # Connection no longer exists, remove from room
                connections_to_remove.append(conn_id)
                continue
            
            try:
                success = await self._send_to_connection(conn_info, message)
                if success:
                    successful_sends += 1
                    conn_info.message_count += 1
                else:
                    failed_sends += 1
                    if not self.connection_manager.is_connection_alive(conn_info):
                        connections_to_remove.append(conn_id)
            except Exception as e:
                logger.error(f"Error sending to connection {conn_id} in room {room_id}: {e}")
                failed_sends += 1
        
        # Clean up connections that are no longer valid
        for conn_id in connections_to_remove:
            self.room_manager.leave_all_rooms(conn_id)
        
        return BroadcastResult(
            successful=successful_sends,
            failed=failed_sends,
            total_connections=len(connection_ids),
            message_type=message.get("type", "unknown") if isinstance(message, dict) else "unknown"
        )
    
    async def _send_to_connection(self, conn_info: ConnectionInfo, message: Union[Dict[str, Any], Any]) -> bool:
        """Send a message to a specific connection.
        
        Args:
            conn_info: Connection to send to
            message: Message to send
            
        Returns:
            True if message was sent successfully
        """
        try:
            if conn_info.websocket.client_state == WebSocketState.CONNECTED:
                prepared_message = prepare_websocket_message(message)
                await conn_info.websocket.send_text(safe_json_dumps(prepared_message))
                return True
            else:
                logger.debug(f"Connection {conn_info.connection_id} not in CONNECTED state")
                return False
        except (RuntimeError, ConnectionError) as e:
            if "Cannot call" in str(e) or "close" in str(e).lower():
                logger.debug(f"Connection {conn_info.connection_id} closed: {e}")
            else:
                logger.warning(f"Error sending to connection {conn_info.connection_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending to connection {conn_info.connection_id}: {e}")
            return False
    
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
        
        return {
            "total_broadcasts": self._stats["total_broadcasts"],
            "successful_sends": self._stats["successful_sends"],
            "failed_sends": self._stats["failed_sends"],
            **room_stats
        }
"""WebSocket broadcast and room management functionality.

Handles broadcasting messages to multiple connections and managing rooms/groups
of WebSocket connections.
"""

import asyncio
import time
from typing import Dict, List, Any, Union, Set, Optional

from starlette.websockets import WebSocketState

from app.logging_config import central_logger
from app.schemas.websocket_unified import WebSocketMessage
from app.schemas.websocket_message_types import ServerMessage, BroadcastResult
from .connection import ConnectionInfo, ConnectionManager

logger = central_logger.get_logger(__name__)


class BroadcastManager:
    """Manages broadcasting messages to WebSocket connections."""
    
    def __init__(self, connection_manager: ConnectionManager):
        """Initialize broadcast manager.
        
        Args:
            connection_manager: Connection manager instance
        """
        self.connection_manager = connection_manager
        self.rooms: Dict[str, Set[str]] = {}  # room_id -> set of connection_ids
        self.connection_rooms: Dict[str, Set[str]] = {}  # connection_id -> set of room_ids
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
        if room_id not in self.rooms:
            logger.debug(f"Room {room_id} does not exist")
            return BroadcastResult(0, 0, 0, "unknown")
        
        connection_ids = self.rooms[room_id].copy()
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
            self._remove_connection_from_room(conn_id, room_id)
        
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
                await conn_info.websocket.send_json(message)
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
    
    def create_room(self, room_id: str) -> bool:
        """Create a new room.
        
        Args:
            room_id: Unique room identifier
            
        Returns:
            True if room was created, False if it already exists
        """
        if room_id in self.rooms:
            return False
        
        self.rooms[room_id] = set()
        logger.info(f"Created room {room_id}")
        return True
    
    def delete_room(self, room_id: str) -> bool:
        """Delete a room and remove all connections from it.
        
        Args:
            room_id: Room to delete
            
        Returns:
            True if room was deleted, False if it didn't exist
        """
        if room_id not in self.rooms:
            return False
        
        # Remove all connections from the room
        connection_ids = self.rooms[room_id].copy()
        for conn_id in connection_ids:
            self._remove_connection_from_room(conn_id, room_id)
        
        del self.rooms[room_id]
        logger.info(f"Deleted room {room_id}")
        return True
    
    def join_room(self, connection_id: str, room_id: str) -> bool:
        """Add a connection to a room.
        
        Args:
            connection_id: Connection to add
            room_id: Room to join
            
        Returns:
            True if connection was added to room
        """
        # Create room if it doesn't exist
        if room_id not in self.rooms:
            self.create_room(room_id)
        
        # Add connection to room
        self.rooms[room_id].add(connection_id)
        
        # Track rooms for this connection
        if connection_id not in self.connection_rooms:
            self.connection_rooms[connection_id] = set()
        self.connection_rooms[connection_id].add(room_id)
        
        logger.debug(f"Connection {connection_id} joined room {room_id}")
        return True
    
    def leave_room(self, connection_id: str, room_id: str) -> bool:
        """Remove a connection from a room.
        
        Args:
            connection_id: Connection to remove
            room_id: Room to leave
            
        Returns:
            True if connection was removed from room
        """
        return self._remove_connection_from_room(connection_id, room_id)
    
    def _remove_connection_from_room(self, connection_id: str, room_id: str) -> bool:
        """Internal method to remove connection from room.
        
        Args:
            connection_id: Connection to remove
            room_id: Room to remove from
            
        Returns:
            True if connection was removed
        """
        removed = False
        
        if room_id in self.rooms:
            if connection_id in self.rooms[room_id]:
                self.rooms[room_id].remove(connection_id)
                removed = True
        
        if connection_id in self.connection_rooms:
            if room_id in self.connection_rooms[connection_id]:
                self.connection_rooms[connection_id].remove(room_id)
            
            # Clean up empty connection room set
            if not self.connection_rooms[connection_id]:
                del self.connection_rooms[connection_id]
        
        if removed:
            logger.debug(f"Connection {connection_id} left room {room_id}")
        
        return removed
    
    def leave_all_rooms(self, connection_id: str):
        """Remove a connection from all rooms it has joined.
        
        Args:
            connection_id: Connection to remove from all rooms
        """
        if connection_id not in self.connection_rooms:
            return
        
        room_ids = self.connection_rooms[connection_id].copy()
        for room_id in room_ids:
            self._remove_connection_from_room(connection_id, room_id)
    
    def get_room_connections(self, room_id: str) -> Set[str]:
        """Get all connection IDs in a room.
        
        Args:
            room_id: Room to get connections for
            
        Returns:
            Set of connection IDs in the room
        """
        return self.rooms.get(room_id, set()).copy()
    
    def get_connection_rooms(self, connection_id: str) -> Set[str]:
        """Get all rooms a connection has joined.
        
        Args:
            connection_id: Connection to get rooms for
            
        Returns:
            Set of room IDs the connection has joined
        """
        return self.connection_rooms.get(connection_id, set()).copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get broadcast and room statistics.
        
        Returns:
            Dictionary with statistics
        """
        room_stats = {}
        for room_id, connections in self.rooms.items():
            room_stats[room_id] = len(connections)
        
        return {
            "total_broadcasts": self._stats["total_broadcasts"],
            "successful_sends": self._stats["successful_sends"],
            "failed_sends": self._stats["failed_sends"],
            "total_rooms": len(self.rooms),
            "room_connections": room_stats,
            "connections_in_rooms": len(self.connection_rooms)
        }
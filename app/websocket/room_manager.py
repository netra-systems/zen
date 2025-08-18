"""WebSocket room management functionality.

Manages rooms/groups of WebSocket connections for targeted broadcasting.
"""

from typing import Dict, Set, Any
from app.logging_config import central_logger
from .connection import ConnectionManager

logger = central_logger.get_logger(__name__)


class RoomManager:
    """Manages WebSocket connection rooms for group messaging."""
    
    def __init__(self, connection_manager: ConnectionManager):
        """Initialize room manager.
        
        Args:
            connection_manager: Connection manager instance
        """
        self.connection_manager = connection_manager
        self.rooms: Dict[str, Set[str]] = {}  # room_id -> set of connection_ids
        self.connection_rooms: Dict[str, Set[str]] = {}  # connection_id -> set of room_ids
    
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
        
        self._remove_all_connections_from_room(room_id)
        self._cleanup_empty_room(room_id)
        return True
    
    def _remove_all_connections_from_room(self, room_id: str):
        """Remove all connections from a room.
        
        Args:
            room_id: Room to clear
        """
        connection_ids = self.rooms[room_id].copy()
        for conn_id in connection_ids:
            self._remove_connection_from_room(conn_id, room_id)
    
    def _cleanup_empty_room(self, room_id: str):
        """Clean up and delete an empty room.
        
        Args:
            room_id: Room to delete
        """
        del self.rooms[room_id]
        logger.info(f"Deleted room {room_id}")
    
    def join_room(self, connection_id: str, room_id: str) -> bool:
        """Add a connection to a room.
        
        Args:
            connection_id: Connection to add
            room_id: Room to join
            
        Returns:
            True if connection was added to room
        """
        self._ensure_room_exists(room_id)
        self._add_to_room_mappings(connection_id, room_id)
        logger.debug(f"Connection {connection_id} joined room {room_id}")
        return True
    
    def _ensure_room_exists(self, room_id: str):
        """Create room if it doesn't exist.
        
        Args:
            room_id: Room to ensure exists
        """
        if room_id not in self.rooms:
            self.create_room(room_id)
    
    def _add_to_room_mappings(self, connection_id: str, room_id: str):
        """Add connection to room mappings.
        
        Args:
            connection_id: Connection to add
            room_id: Room to add to
        """
        self.rooms[room_id].add(connection_id)
        if connection_id not in self.connection_rooms:
            self.connection_rooms[connection_id] = set()
        self.connection_rooms[connection_id].add(room_id)
    
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
        removed = self._remove_from_room_set(connection_id, room_id)
        self._cleanup_connection_rooms(connection_id, room_id)
        self._log_removal(connection_id, room_id, removed)
        return removed
    
    def _remove_from_room_set(self, connection_id: str, room_id: str) -> bool:
        """Remove connection from room set.
        
        Args:
            connection_id: Connection to remove
            room_id: Room to remove from
            
        Returns:
            True if connection was removed
        """
        if room_id in self.rooms and connection_id in self.rooms[room_id]:
            self.rooms[room_id].remove(connection_id)
            return True
        return False
    
    def _cleanup_connection_rooms(self, connection_id: str, room_id: str):
        """Clean up connection rooms mapping.
        
        Args:
            connection_id: Connection to clean up
            room_id: Room to remove from connection's rooms
        """
        if connection_id not in self.connection_rooms:
            return
        
        if room_id in self.connection_rooms[connection_id]:
            self.connection_rooms[connection_id].remove(room_id)
        
        if not self.connection_rooms[connection_id]:
            del self.connection_rooms[connection_id]
    
    def _log_removal(self, connection_id: str, room_id: str, removed: bool):
        """Log connection removal from room.
        
        Args:
            connection_id: Connection that was removed
            room_id: Room it was removed from
            removed: Whether removal was successful
        """
        if removed:
            logger.debug(f"Connection {connection_id} left room {room_id}")
    
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
        """Get room management statistics.
        
        Returns:
            Dictionary with statistics
        """
        room_stats = self._build_room_stats()
        return self._build_stats_dict(room_stats)
    
    def _build_room_stats(self) -> Dict[str, int]:
        """Build room connection statistics.
        
        Returns:
            Dictionary mapping room IDs to connection counts
        """
        room_stats = {}
        for room_id, connections in self.rooms.items():
            room_stats[room_id] = len(connections)
        return room_stats
    
    def _build_stats_dict(self, room_stats: Dict[str, int]) -> Dict[str, Any]:
        """Build complete statistics dictionary.
        
        Args:
            room_stats: Room connection statistics
            
        Returns:
            Complete statistics dictionary
        """
        return {
            "total_rooms": len(self.rooms),
            "room_connections": room_stats,
            "connections_in_rooms": len(self.connection_rooms)
        }
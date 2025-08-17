"""User connection tracking and limits management."""

from typing import Dict, Set, List, Optional

from app.logging_config import central_logger
from .connection import ConnectionInfo

logger = central_logger.get_logger(__name__)


class ConnectionUserTracker:
    """Manages user connection tracking and limits."""
    
    def __init__(self, connection_manager, max_connections_per_user: int = 5):
        """Initialize user tracker."""
        self.connection_manager = connection_manager
        self.max_connections_per_user = max_connections_per_user
        self.user_connections: Dict[str, Set[str]] = {}
    
    def check_connection_limits(self, user_id: str) -> bool:
        """Check if user can create more connections."""
        current_count = len(self.user_connections.get(user_id, set()))
        return current_count < self.max_connections_per_user
    
    def track_user_connection(self, user_id: str, connection_id: str) -> None:
        """Track connection for user."""
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
    
    def untrack_user_connection(self, user_id: str, connection_id: str) -> None:
        """Remove connection tracking for user."""
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
    
    def get_user_connections(self, user_id: str) -> List[ConnectionInfo]:
        """Get all connections for a user."""
        if user_id not in self.user_connections:
            return []
        
        connections = []
        for connection_id in self.user_connections[user_id]:
            conn_info = self.connection_manager.get_connection_by_id(connection_id)
            if conn_info:
                connections.append(conn_info)
        
        return connections
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get connection count for user."""
        return len(self.user_connections.get(user_id, set()))
    
    def get_all_user_stats(self) -> Dict[str, int]:
        """Get connection count statistics for all users."""
        return {
            user_id: len(conn_ids) 
            for user_id, conn_ids in self.user_connections.items()
        }
    
    def validate_user_limits(self, user_id: str) -> None:
        """Validate user connection limits, raise error if exceeded."""
        if not self.check_connection_limits(user_id):
            current_count = self.get_user_connection_count(user_id)
            raise ValueError(
                f"User {user_id} exceeded connection limit "
                f"({current_count}/{self.max_connections_per_user})"
            )
    
    def cleanup_user_tracking(self, connection_id: str, conn_info: Optional[ConnectionInfo]) -> None:
        """Cleanup user connection tracking for removed connection."""
        if not conn_info or not conn_info.user_id:
            return
        
        self.untrack_user_connection(conn_info.user_id, connection_id)
        logger.debug(f"Cleaned up user tracking for {conn_info.user_id}, connection {connection_id}")
    
    def clear_all_tracking(self) -> None:
        """Clear all user connection tracking."""
        self.user_connections.clear()
    
    def get_total_connections(self) -> int:
        """Get total number of tracked connections."""
        return sum(len(conn_ids) for conn_ids in self.user_connections.values())
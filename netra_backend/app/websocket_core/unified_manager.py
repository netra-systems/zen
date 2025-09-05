"""Unified WebSocket Manager - SSOT for WebSocket connection management.

This module is the single source of truth for WebSocket connection management.
"""

import asyncio
from typing import Dict, Optional, Set, Any
from dataclasses import dataclass
from datetime import datetime

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection."""
    connection_id: str
    user_id: str
    websocket: Any
    connected_at: datetime
    metadata: Dict[str, Any] = None


class RegistryCompat:
    """Compatibility registry for legacy tests."""
    
    def __init__(self, manager):
        self.manager = manager
    
    async def register_connection(self, user_id: str, connection_info):
        """Register a connection for test compatibility."""
        # Convert ConnectionInfo to WebSocketConnection format for the unified manager
        websocket_conn = WebSocketConnection(
            connection_id=connection_info.connection_id,
            user_id=user_id,
            websocket=connection_info.websocket,
            connected_at=connection_info.connected_at,
            metadata={"connection_info": connection_info}
        )
        await self.manager.add_connection(websocket_conn)
        # Store connection info for tests that expect it
        if not hasattr(self.manager, '_connection_infos'):
            self.manager._connection_infos = {}
        self.manager._connection_infos[connection_info.connection_id] = connection_info
    
    def get_user_connections(self, user_id: str):
        """Get user connections for test compatibility."""
        if hasattr(self.manager, '_connection_infos') and user_id in self.manager._user_connections:
            conn_ids = self.manager._user_connections[user_id]
            return [self.manager._connection_infos.get(conn_id) for conn_id in conn_ids if conn_id in self.manager._connection_infos]
        return []


class UnifiedWebSocketManager:
    """Unified WebSocket connection manager - SSOT.
    
    Manages all WebSocket connections and ensures proper isolation.
    """
    
    def __init__(self):
        self._connections: Dict[str, WebSocketConnection] = {}
        self._user_connections: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        # Add compatibility registry for legacy tests
        self.registry = RegistryCompat(self)
        logger.info("UnifiedWebSocketManager initialized")
    
    async def add_connection(self, connection: WebSocketConnection) -> None:
        """Add a new WebSocket connection."""
        async with self._lock:
            self._connections[connection.connection_id] = connection
            if connection.user_id not in self._user_connections:
                self._user_connections[connection.user_id] = set()
            self._user_connections[connection.user_id].add(connection.connection_id)
            logger.info(f"Added connection {connection.connection_id} for user {connection.user_id}")
    
    async def remove_connection(self, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if connection_id in self._connections:
                connection = self._connections[connection_id]
                del self._connections[connection_id]
                if connection.user_id in self._user_connections:
                    self._user_connections[connection.user_id].discard(connection_id)
                    if not self._user_connections[connection.user_id]:
                        del self._user_connections[connection.user_id]
                logger.info(f"Removed connection {connection_id}")
    
    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """Get a specific connection."""
        return self._connections.get(connection_id)
    
    def get_user_connections(self, user_id: str) -> Set[str]:
        """Get all connections for a user."""
        return self._user_connections.get(user_id, set()).copy()
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> None:
        """Send a message to all connections for a user."""
        connection_ids = self.get_user_connections(user_id)
        for conn_id in connection_ids:
            connection = self.get_connection(conn_id)
            if connection and connection.websocket:
                try:
                    await connection.websocket.send_json(message)
                    logger.debug(f"Sent message to connection {conn_id}")
                except Exception as e:
                    logger.error(f"Failed to send to {conn_id}: {e}")
                    await self.remove_connection(conn_id)
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to a thread (compatibility method).
        Routes to send_to_user using thread_id as user_id.
        """
        try:
            await self.send_to_user(thread_id, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send to thread {thread_id}: {e}")
            return False
    
    async def emit_critical_event(self, user_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """
        Emit a critical event to a specific user.
        This is the main interface for sending WebSocket events.
        
        Args:
            user_id: Target user ID
            event_type: Event type (e.g., 'agent_started', 'tool_executing')
            data: Event payload
        """
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(user_id, message)
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connections."""
        for connection in list(self._connections.values()):
            try:
                await connection.websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {connection.connection_id}: {e}")
                await self.remove_connection(connection.connection_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self._connections),
            "unique_users": len(self._user_connections),
            "connections_by_user": {
                user_id: len(conns) 
                for user_id, conns in self._user_connections.items()
            }
        }


# Global instance
_manager_instance = None


def get_websocket_manager() -> UnifiedWebSocketManager:
    """Get the global WebSocket manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = UnifiedWebSocketManager()
    return _manager_instance
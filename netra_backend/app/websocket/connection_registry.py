"""Connection Registry Management Module

Manages WebSocket connection tracking and registry operations.
Provides centralized connection lookup and cleanup operations.

Business Value: Ensures accurate connection tracking for billing,
monitoring, and resource management across all user segments.
"""

import asyncio
from typing import Dict, List, Optional

from fastapi import WebSocket

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket.connection_info import (
    ConnectionDurationCalculator,
    ConnectionInfo,
)

logger = central_logger.get_logger(__name__)


class ConnectionRegistry:
    """Manages connection tracking and registry operations."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[ConnectionInfo]] = {}
        self.connection_registry: Dict[str, ConnectionInfo] = {}
        self._registry_lock = asyncio.Lock()
        
    async def register_connection(self, user_id: str, conn_info: ConnectionInfo) -> None:
        """Register new connection in tracking structures."""
        async with self._registry_lock:
            self._ensure_user_connection_list(user_id)
            self.active_connections[user_id].append(conn_info)
            self.connection_registry[conn_info.connection_id] = conn_info
            
            logger.info(f"WebSocket connected for user {user_id} (ID: {conn_info.connection_id})")
            
    def _ensure_user_connection_list(self, user_id: str) -> None:
        """Initialize user's connection list if needed."""
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
            
    async def remove_connection(self, user_id: str, conn_info: ConnectionInfo) -> None:
        """Remove connection from tracking structures."""
        async with self._registry_lock:
            self._remove_from_active_connections(user_id, conn_info)
            self._remove_from_connection_registry(conn_info)
            self._cleanup_empty_user_list(user_id)
            
    def _remove_from_active_connections(self, user_id: str, conn_info: ConnectionInfo) -> None:
        """Remove connection from active connections list."""
        if user_id in self.active_connections and conn_info in self.active_connections[user_id]:
            self.active_connections[user_id].remove(conn_info)
            
    def _remove_from_connection_registry(self, conn_info: ConnectionInfo) -> None:
        """Remove connection from connection registry."""
        if conn_info.connection_id in self.connection_registry:
            del self.connection_registry[conn_info.connection_id]
            
    def _cleanup_empty_user_list(self, user_id: str) -> None:
        """Clean up empty user connection lists."""
        if user_id in self.active_connections and not self.active_connections[user_id]:
            del self.active_connections[user_id]
            
    async def get_user_connections(self, user_id: str) -> List[ConnectionInfo]:
        """Get all connections for a specific user."""
        async with self._registry_lock:
            return list(self.active_connections.get(user_id, []))
        
    async def get_connection_by_id(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection by connection ID."""
        async with self._registry_lock:
            return self.connection_registry.get(connection_id)
        
    async def find_connection_info(self, user_id: str, websocket: WebSocket) -> Optional[ConnectionInfo]:
        """Find connection info for user and websocket."""
        async with self._registry_lock:
            for conn in self.active_connections.get(user_id, []):
                if conn.websocket == websocket:
                    return conn
            return None
        
    async def get_oldest_connection(self, user_id: str) -> Optional[ConnectionInfo]:
        """Get the oldest connection for a user."""
        async with self._registry_lock:
            connections = self.active_connections.get(user_id, [])
            return connections[0] if connections else None
        
    async def collect_all_connections(self) -> List[ConnectionInfo]:
        """Collect all active connections for operations."""
        async with self._registry_lock:
            all_connections = []
            for connections in self.active_connections.values():
                all_connections.extend(connections)
            return all_connections
        
    async def get_user_connection_count(self, user_id: str) -> int:
        """Get connection count for specific user."""
        async with self._registry_lock:
            return len(self.active_connections.get(user_id, []))
        
    async def has_user_connections(self, user_id: str) -> bool:
        """Check if user has any connections."""
        async with self._registry_lock:
            return user_id in self.active_connections
        
    async def clear_all_connections(self) -> None:
        """Clear all connection tracking structures."""
        async with self._registry_lock:
            self.active_connections.clear()
            self.connection_registry.clear()
            
    async def get_registry_stats(self) -> Dict[str, int]:
        """Get basic registry statistics."""
        async with self._registry_lock:
            return {
                "total_active_connections": sum(len(conns) for conns in self.active_connections.values()),
                "active_users": len(self.active_connections),
                "registry_entries": len(self.connection_registry)
            }


class ConnectionInfoProvider:
    """Provides detailed connection information and statistics."""
    
    def __init__(self, registry: ConnectionRegistry):
        self.registry = registry
        
    async def get_connection_info(self, user_id: str) -> List[Dict[str, any]]:
        """Get detailed information about a user's connections."""
        connections = await self.registry.get_user_connections(user_id)
        return [self._create_connection_info_dict(conn) for conn in connections]
        
    def _create_connection_info_dict(self, conn: ConnectionInfo) -> Dict[str, any]:
        """Create connection information dictionary."""
        basic_info = self._get_basic_connection_info(conn)
        timing_info = self._get_connection_timing_info(conn)
        state_info = self._get_connection_state_info(conn)
        return {**basic_info, **timing_info, **state_info}
        
    def _get_basic_connection_info(self, conn: ConnectionInfo) -> Dict[str, any]:
        """Get basic connection information."""
        return {
            "connection_id": conn.connection_id,
            "user_id": conn.user_id,
            "message_count": conn.message_count,
            "error_count": conn.error_count,
            "websocket_state": conn.websocket.client_state.name
        }
        
    def _get_connection_timing_info(self, conn: ConnectionInfo) -> Dict[str, any]:
        """Get connection timing information."""
        return {
            "connected_at": conn.connected_at.isoformat(),
            "last_ping": conn.last_ping.isoformat(),
            "last_pong": conn.last_pong.isoformat() if conn.last_pong else None,
            "last_message_time": conn.last_message_time.isoformat()
        }
        
    def _get_connection_state_info(self, conn: ConnectionInfo) -> Dict[str, any]:
        """Get connection state information."""
        return {
            "state": conn.state.value,
            "is_closing": conn.is_closing,
            "failure_count": conn.failure_count,
            "last_failure_time": conn.last_failure_time.isoformat() if conn.last_failure_time else None,
            "is_ghost": conn.is_ghost_connection()
        }
        
    def get_user_connection_stats(self) -> Dict[str, int]:
        """Get connections count by user."""
        return {
            user_id: len(conns) 
            for user_id, conns in self.registry.active_connections.items()
        }


class ConnectionCleanupManager:
    """Manages connection cleanup and maintenance operations."""
    
    def __init__(self, registry: ConnectionRegistry):
        self.registry = registry
        
    async def cleanup_connection_registry(self, user_id: str, conn_info: ConnectionInfo) -> None:
        """Clean up connection from all tracking structures."""
        await self.registry.remove_connection(user_id, conn_info)
        self._log_disconnection_details(user_id, conn_info)
        
    def _log_disconnection_details(self, user_id: str, conn_info: ConnectionInfo) -> None:
        """Log disconnection with comprehensive details."""
        message = ConnectionDurationCalculator.create_duration_message(user_id, conn_info)
        logger.info(message)
        
    async def enforce_connection_limits(self, user_id: str, max_connections: int) -> bool:
        """Check if connection limits need enforcement."""
        current_connections = await self.registry.get_user_connection_count(user_id)
        return current_connections >= max_connections
        
    async def validate_user_for_disconnect(self, user_id: str) -> bool:
        """Validate user exists in active connections."""
        return await self.registry.has_user_connections(user_id)
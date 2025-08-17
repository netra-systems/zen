"""WebSocket connection management.

Handles individual WebSocket connections, connection pools, and lifecycle management.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import time
import asyncio
import threading

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.logging_config import central_logger
from app.schemas.registry import WebSocketConnectionState

logger = central_logger.get_logger(__name__)


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    user_id: str
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_ping: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_pong: Optional[datetime] = None
    message_count: int = 0
    error_count: int = 0
    connection_id: str = field(default_factory=lambda: f"conn_{int(time.time() * 1000)}")
    last_message_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rate_limit_count: int = 0
    rate_limit_window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_closing: bool = False  # Track if connection is in closing state


class ConnectionManager:
    """Manages WebSocket connections and their lifecycle."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[ConnectionInfo]] = {}
        self.connection_registry: Dict[str, ConnectionInfo] = {}
        self._connection_lock = asyncio.Lock()
        self.max_connections_per_user = 5
        self._stats = self._initialize_stats()

    def _initialize_stats(self) -> Dict[str, int]:
        """Initialize connection statistics."""
        return {"total_connections": 0, "connection_failures": 0}
    
    async def connect(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Establish and register a new WebSocket connection."""
        async with self._connection_lock:
            return await self._perform_connection_setup(user_id, websocket)
    
    async def _perform_connection_setup(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Execute connection setup steps."""
        self._ensure_user_connection_list(user_id)
        await self._handle_connection_limit(user_id)
        conn_info = ConnectionInfo(websocket=websocket, user_id=user_id)
        self._register_new_connection(user_id, conn_info)
        logger.info(f"WebSocket connected for user {user_id} (ID: {conn_info.connection_id})")
        return conn_info
    
    def _register_new_connection(self, user_id: str, conn_info: ConnectionInfo) -> None:
        """Register new connection and update stats."""
        self._add_connection_to_registry(user_id, conn_info)
        self._update_connection_stats()
    
    def _ensure_user_connection_list(self, user_id: str) -> None:
        """Initialize user's connection list if needed."""
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
    
    async def _handle_connection_limit(self, user_id: str) -> None:
        """Handle connection limit enforcement by closing oldest connection."""
        if len(self.active_connections[user_id]) >= self.max_connections_per_user:
            oldest_conn = self.active_connections[user_id][0]
            logger.warning(f"User {user_id} exceeded connection limit, closing oldest connection {oldest_conn.connection_id}")
            await self._disconnect_internal(user_id, oldest_conn.websocket, code=1008, reason="Connection limit exceeded")
    
    def _add_connection_to_registry(self, user_id: str, conn_info: ConnectionInfo) -> None:
        """Add connection to tracking structures."""
        self.active_connections[user_id].append(conn_info)
        self.connection_registry[conn_info.connection_id] = conn_info
    
    def _update_connection_stats(self) -> None:
        """Update connection statistics."""
        self._stats["total_connections"] += 1
    
    async def disconnect(self, user_id: str, websocket: WebSocket, code: int = 1000, reason: str = "Normal closure"):
        """Properly disconnect and clean up a WebSocket connection."""
        async with self._connection_lock:
            await self._disconnect_internal(user_id, websocket, code, reason)
    
    async def _disconnect_internal(self, user_id: str, websocket: WebSocket, code: int = 1000, reason: str = "Normal closure"):
        """Internal disconnect method - requires lock to be held."""
        if user_id not in self.active_connections:
            return
        conn_info = self._find_connection_info(user_id, websocket)
        if conn_info:
            await self._execute_disconnection(user_id, conn_info, websocket, code, reason)
    
    async def _execute_disconnection(self, user_id: str, conn_info: ConnectionInfo, 
                                   websocket: WebSocket, code: int, reason: str) -> None:
        """Execute disconnection cleanup steps."""
        self._mark_connection_closing(conn_info)
        self._cleanup_connection_registry(user_id, conn_info)
        await self._close_websocket_safely(websocket, code, reason)
        self._log_disconnection_stats(user_id, conn_info)
    
    def _mark_connection_closing(self, conn_info: ConnectionInfo) -> None:
        """Mark connection as closing to prevent further sends."""
        conn_info.is_closing = True
    
    def _cleanup_connection_registry(self, user_id: str, conn_info: ConnectionInfo) -> None:
        """Clean up connection from registry and user lists."""
        self._remove_from_registry(user_id, conn_info)
        self._cleanup_empty_user_list(user_id)
    
    def _find_connection_info(self, user_id: str, websocket: WebSocket) -> Optional[ConnectionInfo]:
        """Find connection info for user and websocket."""
        for conn in self.active_connections[user_id]:
            if conn.websocket == websocket:
                return conn
        return None
    
    def _remove_from_registry(self, user_id: str, conn_info: ConnectionInfo) -> None:
        """Remove connection from tracking structures."""
        self.active_connections[user_id].remove(conn_info)
        if conn_info.connection_id in self.connection_registry:
            del self.connection_registry[conn_info.connection_id]
    
    def _cleanup_empty_user_list(self, user_id: str) -> None:
        """Clean up empty user lists."""
        if not self.active_connections[user_id]:
            del self.active_connections[user_id]
    
    async def _close_websocket_safely(self, websocket: WebSocket, code: int, reason: str) -> None:
        """Close websocket connection safely with error handling."""
        try:
            if self._is_websocket_safe_to_close(websocket):
                await websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.debug(f"Error closing WebSocket: {e}")
    
    def _is_websocket_safe_to_close(self, websocket: WebSocket) -> bool:
        """Check if websocket is safe to close."""
        return (self._has_valid_client_state(websocket) and 
                self._has_valid_application_state(websocket))
    
    def _has_valid_client_state(self, websocket: WebSocket) -> bool:
        """Check if websocket has valid client state for closing."""
        return (hasattr(websocket, 'client_state') and 
                websocket.client_state == WebSocketState.CONNECTED)
    
    def _has_valid_application_state(self, websocket: WebSocket) -> bool:
        """Check if websocket has valid application state for closing."""
        return (hasattr(websocket, 'application_state') and
                websocket.application_state != WebSocketState.DISCONNECTED)
    
    def _log_disconnection_stats(self, user_id: str, conn_info: ConnectionInfo) -> None:
        """Log disconnection with statistics."""
        duration = (datetime.now(timezone.utc) - conn_info.connected_at).total_seconds()
        logger.info(
            f"WebSocket disconnected for user {user_id} "
            f"(ID: {conn_info.connection_id}, Duration: {duration:.1f}s, "
            f"Messages: {conn_info.message_count}, Errors: {conn_info.error_count})"
        )
    
    def get_user_connections(self, user_id: str) -> List[ConnectionInfo]:
        """Get all connections for a specific user."""
        return self.active_connections.get(user_id, [])
    
    def get_connection_by_id(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection by connection ID."""
        return self.connection_registry.get(connection_id)
    
    def get_connection_info(self, user_id: str) -> List[Dict[str, any]]:
        """Get detailed information about a user's connections."""
        if user_id not in self.active_connections:
            return []
        return [self._create_connection_dict(conn) for conn in self.active_connections[user_id]]
    
    def _create_connection_dict(self, conn: ConnectionInfo) -> Dict[str, any]:
        """Create connection information dictionary."""
        basic_info = self._get_basic_connection_info(conn)
        timing_info = self._get_connection_timing_info(conn)
        return {**basic_info, **timing_info}
    
    def _get_basic_connection_info(self, conn: ConnectionInfo) -> Dict[str, any]:
        """Get basic connection information."""
        return {
            "connection_id": conn.connection_id,
            "message_count": conn.message_count,
            "error_count": conn.error_count,
            "state": conn.websocket.client_state.name
        }
    
    def _get_connection_timing_info(self, conn: ConnectionInfo) -> Dict[str, any]:
        """Get connection timing information."""
        return {
            "connected_at": conn.connected_at.isoformat(),
            "last_ping": conn.last_ping.isoformat(),
            "last_pong": conn.last_pong.isoformat() if conn.last_pong else None
        }
    
    def is_connection_alive(self, conn_info: ConnectionInfo) -> bool:
        """Check if a connection is still alive."""
        return conn_info.websocket.client_state == WebSocketState.CONNECTED
    
    async def find_connection(self, user_id: str, websocket: WebSocket) -> Optional[ConnectionInfo]:
        """Find connection info for a user and websocket."""
        for conn_info in self.active_connections.get(user_id, []):
            if conn_info.websocket == websocket:
                return conn_info
        return None
    
    async def cleanup_dead_connections(self):
        """Clean up connections that are no longer alive."""
        connections_to_remove = await self._identify_dead_connections()
        await self._remove_dead_connections(connections_to_remove)
    
    async def _identify_dead_connections(self) -> List[tuple]:
        """Identify connections that are no longer alive."""
        connections_to_remove = []
        async with self._connection_lock:
            self._scan_for_dead_connections(connections_to_remove)
        return connections_to_remove
    
    def _scan_for_dead_connections(self, connections_to_remove: List[tuple]) -> None:
        """Scan all connections and identify dead ones."""
        for user_id, connections in list(self.active_connections.items()):
            self._check_user_connections(user_id, connections, connections_to_remove)
    
    def _check_user_connections(self, user_id: str, connections: List[ConnectionInfo], 
                              connections_to_remove: List[tuple]) -> None:
        """Check all connections for a user and add dead ones to removal list."""
        for conn_info in connections:
            if not self.is_connection_alive(conn_info):
                connections_to_remove.append((user_id, conn_info))
    
    async def _remove_dead_connections(self, connections_to_remove: List[tuple]) -> None:
        """Remove dead connections from registry."""
        for user_id, conn_info in connections_to_remove:
            await self._disconnect_internal(user_id, conn_info.websocket, code=1001, reason="Connection lost")
    
    def get_stats(self) -> Dict[str, any]:
        """Get connection statistics."""
        basic_stats = self._get_basic_stats()
        detailed_stats = self._get_detailed_stats()
        return {**basic_stats, **detailed_stats}
    
    def _get_basic_stats(self) -> Dict[str, any]:
        """Get basic connection statistics."""
        return {
            "total_connections": self._stats["total_connections"],
            "active_connections": self._get_active_connection_count(),
            "active_users": len(self.active_connections)
        }
    
    def _get_detailed_stats(self) -> Dict[str, any]:
        """Get detailed connection statistics."""
        return {
            "connection_failures": self._stats["connection_failures"],
            "connections_by_user": self._get_connections_by_user()
        }
    
    def _get_active_connection_count(self) -> int:
        """Calculate total active connection count."""
        return sum(len(conns) for conns in self.active_connections.values())
    
    def _get_connections_by_user(self) -> Dict[str, int]:
        """Get connection count by user."""
        return {
            user_id: len(conns) 
            for user_id, conns in self.active_connections.items()
        }
    
    async def shutdown(self):
        """Gracefully shutdown all connections."""
        logger.info("Starting connection manager shutdown...")
        await self._close_all_connections()
        self._clear_tracking_structures()
        logger.info(f"Connection manager shutdown complete. Final stats: {self.get_stats()}")
    
    async def _close_all_connections(self) -> None:
        """Close all active connections during shutdown."""
        for user_id, connections in list(self.active_connections.items()):
            for conn_info in connections:
                await self._close_connection_safely(conn_info)
    
    async def _close_connection_safely(self, conn_info: ConnectionInfo) -> None:
        """Close a connection safely with error handling."""
        try:
            await conn_info.websocket.close(code=1001, reason="Server shutdown")
        except Exception as e:
            logger.debug(f"Error closing connection during shutdown: {e}")
    
    def _clear_tracking_structures(self) -> None:
        """Clear all connection tracking structures."""
        self.active_connections.clear()
        self.connection_registry.clear()


# Global instance for backward compatibility
connection_manager = ConnectionManager()
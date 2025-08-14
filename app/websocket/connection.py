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
from app.schemas.websocket_unified import WebSocketConnectionState

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


class ConnectionManager:
    """Manages WebSocket connections and their lifecycle."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[ConnectionInfo]] = {}
        self.connection_registry: Dict[str, ConnectionInfo] = {}
        self._connection_lock = asyncio.Lock()
        self.max_connections_per_user = 5
        self._stats = {
            "total_connections": 0,
            "connection_failures": 0
        }
    
    async def connect(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Establish and register a new WebSocket connection."""
        async with self._connection_lock:
            # Initialize user's connection list if needed
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            
            # Check connection limit
            if len(self.active_connections[user_id]) >= self.max_connections_per_user:
                # Close oldest connection to make room
                oldest_conn = self.active_connections[user_id][0]
                logger.warning(f"User {user_id} exceeded connection limit, closing oldest connection {oldest_conn.connection_id}")
                await self._disconnect_internal(user_id, oldest_conn.websocket, code=1008, reason="Connection limit exceeded")
            
            conn_info = ConnectionInfo(websocket=websocket, user_id=user_id)
            
            # Add connection to tracking structures
            self.active_connections[user_id].append(conn_info)
            self.connection_registry[conn_info.connection_id] = conn_info
            
            # Update statistics
            self._stats["total_connections"] += 1
            
            logger.info(f"WebSocket connected for user {user_id} (ID: {conn_info.connection_id})")
            
            return conn_info
    
    async def disconnect(self, user_id: str, websocket: WebSocket, code: int = 1000, reason: str = "Normal closure"):
        """Properly disconnect and clean up a WebSocket connection."""
        async with self._connection_lock:
            await self._disconnect_internal(user_id, websocket, code, reason)
    
    async def _disconnect_internal(self, user_id: str, websocket: WebSocket, code: int = 1000, reason: str = "Normal closure"):
        """Internal disconnect method - requires lock to be held."""
        if user_id not in self.active_connections:
            return
        
        # Find and remove the connection info
        conn_info = None
        for conn in self.active_connections[user_id]:
            if conn.websocket == websocket:
                conn_info = conn
                break
        
        if conn_info:
            # Remove from tracking structures
            self.active_connections[user_id].remove(conn_info)
            if conn_info.connection_id in self.connection_registry:
                del self.connection_registry[conn_info.connection_id]
            
            # Clean up empty user lists
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            # Close connection if still open
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close(code=code, reason=reason)
                except Exception as e:
                    logger.debug(f"Error closing WebSocket: {e}")
            
            # Log disconnection with statistics
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
        
        return [
            {
                "connection_id": conn.connection_id,
                "connected_at": conn.connected_at.isoformat(),
                "last_ping": conn.last_ping.isoformat(),
                "last_pong": conn.last_pong.isoformat() if conn.last_pong else None,
                "message_count": conn.message_count,
                "error_count": conn.error_count,
                "state": conn.websocket.client_state.name
            }
            for conn in self.active_connections[user_id]
        ]
    
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
        connections_to_remove = []
        
        async with self._connection_lock:
            for user_id, connections in list(self.active_connections.items()):
                for conn_info in connections:
                    if not self.is_connection_alive(conn_info):
                        connections_to_remove.append((user_id, conn_info))
        
        # Remove dead connections
        for user_id, conn_info in connections_to_remove:
            await self._disconnect_internal(user_id, conn_info.websocket, code=1001, reason="Connection lost")
    
    def get_stats(self) -> Dict[str, any]:
        """Get connection statistics."""
        active_count = sum(len(conns) for conns in self.active_connections.values())
        
        return {
            "total_connections": self._stats["total_connections"],
            "active_connections": active_count,
            "active_users": len(self.active_connections),
            "connection_failures": self._stats["connection_failures"],
            "connections_by_user": {
                user_id: len(conns) 
                for user_id, conns in self.active_connections.items()
            }
        }
    
    async def shutdown(self):
        """Gracefully shutdown all connections."""
        logger.info("Starting connection manager shutdown...")
        
        # Close all connections
        for user_id, connections in list(self.active_connections.items()):
            for conn_info in connections:
                try:
                    await conn_info.websocket.close(code=1001, reason="Server shutdown")
                except Exception as e:
                    logger.debug(f"Error closing connection during shutdown: {e}")
        
        # Clear all tracking structures
        self.active_connections.clear()
        self.connection_registry.clear()
        
        logger.info(f"Connection manager shutdown complete. Final stats: {self.get_stats()}")


# Global instance for backward compatibility
connection_manager = ConnectionManager()
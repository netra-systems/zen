"""WebSocketConnectionPool - Infrastructure for Secure Connection Management

Business Value Justification:
- Segment: Platform/Internal (Security Critical)
- Business Goal: Risk Reduction & Stability
- Value Impact: Prevents user data leakage through WebSocket event isolation
- Strategic Impact: Foundational security infrastructure for all WebSocket communications

This module provides infrastructure-level connection management that maps user_id/connection_id
to actual WebSocket connections while ensuring strict user isolation. It manages the connection
pool without owning the business logic of event routing.

Key Security Features:
- Thread-safe connection mapping with user validation
- Automatic cleanup of dead connections
- Connection health monitoring
- Audit logging for security compliance
- User isolation verification

CRITICAL: This is infrastructure only - does not handle business event routing.
Event routing is handled by WebSocketEventEmitter.
"""

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Set, List, Any, Tuple
from weakref import WeakSet
import logging
import threading

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection with security metadata."""
    
    connection_id: str
    user_id: str
    websocket: WebSocket
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate connection info after initialization."""
        if not self.connection_id or not self.user_id:
            raise ValueError("connection_id and user_id are required")
        if not isinstance(self.websocket, WebSocket):
            raise ValueError("websocket must be a WebSocket instance")


@dataclass
class ConnectionPoolStats:
    """Statistics for connection pool monitoring."""
    
    total_connections: int = 0
    connections_by_user: Dict[str, int] = field(default_factory=dict)
    stale_connections: int = 0
    dead_connections: int = 0
    last_cleanup: Optional[datetime] = None
    cleanup_count: int = 0


class WebSocketConnectionPool:
    """Infrastructure-level WebSocket connection pool with strict user isolation.
    
    This class manages the physical WebSocket connections and their mapping to users,
    ensuring that connections can only be accessed by the correct user. It provides
    thread-safe operations and automatic cleanup of stale connections.
    
    SECURITY CRITICAL: All connection access must validate user_id matches.
    """
    
    _instance: Optional['WebSocketConnectionPool'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'WebSocketConnectionPool':
        """Singleton pattern with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize connection pool with security features."""
        if hasattr(self, '_initialized'):
            return
        
        # Core connection storage - thread-safe
        self._connections: Dict[str, ConnectionInfo] = {}
        self._user_connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
        self._connection_lock = asyncio.Lock()
        
        # Health monitoring
        self._stats = ConnectionPoolStats()
        self._stale_connection_timeout = 300  # 5 minutes
        self._cleanup_interval = 60  # 1 minute
        self._max_connections_per_user = 5
        self._max_total_connections = 200
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ws-pool")
        
        # Audit trail
        self._audit_events: List[Dict[str, Any]] = []
        self._max_audit_events = 1000
        
        self._initialized = True
        logger.info("WebSocketConnectionPool initialized with security features")
    
    async def add_connection(
        self, 
        connection_id: str, 
        user_id: str, 
        websocket: WebSocket,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a WebSocket connection to the pool with security validation.
        
        Args:
            connection_id: Unique connection identifier
            user_id: User identifier (must not be empty)
            websocket: WebSocket instance
            metadata: Optional connection metadata
            
        Returns:
            True if connection added successfully, False otherwise
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not connection_id or not user_id:
            raise ValueError("connection_id and user_id cannot be empty")
        
        async with self._connection_lock:
            # Check connection limits
            if len(self._connections) >= self._max_total_connections:
                logger.error(f"Connection pool at maximum capacity: {self._max_total_connections}")
                self._audit_event("connection_rejected", {
                    "reason": "pool_full",
                    "connection_id": connection_id,
                    "user_id": user_id
                })
                return False
            
            # Check per-user limits
            user_connection_count = len(self._user_connections.get(user_id, set()))
            if user_connection_count >= self._max_connections_per_user:
                logger.error(f"User {user_id} at maximum connections: {self._max_connections_per_user}")
                self._audit_event("connection_rejected", {
                    "reason": "user_limit",
                    "connection_id": connection_id,
                    "user_id": user_id,
                    "current_count": user_connection_count
                })
                return False
            
            # Validate WebSocket is in correct state
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.error(f"WebSocket not in connected state: {websocket.client_state.name}")
                return False
            
            # Create connection info
            conn_info = ConnectionInfo(
                connection_id=connection_id,
                user_id=user_id,
                websocket=websocket,
                metadata=metadata or {}
            )
            
            # Add to pool
            self._connections[connection_id] = conn_info
            
            # Update user mapping
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)
            
            # Update stats
            self._stats.total_connections = len(self._connections)
            self._stats.connections_by_user[user_id] = len(self._user_connections[user_id])
            
            # Audit log
            self._audit_event("connection_added", {
                "connection_id": connection_id,
                "user_id": user_id,
                "total_connections": self._stats.total_connections,
                "user_connections": self._stats.connections_by_user[user_id]
            })
            
            logger.info(f"Added connection {connection_id} for user {user_id}")
            
            # Start cleanup task if not running
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            return True
    
    async def remove_connection(self, connection_id: str, user_id: str) -> bool:
        """Remove a connection with user validation.
        
        SECURITY CRITICAL: Validates that user_id matches the connection owner.
        
        Args:
            connection_id: Connection to remove
            user_id: User requesting removal (must match connection owner)
            
        Returns:
            True if removed successfully, False if not found or unauthorized
        """
        async with self._connection_lock:
            conn_info = self._connections.get(connection_id)
            if not conn_info:
                logger.warning(f"Connection {connection_id} not found for removal")
                return False
            
            # SECURITY CHECK: Validate user owns this connection
            if conn_info.user_id != user_id:
                logger.error(f"Security violation: User {user_id} attempted to remove "
                           f"connection {connection_id} owned by {conn_info.user_id}")
                self._audit_event("security_violation", {
                    "type": "unauthorized_removal",
                    "connection_id": connection_id,
                    "requesting_user": user_id,
                    "actual_owner": conn_info.user_id
                })
                return False
            
            # Remove from pool
            del self._connections[connection_id]
            
            # Update user mapping
            if user_id in self._user_connections:
                self._user_connections[user_id].discard(connection_id)
                if not self._user_connections[user_id]:
                    del self._user_connections[user_id]
            
            # Update stats
            self._stats.total_connections = len(self._connections)
            if user_id in self._user_connections:
                self._stats.connections_by_user[user_id] = len(self._user_connections[user_id])
            else:
                self._stats.connections_by_user.pop(user_id, None)
            
            # Audit log
            self._audit_event("connection_removed", {
                "connection_id": connection_id,
                "user_id": user_id,
                "total_connections": self._stats.total_connections
            })
            
            logger.info(f"Removed connection {connection_id} for user {user_id}")
            return True
    
    async def get_user_connections(self, user_id: str) -> List[ConnectionInfo]:
        """Get all active connections for a user.
        
        Args:
            user_id: User to get connections for
            
        Returns:
            List of ConnectionInfo for the user
        """
        if not user_id:
            raise ValueError("user_id cannot be empty")
        
        async with self._connection_lock:
            connection_ids = self._user_connections.get(user_id, set())
            connections = []
            
            for conn_id in connection_ids.copy():  # Copy to avoid modification during iteration
                conn_info = self._connections.get(conn_id)
                if conn_info and await self._is_connection_alive(conn_info.websocket):
                    connections.append(conn_info)
                else:
                    # Clean up dead connection
                    self._connections.pop(conn_id, None)
                    self._user_connections[user_id].discard(conn_id)
                    self._stats.dead_connections += 1
            
            return connections
    
    async def get_connection(self, connection_id: str, user_id: str) -> Optional[ConnectionInfo]:
        """Get a specific connection with user validation.
        
        SECURITY CRITICAL: Validates user owns the connection before returning it.
        
        Args:
            connection_id: Connection to retrieve
            user_id: User requesting the connection (must match owner)
            
        Returns:
            ConnectionInfo if found and authorized, None otherwise
        """
        if not connection_id or not user_id:
            raise ValueError("connection_id and user_id cannot be empty")
        
        async with self._connection_lock:
            conn_info = self._connections.get(connection_id)
            if not conn_info:
                return None
            
            # SECURITY CHECK: Validate user owns this connection
            if conn_info.user_id != user_id:
                logger.error(f"Security violation: User {user_id} attempted to access "
                           f"connection {connection_id} owned by {conn_info.user_id}")
                self._audit_event("security_violation", {
                    "type": "unauthorized_access",
                    "connection_id": connection_id,
                    "requesting_user": user_id,
                    "actual_owner": conn_info.user_id
                })
                return None
            
            # Check if connection is still alive
            if not await self._is_connection_alive(conn_info.websocket):
                logger.info(f"Connection {connection_id} is dead, removing")
                await self.remove_connection(connection_id, user_id)
                return None
            
            # Update last activity
            conn_info.last_activity = datetime.now(timezone.utc)
            return conn_info
    
    async def get_stats(self) -> ConnectionPoolStats:
        """Get connection pool statistics."""
        async with self._connection_lock:
            # Update real-time stats
            self._stats.total_connections = len(self._connections)
            
            # Count stale connections
            now = datetime.now(timezone.utc)
            stale_count = 0
            for conn in self._connections.values():
                if (now - conn.last_activity).total_seconds() > self._stale_connection_timeout:
                    stale_count += 1
            
            self._stats.stale_connections = stale_count
            return self._stats
    
    async def cleanup_stale_connections(self) -> int:
        """Clean up stale and dead connections.
        
        Returns:
            Number of connections cleaned up
        """
        cleanup_count = 0
        now = datetime.now(timezone.utc)
        
        async with self._connection_lock:
            # Find connections to clean up
            connections_to_remove = []
            
            for conn_id, conn_info in self._connections.items():
                should_remove = False
                
                # Check if connection is dead
                if not await self._is_connection_alive(conn_info.websocket):
                    logger.info(f"Removing dead connection {conn_id} for user {conn_info.user_id}")
                    should_remove = True
                    self._stats.dead_connections += 1
                
                # Check if connection is stale
                elif (now - conn_info.last_activity).total_seconds() > self._stale_connection_timeout:
                    logger.info(f"Removing stale connection {conn_id} for user {conn_info.user_id}")
                    should_remove = True
                    self._stats.stale_connections += 1
                
                if should_remove:
                    connections_to_remove.append((conn_id, conn_info.user_id))
            
            # Remove the connections
            for conn_id, user_id in connections_to_remove:
                await self.remove_connection(conn_id, user_id)
                cleanup_count += 1
            
            self._stats.cleanup_count += cleanup_count
            self._stats.last_cleanup = now
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} stale/dead connections")
        
        return cleanup_count
    
    async def _is_connection_alive(self, websocket: WebSocket) -> bool:
        """Check if a WebSocket connection is still alive."""
        try:
            return (websocket.client_state == WebSocketState.CONNECTED and 
                   websocket.application_state == WebSocketState.CONNECTED)
        except Exception:
            return False
    
    async def _cleanup_loop(self):
        """Background cleanup loop."""
        try:
            while True:
                await asyncio.sleep(self._cleanup_interval)
                await self.cleanup_stale_connections()
        except asyncio.CancelledError:
            logger.info("Connection pool cleanup loop cancelled")
        except Exception as e:
            logger.error(f"Error in connection pool cleanup loop: {e}")
    
    def _audit_event(self, event_type: str, data: Dict[str, Any]):
        """Record audit event for security compliance."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": data
        }
        
        self._audit_events.append(event)
        
        # Trim audit events if too many
        if len(self._audit_events) > self._max_audit_events:
            self._audit_events = self._audit_events[-self._max_audit_events//2:]
        
        logger.debug(f"Audit event: {event_type} - {data}")
    
    async def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit events."""
        return self._audit_events[-limit:]
    
    async def shutdown(self):
        """Shutdown the connection pool and cleanup resources."""
        logger.info("Shutting down WebSocket connection pool")
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        async with self._connection_lock:
            for conn_info in list(self._connections.values()):
                try:
                    if await self._is_connection_alive(conn_info.websocket):
                        await conn_info.websocket.close()
                except Exception as e:
                    logger.error(f"Error closing connection {conn_info.connection_id}: {e}")
            
            self._connections.clear()
            self._user_connections.clear()
        
        # Shutdown executor
        if self._executor:
            self._executor.shutdown(wait=True)
        
        logger.info("WebSocket connection pool shutdown complete")


# Global instance
_connection_pool: Optional[WebSocketConnectionPool] = None


def get_websocket_connection_pool() -> WebSocketConnectionPool:
    """Get the global WebSocket connection pool instance."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = WebSocketConnectionPool()
    return _connection_pool


async def cleanup_connection_pool():
    """Cleanup the global connection pool (for testing)."""
    global _connection_pool
    if _connection_pool:
        await _connection_pool.shutdown()
        _connection_pool = None
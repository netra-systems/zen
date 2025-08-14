"""Enhanced WebSocket connection manager with comprehensive reliability features.

This module provides reliable connection management with circuit breakers,
health monitoring, and automatic recovery capabilities.
"""

import asyncio
from typing import Dict, Set, Optional, List
from datetime import datetime, timedelta, timezone
import time

from app.logging_config import central_logger
from app.core.reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)
from app.core.json_utils import prepare_websocket_message, safe_json_dumps
from .connection import ConnectionInfo, ConnectionManager
from .heartbeat import HeartbeatManager
from .error_handler import ErrorHandler, default_error_handler
from .reliable_message_handler import ReliableMessageHandler, MessageTypeRouter

logger = central_logger.get_logger(__name__)


class ReliableConnectionManager:
    """Enhanced connection manager with comprehensive reliability features."""
    
    def __init__(
        self,
        heartbeat_interval: int = 30,
        cleanup_interval: int = 60,
        max_connections_per_user: int = 5,
        connection_timeout: int = 300  # 5 minutes
    ):
        # Core components
        self.connection_manager = ConnectionManager()
        self.heartbeat_manager = HeartbeatManager(self.connection_manager, default_error_handler)
        self.error_handler = default_error_handler
        self.message_handler = ReliableMessageHandler()
        self.message_router = MessageTypeRouter()
        
        # Configuration
        self.heartbeat_interval = heartbeat_interval
        self.cleanup_interval = cleanup_interval
        self.max_connections_per_user = max_connections_per_user
        self.connection_timeout = connection_timeout
        
        # Reliability wrapper for connection operations
        self.reliability = get_reliability_wrapper(
            "ReliableConnectionManager",
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=45.0,
                name="ReliableConnectionManager"
            ),
            RetryConfig(
                max_retries=2,
                base_delay=1.0,
                max_delay=10.0
            )
        )
        
        # Connection tracking
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> {connection_ids}
        self.connection_timeouts: Dict[str, float] = {}  # connection_id -> timeout_timestamp
        
        # Health monitoring
        self.last_cleanup_time = time.time()
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "failed_connections": 0,
            "timeouts": 0,
            "heartbeat_failures": 0,
            "cleanup_runs": 0
        }
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the reliable connection manager."""
        if self._running:
            return
        
        self._running = True
        
        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("ReliableConnectionManager started")
    
    async def stop(self):
        """Stop the reliable connection manager."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel background task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown heartbeat manager
        await self.heartbeat_manager.shutdown_all_heartbeats()
        
        # Close all connections
        await self._close_all_connections()
        
        logger.info("ReliableConnectionManager stopped")
    
    async def add_connection(self, websocket, user_id: str, connection_id: str) -> bool:
        """Add a new connection with reliability protection."""
        
        async def _add_connection():
            # Check user connection limits
            if not self._check_connection_limits(user_id):
                raise ValueError(f"User {user_id} exceeded connection limit")
            
            # Create connection info
            conn_info = ConnectionInfo(
                connection_id=connection_id,
                websocket=websocket,
                user_id=user_id,
                connected_at=datetime.now(timezone.utc)
            )
            
            # Add to connection manager
            self.connection_manager.add_connection(conn_info)
            
            # Track user connections
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
            
            # Set connection timeout
            self.connection_timeouts[connection_id] = time.time() + self.connection_timeout
            
            # Start heartbeat monitoring
            await self.heartbeat_manager.start_heartbeat_for_connection(conn_info)
            
            # Update statistics
            self.stats["total_connections"] += 1
            self.stats["active_connections"] = len(self.connection_manager.get_all_connections())
            
            logger.info(f"Added connection {connection_id} for user {user_id}")
            return True
        
        async def _fallback_add_connection():
            """Fallback when connection addition fails."""
            logger.warning(f"Failed to add connection {connection_id} for user {user_id}")
            self.stats["failed_connections"] += 1
            return False
        
        try:
            return await self.reliability.execute_safely(
                _add_connection,
                "add_connection",
                fallback=_fallback_add_connection,
                timeout=10.0
            )
        except Exception as e:
            logger.error(f"Error adding connection {connection_id}: {e}")
            return False
    
    async def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection with cleanup."""
        
        async def _remove_connection():
            conn_info = self.connection_manager.get_connection_by_id(connection_id)
            if not conn_info:
                return True  # Already removed
            
            # Stop heartbeat monitoring
            await self.heartbeat_manager.stop_heartbeat_for_connection(connection_id)
            
            # Remove from user tracking
            if conn_info.user_id and conn_info.user_id in self.user_connections:
                self.user_connections[conn_info.user_id].discard(connection_id)
                if not self.user_connections[conn_info.user_id]:
                    del self.user_connections[conn_info.user_id]
            
            # Remove timeout tracking
            self.connection_timeouts.pop(connection_id, None)
            
            # Remove from connection manager
            self.connection_manager.remove_connection(connection_id)
            
            # Update statistics
            self.stats["active_connections"] = len(self.connection_manager.get_all_connections())
            
            logger.info(f"Removed connection {connection_id}")
            return True
        
        try:
            return await self.reliability.execute_safely(
                _remove_connection,
                "remove_connection",
                timeout=5.0
            )
        except Exception as e:
            logger.error(f"Error removing connection {connection_id}: {e}")
            return False
    
    async def handle_message(self, connection_id: str, raw_message: str) -> bool:
        """Handle incoming message from connection."""
        conn_info = self.connection_manager.get_connection_by_id(connection_id)
        if not conn_info:
            logger.warning(f"Received message from unknown connection: {connection_id}")
            return False
        
        # Update connection activity
        conn_info.last_activity = datetime.now(timezone.utc)
        
        # Handle message through reliable handler
        success = await self.message_handler.handle_message(
            raw_message,
            conn_info,
            self.message_router.route_message
        )
        
        if success:
            # Update timeout
            self.connection_timeouts[connection_id] = time.time() + self.connection_timeout
        
        return success
    
    async def send_message(self, connection_id: str, message: dict) -> bool:
        """Send message to connection with reliability protection."""
        
        async def _send_message():
            conn_info = self.connection_manager.get_connection_by_id(connection_id)
            if not conn_info:
                raise ValueError(f"Connection {connection_id} not found")
            
            # Check connection state
            if not self.connection_manager.is_connection_alive(conn_info):
                raise ConnectionError(f"Connection {connection_id} is not alive")
            
            # Send message
            prepared_message = prepare_websocket_message(message)
            await conn_info.websocket.send_text(safe_json_dumps(prepared_message))
            return True
        
        async def _fallback_send_message():
            """Fallback when message sending fails."""
            logger.warning(f"Failed to send message to connection {connection_id}")
            # Mark connection for removal
            await self.remove_connection(connection_id)
            return False
        
        try:
            return await self.reliability.execute_safely(
                _send_message,
                "send_message",
                fallback=_fallback_send_message,
                timeout=5.0
            )
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            return False
    
    async def broadcast_message(self, message: dict, user_filter: Optional[str] = None) -> int:
        """Broadcast message to multiple connections."""
        sent_count = 0
        connections = self.connection_manager.get_all_connections()
        
        for conn_info in connections:
            # Apply user filter if specified
            if user_filter and conn_info.user_id != user_filter:
                continue
            
            success = await self.send_message(conn_info.connection_id, message)
            if success:
                sent_count += 1
        
        return sent_count
    
    def _check_connection_limits(self, user_id: str) -> bool:
        """Check if user can create more connections."""
        current_count = len(self.user_connections.get(user_id, set()))
        return current_count < self.max_connections_per_user
    
    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._run_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(5)  # Brief delay before retry
    
    async def _run_cleanup(self):
        """Run connection cleanup."""
        start_time = time.time()
        self.stats["cleanup_runs"] += 1
        
        # Find timed out connections
        current_time = time.time()
        timed_out_connections = []
        
        for connection_id, timeout_time in self.connection_timeouts.items():
            if current_time > timeout_time:
                timed_out_connections.append(connection_id)
        
        # Remove timed out connections
        for connection_id in timed_out_connections:
            logger.info(f"Removing timed out connection: {connection_id}")
            await self.remove_connection(connection_id)
            self.stats["timeouts"] += 1
        
        # Clean up dead connections from heartbeat manager
        await self.heartbeat_manager.cleanup_dead_connections()
        
        # Clean up old error records
        self.error_handler.cleanup_old_errors()
        
        self.last_cleanup_time = time.time()
        
        if timed_out_connections:
            logger.info(f"Cleanup completed: removed {len(timed_out_connections)} timed out connections")
    
    async def _close_all_connections(self):
        """Close all active connections."""
        connections = self.connection_manager.get_all_connections()
        
        for conn_info in connections:
            try:
                await conn_info.websocket.close()
            except Exception as e:
                logger.debug(f"Error closing connection {conn_info.connection_id}: {e}")
        
        # Clear all tracking
        self.user_connections.clear()
        self.connection_timeouts.clear()
    
    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection information."""
        return self.connection_manager.get_connection_by_id(connection_id)
    
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
    
    def get_health_status(self) -> dict:
        """Get comprehensive health status."""
        return {
            "connection_manager": {
                "active_connections": self.stats["active_connections"],
                "total_connections": self.stats["total_connections"],
                "failed_connections": self.stats["failed_connections"],
                "timeouts": self.stats["timeouts"],
                "cleanup_runs": self.stats["cleanup_runs"],
                "last_cleanup": self.last_cleanup_time,
                "user_connections": {
                    user_id: len(conn_ids) 
                    for user_id, conn_ids in self.user_connections.items()
                }
            },
            "heartbeat_manager": self.heartbeat_manager.get_stats(),
            "message_handler": self.message_handler.get_health_status(),
            "error_handler": self.error_handler.get_error_stats(),
            "reliability": self.reliability.get_health_status()
        }
    
    def register_message_handler(self, message_type: str, handler):
        """Register a message handler for a specific type."""
        self.message_router.register_handler(message_type, handler)
    
    def register_fallback_handler(self, handler):
        """Register a fallback message handler."""
        self.message_router.register_fallback_handler(handler)


# Global instance
default_reliable_connection_manager = ReliableConnectionManager()
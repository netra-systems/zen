"""Enhanced WebSocket connection manager with comprehensive reliability features.

This module provides reliable connection management with circuit breakers,
health monitoring, and automatic recovery capabilities.
"""

import asyncio
from typing import Dict, Optional, List
import time

from app.logging_config import central_logger
from app.core.reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)
from .connection import ConnectionInfo, ConnectionManager
from .heartbeat import HeartbeatManager
from .error_handler import WebSocketErrorHandler, default_error_handler
from .reliable_message_handler import ReliableMessageHandler, MessageTypeRouter
from .connection_lifecycle_manager import ConnectionLifecycleManager
from .connection_message_handler import ConnectionMessageHandler
from .connection_cleanup_monitor import ConnectionCleanupMonitor
from .connection_user_tracker import ConnectionUserTracker

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
        """Initialize reliable connection manager."""
        self._initialize_core_components()
        self._configure_intervals(heartbeat_interval, cleanup_interval, max_connections_per_user, connection_timeout)
        self._setup_reliability_wrapper()
        self._initialize_tracking_structures()
        self._initialize_specialized_managers()
        self._initialize_background_tasks()
    
    def _initialize_core_components(self) -> None:
        """Initialize core components."""
        self.connection_manager = ConnectionManager()
        self.heartbeat_manager = HeartbeatManager(self.connection_manager, default_error_handler)
        self.error_handler = default_error_handler
        self.message_handler = ReliableMessageHandler()
        self.message_router = MessageTypeRouter()
    
    def _configure_intervals(self, heartbeat_interval: int, cleanup_interval: int, 
                           max_connections_per_user: int, connection_timeout: int) -> None:
        """Configure timing intervals and limits."""
        self.heartbeat_interval = heartbeat_interval
        self.cleanup_interval = cleanup_interval
        self.max_connections_per_user = max_connections_per_user
        self.connection_timeout = connection_timeout
    
    def _setup_reliability_wrapper(self) -> None:
        """Setup reliability wrapper for connection operations."""
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5, recovery_timeout=45.0, name="ReliableConnectionManager"
        )
        retry_config = RetryConfig(max_retries=2, base_delay=1.0, max_delay=10.0)
        self.reliability = get_reliability_wrapper(
            "ReliableConnectionManager", circuit_config, retry_config
        )
    
    def _initialize_tracking_structures(self) -> None:
        """Initialize tracking structures and statistics."""
        self.user_connections: Dict[str, set] = {}
        self.connection_timeouts: Dict[str, float] = {}
        self.stats = {
            "total_connections": 0, "active_connections": 0, "failed_connections": 0,
            "timeouts": 0, "heartbeat_failures": 0, "cleanup_runs": 0
        }
    
    def _initialize_specialized_managers(self) -> None:
        """Initialize specialized manager components."""
        self.lifecycle_manager = ConnectionLifecycleManager(
            self.connection_manager, self.heartbeat_manager, self.reliability,
            self.user_connections, self.connection_timeouts, self.stats, self.connection_timeout
        )
        self.message_handler_manager = ConnectionMessageHandler(
            self.connection_manager, self.message_handler, self.message_router,
            self.reliability, self.connection_timeouts, self.connection_timeout
        )
        self.cleanup_monitor = ConnectionCleanupMonitor(
            self.connection_manager, self.heartbeat_manager, self.error_handler,
            self.connection_timeouts, self.stats, self.cleanup_interval
        )
        self.user_tracker = ConnectionUserTracker(
            self.connection_manager, self.max_connections_per_user
        )
    
    def _initialize_background_tasks(self) -> None:
        """Initialize background task tracking."""
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the reliable connection manager."""
        if self._running:
            return
        self._running = True
        self._cleanup_task = asyncio.create_task(
            self.cleanup_monitor.cleanup_loop(
                lambda: self._running, self.remove_connection
            )
        )
        logger.info("ReliableConnectionManager started")
    
    async def stop(self):
        """Stop the reliable connection manager."""
        if not self._running:
            return
        self._running = False
        await self._stop_background_tasks()
        await self.heartbeat_manager.shutdown_all_heartbeats()
        await self.cleanup_monitor.close_all_connections(
            self.user_connections, self.connection_timeouts
        )
        logger.info("ReliableConnectionManager stopped")
    
    async def _stop_background_tasks(self) -> None:
        """Stop background cleanup tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def add_connection(self, websocket, user_id: str, connection_id: str) -> bool:
        """Add a new connection with reliability protection."""
        return await self.lifecycle_manager.add_connection(websocket, user_id, connection_id)

    async def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection with cleanup."""
        return await self.lifecycle_manager.remove_connection(connection_id)
    
    async def handle_message(self, connection_id: str, raw_message: str) -> bool:
        """Handle incoming message from connection."""
        return await self.message_handler_manager.handle_message(connection_id, raw_message)
    
    async def send_message(self, connection_id: str, message: dict) -> bool:
        """Send message to connection with reliability protection."""
        return await self.message_handler_manager.send_message(connection_id, message)
    
    async def broadcast_message(self, message: dict, user_filter: Optional[str] = None) -> int:
        """Broadcast message to multiple connections."""
        return await self.message_handler_manager.broadcast_message(
            message, user_filter, self.send_message
        )
    
    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection information."""
        return self.connection_manager.get_connection_by_id(connection_id)
    
    def get_user_connections(self, user_id: str) -> List[ConnectionInfo]:
        """Get all connections for a user."""
        return self.user_tracker.get_user_connections(user_id)
    
    def get_health_status(self) -> dict:
        """Get comprehensive health status."""
        return {
            "connection_manager": self._get_connection_manager_health(),
            "heartbeat_manager": self.heartbeat_manager.get_stats(),
            "message_handler": self.message_handler.get_health_status(),
            "error_handler": self.error_handler.get_error_stats(),
            "reliability": self.reliability.get_health_status()
        }
    
    def _get_connection_manager_health(self) -> dict:
        """Get connection manager specific health status."""
        return {
            **self.stats,
            "active_connections": len(self.connection_manager.get_all_connections()),
            "last_cleanup": self.cleanup_monitor.last_cleanup_time,
            "user_connections": self.user_tracker.get_all_user_stats()
        }
    
    def register_message_handler(self, message_type: str, handler):
        """Register a message handler for a specific type."""
        self.message_handler_manager.register_message_handler(message_type, handler)
    
    def register_fallback_handler(self, handler):
        """Register a fallback message handler."""
        self.message_handler_manager.register_fallback_handler(handler)


# Global instance
default_reliable_connection_manager = ReliableConnectionManager()
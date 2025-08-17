"""Connection lifecycle management operations."""

import time
from datetime import datetime, timezone
from typing import Optional

from app.logging_config import central_logger
from .connection import ConnectionInfo

logger = central_logger.get_logger(__name__)


class ConnectionLifecycleManager:
    """Manages connection addition and removal lifecycle."""
    
    def __init__(self, connection_manager, heartbeat_manager, reliability, 
                 user_connections, connection_timeouts, stats, connection_timeout):
        """Initialize lifecycle manager."""
        self.connection_manager = connection_manager
        self.heartbeat_manager = heartbeat_manager
        self.reliability = reliability
        self.user_connections = user_connections
        self.connection_timeouts = connection_timeouts
        self.stats = stats
        self.connection_timeout = connection_timeout
    
    async def add_connection(self, websocket, user_id: str, connection_id: str) -> bool:
        """Add a new connection with reliability protection."""
        try:
            return await self._execute_connection_addition(websocket, user_id, connection_id)
        except Exception as e:
            logger.error(f"Error adding connection {connection_id}: {e}")
            return False

    async def _execute_connection_addition(self, websocket, user_id: str, connection_id: str) -> bool:
        """Execute connection addition with safety mechanisms."""
        add_operation = self._create_add_connection_operation(websocket, user_id, connection_id)
        fallback_operation = self._create_add_connection_fallback(user_id, connection_id)
        
        return await self.reliability.execute_safely(
            add_operation,
            "add_connection",
            fallback=fallback_operation,
            timeout=10.0
        )

    def _create_add_connection_operation(self, websocket, user_id: str, connection_id: str):
        """Create main connection addition operation."""
        async def _add_connection():
            return await self._perform_connection_addition(websocket, user_id, connection_id)
        return _add_connection

    def _create_add_connection_fallback(self, user_id: str, connection_id: str):
        """Create fallback operation for connection addition."""
        async def _fallback_add_connection():
            logger.warning(f"Failed to add connection {connection_id} for user {user_id}")
            self.stats["failed_connections"] += 1
            return False
        return _fallback_add_connection

    async def _perform_connection_addition(self, websocket, user_id: str, connection_id: str) -> bool:
        """Perform the actual connection addition steps."""
        self._validate_connection_limits(user_id)
        conn_info = self._create_connection_info(websocket, user_id, connection_id)
        await self._register_new_connection(conn_info, user_id, connection_id)
        return True

    def _validate_connection_limits(self, user_id: str) -> None:
        """Validate user connection limits."""
        if not self._check_connection_limits(user_id):
            raise ValueError(f"User {user_id} exceeded connection limit")

    def _create_connection_info(self, websocket, user_id: str, connection_id: str) -> ConnectionInfo:
        """Create connection info object."""
        return ConnectionInfo(
            connection_id=connection_id,
            websocket=websocket,
            user_id=user_id,
            connected_at=datetime.now(timezone.utc)
        )

    async def _register_new_connection(self, conn_info: ConnectionInfo, user_id: str, connection_id: str) -> None:
        """Register new connection in all tracking systems."""
        self._add_to_connection_manager(conn_info)
        self._track_user_connection(user_id, connection_id)
        self._set_connection_timeout(connection_id)
        await self._start_connection_monitoring(conn_info)
        self._update_connection_stats(connection_id, user_id)

    def _add_to_connection_manager(self, conn_info: ConnectionInfo) -> None:
        """Add connection to connection manager."""
        self.connection_manager.add_connection(conn_info)

    def _track_user_connection(self, user_id: str, connection_id: str) -> None:
        """Track connection for user."""
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)

    def _set_connection_timeout(self, connection_id: str) -> None:
        """Set connection timeout."""
        self.connection_timeouts[connection_id] = time.time() + self.connection_timeout

    async def _start_connection_monitoring(self, conn_info: ConnectionInfo) -> None:
        """Start heartbeat monitoring for connection."""
        await self.heartbeat_manager.start_heartbeat_for_connection(conn_info)

    def _update_connection_stats(self, connection_id: str, user_id: str) -> None:
        """Update connection statistics."""
        self.stats["total_connections"] += 1
        self.stats["active_connections"] = len(self.connection_manager.get_all_connections())
        logger.info(f"Added connection {connection_id} for user {user_id}")

    async def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection with cleanup."""
        try:
            return await self.reliability.execute_safely(
                lambda: self._execute_connection_removal(connection_id),
                "remove_connection",
                timeout=5.0
            )
        except Exception as e:
            logger.error(f"Error removing connection {connection_id}: {e}")
            return False

    async def _execute_connection_removal(self, connection_id: str) -> bool:
        """Execute the connection removal process."""
        conn_info = self.connection_manager.get_connection_by_id(connection_id)
        if not conn_info:
            return True  # Already removed
        await self._cleanup_connection_resources(connection_id, conn_info)
        self._update_removal_statistics()
        logger.info(f"Removed connection {connection_id}")
        return True

    async def _cleanup_connection_resources(self, connection_id: str, conn_info) -> None:
        """Cleanup all resources associated with connection."""
        await self.heartbeat_manager.stop_heartbeat_for_connection(connection_id)
        self._cleanup_user_tracking(connection_id, conn_info)
        self.connection_timeouts.pop(connection_id, None)
        self.connection_manager.remove_connection(connection_id)

    def _cleanup_user_tracking(self, connection_id: str, conn_info) -> None:
        """Cleanup user connection tracking."""
        if conn_info.user_id and conn_info.user_id in self.user_connections:
            self.user_connections[conn_info.user_id].discard(connection_id)
            if not self.user_connections[conn_info.user_id]:
                del self.user_connections[conn_info.user_id]

    def _update_removal_statistics(self) -> None:
        """Update statistics after connection removal."""
        self.stats["active_connections"] = len(self.connection_manager.get_all_connections())

    def _check_connection_limits(self, user_id: str) -> bool:
        """Check if user can create more connections."""
        max_connections_per_user = 5  # Default, could be injected
        current_count = len(self.user_connections.get(user_id, set()))
        return current_count < max_connections_per_user
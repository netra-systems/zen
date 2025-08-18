"""Core WebSocket heartbeat manager.

Manages heartbeat/ping-pong functionality to detect dead connections
and maintain connection health.
"""

import asyncio
from typing import Dict, Optional, Any

from app.logging_config import central_logger
from .connection import ConnectionInfo, ConnectionManager
from .error_handler import WebSocketErrorHandler
from .heartbeat_config import HeartbeatConfig
from .heartbeat_statistics import HeartbeatStatistics
from .heartbeat_loop_operations import HeartbeatLoopOperations
from .heartbeat_error_recovery import HeartbeatErrorRecovery
from .heartbeat_cleanup import HeartbeatCleanup

logger = central_logger.get_logger(__name__)


class HeartbeatManager:
    """Manages WebSocket heartbeat functionality."""
    
    def __init__(self, connection_manager: ConnectionManager, error_handler: Optional[WebSocketErrorHandler] = None):
        """Initialize heartbeat manager."""
        self.connection_manager = connection_manager
        self.error_handler = error_handler
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self.config = HeartbeatConfig()
        self.missed_heartbeats: Dict[str, int] = {}
        self._running = False
        self._initialize_modules()
    
    def _initialize_modules(self) -> None:
        """Initialize component modules."""
        self._initialize_core_modules()
        self._initialize_helper_modules()
    
    def _initialize_core_modules(self) -> None:
        """Initialize statistics and loop operations modules."""
        self.statistics = HeartbeatStatistics()
        self.loop_ops = HeartbeatLoopOperations(
            self.connection_manager, self.config, 
            self.statistics, self.missed_heartbeats
        )
    
    def _initialize_helper_modules(self) -> None:
        """Initialize error recovery and cleanup modules."""
        self.error_recovery = HeartbeatErrorRecovery(self.error_handler, self.statistics)
        self.cleanup = HeartbeatCleanup(
            self.connection_manager, self.heartbeat_tasks, self.missed_heartbeats
        )
    
    async def start_heartbeat_for_connection(self, conn_info: ConnectionInfo):
        """Start heartbeat monitoring for a connection."""
        if self._is_heartbeat_already_running(conn_info):
            return
        self._create_and_store_heartbeat_task(conn_info)
        self._initialize_missed_heartbeat_counter(conn_info)
        self._log_heartbeat_started(conn_info)

    def _is_heartbeat_already_running(self, conn_info: ConnectionInfo) -> bool:
        """Check if heartbeat is already running for connection."""
        if conn_info.connection_id in self.heartbeat_tasks:
            logger.warning(f"Heartbeat already running for connection {conn_info.connection_id}")
            return True
        return False

    def _create_and_store_heartbeat_task(self, conn_info: ConnectionInfo) -> None:
        """Create and store heartbeat task for connection."""
        task = asyncio.create_task(self._heartbeat_loop(conn_info))
        self.heartbeat_tasks[conn_info.connection_id] = task

    def _initialize_missed_heartbeat_counter(self, conn_info: ConnectionInfo) -> None:
        """Initialize missed heartbeat counter for connection."""
        self.missed_heartbeats[conn_info.connection_id] = 0

    def _log_heartbeat_started(self, conn_info: ConnectionInfo) -> None:
        """Log heartbeat started message."""
        logger.debug(f"Started heartbeat for connection {conn_info.connection_id}")

    async def stop_heartbeat_for_connection(self, connection_id: str):
        """Stop heartbeat monitoring for a connection."""
        if connection_id not in self.heartbeat_tasks:
            return
        task = self.heartbeat_tasks[connection_id]
        await self.error_recovery.safely_cancel_task(task, connection_id)
        self._cleanup_heartbeat_tracking(connection_id)
        self._log_heartbeat_stopped(connection_id)

    def _cleanup_heartbeat_tracking(self, connection_id: str) -> None:
        """Clean up heartbeat tracking data for connection."""
        self.heartbeat_tasks.pop(connection_id, None)
        self.missed_heartbeats.pop(connection_id, None)

    def _log_heartbeat_stopped(self, connection_id: str) -> None:
        """Log heartbeat stopped message."""
        logger.debug(f"Stopped heartbeat for connection {connection_id}")

    async def handle_pong(self, conn_info: ConnectionInfo):
        """Handle pong response from client."""
        self.loop_ops.handle_pong_received(conn_info)

    def is_connection_alive(self, conn_info: ConnectionInfo) -> bool:
        """Check if a connection is still alive based on heartbeat."""
        if not self.connection_manager.is_connection_alive(conn_info):
            return False
        return self.loop_ops._check_heartbeat_health(conn_info)

    async def _heartbeat_loop(self, conn_info: ConnectionInfo):
        """Heartbeat loop for a specific connection."""
        try:
            await self.loop_ops.run_heartbeat_monitoring(conn_info)
        except asyncio.CancelledError:
            self.error_recovery.log_heartbeat_cancelled(conn_info)
        except Exception as e:
            await self.error_recovery.handle_heartbeat_loop_error(conn_info, e)
        finally:
            self.cleanup.cleanup_connection_resources(conn_info)

    async def cleanup_dead_connections(self):
        """Check all monitored connections and clean up dead ones."""
        await self.cleanup.cleanup_dead_connections(self.is_connection_alive)

    async def shutdown_all_heartbeats(self):
        """Stop all heartbeat monitoring."""
        await self.cleanup.shutdown_all_heartbeats(self.statistics)

    def get_stats(self) -> Dict[str, any]:
        """Get heartbeat statistics."""
        active_heartbeats = len(self.heartbeat_tasks)
        total_missed = sum(self.missed_heartbeats.values())
        base_stats = self.statistics.get_base_stats(active_heartbeats, total_missed)
        config_stats = self.statistics.get_config_stats(self.config)
        return {**base_stats, "config": config_stats}

    def get_connection_heartbeat_info(self, connection_id: str) -> Optional[Dict[str, any]]:
        """Get heartbeat information for a specific connection."""
        if not self._is_connection_monitored(connection_id):
            return None
        conn_info = self.connection_manager.get_connection_by_id(connection_id)
        if not conn_info:
            return None
        return self._build_connection_heartbeat_info(connection_id, conn_info)

    def _is_connection_monitored(self, connection_id: str) -> bool:
        """Check if connection is being monitored."""
        return connection_id in self.heartbeat_tasks

    def _build_connection_heartbeat_info(self, connection_id: str, conn_info) -> Dict[str, any]:
        """Build heartbeat info dictionary for connection."""
        missed_count = self.missed_heartbeats.get(connection_id, 0)
        task = self.heartbeat_tasks[connection_id]
        return self.statistics.build_connection_info(
            connection_id, conn_info, missed_count, self.config, task
        )
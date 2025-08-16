"""Core WebSocket heartbeat manager.

Manages heartbeat/ping-pong functionality to detect dead connections
and maintain connection health.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional, Any

from app.logging_config import central_logger
from .connection import ConnectionInfo, ConnectionManager
from .error_handler import WebSocketErrorHandler
from .error_types import ErrorSeverity
from .heartbeat_config import HeartbeatConfig
from . import heartbeat_utils as utils

logger = central_logger.get_logger(__name__)


class HeartbeatManager:
    """Manages WebSocket heartbeat functionality."""
    
    def __init__(self, connection_manager: ConnectionManager, error_handler: Optional[WebSocketErrorHandler] = None):
        """Initialize heartbeat manager.
        
        Args:
            connection_manager: Connection manager instance
            error_handler: Error handler for reporting issues
        """
        self.connection_manager = connection_manager
        self.error_handler = error_handler
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self.config = HeartbeatConfig()
        self.missed_heartbeats: Dict[str, int] = {}  # Track missed heartbeats per connection
        self._running = False
        self._stats = {
            "total_pings_sent": 0,
            "total_pongs_received": 0,
            "connections_timed_out": 0,
            "heartbeat_failures": 0
        }

    async def start_heartbeat_for_connection(self, conn_info: ConnectionInfo):
        """Start heartbeat monitoring for a connection.
        
        Args:
            conn_info: Connection to monitor
        """
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
        """Stop heartbeat monitoring for a connection.
        
        Args:
            connection_id: Connection to stop monitoring
        """
        if connection_id not in self.heartbeat_tasks:
            return
        task = self.heartbeat_tasks[connection_id]
        await self._safely_cancel_heartbeat_task(task, connection_id)
        self._cleanup_heartbeat_tracking(connection_id)
        self._log_heartbeat_stopped(connection_id)

    async def _safely_cancel_heartbeat_task(self, task: asyncio.Task, connection_id: str) -> None:
        """Safely cancel heartbeat task with error handling."""
        if not task.done():
            task.cancel()
            await self._wait_for_task_cancellation(task, connection_id)

    async def _wait_for_task_cancellation(self, task: asyncio.Task, connection_id: str) -> None:
        """Wait for task cancellation with error handling."""
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Error stopping heartbeat for {connection_id}: {e}")

    def _cleanup_heartbeat_tracking(self, connection_id: str) -> None:
        """Clean up heartbeat tracking data for connection."""
        self.heartbeat_tasks.pop(connection_id, None)
        self.missed_heartbeats.pop(connection_id, None)

    def _log_heartbeat_stopped(self, connection_id: str) -> None:
        """Log heartbeat stopped message."""
        logger.debug(f"Stopped heartbeat for connection {connection_id}")

    async def handle_pong(self, conn_info: ConnectionInfo):
        """Handle pong response from client.
        
        Args:
            conn_info: Connection that sent pong
        """
        self._update_pong_timestamp(conn_info)
        self._reset_missed_heartbeat_counter(conn_info)
        self._increment_pong_stats()
        self._log_pong_received(conn_info)

    def _update_pong_timestamp(self, conn_info: ConnectionInfo) -> None:
        """Update pong timestamp for connection."""
        conn_info.last_pong = datetime.now(timezone.utc)

    def _reset_missed_heartbeat_counter(self, conn_info: ConnectionInfo) -> None:
        """Reset missed heartbeat counter for connection."""
        if conn_info.connection_id in self.missed_heartbeats:
            self.missed_heartbeats[conn_info.connection_id] = 0

    def _increment_pong_stats(self) -> None:
        """Increment pong received statistics."""
        self._stats["total_pongs_received"] += 1

    def _log_pong_received(self, conn_info: ConnectionInfo) -> None:
        """Log pong received message."""
        logger.debug(f"Received pong from connection {conn_info.connection_id}")

    def is_connection_alive(self, conn_info: ConnectionInfo) -> bool:
        """Check if a connection is still alive based on heartbeat.
        
        Args:
            conn_info: Connection to check
            
        Returns:
            True if connection appears to be alive
        """
        if not self.connection_manager.is_connection_alive(conn_info):
            return False
        return self._check_heartbeat_health(conn_info)

    def _check_heartbeat_health(self, conn_info: ConnectionInfo) -> bool:
        """Check heartbeat-specific health indicators."""
        if not self._is_heartbeat_timeout_ok(conn_info):
            return False
        return self._is_missed_heartbeats_ok(conn_info)

    def _is_heartbeat_timeout_ok(self, conn_info: ConnectionInfo) -> bool:
        """Check if heartbeat timeout is within limits."""
        now = datetime.now(timezone.utc)
        time_since_ping = (now - conn_info.last_ping).total_seconds()
        if time_since_ping > self.config.timeout_seconds:
            logger.debug(f"Connection {conn_info.connection_id} heartbeat timeout ({time_since_ping:.1f}s)")
            return False
        return True

    def _is_missed_heartbeats_ok(self, conn_info: ConnectionInfo) -> bool:
        """Check if missed heartbeats are within limits."""
        missed_count = self.missed_heartbeats.get(conn_info.connection_id, 0)
        if missed_count >= self.config.max_missed_heartbeats:
            logger.debug(f"Connection {conn_info.connection_id} exceeded missed heartbeat limit ({missed_count})")
            return False
        return True

    async def _heartbeat_loop(self, conn_info: ConnectionInfo):
        """Heartbeat loop for a specific connection.
        
        Args:
            conn_info: Connection to monitor
        """
        try:
            await self._run_heartbeat_monitoring(conn_info)
        except asyncio.CancelledError:
            self._log_heartbeat_cancelled(conn_info)
        except Exception as e:
            await self._handle_loop_error(conn_info, e)
        finally:
            self._cleanup_heartbeat_resources(conn_info)

    def _log_heartbeat_cancelled(self, conn_info: ConnectionInfo) -> None:
        """Log heartbeat cancellation."""
        logger.debug(f"Heartbeat cancelled for {conn_info.connection_id}")

    async def _run_heartbeat_monitoring(self, conn_info: ConnectionInfo) -> None:
        """Run main heartbeat monitoring loop."""
        while self.connection_manager.is_connection_alive(conn_info):
            try:
                should_continue = await self._execute_heartbeat_cycle(conn_info)
                if not should_continue:
                    break
            except asyncio.CancelledError:
                raise
            except ConnectionError as e:
                utils.log_connection_closed(conn_info.connection_id, e)
                break
            except Exception as e:
                if await self._should_break_on_error(conn_info, e):
                    break

    async def _should_break_on_error(self, conn_info: ConnectionInfo, error: Exception) -> bool:
        """Determine if monitoring should break on this error."""
        if self._is_connection_closed_error(conn_info, error):
            return True
        await self._handle_heartbeat_error(conn_info, error)
        return False

    async def _execute_heartbeat_cycle(self, conn_info: ConnectionInfo) -> bool:
        """Execute single heartbeat cycle."""
        await self._send_ping_and_update_stats(conn_info)
        await asyncio.sleep(self.config.interval_seconds)
        await self._check_pong_response(conn_info)
        return self._validate_connection_health(conn_info)

    async def _send_ping_and_update_stats(self, conn_info: ConnectionInfo) -> None:
        """Send ping and update statistics."""
        await self._send_ping(conn_info)
        conn_info.last_ping = datetime.now(timezone.utc)
        self._stats["total_pings_sent"] += 1

    def _validate_connection_health(self, conn_info: ConnectionInfo) -> bool:
        """Validate connection health after heartbeat cycle."""
        if not self.is_connection_alive(conn_info):
            logger.warning(f"Connection {conn_info.connection_id} failed heartbeat check")
            return False
        return True

    def _is_connection_closed_error(self, conn_info: ConnectionInfo, error: Exception) -> bool:
        """Check if error indicates connection is closed."""
        error_msg = str(error).lower()
        if 'close' in error_msg or 'disconnect' in error_msg:
            logger.debug(f"Connection appears closed for {conn_info.connection_id}: {error}")
            return True
        return False

    async def _handle_loop_error(self, conn_info: ConnectionInfo, error: Exception) -> None:
        """Handle top-level heartbeat loop errors."""
        self._log_heartbeat_loop_error(conn_info, error)
        await self._report_loop_error(conn_info, error)

    def _log_heartbeat_loop_error(self, conn_info: ConnectionInfo, error: Exception) -> None:
        """Log heartbeat loop error."""
        logger.error(f"Heartbeat error for {conn_info.connection_id}: {error}")

    async def _report_loop_error(self, conn_info: ConnectionInfo, error: Exception) -> None:
        """Report loop error to error handler."""
        if self.error_handler:
            await self.error_handler.handle_connection_error(
                conn_info, 
                f"Heartbeat loop error: {error}",
                "heartbeat_error",
                ErrorSeverity.MEDIUM
            )

    def _cleanup_heartbeat_resources(self, conn_info: ConnectionInfo) -> None:
        """Clean up heartbeat resources for connection."""
        self.heartbeat_tasks.pop(conn_info.connection_id, None)
        self.missed_heartbeats.pop(conn_info.connection_id, None)

    async def _send_ping(self, conn_info: ConnectionInfo):
        """Send ping message to connection.
        
        Args:
            conn_info: Connection to ping
        """
        ping_message = utils.create_ping_message()
        try:
            utils.validate_connection_for_ping(conn_info, self.connection_manager)
            await utils.perform_ping_send(conn_info, ping_message)
        except ConnectionError:
            raise
        except Exception as e:
            self._handle_ping_error(conn_info, e)

    def _handle_ping_error(self, conn_info: ConnectionInfo, error: Exception) -> None:
        """Handle errors during ping sending."""
        if utils.is_connection_closed_ping_error(error):
            utils.handle_closed_connection_ping_error(conn_info.connection_id, error)
        utils.handle_general_ping_error(conn_info.connection_id, error)
        raise

    async def _check_pong_response(self, conn_info: ConnectionInfo):
        """Check if we received a pong response within the timeout.
        
        Args:
            conn_info: Connection to check
        """
        time_since_response = utils.calculate_response_time(conn_info)
        if utils.is_response_timeout(time_since_response, self.config.timeout_seconds):
            await self._handle_pong_timeout(conn_info)

    async def _handle_pong_timeout(self, conn_info: ConnectionInfo) -> None:
        """Handle pong response timeout."""
        missed_count = utils.increment_missed_counter(self.missed_heartbeats, conn_info.connection_id)
        utils.log_missed_heartbeat(conn_info.connection_id, missed_count, self.config.max_missed_heartbeats)
        if utils.should_handle_timeout(missed_count, self.config.max_missed_heartbeats):
            await self._handle_timeout_error(conn_info, missed_count)

    async def _handle_timeout_error(self, conn_info: ConnectionInfo, missed_count: int) -> None:
        """Handle connection timeout error."""
        self._increment_timeout_stats()
        await self._report_timeout_error(conn_info, missed_count)

    def _increment_timeout_stats(self) -> None:
        """Increment timeout statistics."""
        self._stats["connections_timed_out"] += 1

    async def _report_timeout_error(self, conn_info: ConnectionInfo, missed_count: int) -> None:
        """Report timeout error to error handler."""
        if self.error_handler:
            await self.error_handler.handle_connection_error(
                conn_info,
                f"Connection timed out after {missed_count} missed heartbeats",
                "heartbeat_timeout",
                ErrorSeverity.HIGH
            )

    async def _handle_heartbeat_error(self, conn_info: ConnectionInfo, error: Exception):
        """Handle errors during heartbeat operations.
        
        Args:
            conn_info: Connection that had the error
            error: Error that occurred
        """
        self._increment_heartbeat_failure_stats()
        await self._report_heartbeat_error(conn_info, error)
        await self.stop_heartbeat_for_connection(conn_info.connection_id)

    def _increment_heartbeat_failure_stats(self) -> None:
        """Increment heartbeat failure statistics."""
        self._stats["heartbeat_failures"] += 1

    async def _report_heartbeat_error(self, conn_info: ConnectionInfo, error: Exception) -> None:
        """Report heartbeat error to error handler."""
        if self.error_handler:
            await self.error_handler.handle_connection_error(
                conn_info,
                f"Heartbeat error: {error}",
                "heartbeat_error",
                ErrorSeverity.MEDIUM
            )

    async def cleanup_dead_connections(self):
        """Check all monitored connections and clean up dead ones."""
        dead_connections = self._identify_dead_connections()
        await self._cleanup_identified_dead_connections(dead_connections)

    def _identify_dead_connections(self) -> list:
        """Identify connections that are dead."""
        dead_connections = []
        for connection_id, task in list(self.heartbeat_tasks.items()):
            conn_info = self.connection_manager.get_connection_by_id(connection_id)
            if not conn_info or not self.is_connection_alive(conn_info):
                dead_connections.append(connection_id)
        return dead_connections

    async def _cleanup_identified_dead_connections(self, dead_connections: list) -> None:
        """Clean up identified dead connections."""
        for connection_id in dead_connections:
            await self.stop_heartbeat_for_connection(connection_id)
            logger.info(f"Cleaned up heartbeat for dead connection {connection_id}")

    async def shutdown_all_heartbeats(self):
        """Stop all heartbeat monitoring."""
        logger.info("Shutting down all heartbeat monitoring...")
        tasks_to_cancel = self._gather_tasks_to_cancel()
        await self._cancel_all_tasks(tasks_to_cancel)
        self._clear_all_tracking_data()
        self._log_shutdown_complete()

    def _gather_tasks_to_cancel(self) -> list:
        """Gather all active tasks that need cancellation."""
        tasks_to_cancel = []
        for connection_id, task in self.heartbeat_tasks.items():
            if not task.done():
                task.cancel()
                tasks_to_cancel.append(task)
        return tasks_to_cancel

    async def _cancel_all_tasks(self, tasks_to_cancel: list) -> None:
        """Cancel all tasks and wait for completion."""
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

    def _clear_all_tracking_data(self) -> None:
        """Clear all heartbeat tracking data."""
        self.heartbeat_tasks.clear()
        self.missed_heartbeats.clear()

    def _log_shutdown_complete(self) -> None:
        """Log shutdown completion with final stats."""
        logger.info(f"Heartbeat shutdown complete. Final stats: {self.get_stats()}")

    def get_stats(self) -> Dict[str, any]:
        """Get heartbeat statistics.
        
        Returns:
            Dictionary with heartbeat statistics
        """
        active_heartbeats = len(self.heartbeat_tasks)
        total_missed = sum(self.missed_heartbeats.values())
        base_stats = self._build_base_stats(active_heartbeats, total_missed)
        config_stats = self._build_config_stats()
        return {**base_stats, "config": config_stats}

    def _build_base_stats(self, active_heartbeats: int, total_missed: int) -> Dict[str, any]:
        """Build base statistics dictionary."""
        return {
            "active_heartbeats": active_heartbeats,
            "total_pings_sent": self._stats["total_pings_sent"],
            "total_pongs_received": self._stats["total_pongs_received"],
            "connections_timed_out": self._stats["connections_timed_out"],
            "heartbeat_failures": self._stats["heartbeat_failures"],
            "total_missed_heartbeats": total_missed
        }

    def _build_config_stats(self) -> Dict[str, any]:
        """Build configuration statistics dictionary."""
        return {
            "interval_seconds": self.config.interval_seconds,
            "timeout_seconds": self.config.timeout_seconds,
            "max_missed_heartbeats": self.config.max_missed_heartbeats
        }

    def get_connection_heartbeat_info(self, connection_id: str) -> Optional[Dict[str, any]]:
        """Get heartbeat information for a specific connection.
        
        Args:
            connection_id: Connection to get info for
            
        Returns:
            Dictionary with heartbeat info or None if not monitored
        """
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
        is_alive = self.is_connection_alive(conn_info)
        return {
            "connection_id": connection_id,
            "is_alive": is_alive,
            "last_ping": conn_info.last_ping.isoformat(),
            "last_pong": conn_info.last_pong.isoformat() if conn_info.last_pong else None,
            "missed_heartbeats": missed_count,
            "max_missed_heartbeats": self.config.max_missed_heartbeats,
            "heartbeat_active": not self.heartbeat_tasks[connection_id].done()
        }
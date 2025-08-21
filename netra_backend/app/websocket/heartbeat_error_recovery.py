"""Heartbeat error handling and recovery operations."""

import asyncio
from typing import Optional

from app.logging_config import central_logger
from netra_backend.app.connection import ConnectionInfo
from netra_backend.app.error_types import ErrorSeverity

logger = central_logger.get_logger(__name__)


class HeartbeatErrorRecovery:
    """Handles heartbeat error recovery and reporting."""
    
    def __init__(self, error_handler: Optional[object], statistics):
        """Initialize error recovery handler."""
        self.error_handler = error_handler
        self.statistics = statistics
    
    async def handle_heartbeat_loop_error(self, conn_info: ConnectionInfo, error: Exception) -> None:
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
    
    async def handle_heartbeat_error(self, conn_info: ConnectionInfo, error: Exception, 
                                   stop_callback) -> None:
        """Handle errors during heartbeat operations."""
        self.statistics.increment_failure()
        await self._report_heartbeat_error(conn_info, error)
        await stop_callback(conn_info.connection_id)
    
    async def _report_heartbeat_error(self, conn_info: ConnectionInfo, error: Exception) -> None:
        """Report heartbeat error to error handler."""
        if self.error_handler:
            await self.error_handler.handle_connection_error(
                conn_info,
                f"Heartbeat error: {error}",
                "heartbeat_error",
                ErrorSeverity.MEDIUM
            )
    
    async def handle_timeout_error(self, conn_info: ConnectionInfo, missed_count: int) -> None:
        """Handle connection timeout error."""
        await self._report_timeout_error(conn_info, missed_count)
    
    async def _report_timeout_error(self, conn_info: ConnectionInfo, missed_count: int) -> None:
        """Report timeout error to error handler."""
        if self.error_handler:
            await self.error_handler.handle_connection_error(
                conn_info,
                f"Connection timed out after {missed_count} missed heartbeats",
                "heartbeat_timeout",
                ErrorSeverity.HIGH
            )
    
    def log_heartbeat_cancelled(self, conn_info: ConnectionInfo) -> None:
        """Log heartbeat cancellation."""
        logger.debug(f"Heartbeat cancelled for {conn_info.connection_id}")
    
    async def safely_cancel_task(self, task: asyncio.Task, connection_id: str) -> None:
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
"""WebSocket Error Handler Recovery System.

Handles error recovery strategies and timing.
"""

import asyncio
import time
from typing import Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket.connection import ConnectionInfo
from netra_backend.app.websocket.error_handler_config import ErrorHandlerConfig
from netra_backend.app.websocket.error_types import WebSocketErrorInfo

logger = central_logger.get_logger(__name__)


class ErrorHandlerRecovery:
    """Handles error recovery strategies and rate limiting."""
    
    def __init__(self, config: ErrorHandlerConfig):
        self.config = config

    async def attempt_error_recovery(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Attempt error recovery if conditions are met."""
        if not self._can_attempt_recovery(error):
            return False
        recovered = await self._attempt_recovery(error, conn_info)
        self.config.update_recovery_stats(recovered)
        return recovered

    def _can_attempt_recovery(self, error: WebSocketErrorInfo) -> bool:
        """Check if error recovery can be attempted."""
        return error.recoverable and error.retry_count < error.max_retries

    async def _attempt_recovery(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Attempt to recover from an error with rate limiting."""
        error.retry_count += 1
        recovery_key = self._create_recovery_key(error)
        if not await self._check_recovery_rate_limit(recovery_key):
            return False
        self._update_recovery_tracking(recovery_key)
        return await self._execute_recovery_strategy(error, conn_info, recovery_key)

    def _create_recovery_key(self, error: WebSocketErrorInfo) -> str:
        """Create recovery key for rate limiting."""
        return f"{error.error_type}:{error.connection_id or error.user_id}"

    async def _check_recovery_rate_limit(self, recovery_key: str) -> bool:
        """Check if recovery is rate limited."""
        current_time = time.time()
        if recovery_key not in self.config.recovery_timestamps:
            return True
        return self._evaluate_rate_limit_timing(recovery_key, current_time)

    def _evaluate_rate_limit_timing(self, recovery_key: str, current_time: float) -> bool:
        """Evaluate rate limit timing for recovery key."""
        last_attempt = self.config.recovery_timestamps[recovery_key]
        backoff_delay = self.config.recovery_backoff.get(recovery_key, 1.0)
        time_since_last = current_time - last_attempt
        return self._check_backoff_timing(recovery_key, time_since_last, backoff_delay)

    def _check_backoff_timing(self, recovery_key: str, time_since_last: float, backoff_delay: float) -> bool:
        """Check if enough time has passed since last recovery attempt."""
        if time_since_last < backoff_delay:
            logger.debug(f"Recovery rate limited for {recovery_key}, waiting {backoff_delay - time_since_last:.1f}s")
            return False
        return True

    def _update_recovery_tracking(self, recovery_key: str) -> None:
        """Update recovery tracking timestamps and backoff."""
        current_time = time.time()
        self.config.recovery_timestamps[recovery_key] = current_time
        current_backoff = self.config.recovery_backoff.get(recovery_key, 1.0)
        next_backoff = min(current_backoff * 2, 60.0)
        self.config.recovery_backoff[recovery_key] = next_backoff

    async def _execute_recovery_strategy(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo], recovery_key: str) -> bool:
        """Execute recovery strategy based on error type."""
        try:
            await self._apply_recovery_delay(error)
            return await self._apply_type_specific_recovery(error, conn_info, recovery_key)
        except Exception as recovery_error:
            return self._handle_recovery_error(error, recovery_error)

    def _handle_recovery_error(self, error: WebSocketErrorInfo, recovery_error: Exception) -> bool:
        """Handle recovery error."""
        logger.error(f"Error during recovery attempt for {error.error_id}: {recovery_error}")
        return False

    async def _apply_recovery_delay(self, error: WebSocketErrorInfo) -> None:
        """Apply delay before recovery attempt."""
        delay = min(error.retry_count * 0.5, 5.0)
        await asyncio.sleep(delay)

    async def _apply_type_specific_recovery(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo], recovery_key: str) -> bool:
        """Apply recovery strategy based on error type."""
        recovery_handlers = self.config.get_recovery_handlers()
        handler = recovery_handlers.get(error.error_type)
        if handler:
            return await handler(error, conn_info)
        return self._handle_unknown_error_recovery(error, recovery_key)

    def _handle_unknown_error_recovery(self, error: WebSocketErrorInfo, recovery_key: str) -> bool:
        """Handle recovery for unknown error types."""
        current_backoff = self.config.recovery_backoff.get(recovery_key, 1.0)
        logger.info(f"Generic recovery attempted for error {error.error_id} after {current_backoff:.1f}s backoff")
        return False

    async def recover_connection_error(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Attempt to recover from a connection error."""
        if not conn_info:
            return False
        logger.info(f"Connection error recovery: marking connection {conn_info.connection_id} for cleanup")
        return False  # Connection needs to be cleaned up

    async def recover_rate_limit_error(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Attempt to recover from a rate limit error."""
        logger.info(f"Rate limit error recovery: connection {error.connection_id} can resume after window")
        return True

    async def recover_heartbeat_error(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Attempt to recover from a heartbeat error."""
        if not conn_info:
            return False
        connection_alive = self._check_heartbeat_connection_state(conn_info)
        self._log_heartbeat_recovery_result(conn_info.connection_id, connection_alive)
        return connection_alive

    def _check_heartbeat_connection_state(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection is still alive for heartbeat recovery."""
        from starlette.websockets import WebSocketState
        return conn_info.websocket.client_state == WebSocketState.CONNECTED

    def _log_heartbeat_recovery_result(self, connection_id: str, connection_alive: bool) -> None:
        """Log heartbeat recovery attempt result."""
        if connection_alive:
            logger.info(f"Heartbeat error recovery: connection {connection_id} may continue")
        else:
            logger.info(f"Heartbeat error: connection {connection_id} is closed, cannot recover")
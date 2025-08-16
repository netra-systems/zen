"""Core WebSocket error handling functionality.

Provides centralized error handling, logging, and recovery mechanisms.
"""

from typing import Dict, Any, Optional, List, Callable
import asyncio
import time

from app.logging_config import central_logger
from .connection import ConnectionInfo
from .error_types import WebSocketErrorInfo, ErrorSeverity
from app.core.exceptions_websocket import WebSocketError

logger = central_logger.get_logger(__name__)


class WebSocketErrorHandler:
    """Handles WebSocket errors with logging, tracking, and recovery."""
    
    def __init__(self):
        """Initialize error handler."""
        self.error_history: Dict[str, WebSocketErrorInfo] = {}
        self.error_patterns: Dict[str, int] = {}  # Track common error patterns
        self.connection_errors: Dict[str, int] = {}  # Track errors per connection
        self.recovery_timestamps: Dict[str, float] = {}  # Track last recovery attempt time
        self.recovery_backoff: Dict[str, float] = {}  # Track backoff delays
        self._stats = self._initialize_stats()

    def _initialize_stats(self) -> Dict[str, int]:
        """Initialize error statistics dictionary."""
        return {
            "total_errors": 0, "critical_errors": 0, "recovered_errors": 0,
            "connection_errors": 0, "validation_errors": 0, "rate_limit_errors": 0
        }
    
    async def handle_error(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Handle a WebSocket error with appropriate logging and recovery."""
        self._store_and_track_error(error, conn_info)
        self._log_error(error, conn_info)
        
        return await self._attempt_error_recovery(error, conn_info)

    def _store_and_track_error(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo]) -> None:
        """Store error and update tracking information."""
        self.error_history[error.error_id] = error
        self._update_error_statistics(error)
        self._update_connection_tracking(error, conn_info)
        self._track_error_patterns(error)

    def _update_error_statistics(self, error: WebSocketErrorInfo) -> None:
        """Update error statistics."""
        self._stats["total_errors"] += 1
        if error.severity == ErrorSeverity.CRITICAL:
            self._stats["critical_errors"] += 1

    def _update_connection_tracking(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo]) -> None:
        """Update connection-specific error tracking."""
        if conn_info:
            error.connection_id = conn_info.connection_id
            error.user_id = conn_info.user_id
            conn_info.error_count += 1
            self.connection_errors[conn_info.connection_id] = self.connection_errors.get(conn_info.connection_id, 0) + 1

    def _track_error_patterns(self, error: WebSocketErrorInfo) -> None:
        """Track error patterns for analysis."""
        error_pattern = f"{error.error_type}:{error.message[:50]}"
        self.error_patterns[error_pattern] = self.error_patterns.get(error_pattern, 0) + 1

    async def _attempt_error_recovery(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo]) -> bool:
        """Attempt error recovery if conditions are met."""
        if not self._can_attempt_recovery(error):
            return False
        recovered = await self._attempt_recovery(error, conn_info)
        self._update_recovery_stats(recovered)
        return recovered

    def _update_recovery_stats(self, recovered: bool) -> None:
        """Update recovery statistics."""
        if recovered:
            self._stats["recovered_errors"] += 1

    def _can_attempt_recovery(self, error: WebSocketErrorInfo) -> bool:
        """Check if error recovery can be attempted."""
        return error.recoverable and error.retry_count < error.max_retries
    
    async def handle_connection_error(self, conn_info: ConnectionInfo, error_message: str, 
                                    error_type: str = "connection_error", 
                                    severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> WebSocketErrorInfo:
        """Handle a connection-specific error."""
        error = self._create_connection_error_info(conn_info, error_message, error_type, severity)
        self._stats["connection_errors"] += 1
        await self.handle_error(error, conn_info)
        return error

    def _create_connection_error_info(self, conn_info: ConnectionInfo, error_message: str,
                                    error_type: str, severity: ErrorSeverity) -> WebSocketErrorInfo:
        """Create WebSocketErrorInfo for connection error."""
        context = self._build_connection_error_context(conn_info)
        return self._build_websocket_error_info(conn_info, error_message, error_type, severity, context)

    def _build_websocket_error_info(self, conn_info: ConnectionInfo, error_message: str,
                                  error_type: str, severity: ErrorSeverity, context: Dict[str, Any]) -> WebSocketErrorInfo:
        """Build WebSocketErrorInfo object."""
        return WebSocketErrorInfo(
            connection_id=conn_info.connection_id, user_id=conn_info.user_id,
            error_type=error_type, message=error_message, severity=severity, context=context
        )

    def _build_connection_error_context(self, conn_info: ConnectionInfo) -> Dict[str, Any]:
        """Build context information for connection error."""
        return {
            "connected_at": conn_info.connected_at.isoformat(),
            "message_count": conn_info.message_count,
            "error_count": conn_info.error_count,
            "last_ping": conn_info.last_ping.isoformat()
        }
    
    async def handle_validation_error(self, user_id: str, message: str, 
                                    validation_details: Dict[str, Any]) -> WebSocketErrorInfo:
        """Handle a message validation error."""
        error = self._create_validation_error_info(user_id, message, validation_details)
        self._stats["validation_errors"] += 1
        await self.handle_error(error)
        return error

    def _create_validation_error_info(self, user_id: str, message: str, 
                                    validation_details: Dict[str, Any]) -> WebSocketErrorInfo:
        """Create WebSocketErrorInfo for validation error."""
        return WebSocketErrorInfo(
            user_id=user_id, error_type="validation_error", message=message,
            severity=ErrorSeverity.LOW, context=validation_details, recoverable=False
        )
    
    async def handle_rate_limit_error(self, conn_info: ConnectionInfo, limit_info: Dict[str, Any]) -> WebSocketErrorInfo:
        """Handle a rate limiting error."""
        error = self._create_rate_limit_error_info(conn_info, limit_info)
        self._stats["rate_limit_errors"] += 1
        await self.handle_error(error, conn_info)
        return error

    def _create_rate_limit_error_info(self, conn_info: ConnectionInfo, limit_info: Dict[str, Any]) -> WebSocketErrorInfo:
        """Create WebSocketErrorInfo for rate limit error."""
        return WebSocketErrorInfo(
            connection_id=conn_info.connection_id, user_id=conn_info.user_id,
            error_type="rate_limit_error", message="Rate limit exceeded",
            severity=ErrorSeverity.LOW, context=limit_info, recoverable=True
        )
    
    def _log_error(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo] = None):
        """Log error with appropriate level and context."""
        log_context = self._build_error_log_context(error)
        if conn_info:
            log_context.update(self._build_connection_log_context(conn_info))
        log_message = f"WebSocket error: {error.message}"
        self._log_with_appropriate_level(error.severity, log_message, log_context)

    def _build_error_log_context(self, error: WebSocketErrorInfo) -> Dict[str, Any]:
        """Build base log context for error."""
        base_context = self._get_error_base_context(error)
        recovery_context = self._get_error_recovery_context(error)
        return {**base_context, **recovery_context}

    def _get_error_base_context(self, error: WebSocketErrorInfo) -> Dict[str, Any]:
        """Get base error context."""
        return {"error_id": error.error_id, "error_type": error.error_type,
               "severity": error.severity.value, "user_id": error.user_id}

    def _get_error_recovery_context(self, error: WebSocketErrorInfo) -> Dict[str, Any]:
        """Get error recovery context."""
        return {"connection_id": error.connection_id, "recoverable": error.recoverable,
               "retry_count": error.retry_count}

    def _build_connection_log_context(self, conn_info: ConnectionInfo) -> Dict[str, Any]:
        """Build connection-specific log context."""
        from datetime import datetime, timezone
        return {
            "message_count": conn_info.message_count, "error_count": conn_info.error_count,
            "connection_duration": (datetime.now(timezone.utc) - conn_info.connected_at).total_seconds()
        }

    def _log_with_appropriate_level(self, severity: ErrorSeverity, message: str, context: Dict[str, Any]) -> None:
        """Log message with severity-appropriate level."""
        log_methods = self._get_log_methods()
        log_method = log_methods.get(severity, logger.info)
        log_method(message, extra=context)

    def _get_log_methods(self) -> Dict[ErrorSeverity, Callable]:
        """Get logging methods mapped to severity levels."""
        return {
            ErrorSeverity.CRITICAL: logger.critical,
            ErrorSeverity.HIGH: logger.error,
            ErrorSeverity.MEDIUM: logger.warning
        }
    
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
        if recovery_key not in self.recovery_timestamps:
            return True
        return self._evaluate_rate_limit_timing(recovery_key, current_time)

    def _evaluate_rate_limit_timing(self, recovery_key: str, current_time: float) -> bool:
        """Evaluate rate limit timing for recovery key."""
        last_attempt = self.recovery_timestamps[recovery_key]
        backoff_delay = self.recovery_backoff.get(recovery_key, 1.0)
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
        self.recovery_timestamps[recovery_key] = current_time
        current_backoff = self.recovery_backoff.get(recovery_key, 1.0)
        next_backoff = min(current_backoff * 2, 60.0)
        self.recovery_backoff[recovery_key] = next_backoff

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
        recovery_handlers = self._get_recovery_handlers()
        handler = recovery_handlers.get(error.error_type)
        if handler:
            return await handler(error, conn_info)
        return self._handle_unknown_error_recovery(error, recovery_key)

    def _get_recovery_handlers(self) -> Dict[str, Callable]:
        """Get dictionary of recovery handlers."""
        return {
            "connection_error": self._recover_connection_error,
            "rate_limit_error": self._recover_rate_limit_error,
            "heartbeat_error": self._recover_heartbeat_error
        }

    def _handle_unknown_error_recovery(self, error: WebSocketErrorInfo, recovery_key: str) -> bool:
        """Handle recovery for unknown error types."""
        current_backoff = self.recovery_backoff.get(recovery_key, 1.0)
        logger.info(f"Generic recovery attempted for error {error.error_id} after {current_backoff:.1f}s backoff")
        return False
    
    async def _recover_connection_error(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Attempt to recover from a connection error."""
        if not conn_info:
            return False
        # For connection errors, we typically can't recover the same connection
        logger.info(f"Connection error recovery: marking connection {conn_info.connection_id} for cleanup")
        return False  # Connection needs to be cleaned up
    
    async def _recover_rate_limit_error(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Attempt to recover from a rate limit error."""
        # For rate limit errors, recovery means waiting and then allowing normal operation
        logger.info(f"Rate limit error recovery: connection {error.connection_id} can resume after window")
        return True
    
    async def _recover_heartbeat_error(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo] = None) -> bool:
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
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        basic_stats = self._get_basic_error_stats()
        recovery_rate = self._stats["recovered_errors"] / max(1, self._stats["total_errors"])
        top_patterns = dict(sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True)[:10])
        return {**basic_stats, "recovery_rate": recovery_rate, "top_error_patterns": top_patterns}

    def _get_basic_error_stats(self) -> Dict[str, Any]:
        """Get basic error statistics."""
        return {
            "total_errors": self._stats["total_errors"], "critical_errors": self._stats["critical_errors"],
            "recovered_errors": self._stats["recovered_errors"], "connection_errors": self._stats["connection_errors"],
            "validation_errors": self._stats["validation_errors"], "rate_limit_errors": self._stats["rate_limit_errors"]
        }
    
    def get_connection_error_count(self, connection_id: str) -> int:
        """Get error count for a specific connection."""
        return self.connection_errors.get(connection_id, 0)
    
    def is_connection_problematic(self, connection_id: str, threshold: int = 5) -> bool:
        """Check if a connection has too many errors."""
        return self.get_connection_error_count(connection_id) >= threshold
    
    def cleanup_old_errors(self, max_age_hours: int = 24):
        """Clean up old error records."""
        cutoff_time = self._calculate_cutoff_time(max_age_hours)
        errors_removed = self._cleanup_old_error_records(cutoff_time)
        recovery_keys_removed = self._cleanup_old_recovery_tracking(cutoff_time)
        self._log_cleanup_results(errors_removed, recovery_keys_removed)

    def _calculate_cutoff_time(self, max_age_hours: int) -> float:
        """Calculate cutoff timestamp for cleanup."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)

    def _cleanup_old_error_records(self, cutoff_time: float) -> List[str]:
        """Clean up old error records and return removed error IDs."""
        errors_to_remove = self._identify_old_errors(cutoff_time)
        self._remove_old_errors(errors_to_remove)
        return errors_to_remove

    def _identify_old_errors(self, cutoff_time: float) -> List[str]:
        """Identify old error records for removal."""
        return [
            error_id for error_id, error in self.error_history.items()
            if error.timestamp.timestamp() < cutoff_time
        ]

    def _remove_old_errors(self, error_ids: List[str]) -> None:
        """Remove old error records from history."""
        for error_id in error_ids:
            del self.error_history[error_id]

    def _cleanup_old_recovery_tracking(self, cutoff_time: float) -> List[str]:
        """Clean up old recovery tracking and return removed keys."""
        recovery_keys_to_remove = self._find_old_recovery_keys(cutoff_time)
        self._remove_recovery_keys(recovery_keys_to_remove)
        return recovery_keys_to_remove

    def _find_old_recovery_keys(self, cutoff_time: float) -> List[str]:
        """Find old recovery keys for removal."""
        return [
            key for key, timestamp in self.recovery_timestamps.items()
            if timestamp < cutoff_time
        ]

    def _remove_recovery_keys(self, keys_to_remove: List[str]) -> None:
        """Remove recovery keys from tracking structures."""
        for key in keys_to_remove:
            del self.recovery_timestamps[key]
            if key in self.recovery_backoff:
                del self.recovery_backoff[key]

    def _log_cleanup_results(self, errors_removed: List[str], recovery_keys_removed: List[str]) -> None:
        """Log cleanup operation results."""
        if errors_removed or recovery_keys_removed:
            logger.info(
                f"Cleaned up {len(errors_removed)} old error records and "
                f"{len(recovery_keys_removed)} recovery trackers"
            )


# Default error handler instance
default_error_handler = WebSocketErrorHandler()

# Alias for backward compatibility
ErrorHandler = WebSocketErrorHandler
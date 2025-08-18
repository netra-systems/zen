"""Core WebSocket error handling functionality.

Main entry point for WebSocket error handling system.
"""

from typing import Dict, Any, Optional

from app.websocket.connection import ConnectionInfo
from app.websocket.error_types import WebSocketErrorInfo, ErrorSeverity
from app.websocket.error_handler_config import ErrorHandlerConfig
from app.websocket.error_handler_recovery import ErrorHandlerRecovery
from app.websocket.error_handler_logging import ErrorHandlerLogger
from app.websocket.error_handler_cleanup import ErrorHandlerCleanup


class WebSocketErrorHandler:
    """Handles WebSocket errors with logging, tracking, and recovery."""
    
    def __init__(self):
        """Initialize error handler."""
        self.config = ErrorHandlerConfig()
        self.recovery = ErrorHandlerRecovery(self.config)
        self.logger = ErrorHandlerLogger(self.config)
        self.cleanup = ErrorHandlerCleanup(self.config)

    async def handle_error(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo] = None) -> bool:
        """Handle a WebSocket error with appropriate logging and recovery."""
        self._store_and_track_error(error, conn_info)
        self.logger.log_error(error, conn_info)
        return await self.recovery.attempt_error_recovery(error, conn_info)

    def _store_and_track_error(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo]) -> None:
        """Store error and update tracking information."""
        self.config.error_history[error.error_id] = error
        self.config.update_error_statistics(error.severity)
        self._update_connection_tracking(error, conn_info)
        self.config.track_error_patterns(error.error_type, error.message)

    def _update_connection_tracking(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo]) -> None:
        """Update connection-specific error tracking."""
        if conn_info:
            error.connection_id = conn_info.connection_id
            error.user_id = conn_info.user_id
            conn_info.error_count += 1
            self.config.update_connection_tracking(conn_info.connection_id, conn_info.user_id)

    async def handle_connection_error(self, conn_info: ConnectionInfo, error_message: str, 
                                    error_type: str = "connection_error", 
                                    severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> WebSocketErrorInfo:
        """Handle a connection-specific error."""
        error = self._create_connection_error_info(conn_info, error_message, error_type, severity)
        self.config.increment_stat("connection_errors")
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
        self.config.increment_stat("validation_errors")
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
        self.config.increment_stat("rate_limit_errors")
        await self.handle_error(error, conn_info)
        return error

    def _create_rate_limit_error_info(self, conn_info: ConnectionInfo, limit_info: Dict[str, Any]) -> WebSocketErrorInfo:
        """Create WebSocketErrorInfo for rate limit error."""
        return WebSocketErrorInfo(
            connection_id=conn_info.connection_id, user_id=conn_info.user_id,
            error_type="rate_limit_error", message="Rate limit exceeded",
            severity=ErrorSeverity.LOW, context=limit_info, recoverable=True
        )

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        basic_stats = self._get_basic_error_stats()
        recovery_rate = self.config.stats["recovered_errors"] / max(1, self.config.stats["total_errors"])
        top_patterns = dict(sorted(self.config.error_patterns.items(), key=lambda x: x[1], reverse=True)[:10])
        return {**basic_stats, "recovery_rate": recovery_rate, "top_error_patterns": top_patterns}

    def _get_basic_error_stats(self) -> Dict[str, Any]:
        """Get basic error statistics."""
        stats = self.config.stats
        return {
            "total_errors": stats["total_errors"], "critical_errors": stats["critical_errors"],
            "recovered_errors": stats["recovered_errors"], "connection_errors": stats["connection_errors"],
            "validation_errors": stats["validation_errors"], "rate_limit_errors": stats["rate_limit_errors"]
        }

    def get_connection_error_count(self, connection_id: str) -> int:
        """Get error count for a specific connection."""
        return self.config.connection_errors.get(connection_id, 0)

    def is_connection_problematic(self, connection_id: str, threshold: int = 5) -> bool:
        """Check if a connection has too many errors."""
        return self.get_connection_error_count(connection_id) >= threshold

    def cleanup_old_errors(self, max_age_hours: int = 24):
        """Clean up old error records."""
        self.cleanup.cleanup_old_errors(max_age_hours)


# Default error handler instance
default_error_handler = WebSocketErrorHandler()

# Alias for backward compatibility
ErrorHandler = WebSocketErrorHandler
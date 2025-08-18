"""WebSocket Error Handler Logging System.

Handles error logging and context building.
"""

from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone

from app.logging_config import central_logger
from app.websocket.connection import ConnectionInfo
from app.websocket.error_types import WebSocketErrorInfo, ErrorSeverity
from app.websocket.error_handler_config import ErrorHandlerConfig

logger = central_logger.get_logger(__name__)


class ErrorHandlerLogger:
    """Handles error logging with appropriate context."""
    
    def __init__(self, config: ErrorHandlerConfig):
        self.config = config

    def log_error(self, error: WebSocketErrorInfo, conn_info: Optional[ConnectionInfo] = None):
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
        return {
            "message_count": conn_info.message_count, "error_count": conn_info.error_count,
            "connection_duration": (datetime.now(timezone.utc) - conn_info.connected_at).total_seconds()
        }

    def _log_with_appropriate_level(self, severity: ErrorSeverity, message: str, context: Dict[str, Any]) -> None:
        """Log message with severity-appropriate level."""
        log_methods = self.config.get_log_methods()
        log_method = log_methods.get(severity, logger.info)
        log_method(message, extra=context)
"""WebSocket Error Handler Configuration.

Configuration and initialization for error handling system.
"""

from typing import Dict, Any, Callable, Optional
from app.logging_config import central_logger
from app.websocket.error_types import ErrorSeverity

logger = central_logger.get_logger(__name__)


class ErrorHandlerConfig:
    """Configuration container for error handler."""
    
    def __init__(self):
        self.error_history: Dict[str, Any] = {}
        self.error_patterns: Dict[str, int] = {}
        self.connection_errors: Dict[str, int] = {}
        self.recovery_timestamps: Dict[str, float] = {}
        self.recovery_backoff: Dict[str, float] = {}
        self.stats = self._initialize_stats()

    def _initialize_stats(self) -> Dict[str, int]:
        """Initialize error statistics dictionary."""
        return {
            "total_errors": 0, "critical_errors": 0, "recovered_errors": 0,
            "connection_errors": 0, "validation_errors": 0, "rate_limit_errors": 0
        }

    def get_log_methods(self) -> Dict[ErrorSeverity, Callable]:
        """Get logging methods mapped to severity levels."""
        return {
            ErrorSeverity.CRITICAL: logger.critical,
            ErrorSeverity.HIGH: logger.error,
            ErrorSeverity.MEDIUM: logger.warning
        }

    def get_recovery_handlers(self) -> Dict[str, Callable]:
        """Get dictionary of recovery handlers."""
        from app.websocket.error_handler_recovery import ErrorHandlerRecovery
        recovery = ErrorHandlerRecovery(self)
        return {
            "connection_error": recovery.recover_connection_error,
            "rate_limit_error": recovery.recover_rate_limit_error,
            "heartbeat_error": recovery.recover_heartbeat_error
        }

    def update_error_statistics(self, error_severity: ErrorSeverity) -> None:
        """Update error statistics."""
        self.stats["total_errors"] += 1
        if error_severity == ErrorSeverity.CRITICAL:
            self.stats["critical_errors"] += 1

    def update_connection_tracking(self, connection_id: str, user_id: Optional[str] = None) -> None:
        """Update connection-specific error tracking."""
        if connection_id:
            self.connection_errors[connection_id] = self.connection_errors.get(connection_id, 0) + 1

    def track_error_patterns(self, error_type: str, message: str) -> None:
        """Track error patterns for analysis."""
        error_pattern = f"{error_type}:{message[:50]}"
        self.error_patterns[error_pattern] = self.error_patterns.get(error_pattern, 0) + 1

    def update_recovery_stats(self, recovered: bool) -> None:
        """Update recovery statistics."""
        if recovered:
            self.stats["recovered_errors"] += 1

    def increment_stat(self, stat_name: str) -> None:
        """Increment a specific statistic."""
        if stat_name in self.stats:
            self.stats[stat_name] += 1
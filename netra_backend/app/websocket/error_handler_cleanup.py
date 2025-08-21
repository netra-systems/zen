"""WebSocket Error Handler Cleanup System.

Handles cleanup of old error records and recovery tracking.
"""

from datetime import datetime, timezone
from typing import List

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket.error_handler_config import ErrorHandlerConfig

logger = central_logger.get_logger(__name__)


class ErrorHandlerCleanup:
    """Handles cleanup of old error records."""
    
    def __init__(self, config: ErrorHandlerConfig):
        self.config = config

    def cleanup_old_errors(self, max_age_hours: int = 24):
        """Clean up old error records."""
        cutoff_time = self._calculate_cutoff_time(max_age_hours)
        errors_removed = self._cleanup_old_error_records(cutoff_time)
        recovery_keys_removed = self._cleanup_old_recovery_tracking(cutoff_time)
        self._log_cleanup_results(errors_removed, recovery_keys_removed)

    def _calculate_cutoff_time(self, max_age_hours: int) -> float:
        """Calculate cutoff timestamp for cleanup."""
        return datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)

    def _cleanup_old_error_records(self, cutoff_time: float) -> List[str]:
        """Clean up old error records and return removed error IDs."""
        errors_to_remove = self._identify_old_errors(cutoff_time)
        self._remove_old_errors(errors_to_remove)
        return errors_to_remove

    def _identify_old_errors(self, cutoff_time: float) -> List[str]:
        """Identify old error records for removal."""
        return [
            error_id for error_id, error in self.config.error_history.items()
            if error.timestamp.timestamp() < cutoff_time
        ]

    def _remove_old_errors(self, error_ids: List[str]) -> None:
        """Remove old error records from history."""
        for error_id in error_ids:
            del self.config.error_history[error_id]

    def _cleanup_old_recovery_tracking(self, cutoff_time: float) -> List[str]:
        """Clean up old recovery tracking and return removed keys."""
        recovery_keys_to_remove = self._find_old_recovery_keys(cutoff_time)
        self._remove_recovery_keys(recovery_keys_to_remove)
        return recovery_keys_to_remove

    def _find_old_recovery_keys(self, cutoff_time: float) -> List[str]:
        """Find old recovery keys for removal."""
        return [
            key for key, timestamp in self.config.recovery_timestamps.items()
            if timestamp < cutoff_time
        ]

    def _remove_recovery_keys(self, keys_to_remove: List[str]) -> None:
        """Remove recovery keys from tracking structures."""
        for key in keys_to_remove:
            del self.config.recovery_timestamps[key]
            if key in self.config.recovery_backoff:
                del self.config.recovery_backoff[key]

    def _log_cleanup_results(self, errors_removed: List[str], recovery_keys_removed: List[str]) -> None:
        """Log cleanup operation results."""
        if errors_removed or recovery_keys_removed:
            logger.info(
                f"Cleaned up {len(errors_removed)} old error records and "
                f"{len(recovery_keys_removed)} recovery trackers"
            )
"""Reconnection status and metrics reporting functionality."""

from datetime import datetime
from typing import Any, Dict, List

from netra_backend.app.reconnection_types import ReconnectionAttempt, ReconnectionState


class ReconnectionStatusReporter:
    """Handles status reporting for reconnection manager."""
    
    def __init__(self, manager):
        self.manager = manager
    
    def get_status(self) -> Dict[str, Any]:
        """Get current reconnection status."""
        base_status = self._get_base_status()
        timestamp_info = self._get_timestamp_info()
        delay_info = self._get_delay_info()
        return {**base_status, **timestamp_info, **delay_info}

    def _get_base_status(self) -> Dict[str, Any]:
        """Get base status information."""
        connection_info = self._get_connection_info()
        attempt_info = self._get_attempt_info()
        return {**connection_info, **attempt_info}

    def _get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            "connection_id": self.manager.connection_id,
            "state": self.manager.state.value,
            "permanent_failure": self.manager._permanent_failure,
            "reconnection_enabled": self.manager.config.enabled
        }

    def _get_attempt_info(self) -> Dict[str, Any]:
        """Get attempt information."""
        return {
            "current_attempt": self.manager.current_attempt,
            "max_attempts": self.manager.config.max_attempts
        }

    def _get_timestamp_info(self) -> Dict[str, Any]:
        """Get timestamp information for status."""
        return {
            "last_disconnect_time": self.manager.last_disconnect_time.isoformat() if self.manager.last_disconnect_time else None,
            "last_successful_connect_time": self.manager.last_successful_connect_time.isoformat() if self.manager.last_successful_connect_time else None
        }

    def _get_delay_info(self) -> Dict[str, Any]:
        """Get delay information for status."""
        delay_ms = None
        if self.manager.state == ReconnectionState.RECONNECTING:
            delay_ms = self.manager._calculate_backoff_delay()
        return {"next_attempt_delay_ms": delay_ms}

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive reconnection metrics."""
        return {
            "metrics": self.manager.metrics.__dict__,
            "config": self.manager.config.__dict__,
            "recent_attempts": self._format_recent_attempts(),
            "status": self.get_status()
        }

    def _format_recent_attempts(self) -> List[Dict[str, Any]]:
        """Format recent attempts for metrics."""
        recent_attempts = self.manager.attempt_history[-10:]  # Last 10 attempts
        return [self._format_single_attempt(attempt) for attempt in recent_attempts]

    def _format_single_attempt(self, attempt: ReconnectionAttempt) -> Dict[str, Any]:
        """Format single attempt for metrics."""
        basic_info = self._get_attempt_basic_info(attempt)
        result_info = self._get_attempt_result_info(attempt)
        return {**basic_info, **result_info}

    def _get_attempt_basic_info(self, attempt: ReconnectionAttempt) -> Dict[str, Any]:
        """Get basic attempt information."""
        return {
            "attempt_number": attempt.attempt_number,
            "timestamp": attempt.timestamp.isoformat(),
            "delay_ms": attempt.delay_ms
        }

    def _get_attempt_result_info(self, attempt: ReconnectionAttempt) -> Dict[str, Any]:
        """Get attempt result information."""
        return {
            "success": attempt.success,
            "duration_ms": attempt.duration_ms,
            "error_message": attempt.error_message
        }
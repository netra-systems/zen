"""Agent error handling and classification functionality.

This module provides error recording, classification, and logging capabilities.
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from app.logging_config import central_logger
from netra_backend.app.error_codes import ErrorSeverity
from netra_backend.app.agent_reliability_types import AgentError

logger = central_logger.get_logger(__name__)


class AgentErrorHandler:
    """Handler for agent error recording and classification."""
    
    def __init__(self, max_error_history: int = 50):
        self.error_history: List[AgentError] = []
        self.max_error_history = max_error_history

    def create_error_record(
        self, operation_name: str, error: Exception, context: Optional[Dict[str, Any]], agent_name: str
    ) -> AgentError:
        """Create an error record for failed operation."""
        error_attrs = self._build_error_attributes(operation_name, error, context, agent_name)
        return AgentError(**error_attrs)

    def _build_error_attributes(self, operation_name: str, error: Exception, context: Optional[Dict[str, Any]], agent_name: str) -> Dict[str, Any]:
        """Build error attributes dictionary for AgentError creation."""
        base_attrs = self._get_basic_error_attributes(operation_name, error, agent_name)
        timing_attrs = self._get_error_timing_attributes(error)
        return {**base_attrs, **timing_attrs, 'context': context or {}}

    def _get_basic_error_attributes(self, operation_name: str, error: Exception, agent_name: str) -> Dict[str, Any]:
        """Get basic error attributes."""
        return {
            'error_id': f"{int(time.time() * 1000)}_{len(self.error_history)}",
            'agent_name': agent_name,
            'operation': operation_name,
            'error_type': type(error).__name__,
            'message': str(error)
        }

    def _get_error_timing_attributes(self, error: Exception) -> Dict[str, Any]:
        """Get error timing and severity attributes."""
        return {
            'timestamp': datetime.now(timezone.utc),
            'severity': self.classify_error_severity(error)
        }

    def add_error_to_history(self, error_record: AgentError) -> None:
        """Add error record to history with size management."""
        self.error_history.append(error_record)
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]

    def classify_error_severity(self, error: Exception) -> ErrorSeverity:
        """Classify error severity based on error type."""
        error_type = type(error).__name__
        critical_errors = self._get_critical_error_types()
        high_errors = self._get_high_error_types()
        medium_errors = self._get_medium_error_types()
        return self._determine_severity_level(error_type, critical_errors, high_errors, medium_errors)

    def _get_critical_error_types(self) -> List[str]:
        """Get list of critical error types."""
        return [
            "SystemExit", "KeyboardInterrupt", "MemoryError",
            "OutOfMemoryError", "RecursionError"
        ]

    def _get_high_error_types(self) -> List[str]:
        """Get list of high severity error types."""
        return [
            "ConnectionError", "TimeoutError", "DatabaseError",
            "AuthenticationError", "PermissionError"
        ]

    def _get_medium_error_types(self) -> List[str]:
        """Get list of medium severity error types."""
        return [
            "HTTPError", "RequestException", "ValidationError",
            "ConfigurationError", "ServiceUnavailableError"
        ]

    def _determine_severity_level(
        self, error_type: str, critical: List[str], high: List[str], medium: List[str]
    ) -> ErrorSeverity:
        """Determine severity level based on error type."""
        severity_map = self._build_severity_map(critical, high, medium)
        return severity_map.get(error_type, ErrorSeverity.LOW)
    
    def _build_severity_map(self, critical: List[str], high: List[str], medium: List[str]) -> Dict[str, ErrorSeverity]:
        """Build mapping of error types to severity levels."""
        severity_map = {}
        for error_type in critical:
            severity_map[error_type] = ErrorSeverity.CRITICAL
        for error_type in high:
            severity_map[error_type] = ErrorSeverity.HIGH
        for error_type in medium:
            severity_map[error_type] = ErrorSeverity.MEDIUM
        return severity_map

    def log_error(self, error_record: AgentError) -> None:
        """Log error with appropriate level."""
        log_message = self._format_error_message(error_record)
        log_context = self._create_log_context(error_record)
        self._write_log_with_severity(error_record.severity, log_message, log_context)

    def _format_error_message(self, error_record: AgentError) -> str:
        """Format error message for logging."""
        return (
            f"Agent {error_record.agent_name} operation {error_record.operation} "
            f"failed: {error_record.message}"
        )

    def _create_log_context(self, error_record: AgentError) -> Dict[str, Any]:
        """Create log context from error record."""
        return {
            "error_id": error_record.error_id,
            "agent_name": error_record.agent_name,
            "operation": error_record.operation,
            "error_type": error_record.error_type,
            "severity": error_record.severity.value,
            "context": error_record.context
        }

    def _write_log_with_severity(
        self, severity: ErrorSeverity, message: str, context: Dict[str, Any]
    ) -> None:
        """Write log with appropriate severity level."""
        log_methods = self._get_severity_log_methods()
        log_method = log_methods.get(severity, logger.info)
        log_method(message, extra=context)
    
    def _get_severity_log_methods(self) -> Dict[ErrorSeverity, callable]:
        """Get mapping of severity levels to log methods."""
        return {
            ErrorSeverity.CRITICAL: logger.critical,
            ErrorSeverity.HIGH: logger.error,
            ErrorSeverity.MEDIUM: logger.warning,
            ErrorSeverity.LOW: logger.info
        }

    async def record_failed_operation(
        self,
        operation_name: str,
        error: Exception,
        execution_time: float,
        context: Optional[Dict[str, Any]],
        agent_name: str
    ) -> None:
        """Record a failed operation for monitoring."""
        error_record = self.create_error_record(operation_name, error, context, agent_name)
        self.add_error_to_history(error_record)
        self.log_error(error_record)
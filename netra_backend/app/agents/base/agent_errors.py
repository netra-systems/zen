"""Agent-specific error types.

Business Value: Structured error handling enables precise error tracking and recovery.
"""

from typing import Optional, Dict, Any
from netra_backend.app.core.exceptions_agent import AgentExecutionError as CoreAgentExecutionError


class AgentExecutionError(CoreAgentExecutionError):
    """Enhanced agent execution error with context."""
    
    def __init__(self, 
                 message: str,
                 context: Optional[Dict[str, Any]] = None,
                 is_retryable: bool = False,
                 recovery_suggestions: Optional[list] = None):
        super().__init__(message)
        self._initialize_error_properties(context, is_retryable, recovery_suggestions)
    
    def _initialize_error_properties(self, context: Optional[Dict[str, Any]], 
                                   is_retryable: bool, recovery_suggestions: Optional[list]) -> None:
        """Initialize error properties."""
        self.context = context or {}
        self.is_retryable = is_retryable
        self.recovery_suggestions = recovery_suggestions or []


class ValidationError(AgentExecutionError):
    """Error during input validation."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, is_retryable=False)
        self.field = field


class ExternalServiceError(AgentExecutionError):
    """Error from external service calls."""
    
    def __init__(self, message: str, service: str, status_code: Optional[int] = None):
        super().__init__(message, is_retryable=True)
        self._initialize_service_error_properties(service, status_code)
    
    def _initialize_service_error_properties(self, service: str, status_code: Optional[int]) -> None:
        """Initialize service error specific properties."""
        self.service = service
        self.status_code = status_code
        self.recovery_suggestions = self._get_default_recovery_suggestions()
    
    def _get_default_recovery_suggestions(self) -> list:
        """Get default recovery suggestions for service errors."""
        return [
            "Check service availability",
            "Verify authentication credentials",
            "Retry after delay"
        ]


class DatabaseError(AgentExecutionError):
    """Database operation error."""
    
    def __init__(self, message: str, table: Optional[str] = None):
        super().__init__(message, is_retryable=True)
        self.table = table
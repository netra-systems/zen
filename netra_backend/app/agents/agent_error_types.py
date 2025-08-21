"""Agent Error Types Module.

Defines custom error types for agent operations.
Includes validation, network, and other agent-specific errors.
"""

from typing import Optional

from app.core.error_codes import ErrorSeverity
from app.schemas.core_enums import ErrorCategory
from app.schemas.shared_types import ErrorContext
from app.core.exceptions_agent import AgentError


class AgentValidationError(AgentError):
    """Error for agent input validation failures."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message, 
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.VALIDATION,
            context=context,
            recoverable=False
        )


class NetworkError(AgentError):
    """Error for network-related failures."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            context=context,
            recoverable=True
        )
"""Agent Error Types Module.

Defines custom error types for agent operations.
Includes validation, network, and other agent-specific errors.
"""

from typing import Optional

from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.core.exceptions_agent import AgentError
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.schemas.shared_types import ErrorContext


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
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
    
    def __init__(self, message: str, field_name: str = None, context: Optional[ErrorContext] = None):
        self.field_name = field_name
        super().__init__(
            message, 
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.VALIDATION,
            context=context
        )


class NetworkError(AgentError):
    """Error for network-related failures."""
    
    def __init__(self, message: str, endpoint: str = None, context: Optional[ErrorContext] = None):
        self.endpoint = endpoint
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            context=context
        )


class AgentDatabaseError(AgentError):
    """Error for database-related failures in agent operations."""
    
    def __init__(self, message: str, query: str = None, context: Optional[ErrorContext] = None):
        self.query = query
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATABASE,
            context=context
        )


# Alias for backward compatibility with tests
DatabaseError = AgentDatabaseError
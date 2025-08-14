"""Refactored exceptions module - compliant with 300-line/8-line limits.

This module re-exports all exception classes from the modular files.
"""

# Re-export error codes and severity
from app.core.error_codes import ErrorCode, ErrorSeverity

# Re-export base classes
from app.core.exceptions_base import ErrorDetails, NetraException

# Re-export configuration exceptions
from app.core.exceptions_config import ConfigurationError, ValidationError

# Re-export authentication exceptions
from app.core.exceptions_auth import (
    AuthenticationError,
    AuthorizationError,
    TokenExpiredError,
    TokenInvalidError
)

# Re-export database exceptions
from app.core.exceptions_database import (
    DatabaseError,
    DatabaseConnectionError,
    RecordNotFoundError,
    RecordAlreadyExistsError,
    DatabaseConstraintError
)

# Re-export service exceptions
from app.core.exceptions_service import (
    ServiceError,
    ServiceUnavailableError,
    ServiceTimeoutError,
    ExternalServiceError,
    AgentExecutionError,
    AgentTimeoutError,
    LLMRequestError,
    LLMRateLimitError
)

# Re-export WebSocket exceptions
from app.core.exceptions_websocket import (
    WebSocketError,
    WebSocketConnectionError,
    WebSocketMessageError,
    WebSocketAuthenticationError
)

# Re-export file exceptions
from app.core.exceptions_file import (
    FileError,
    FileNotFoundError,
    FileAccessDeniedError,
    DataParsingError,
    DataValidationError
)

# Export all symbols
__all__ = [
    # Error codes
    'ErrorCode',
    'ErrorSeverity',
    'ErrorDetails',
    
    # Base
    'NetraException',
    
    # Configuration
    'ConfigurationError',
    'ValidationError',
    
    # Authentication
    'AuthenticationError',
    'AuthorizationError',
    'TokenExpiredError',
    'TokenInvalidError',
    
    # Database
    'DatabaseError',
    'DatabaseConnectionError',
    'RecordNotFoundError',
    'RecordAlreadyExistsError',
    'DatabaseConstraintError',
    
    # Service
    'ServiceError',
    'ServiceUnavailableError',
    'ServiceTimeoutError',
    'ExternalServiceError',
    'AgentExecutionError',
    'AgentTimeoutError',
    'LLMRequestError',
    'LLMRateLimitError',
    
    # WebSocket
    'WebSocketError',
    'WebSocketConnectionError',
    'WebSocketMessageError',
    'WebSocketAuthenticationError',
    
    # File
    'FileError',
    'FileNotFoundError',
    'FileAccessDeniedError',
    'DataParsingError',
    'DataValidationError'
]
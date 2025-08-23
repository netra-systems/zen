"""DEPRECATED: Legacy exception compatibility layer.

This module is DEPRECATED and should not be used for new code.
All exception classes have been moved to focused modules:

- Base exceptions: app.core.exceptions_base
- Agent exceptions: app.core.exceptions_agent  
- Database exceptions: app.core.exceptions_database
- Service exceptions: app.core.exceptions_service
- Authentication exceptions: app.core.exceptions_auth
- Configuration exceptions: app.core.exceptions_config
- WebSocket exceptions: app.core.exceptions_websocket
- File exceptions: app.core.exceptions_file
- Error codes and severity: app.core.error_codes

This compatibility layer exists to support any remaining imports.
Please update imports to use the focused modules instead.

This file was originally 515 lines and has been successfully split into 
focused modules under 300 lines each, meeting architectural requirements.
"""

# Import all exception classes from their focused modules for backward compatibility
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.core.exceptions_agent import (
    AgentConfigurationError,
    AgentCoordinationError,
    AgentError,
    AgentExecutionError,
    AgentTimeoutError,
    LLMError,
    LLMRateLimitError,
    LLMRequestError,
)
from netra_backend.app.core.exceptions_auth import (
    AuthenticationError,
    AuthorizationError,
    NetraSecurityException,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    TokenTamperError,
)
from netra_backend.app.core.exceptions_base import ErrorDetails, NetraException
from netra_backend.app.core.exceptions_config import ConfigurationError, ValidationError
from netra_backend.app.core.exceptions_database import (
    DatabaseConnectionError,
    DatabaseError,
    RecordAlreadyExistsError,
    RecordNotFoundError,
)
from netra_backend.app.core.exceptions_database import (
    DatabaseConstraintError as ConstraintViolationError,
)
from netra_backend.app.core.exceptions_file import (
    DataParsingError,
    DataValidationError,
    FileAccessDeniedError,
    FileError,
    FileNotFoundError,
)
from netra_backend.app.core.exceptions_service import (
    ExternalServiceError,
    ProcessingError,
    ServiceError,
    ServiceTimeoutError,
)
from netra_backend.app.core.exceptions_websocket import (
    WebSocketAuthenticationError,
    WebSocketConnectionError,
    WebSocketError,
    WebSocketMessageError,
)

# Maintain compatibility with the old interface
__all__ = [
    # Core classes
    'ErrorCode', 'ErrorSeverity', 'ErrorDetails', 'NetraException',
    
    # Base exceptions
    'ValidationError', 'ConfigurationError',
    
    # Authentication
    'AuthenticationError', 'AuthorizationError', 'TokenExpiredError', 'TokenInvalidError',
    
    # Database
    'DatabaseError', 'DatabaseConnectionError', 'RecordNotFoundError', 
    'RecordAlreadyExistsError', 'ConstraintViolationError',
    
    # Service
    'ServiceError', 'ServiceTimeoutError', 'ExternalServiceError', 'ProcessingError',
    
    # Agent/LLM
    'AgentError', 'AgentExecutionError', 'AgentTimeoutError', 'LLMError',
    'LLMRequestError', 'LLMRateLimitError', 'AgentCoordinationError', 'AgentConfigurationError',
    
    # WebSocket
    'WebSocketError', 'WebSocketConnectionError', 'WebSocketMessageError', 'WebSocketAuthenticationError',
    
    # File/Data
    'FileError', 'FileNotFoundError', 'FileAccessDeniedError', 'DataParsingError', 'DataValidationError'
]
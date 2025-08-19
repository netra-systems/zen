"""Centralized error handling and recovery mechanisms for agents.

DEPRECATED: This module has been replaced by the consolidated error handlers
in app.core.error_handlers. This file now provides backward compatibility.
"""

# Import from consolidated error handlers for backward compatibility
from app.core.error_handlers import (
    AgentErrorHandler,
    global_agent_error_handler as global_error_handler
)

# Import from existing modular components for backward compatibility
from .agent_error_types import AgentValidationError, NetworkError
from .error_recovery_strategy import ErrorRecoveryStrategy
from .error_decorators import handle_agent_error

# Import external dependencies that were referenced
from app.core.exceptions_database import DatabaseError
from app.core.exceptions_websocket import WebSocketError
from app.core.error_codes import ErrorSeverity
from app.schemas.core_enums import ErrorCategory
from app.schemas.shared_types import ErrorContext
from app.core.exceptions_agent import AgentError

# Maintain the same interface for existing code
__all__ = [
    'AgentValidationError', 'NetworkError', 'DatabaseError', 'WebSocketError',
    'ErrorRecoveryStrategy', 'AgentErrorHandler', 'handle_agent_error', 
    'global_error_handler', 'ErrorSeverity', 'ErrorCategory', 'ErrorContext', 'AgentError'
]
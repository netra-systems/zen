"""Centralized error handling and recovery mechanisms for agents.

DEPRECATED: This module has been replaced by the consolidated error handlers
in app.core.error_handlers. This file now provides backward compatibility.
"""

# Import from consolidated error handlers for backward compatibility
from netra_backend.app.core.error_handlers import (
    AgentErrorHandler,
    global_agent_error_handler as global_error_handler
)

# Import from existing modular components for backward compatibility
from netra_backend.app.agents.agent_error_types import AgentValidationError, NetworkError
from netra_backend.app.agents.error_recovery_strategy import ErrorRecoveryStrategy
from netra_backend.app.agents.error_decorators import handle_agent_error

# Import external dependencies that were referenced
from netra_backend.app.core.exceptions_database import DatabaseError
from netra_backend.app.core.exceptions_websocket import WebSocketError
from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.core.exceptions_agent import AgentError

# Maintain the same interface for existing code
__all__ = [
    'AgentValidationError', 'NetworkError', 'DatabaseError', 'WebSocketError',
    'ErrorRecoveryStrategy', 'AgentErrorHandler', 'handle_agent_error', 
    'global_error_handler', 'ErrorSeverity', 'ErrorCategory', 'ErrorContext', 'AgentError'
]
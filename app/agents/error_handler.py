"""Centralized error handling and recovery mechanisms for agents.

Backwards compatibility interface for refactored error handling.
This module now delegates to the modular components.
"""

# Import from modular components for backwards compatibility
from .agent_error_types import AgentValidationError, NetworkError
from .error_recovery_strategy import ErrorRecoveryStrategy
from .agent_error_handler import AgentErrorHandler
from .error_decorators import handle_agent_error, global_error_handler

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
"""Consolidated error handlers package.

Provides unified error handling interfaces and implementations.
All error handlers follow consistent patterns and interfaces.
"""

# Base components
from netra_backend.app.core.error_handlers.base_error_handler import BaseErrorHandler
from netra_backend.app.core.error_handlers.error_classification import ErrorClassifier, ErrorClassification
from netra_backend.app.core.error_handlers.error_recovery import ErrorRecoveryStrategy, RecoveryCoordinator, RecoveryResult

# Agent-specific handlers
from netra_backend.app.core.error_handlers.agents.agent_error_handler import AgentErrorHandler
from netra_backend.app.core.error_handlers.agents.execution_error_handler import ExecutionErrorHandler

# API handlers
from netra_backend.app.core.error_handlers.api.api_error_handler import ApiErrorHandler
from netra_backend.app.core.error_handlers.api.fastapi_exception_handlers import (
    netra_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)

# Global instances for backward compatibility
from netra_backend.app.core.error_handlers.agents.agent_error_handler import global_agent_error_handler
from netra_backend.app.core.error_handlers.agents.execution_error_handler import global_execution_error_handler
from netra_backend.app.core.error_handlers.api.api_error_handler import api_error_handler, handle_exception, get_http_status_code

__all__ = [
    # Base components
    'BaseErrorHandler',
    'ErrorClassifier',
    'ErrorClassification',
    'ErrorRecoveryStrategy',
    'RecoveryCoordinator',
    'RecoveryResult',
    
    # Agent handlers
    'AgentErrorHandler',
    'ExecutionErrorHandler',
    
    # API handlers
    'ApiErrorHandler',
    'netra_exception_handler',
    'validation_exception_handler',
    'http_exception_handler',
    'general_exception_handler',
    
    # Global instances
    'global_agent_error_handler',
    'global_execution_error_handler',
    'api_error_handler',
    'handle_exception',
    'get_http_status_code'
]
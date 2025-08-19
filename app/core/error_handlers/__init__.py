"""Consolidated error handlers package.

Provides unified error handling interfaces and implementations.
All error handlers follow consistent patterns and interfaces.
"""

# Base components
from .base_error_handler import BaseErrorHandler
from .error_classification import ErrorClassifier, ErrorClassification
from .error_recovery import ErrorRecoveryStrategy, RecoveryCoordinator, RecoveryResult

# Agent-specific handlers
from .agents import AgentErrorHandler, ExecutionErrorHandler

# API handlers
from .api import (
    ApiErrorHandler,
    netra_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)

# Global instances for backward compatibility
from .agents.agent_error_handler import global_agent_error_handler
from .agents.execution_error_handler import global_execution_error_handler
from .api.api_error_handler import api_error_handler, handle_exception, get_http_status_code

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
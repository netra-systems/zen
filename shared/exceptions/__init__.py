"""
Shared exceptions module providing unified exception handling across all services.

This module eliminates duplicate exception handling patterns by providing
standardized exception classes, handlers, and utilities.
"""

from .unified_exception_handler import (
    # Exception classes
    NetraBaseException,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    DatabaseError,
    NetworkError,
    LLMProviderError,
    ConfigurationError,
    # Enums
    ErrorSeverity,
    ErrorCategory,
    # Handler classes
    UnifiedExceptionHandler,
    ExceptionContext,
    # Decorators and utilities
    handle_exceptions,
    safe_call,
    safe_async_call
)

__all__ = [
    # Exception classes
    'NetraBaseException',
    'AuthenticationError',
    'AuthorizationError', 
    'ValidationError',
    'DatabaseError',
    'NetworkError',
    'LLMProviderError',
    'ConfigurationError',
    # Enums
    'ErrorSeverity',
    'ErrorCategory',
    # Handler classes
    'UnifiedExceptionHandler',
    'ExceptionContext',
    # Decorators and utilities
    'handle_exceptions',
    'safe_call',
    'safe_async_call'
]
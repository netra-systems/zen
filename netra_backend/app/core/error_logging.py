"""Comprehensive error logging system with rich context and correlation.

This module provides a unified interface to the modular error logging system.
All core functionality has been split into focused modules for maintainability.
"""

# Import all core types and classes
from netra_backend.app.core.error_logging_types import (
    LogLevel,
    ErrorCategory,
    DetailedErrorContext,
    ErrorAggregation
)

from netra_backend.app.core.error_logging_context import (
    ErrorContextManager,
    RecoveryLogger,
    error_context_manager,
    recovery_logger
)

from netra_backend.app.core.error_logger_core import (
    ErrorLogger,
    error_logger
)

from netra_backend.app.core.error_report_generator import (
    ErrorReportGenerator,
    error_report_generator
)

from netra_backend.app.core.error_logging_helpers import (
    log_agent_error,
    log_database_error,
    log_api_error
)

# Export main interfaces for backward compatibility
__all__ = [
    # Core types
    'LogLevel',
    'ErrorCategory', 
    'DetailedErrorContext',
    'ErrorAggregation',
    
    # Core classes
    'ErrorLogger',
    'ErrorContextManager',
    'RecoveryLogger',
    'ErrorReportGenerator',
    
    # Global instances
    'error_logger',
    'error_context_manager',
    'recovery_logger',
    'error_report_generator',
    
    # Convenience functions
    'log_agent_error',
    'log_database_error', 
    'log_api_error'
]
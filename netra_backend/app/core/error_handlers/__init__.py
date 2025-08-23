"""Consolidated error handlers package.

Provides unified error handling interfaces and implementations.
All error handlers follow consistent patterns and interfaces.
"""

# Base components
# Agent-specific handlers
# Global instances for backward compatibility
from netra_backend.app.core.error_handlers.agents.agent_error_handler import (
    AgentErrorHandler,
    global_agent_error_handler,
)
from netra_backend.app.core.error_handlers.agents.execution_error_handler import (
    ExecutionErrorHandler,
    global_execution_error_handler,
)

# API handlers
from netra_backend.app.core.error_handlers.api.api_error_handler import (
    ApiErrorHandler,
    api_error_handler,
    get_http_status_code,
    handle_exception,
)
from netra_backend.app.core.error_handlers.api.fastapi_exception_handlers import (
    general_exception_handler,
    http_exception_handler,
    netra_exception_handler,
    validation_exception_handler,
)

# Route utility handlers
from netra_backend.app.routes.utils.error_handlers import (
    handle_access_denied_error,
    handle_auth_error,
    handle_circuit_breaker_error,
    handle_database_error,
    handle_job_error,
    handle_not_found_error,
    handle_service_error,
    handle_validation_error,
)
from netra_backend.app.core.error_handlers.base_error_handler import BaseErrorHandler
from netra_backend.app.core.error_handlers.error_classification import (
    ErrorClassification,
    ErrorClassifier,
)
from netra_backend.app.core.error_handlers.error_recovery import (
    ErrorRecoveryStrategy,
    RecoveryCoordinator,
    RecoveryResult,
)

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
    
    # Route utility handlers
    'handle_service_error',
    'handle_circuit_breaker_error',
    'handle_database_error',
    'handle_auth_error',
    'handle_not_found_error',
    'handle_access_denied_error',
    'handle_validation_error',
    'handle_job_error',
    
    # Global instances
    'global_agent_error_handler',
    'global_execution_error_handler',
    'api_error_handler',
    'handle_exception',
    'get_http_status_code'
]
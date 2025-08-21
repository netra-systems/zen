"""Convenience functions for common error logging use cases.

Provides simplified interfaces for logging agent, database, and API errors.
"""

from typing import Optional

from netra_backend.app.core.error_logger_core import error_logger
from netra_backend.app.core.error_logging_context import error_context_manager
from netra_backend.app.core.error_recovery import OperationType


def log_agent_error(
    agent_type: str,
    operation: str,
    error: Exception,
    user_id: Optional[str] = None,
    **kwargs
) -> str:
    """Log agent-specific error."""
    context = error_context_manager.create_context(
        error,
        agent_type=agent_type,
        component=f"{agent_type}_agent",
        operation_id=operation,
        user_id=user_id,
        tags=['agent', agent_type],
        **kwargs
    )
    return error_logger.log_error(error, context)


def log_database_error(
    table_name: str,
    operation: str,
    error: Exception,
    **kwargs
) -> str:
    """Log database-specific error."""
    operation_type = _determine_db_operation_type(operation)
    
    context = error_context_manager.create_context(
        error,
        component='database',
        operation_type=operation_type,
        metadata=_build_db_metadata(table_name, operation),
        tags=['database', operation.lower()],
        **kwargs
    )
    return error_logger.log_error(error, context)


def log_api_error(
    endpoint: str,
    method: str,
    error: Exception,
    status_code: Optional[int] = None,
    **kwargs
) -> str:
    """Log API-specific error."""
    context = error_context_manager.create_context(
        error,
        component='api',
        metadata=_build_api_metadata(endpoint, method, status_code),
        tags=['api', method.lower()],
        **kwargs
    )
    return error_logger.log_error(error, context)


def _determine_db_operation_type(operation: str) -> OperationType:
    """Determine database operation type."""
    write_operations = ['INSERT', 'UPDATE', 'DELETE']
    if operation in write_operations:
        return OperationType.DATABASE_WRITE
    return OperationType.DATABASE_READ


def _build_db_metadata(table_name: str, operation: str) -> dict:
    """Build database operation metadata."""
    return {
        'table_name': table_name, 
        'sql_operation': operation
    }


def _build_api_metadata(
    endpoint: str, 
    method: str, 
    status_code: Optional[int]
) -> dict:
    """Build API operation metadata."""
    metadata = {
        'endpoint': endpoint,
        'method': method
    }
    if status_code is not None:
        metadata['status_code'] = status_code
    return metadata
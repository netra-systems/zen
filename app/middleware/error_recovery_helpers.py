"""Helper functions for error recovery middleware.

Provides utility functions for error analysis, metadata extraction,
and severity determination for the error recovery system.
"""

import traceback
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import Request

from app.core.error_recovery import RecoveryContext, OperationType
from app.core.error_codes import ErrorSeverity
from app.core.exceptions_base import NetraException
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def get_operation_mapping() -> Dict[str, OperationType]:
    """Get request method to operation type mapping."""
    write_methods = ['POST', 'PUT', 'PATCH', 'DELETE']
    mapping = {method: OperationType.DATABASE_WRITE for method in write_methods}
    mapping['GET'] = OperationType.DATABASE_READ
    return mapping


def get_special_operation_type(path: str) -> Optional[OperationType]:
    """Get special operation type for specific paths."""
    path_mappings = _get_path_operation_mappings()
    for path_patterns, operation_type in path_mappings.items():
        if any(pattern in path for pattern in path_patterns):
            return operation_type
    return None


def _get_path_operation_mappings() -> Dict[tuple, OperationType]:
    """Get path pattern to operation type mappings."""
    return {
        ('/websocket', '/ws'): OperationType.WEBSOCKET_SEND,
        ('/llm', '/ai', '/agent'): OperationType.LLM_REQUEST,
        ('/api/external',): OperationType.EXTERNAL_API,
        ('/files', '/upload'): OperationType.FILE_OPERATION,
        ('/cache',): OperationType.CACHE_OPERATION
    }


def determine_operation_type(request: Request) -> OperationType:
    """Determine operation type from request."""
    path = request.url.path.lower()
    special_type = get_special_operation_type(path)
    if special_type:
        return special_type
    return get_operation_mapping().get(request.method, OperationType.DATABASE_READ)


def get_severity_mapping() -> Dict[str, ErrorSeverity]:
    """Get error type to severity mapping."""
    high_severity = ['ValidationError', 'PermissionError', 'ValueError', 'TypeError']
    medium_severity = ['ConnectionError', 'TimeoutError', 'HTTPException', 'KeyError', 'FileNotFoundError']
    mapping = {error: ErrorSeverity.HIGH for error in high_severity}
    mapping.update({error: ErrorSeverity.MEDIUM for error in medium_severity})
    mapping['MemoryError'] = ErrorSeverity.CRITICAL
    return mapping


def determine_severity(error: Exception) -> ErrorSeverity:
    """Determine error severity from exception type."""
    if isinstance(error, NetraException):
        return error.error_details.severity
    error_type = type(error).__name__
    return get_severity_mapping().get(error_type, ErrorSeverity.MEDIUM)


def extract_request_metadata(request: Request) -> Dict[str, Any]:
    """Extract metadata from request for recovery context."""
    metadata = get_base_metadata(request)
    add_user_metadata(metadata, request)
    add_request_id_metadata(metadata, request)
    return metadata


def get_base_metadata(request: Request) -> Dict[str, Any]:
    """Get base request metadata."""
    metadata = {
        'method': request.method, 'path': request.url.path,
        'query_params': dict(request.query_params), 'headers': dict(request.headers)
    }
    add_client_metadata(metadata, request)
    return metadata


def add_client_metadata(metadata: Dict[str, Any], request: Request) -> None:
    """Add client-specific metadata to base metadata."""
    metadata['client_host'] = request.client.host if request.client else None
    metadata['user_agent'] = request.headers.get('user-agent')
    metadata['content_type'] = request.headers.get('content-type')


def add_user_metadata(metadata: Dict[str, Any], request: Request) -> None:
    """Add user context to metadata if available."""
    if hasattr(request.state, 'user') and request.state.user:
        metadata['user_id'] = str(request.state.user.id)
        metadata['user_email'] = getattr(request.state.user, 'email', None)


def add_request_id_metadata(metadata: Dict[str, Any], request: Request) -> None:
    """Add request ID to metadata if available."""
    if hasattr(request.state, 'request_id'):
        metadata['request_id'] = request.state.request_id


def build_error_data(error: Exception, context: RecoveryContext, request: Request) -> Dict[str, Any]:
    """Build base error data dictionary."""
    base_data = get_error_base_data(error, context)
    request_data = get_error_request_data(request)
    base_data.update(request_data)
    return base_data


def get_error_base_data(error: Exception, context: RecoveryContext) -> Dict[str, Any]:
    """Get base error data from error and context."""
    return {
        'operation_id': context.operation_id, 'operation_type': context.operation_type.value,
        'severity': context.severity.value, 'retry_count': context.retry_count,
        'error_type': type(error).__name__, 'error_message': str(error),
        'elapsed_time_ms': context.elapsed_time.total_seconds() * 1000
    }


def get_error_request_data(request: Request) -> Dict[str, Any]:
    """Get error data from request."""
    return {
        'request_method': request.method, 'request_path': request.url.path,
        'client_ip': request.client.host if request.client else None,
        'user_agent': request.headers.get('user-agent')
    }


def enhance_error_data(error_data: dict, request: Request, context: RecoveryContext) -> None:
    """Enhance error data with additional context."""
    add_user_context_to_error_data(error_data, request)
    add_stack_trace_if_critical(error_data, context)


def add_user_context_to_error_data(error_data: Dict[str, Any], request: Request) -> None:
    """Add user context to error data if available."""
    if hasattr(request.state, 'user') and request.state.user:
        error_data['user_id'] = str(request.state.user.id)


def add_stack_trace_if_critical(error_data: Dict[str, Any], context: RecoveryContext) -> None:
    """Add stack trace for critical errors."""
    if context.severity == ErrorSeverity.CRITICAL:
        error_data['stack_trace'] = traceback.format_exc()


def log_by_severity(severity: ErrorSeverity, error_data: Dict[str, Any]) -> None:
    """Log error based on severity level."""
    log_methods = _get_severity_log_methods()
    log_method = log_methods.get(severity, logger.info)
    message = "Error in request processing"
    log_method(f"{severity.value.title()} {message.lower()}", **error_data)


def _get_severity_log_methods() -> Dict[ErrorSeverity, callable]:
    """Get severity to log method mappings."""
    return {
        ErrorSeverity.CRITICAL: logger.critical,
        ErrorSeverity.HIGH: logger.error,
        ErrorSeverity.MEDIUM: logger.warning
    }


def build_recovery_context(
    operation_id: str, operation_type: OperationType, error: Exception,
    severity: ErrorSeverity, attempt: int, max_attempts: int, metadata: Dict[str, Any]
) -> RecoveryContext:
    """Build recovery context with all parameters."""
    return RecoveryContext(
        operation_id=operation_id, operation_type=operation_type, error=error,
        severity=severity, retry_count=attempt, max_retries=max_attempts - 1, metadata=metadata
    )
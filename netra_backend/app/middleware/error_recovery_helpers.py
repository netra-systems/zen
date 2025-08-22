"""Helper functions for error recovery middleware.

Provides utility functions for error analysis, metadata extraction,
and severity determination for the error recovery system.
"""

import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Request

from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.core.error_recovery import OperationType, RecoveryContext
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.logging_config import central_logger

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
    return _build_all_path_mappings()

def _build_all_path_mappings() -> Dict[tuple, OperationType]:
    """Build all path operation mappings."""
    basic_mappings = _get_basic_path_mappings()
    advanced_mappings = _get_advanced_path_mappings()
    return {**basic_mappings, **advanced_mappings}

def _get_basic_path_mappings() -> Dict[tuple, OperationType]:
    """Get basic path operation mappings."""
    return {
        ('/websocket', '/ws'): OperationType.WEBSOCKET_SEND,
        ('/llm', '/ai', '/agent'): OperationType.LLM_REQUEST
    }

def _get_advanced_path_mappings() -> Dict[tuple, OperationType]:
    """Get advanced path operation mappings."""
    return {
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
    mapping = _build_high_severity_mapping()
    mapping.update(_build_medium_severity_mapping())
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
    metadata = _build_base_request_metadata(request)
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
    context_data = _extract_context_data(context)
    error_data = _extract_error_data(error)
    return {**context_data, **error_data}


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
    log_method = _get_log_method_for_severity(severity)
    message = _build_severity_log_message(severity)
    log_method(message, **error_data)


def _build_high_severity_mapping() -> Dict[str, ErrorSeverity]:
    """Build high severity error mapping."""
    high_severity = ['ValidationError', 'PermissionError', 'ValueError', 'TypeError']
    return {error: ErrorSeverity.HIGH for error in high_severity}

def _build_medium_severity_mapping() -> Dict[str, ErrorSeverity]:
    """Build medium severity error mapping."""
    medium_severity = ['ConnectionError', 'TimeoutError', 'HTTPException', 'KeyError', 'FileNotFoundError']
    return {error: ErrorSeverity.MEDIUM for error in medium_severity}

def _build_base_request_metadata(request: Request) -> Dict[str, Any]:
    """Build base request metadata dictionary."""
    return {
        'method': request.method, 'path': request.url.path,
        'query_params': dict(request.query_params), 'headers': dict(request.headers)
    }

def _extract_context_data(context: RecoveryContext) -> Dict[str, Any]:
    """Extract data from recovery context."""
    return {
        'operation_id': context.operation_id, 'operation_type': context.operation_type.value,
        'severity': context.severity.value, 'retry_count': context.retry_count,
        'elapsed_time_ms': context.elapsed_time.total_seconds() * 1000
    }

def _extract_error_data(error: Exception) -> Dict[str, Any]:
    """Extract data from exception."""
    return {'error_type': type(error).__name__, 'error_message': str(error)}

def _get_log_method_for_severity(severity: ErrorSeverity) -> callable:
    """Get log method for severity level."""
    log_methods = _get_severity_log_methods()
    return log_methods.get(severity, logger.info)

def _build_severity_log_message(severity: ErrorSeverity) -> str:
    """Build log message for severity level."""
    base_message = "Error in request processing"
    return f"{severity.value.title()} {base_message.lower()}"

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
    return _create_recovery_context(
        operation_id, operation_type, error, severity, attempt, max_attempts, metadata
    )

def _create_recovery_context(
    operation_id: str, operation_type: OperationType, error: Exception,
    severity: ErrorSeverity, attempt: int, max_attempts: int, metadata: Dict[str, Any]
) -> RecoveryContext:
    """Create RecoveryContext with provided parameters."""
    return RecoveryContext(
        operation_id=operation_id, operation_type=operation_type, error=error,
        severity=severity, retry_count=attempt, max_retries=max_attempts - 1, metadata=metadata
    )
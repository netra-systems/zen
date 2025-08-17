"""Response building utilities for error recovery middleware.

Provides functions to build various types of responses including
error responses, recovery responses, and circuit breaker responses.
"""

from typing import Dict, Any
from datetime import datetime
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from app.core.error_recovery import RecoveryContext


def create_circuit_breaker_response() -> JSONResponse:
    """Create service unavailable response for circuit breaker."""
    content = _get_circuit_breaker_content()
    return JSONResponse(status_code=503, content=content)


def _get_circuit_breaker_content() -> Dict[str, Any]:
    """Get circuit breaker response content."""
    return {
        "error": "SERVICE_UNAVAILABLE",
        "message": "Service temporarily unavailable",
        "retry_after": 60
    }


def create_recovery_response(
    request: Request,
    context: RecoveryContext,
    recovery_result
) -> JSONResponse:
    """Create response after successful recovery."""
    content = build_recovery_content(context, recovery_result)
    headers = build_recovery_headers(context, recovery_result)
    return JSONResponse(status_code=200, content=content, headers=headers)


def build_recovery_content(context: RecoveryContext, recovery_result) -> Dict[str, Any]:
    """Build recovery response content."""
    recovery_info = _build_recovery_info(context, recovery_result)
    return {
        "success": True,
        "message": "Request completed with recovery",
        "recovery_info": recovery_info
    }


def _build_recovery_info(context: RecoveryContext, recovery_result) -> Dict[str, Any]:
    """Build recovery info section."""
    return {
        "action_taken": recovery_result.action_taken.value,
        "operation_id": context.operation_id,
        "compensation_required": recovery_result.compensation_required,
        "retry_count": context.retry_count
    }


def build_recovery_headers(context: RecoveryContext, recovery_result) -> Dict[str, str]:
    """Build recovery response headers."""
    return {
        "X-Operation-ID": context.operation_id,
        "X-Recovery-Action": recovery_result.action_taken.value,
        "X-Retry-Count": str(context.retry_count)
    }


def create_error_response(
    request: Request,
    error: Exception,
    operation_id: str
) -> JSONResponse:
    """Create final error response after all recovery attempts failed."""
    status_code = determine_error_status_code(error)
    error_response = build_complete_error_response(error, operation_id, request)
    headers = build_error_response_headers(operation_id, error)
    return JSONResponse(status_code=status_code, content=error_response, headers=headers)


def determine_error_status_code(error: Exception) -> int:
    """Determine HTTP status code for error type."""
    if isinstance(error, HTTPException):
        return error.status_code
    return _get_status_code_for_standard_errors(error)

def _get_status_code_for_standard_errors(error: Exception) -> int:
    """Get status code for standard error types."""
    error_mapping = _get_error_status_mapping()
    for error_types, status_code in error_mapping.items():
        if isinstance(error, error_types):
            return status_code
    return 500


def _get_error_status_mapping() -> Dict[tuple, int]:
    """Get error type to status code mapping."""
    return {
        (ValueError, TypeError): 400,
        PermissionError: 403,
        FileNotFoundError: 404
    }


def build_complete_error_response(error: Exception, operation_id: str, request: Request) -> dict:
    """Build complete error response with all fields."""
    error_response = build_error_response_content(error, operation_id, request)
    add_optional_error_ids(error_response, request)
    return error_response


def build_error_response_content(error: Exception, operation_id: str, request: Request) -> Dict[str, Any]:
    """Build error response content."""
    base_content = get_error_response_base(error, operation_id)
    request_content = get_error_response_request_data(request)
    base_content.update(request_content)
    return base_content


def get_error_response_base(error: Exception, operation_id: str) -> Dict[str, Any]:
    """Get base error response data."""
    return {
        "error": True, "error_type": type(error).__name__, "message": str(error),
        "operation_id": operation_id, "timestamp": datetime.now().isoformat()
    }


def get_error_response_request_data(request: Request) -> Dict[str, Any]:
    """Get error response request data."""
    return {"path": request.url.path, "method": request.method}


def add_optional_error_ids(error_response: Dict[str, Any], request: Request) -> None:
    """Add optional request and trace IDs to error response."""
    if hasattr(request.state, 'request_id'):
        error_response["request_id"] = request.state.request_id
    if hasattr(request.state, 'trace_id'):
        error_response["trace_id"] = request.state.trace_id


def build_error_response_headers(operation_id: str, error: Exception) -> Dict[str, str]:
    """Build error response headers."""
    return {
        "X-Operation-ID": operation_id,
        "X-Error-Type": type(error).__name__,
        "X-Error-Recovery": "failed"
    }


def add_success_headers(response, operation_id: str, attempt: int):
    """Add success headers to response."""
    response.headers["X-Operation-ID"] = operation_id
    response.headers["X-Attempt"] = str(attempt + 1)
    return response
"""
Request context management module.
Handles request tracing, error context, and logging middleware.
"""
import time
import logging
from typing import Any, Callable, Optional, Tuple
from fastapi import Request

from app.core.error_context import ErrorContext
from app.logging_config import central_logger


def generate_context_ids(request: Request) -> Tuple[str, Optional[str]]:
    """Generate trace and request IDs."""
    trace_id = ErrorContext.generate_trace_id()
    request_id = request.headers.get("x-request-id")
    return trace_id, request_id


def set_error_context(request_id: Optional[str]) -> None:
    """Set error context if request ID available."""
    if request_id:
        ErrorContext.set_request_id(request_id)


def store_context_in_state(request: Request, trace_id: str, request_id: Optional[str]) -> None:
    """Store context in request state."""
    request.state.trace_id = trace_id
    request.state.request_id = request_id


def setup_request_context(request: Request) -> Tuple[str, Optional[str]]:
    """Setup request context with trace and request IDs."""
    trace_id, request_id = generate_context_ids(request)
    set_error_context(request_id)
    store_context_in_state(request, trace_id, request_id)
    return trace_id, request_id


def add_context_headers(response: Any, trace_id: str, request_id: Optional[str]) -> None:
    """Add context headers to response."""
    response.headers["x-trace-id"] = trace_id
    if request_id:
        response.headers["x-request-id"] = request_id


def create_error_context_middleware() -> Callable:
    """Create error context middleware."""
    async def error_context_middleware(request: Request, call_next: Callable) -> Any:
        """Middleware to set up error context for each request."""
        trace_id, request_id = setup_request_context(request)
        response = await call_next(request)
        add_context_headers(response, trace_id, request_id)
        return response
    return error_context_middleware


def calculate_request_duration(start_time: float) -> str:
    """Calculate and format request duration."""
    process_time = (time.time() - start_time) * 1000
    return f'{process_time:.2f}ms'


def log_request_details(logger: logging.Logger, request: Request, response: Any, duration: str) -> None:
    """Log request details with timing information."""
    trace_id = getattr(request.state, 'trace_id', 'unknown')
    logger.info(f"Request: {request.method} {request.url.path} | Status: {response.status_code} | Duration: {duration} | Trace: {trace_id}")


def create_request_logging_middleware() -> Callable:
    """Create request logging middleware."""
    async def log_requests(request: Request, call_next: Callable) -> Any:
        """Log request details with timing."""
        logger = central_logger.get_logger("api")
        start_time = time.time()
        response = await call_next(request)
        duration = calculate_request_duration(start_time)
        log_request_details(logger, request, response, duration)
        return response
    return log_requests
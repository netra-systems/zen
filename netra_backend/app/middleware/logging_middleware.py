"""Logging middleware for request tracking and performance monitoring."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from netra_backend.app.logging_config import (
    central_logger,
    request_id_context,
    trace_id_context,
    user_id_context,
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add logging context and track request performance."""
    
    def __init__(self, app) -> None:
        super().__init__(app)
        self.logger = central_logger.get_logger(__name__)
    
    def _generate_request_ids(self, request: Request) -> tuple[str, str]:
        """Generate request and trace IDs."""
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        request_id = UnifiedIdGenerator.generate_base_id("request")
        trace_id = request.headers.get("X-Trace-ID", UnifiedIdGenerator.generate_base_id("trace"))
        return request_id, trace_id

    def _set_context_ids(self, request_id: str, trace_id: str) -> None:
        """Set logging context IDs."""
        request_id_context.set(request_id)
        trace_id_context.set(trace_id)

    def _setup_request_context(self, request: Request) -> tuple[str, str, float]:
        """Setup request IDs, context and timing."""
        request_id, trace_id = self._generate_request_ids(request)
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        self._set_context_ids(request_id, trace_id)
        return request_id, trace_id, time.time()

    def _setup_user_context(self, request: Request) -> None:
        """Extract and set user context if available."""
        if not hasattr(request.state, "user") or not request.state.user:
            return
        user_id = str(request.state.user.id)
        user_id_context.set(user_id)

    def _get_client_host(self, request: Request) -> str:
        """Extract client host from request."""
        return request.client.host if request.client else None

    def _build_start_log_data(self, request: Request) -> dict:
        """Build start log data dict."""
        return {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_host": self._get_client_host(request),
        }

    def _log_request_start(self, request: Request) -> None:
        """Log incoming request details."""
        log_data = self._build_start_log_data(request)
        message = f"Request started: {request.method} {request.url.path}"
        self.logger.info(message, **log_data)

    def _build_success_log_data(self, request: Request, response: Response, duration: float) -> dict:
        """Build success log data dict."""
        return {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        }

    def _log_request_success(self, request: Request, response: Response, duration: float) -> None:
        """Log successful request completion."""
        log_data = self._build_success_log_data(request, response, duration)
        message = f"Request completed: {request.method} {request.url.path} -> {response.status_code}"
        self.logger.info(message, **log_data)

    def _add_response_headers(self, response: Response, request_id: str, trace_id: str) -> Response:
        """Add tracking headers to response."""
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        return response

    def _build_error_log_basic(self, request: Request, duration: float) -> dict:
        """Build basic error log data."""
        return {
            "method": request.method,
            "path": request.url.path,
            "duration_ms": round(duration * 1000, 2),
        }

    def _build_error_details(self, error: Exception) -> dict:
        """Build error-specific details."""
        return {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "exc_info": True
        }

    def _build_error_log_data(self, request: Request, error: Exception, duration: float) -> dict:
        """Build error log data dict."""
        basic_data = self._build_error_log_basic(request, duration)
        error_details = self._build_error_details(error)
        basic_data.update(error_details)
        return basic_data

    def _log_request_error(self, request: Request, error: Exception, duration: float) -> None:
        """Log request error with context."""
        log_data = self._build_error_log_data(request, error, duration)
        message = f"Request failed: {request.method} {request.url.path}"
        self.logger.error(message, **log_data)

    def _create_error_content(self, request_id: str, trace_id: str) -> dict:
        """Create error response content."""
        return {
            "error": True,
            "message": "Internal server error",
            "request_id": request_id,
            "trace_id": trace_id,
        }

    def _create_error_headers(self, request_id: str, trace_id: str) -> dict:
        """Create error response headers."""
        return {"X-Request-ID": request_id, "X-Trace-ID": trace_id}

    def _create_error_response(self, request_id: str, trace_id: str) -> JSONResponse:
        """Create standardized error response."""
        content = self._create_error_content(request_id, trace_id)
        headers = self._create_error_headers(request_id, trace_id)
        return JSONResponse(status_code=500, content=content, headers=headers)

    def _handle_successful_request(self, request: Request, response: Response, request_id: str, trace_id: str, start_time: float) -> Response:
        """Handle successful request completion."""
        duration = time.time() - start_time
        self._log_request_success(request, response, duration)
        return self._add_response_headers(response, request_id, trace_id)

    def _handle_failed_request(self, request: Request, error: Exception, request_id: str, trace_id: str, start_time: float) -> JSONResponse:
        """Handle failed request completion."""
        duration = time.time() - start_time
        self._log_request_error(request, error, duration)
        return self._create_error_response(request_id, trace_id)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process each request with logging context."""
        request_id, trace_id, start_time = self._setup_complete_logging_context(request)
        try:
            return await self._process_request_with_logging(request, call_next, request_id, trace_id, start_time)
        finally:
            central_logger.clear_context()
    
    def _setup_complete_logging_context(self, request: Request) -> tuple[str, str, float]:
        """Setup complete logging context including user context."""
        request_id, trace_id, start_time = self._setup_request_context(request)
        self._setup_user_context(request)
        self._log_request_start(request)
        return request_id, trace_id, start_time
    
    async def _process_request_with_logging(self, request: Request, call_next: Callable, request_id: str, trace_id: str, start_time: float) -> Response:
        """Process request and handle success/error logging."""
        try:
            response = await call_next(request)
            return self._handle_successful_request(request, response, request_id, trace_id, start_time)
        except Exception as e:
            return self._handle_failed_request(request, e, request_id, trace_id, start_time)


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware specifically for performance monitoring."""
    
    SLOW_REQUEST_THRESHOLD = 1.0  # seconds
    
    def __init__(self, app) -> None:
        super().__init__(app)
        self.logger = central_logger.get_logger(__name__)
    
    def _is_slow_request(self, duration: float) -> bool:
        """Check if request exceeds slow threshold."""
        return duration > self.SLOW_REQUEST_THRESHOLD

    def _build_slow_log_base(self, request: Request, duration: float) -> dict:
        """Build base slow log data."""
        return {
            "method": request.method,
            "path": request.url.path,
            "duration_ms": round(duration * 1000, 2),
            "threshold_ms": self.SLOW_REQUEST_THRESHOLD * 1000,
        }

    def _build_slow_log_data(self, request: Request, response: Response, duration: float) -> dict:
        """Build slow request log data dict."""
        base_data = self._build_slow_log_base(request, duration)
        base_data["status_code"] = response.status_code
        return base_data

    def _log_slow_request(self, request: Request, response: Response, duration: float) -> None:
        """Log slow request warning."""
        if not self._is_slow_request(duration):
            return
        log_data = self._build_slow_log_data(request, response, duration)
        message = f"Slow request detected: {request.method} {request.url.path}"
        self.logger.warning(message, **log_data)

    def _add_performance_header(self, response: Response, duration: float) -> Response:
        """Add performance timing header to response."""
        response.headers["X-Response-Time"] = f"{round(duration * 1000, 2)}ms"
        return response

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor request performance and log slow requests."""
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        self._log_slow_request(request, response, duration)
        return self._add_performance_header(response, duration)
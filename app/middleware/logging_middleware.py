"""Logging middleware for request tracking and performance monitoring."""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.logging_config import central_logger, request_id_context, user_id_context, trace_id_context


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add logging context and track request performance."""
    
    def __init__(self, app) -> None:
        super().__init__(app)
        self.logger = central_logger.get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process each request with logging context."""
        # Generate request ID and trace ID
        request_id = str(uuid.uuid4())
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        
        # Store in request state for access by other components
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        
        # Set context for logging
        request_id_context.set(request_id)
        trace_id_context.set(trace_id)
        
        # Extract user ID if available (from JWT or session)
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = str(request.state.user.id)
            user_id_context.set(user_id)
        
        # Track timing
        start_time = time.time()
        
        # Log incoming request
        self.logger.info(
            f"Request started: {request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_host=request.client.host if request.client else None,
        )
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log successful response
            self.logger.info(
                f"Request completed: {request.method} {request.url.path} -> {response.status_code}",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )
            
            # Add headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = trace_id
            
            return response
            
        except Exception as e:
            # Calculate duration even for errors
            duration = time.time() - start_time
            
            # Log the error with full context
            self.logger.error(
                f"Request failed: {request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "message": "Internal server error",
                    "request_id": request_id,
                    "trace_id": trace_id,
                },
                headers={
                    "X-Request-ID": request_id,
                    "X-Trace-ID": trace_id,
                }
            )
        finally:
            # Clear context after request
            central_logger.clear_context()


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware specifically for performance monitoring."""
    
    SLOW_REQUEST_THRESHOLD = 1.0  # seconds
    
    def __init__(self, app) -> None:
        super().__init__(app)
        self.logger = central_logger.get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor request performance and log slow requests."""
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log slow requests
        if duration > self.SLOW_REQUEST_THRESHOLD:
            self.logger.warning(
                f"Slow request detected: {request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                threshold_ms=self.SLOW_REQUEST_THRESHOLD * 1000,
                status_code=response.status_code,
            )
        
        # Add performance header
        response.headers["X-Response-Time"] = f"{round(duration * 1000, 2)}ms"
        
        return response
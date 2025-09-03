"""
Telemetry Middleware for Request Tracing

Provides comprehensive request tracing with OpenTelemetry integration.
"""

import time
import json
from typing import Callable, Optional, Dict, Any
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.propagate import extract, inject

from netra_backend.app.core.telemetry import telemetry_manager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TelemetryMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request tracing with OpenTelemetry.
    
    Features:
    - Creates spans for all HTTP requests
    - Propagates trace context from incoming requests
    - Adds request/response metadata to spans
    - Handles errors and exceptions
    - Supports streaming responses
    """
    
    def __init__(
        self,
        app,
        service_name: str = "netra-backend",
        excluded_paths: Optional[list] = None
    ):
        """
        Initialize telemetry middleware.
        
        Args:
            app: FastAPI application instance
            service_name: Name of the service for tracing
            excluded_paths: List of paths to exclude from tracing
        """
        super().__init__(app)
        self.service_name = service_name
        self.excluded_paths = excluded_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/favicon.ico"
        ]
        self.tracer = trace.get_tracer(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request with telemetry tracing.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
        
        Returns:
            The response from the application
        """
        # Check if path should be excluded from tracing
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # Extract trace context from headers
        context = extract(dict(request.headers))
        
        # Create span name
        span_name = f"{request.method} {request.url.path}"
        
        # Start span with extracted context
        with self.tracer.start_as_current_span(
            span_name,
            context=context,
            kind=trace.SpanKind.SERVER
        ) as span:
            # Add request ID for correlation
            request_id = request.headers.get("x-request-id", str(uuid4()))
            request.state.request_id = request_id
            
            # Add trace ID to request state for downstream use
            if span and span.get_span_context().trace_id:
                trace_id = format(span.get_span_context().trace_id, '032x')
                request.state.trace_id = trace_id
                request.state.span_id = format(span.get_span_context().span_id, '016x')
            
            try:
                # Record request attributes
                self._record_request_attributes(span, request, request_id)
                
                # Process the request
                start_time = time.time()
                response = await call_next(request)
                duration = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Handle streaming responses
                if isinstance(response, StreamingResponse):
                    response = await self._handle_streaming_response(
                        response, span, duration
                    )
                
                # Record response attributes
                self._record_response_attributes(span, response, duration)
                
                # Add trace headers to response
                self._add_trace_headers(response, span)
                
                # Set successful status
                span.set_status(Status(StatusCode.OK))
                
                return response
                
            except Exception as e:
                # Record exception
                self._record_exception(span, e)
                span.set_status(
                    Status(StatusCode.ERROR, f"Request failed: {str(e)}")
                )
                logger.error(f"Request failed: {e}", exc_info=True)
                raise
    
    def _should_exclude_path(self, path: str) -> bool:
        """Check if the path should be excluded from tracing."""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    def _record_request_attributes(
        self, 
        span: Optional[Span], 
        request: Request,
        request_id: str
    ) -> None:
        """Record request attributes in the span."""
        if not span:
            return
        
        try:
            # HTTP attributes
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.scheme", request.url.scheme)
            span.set_attribute("http.host", request.url.hostname)
            span.set_attribute("http.target", request.url.path)
            
            # Request metadata
            span.set_attribute("http.request_id", request_id)
            span.set_attribute("http.user_agent", 
                             request.headers.get("user-agent", "unknown"))
            
            # Client information
            if request.client:
                span.set_attribute("http.client_ip", request.client.host)
                span.set_attribute("http.client_port", request.client.port)
            
            # Custom attributes
            span.set_attribute("service.name", self.service_name)
            
            # Add user context if available
            if hasattr(request.state, "user_id"):
                span.set_attribute("user.id", request.state.user_id)
            
            if hasattr(request.state, "session_id"):
                span.set_attribute("session.id", request.state.session_id)
            
            # Add query parameters (be careful with sensitive data)
            if request.query_params:
                # Filter out sensitive parameters
                safe_params = {
                    k: v for k, v in request.query_params.items()
                    if k.lower() not in ["password", "token", "secret", "key", "api_key"]
                }
                if safe_params:
                    span.set_attribute("http.query_params", 
                                     json.dumps(dict(safe_params)))
            
        except Exception as e:
            logger.warning(f"Failed to record request attributes: {e}")
    
    def _record_response_attributes(
        self, 
        span: Optional[Span], 
        response: Response,
        duration: float
    ) -> None:
        """Record response attributes in the span."""
        if not span:
            return
        
        try:
            # Response attributes
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.response.duration_ms", duration)
            
            # Set span status based on HTTP status
            if response.status_code >= 400:
                span.set_status(
                    Status(StatusCode.ERROR, f"HTTP {response.status_code}")
                )
            
            # Add response size if available
            if hasattr(response, "body") and response.body:
                span.set_attribute("http.response.size", len(response.body))
            
            # Add custom response headers if any
            if "x-process-time" in response.headers:
                span.set_attribute("http.process_time", 
                                 response.headers["x-process-time"])
            
        except Exception as e:
            logger.warning(f"Failed to record response attributes: {e}")
    
    def _record_exception(self, span: Optional[Span], exception: Exception) -> None:
        """Record exception in the span."""
        if not span:
            return
        
        try:
            span.record_exception(exception)
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(exception).__name__)
            span.set_attribute("error.message", str(exception))
        except Exception as e:
            logger.warning(f"Failed to record exception: {e}")
    
    def _add_trace_headers(self, response: Response, span: Optional[Span]) -> None:
        """Add trace headers to the response."""
        if not span:
            return
        
        try:
            span_context = span.get_span_context()
            if span_context.trace_id:
                trace_id = format(span_context.trace_id, '032x')
                span_id = format(span_context.span_id, '016x')
                
                # Add W3C Trace Context headers
                response.headers["traceparent"] = f"00-{trace_id}-{span_id}-01"
                
                # Add custom trace headers
                response.headers["x-trace-id"] = trace_id
                response.headers["x-span-id"] = span_id
                
        except Exception as e:
            logger.warning(f"Failed to add trace headers: {e}")
    
    async def _handle_streaming_response(
        self,
        response: StreamingResponse,
        span: Optional[Span],
        duration: float
    ) -> StreamingResponse:
        """
        Handle streaming responses by wrapping the body iterator.
        
        Args:
            response: The streaming response
            span: The current span
            duration: Request duration so far
        
        Returns:
            The wrapped streaming response
        """
        if not span:
            return response
        
        # Record initial attributes
        span.set_attribute("http.response.streaming", True)
        span.set_attribute("http.response.initial_duration_ms", duration)
        
        # Get the original body iterator
        original_body = response.body_iterator
        
        async def wrapped_body():
            """Wrapped body iterator to track streaming."""
            chunk_count = 0
            total_bytes = 0
            
            try:
                async for chunk in original_body:
                    chunk_count += 1
                    if isinstance(chunk, bytes):
                        total_bytes += len(chunk)
                    yield chunk
                
                # Record final streaming metrics
                span.set_attribute("http.response.chunks", chunk_count)
                span.set_attribute("http.response.total_bytes", total_bytes)
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                self._record_exception(span, e)
                span.set_status(
                    Status(StatusCode.ERROR, f"Streaming failed: {str(e)}")
                )
                raise
        
        # Replace the body iterator
        response.body_iterator = wrapped_body()
        return response


class AgentExecutionTracer:
    """
    Specialized tracer for agent execution spans.
    
    Provides high-level methods for tracing agent operations.
    """
    
    def __init__(self):
        """Initialize the agent execution tracer."""
        self.tracer = trace.get_tracer(__name__)
    
    def trace_agent_execution(
        self,
        agent_name: str,
        operation: str,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        **attributes
    ):
        """
        Decorator for tracing agent execution.
        
        Args:
            agent_name: Name of the agent
            operation: Operation being performed
            user_id: Optional user ID
            thread_id: Optional thread ID
            **attributes: Additional attributes to add to span
        
        Returns:
            Decorator function
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                span_name = f"{agent_name}.{operation}"
                
                with self.tracer.start_as_current_span(
                    span_name,
                    kind=trace.SpanKind.INTERNAL
                ) as span:
                    # Add standard attributes
                    span.set_attribute("agent.name", agent_name)
                    span.set_attribute("agent.operation", operation)
                    
                    if user_id:
                        span.set_attribute("user.id", user_id)
                    if thread_id:
                        span.set_attribute("thread.id", thread_id)
                    
                    # Add custom attributes
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                    
                    try:
                        # Execute the function
                        result = await func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(
                            Status(StatusCode.ERROR, str(e))
                        )
                        raise
            
            return wrapper
        return decorator


# Global agent execution tracer instance
agent_execution_tracer = AgentExecutionTracer()
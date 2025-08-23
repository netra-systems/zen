"""
Distributed Tracing Manager for OpenTelemetry integration
Handles trace context propagation across services for OAuth integration
"""

import logging
import uuid
from typing import Dict, Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class TracingManager:
    """Manages OpenTelemetry distributed tracing for cross-service communication"""
    
    def __init__(self):
        self.enabled = True
        self._current_traces: Dict[str, Any] = {}
        
    def extract_trace_headers(self, headers: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Extract trace context headers from HTTP request"""
        trace_headers = {}
        
        # Extract W3C Trace Context headers
        if "traceparent" in headers:
            trace_headers["traceparent"] = headers["traceparent"]
            
        if "tracestate" in headers:
            trace_headers["tracestate"] = headers["tracestate"]
            
        # Extract custom headers
        for key, value in headers.items():
            if key.lower().startswith("x-trace-"):
                trace_headers[key] = value
                
        return trace_headers if trace_headers else None
    
    def inject_trace_headers(self, trace_id: Optional[str] = None) -> Dict[str, str]:
        """Inject trace context headers for outgoing HTTP requests"""
        if not trace_id:
            trace_id = str(uuid.uuid4()).replace("-", "")
            
        span_id = str(uuid.uuid4()).replace("-", "")[:16]
        
        return {
            "traceparent": f"00-{trace_id}-{span_id}-01",
            "tracestate": "netra=cross_service_request",
            "x-trace-id": trace_id,
            "x-span-id": span_id
        }
    
    @contextmanager
    def start_span(self, operation_name: str, trace_id: Optional[str] = None):
        """Start a new trace span"""
        span_id = str(uuid.uuid4())
        
        if not trace_id:
            trace_id = str(uuid.uuid4()).replace("-", "")
            
        span = TracingSpan(operation_name, trace_id, span_id)
        self._current_traces[span_id] = span
        
        try:
            logger.info(f"Started trace span: {operation_name} (trace_id: {trace_id})")
            yield span
        finally:
            if span_id in self._current_traces:
                del self._current_traces[span_id]
            logger.info(f"Completed trace span: {operation_name}")
    
    def get_current_trace_id(self) -> Optional[str]:
        """Get current trace ID if any"""
        if self._current_traces:
            return list(self._current_traces.values())[0].trace_id
        return None


class TracingSpan:
    """Represents a tracing span"""
    
    def __init__(self, operation_name: str, trace_id: str, span_id: str):
        self.operation_name = operation_name
        self.trace_id = trace_id
        self.span_id = span_id
        self.attributes: Dict[str, Any] = {}
        
    def set_attribute(self, key: str, value: Any):
        """Set an attribute on the span"""
        self.attributes[key] = value
        logger.debug(f"Span attribute set: {key}={value}")
        
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to the span"""
        logger.info(f"Span event: {name} {attributes or {}}")
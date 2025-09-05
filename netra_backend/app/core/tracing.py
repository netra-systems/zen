"""
Tracing and Observability Module

Provides distributed tracing capabilities for the Netra platform.
Supports OpenTelemetry integration for monitoring and debugging.
"""

import logging
import time
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from dataclasses import dataclass, field
import threading

logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    """Represents a trace span"""
    name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    parent_span_id: Optional[str] = None
    span_id: str = field(default_factory=lambda: str(int(time.time() * 1000000)))
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute"""
        self.attributes[key] = value
    
    def finish(self) -> None:
        """Mark the span as finished"""
        self.end_time = time.time()
    
    @property
    def duration(self) -> Optional[float]:
        """Get span duration in seconds"""
        if self.end_time:
            return self.end_time - self.start_time
        return None


class TraceContext:
    """Thread-local trace context"""
    
    def __init__(self):
        self._local = threading.local()
    
    @property
    def current_span(self) -> Optional[TraceSpan]:
        """Get current active span"""
        return getattr(self._local, 'current_span', None)
    
    @current_span.setter
    def current_span(self, span: Optional[TraceSpan]) -> None:
        """Set current active span"""
        self._local.current_span = span
    
    @property
    def trace_id(self) -> Optional[str]:
        """Get current trace ID"""
        return getattr(self._local, 'trace_id', None)
    
    @trace_id.setter
    def trace_id(self, trace_id: Optional[str]) -> None:
        """Set current trace ID"""
        self._local.trace_id = trace_id


class Tracer:
    """
    Simple tracer implementation for the Netra platform.
    
    Provides basic tracing functionality with span creation and context management.
    """
    
    def __init__(self, name: str = "netra_tracer"):
        self.name = name
        self.context = TraceContext()
        self._spans: List[TraceSpan] = []
        logger.info(f"Tracer initialized: {name}")
    
    def start_span(self, name: str, **attributes) -> TraceSpan:
        """
        Start a new trace span.
        
        Args:
            name: Span name
            **attributes: Span attributes
            
        Returns:
            New trace span
        """
        parent_span = self.context.current_span
        span = TraceSpan(
            name=name,
            parent_span_id=parent_span.span_id if parent_span else None,
            attributes=attributes
        )
        
        self._spans.append(span)
        self.context.current_span = span
        
        if not self.context.trace_id:
            self.context.trace_id = span.span_id
        
        return span
    
    def finish_span(self, span: TraceSpan) -> None:
        """Finish a trace span"""
        span.finish()
        
        # Reset current span to parent if this was the current span
        if self.context.current_span == span:
            parent_span_id = span.parent_span_id
            if parent_span_id:
                # Find parent span
                parent_span = next(
                    (s for s in self._spans if s.span_id == parent_span_id), 
                    None
                )
                self.context.current_span = parent_span
            else:
                self.context.current_span = None
    
    @contextmanager
    def span(self, name: str, **attributes):
        """Context manager for creating spans"""
        span = self.start_span(name, **attributes)
        try:
            yield span
        finally:
            self.finish_span(span)
    
    def get_spans(self) -> List[TraceSpan]:
        """Get all recorded spans"""
        return self._spans.copy()
    
    def clear_spans(self) -> None:
        """Clear all recorded spans"""
        self._spans.clear()


# Global tracer instance
_tracer = None


def get_tracer() -> Tracer:
    """Get the global tracer instance"""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer


def start_span(name: str, **attributes) -> TraceSpan:
    """Convenience function to start a span"""
    return get_tracer().start_span(name, **attributes)


def trace(name: str, **attributes):
    """Decorator for tracing function calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with get_tracer().span(name or func.__name__, **attributes):
                return func(*args, **kwargs)
        return wrapper
    return decorator


@contextmanager
def trace_span(name: str, **attributes):
    """Context manager for creating trace spans"""
    with get_tracer().span(name, **attributes) as span:
        yield span


class TracingManager:
    """
    Manager for tracing operations.
    
    Provides centralized management of tracers and spans
    across the application.
    """
    
    def __init__(self):
        self._tracers: Dict[str, Tracer] = {}
        self._default_tracer = Tracer("default")
        logger.info("TracingManager initialized")
    
    def get_tracer(self, name: str = "default") -> Tracer:
        """Get or create a tracer by name"""
        if name == "default":
            return self._default_tracer
        
        if name not in self._tracers:
            self._tracers[name] = Tracer(name)
        
        return self._tracers[name]
    
    def start_span(self, name: str, tracer_name: str = "default", **attributes) -> TraceSpan:
        """Start a span with specified tracer"""
        tracer = self.get_tracer(tracer_name)
        return tracer.start_span(name, **attributes)
    
    def get_all_spans(self) -> Dict[str, List[TraceSpan]]:
        """Get all spans from all tracers"""
        all_spans = {"default": self._default_tracer.get_spans()}
        
        for name, tracer in self._tracers.items():
            all_spans[name] = tracer.get_spans()
        
        return all_spans
    
    def clear_all_spans(self) -> None:
        """Clear spans from all tracers"""
        self._default_tracer.clear_spans()
        
        for tracer in self._tracers.values():
            tracer.clear_spans()


# Global tracing manager
_tracing_manager = None


def get_tracing_manager() -> TracingManager:
    """Get the global tracing manager instance"""
    global _tracing_manager
    if _tracing_manager is None:
        _tracing_manager = TracingManager()
    return _tracing_manager
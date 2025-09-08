"""Unified trace context for request tracking and correlation.

This module provides a simple trace context implementation to fix import errors.
"""

from typing import Optional, Dict, Any
from contextvars import ContextVar
from dataclasses import dataclass, field
import uuid
import time


@dataclass
class TraceSpan:
    """Simple trace span representation."""
    name: str
    span_id: str = field(default_factory=lambda: str(uuid.uuid4().hex[:16]))
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedTraceContext:
    """Trace context for request tracking."""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    correlation_id: Optional[str] = None
    thread_id: Optional[str] = None
    _current_span: Optional[TraceSpan] = field(default=None, init=False)
    
    def propagate_to_child(self) -> 'UnifiedTraceContext':
        """Create child context with parent references."""
        return UnifiedTraceContext(
            request_id=self.request_id,
            user_id=self.user_id,
            trace_id=self.trace_id or str(uuid.uuid4()),
            correlation_id=self.correlation_id,
            thread_id=self.thread_id,
            span_id=str(uuid.uuid4().hex[:16])  # New span for child
        )
    
    def start_span(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None) -> TraceSpan:
        """Start a new span."""
        span = TraceSpan(
            name=operation_name,
            attributes=attributes or {}
        )
        self._current_span = span
        return span
    
    def finish_span(self, span: TraceSpan) -> None:
        """Finish a span."""
        if span:
            span.end_time = time.time()
        if self._current_span == span:
            self._current_span = None
    
    def add_event(self, event_name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the current span."""
        if self._current_span:
            if 'events' not in self._current_span.attributes:
                self._current_span.attributes['events'] = []
            self._current_span.attributes['events'].append({
                'name': event_name,
                'timestamp': time.time(),
                'attributes': attributes or {}
            })
    
    def to_websocket_context(self) -> Dict[str, str]:
        """Convert to websocket context format."""
        return {
            'trace_id': self.trace_id or '',
            'span_id': self.span_id or '',
            'correlation_id': self.correlation_id or '',
            'user_id': self.user_id or '',
            'thread_id': self.thread_id or ''
        }


class TraceContextManager:
    """Context manager for managing trace context lifecycle."""
    
    def __init__(self, trace_context: UnifiedTraceContext):
        self.trace_context = trace_context
        self.previous_context = None
    
    async def __aenter__(self):
        """Enter async context manager."""
        self.previous_context = _trace_context.get()
        _trace_context.set(self.trace_context)
        return self.trace_context
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        _trace_context.set(self.previous_context)


# Context variable for trace context
_trace_context: ContextVar[Optional[UnifiedTraceContext]] = ContextVar('trace_context', default=None)


def get_current_trace_context() -> Optional[UnifiedTraceContext]:
    """Get the current trace context."""
    return _trace_context.get()


def set_trace_context(context: UnifiedTraceContext) -> None:
    """Set the trace context."""
    _trace_context.set(context)


def clear_trace_context() -> None:
    """Clear the trace context."""
    _trace_context.set(None)
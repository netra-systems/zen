"""Unified Trace Context with W3C Trace Context support.

This module implements distributed tracing across all layers of the system,
enabling correlation of requests through agents, sub-agents, and WebSocket events.

W3C Trace Context: https://www.w3.org/TR/trace-context/
"""

import asyncio
import json
import random
import time
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

# Use loguru directly to avoid circular import
from loguru import logger

# Global context variables for trace propagation
_trace_context_var: ContextVar[Optional['UnifiedTraceContext']] = ContextVar('trace_context', default=None)


@dataclass
class TraceFlags:
    """W3C Trace Flags."""
    sampled: bool = True
    
    def to_byte(self) -> int:
        """Convert flags to byte representation."""
        flags = 0
        if self.sampled:
            flags |= 0x01
        return flags
    
    @classmethod
    def from_byte(cls, flags: int) -> 'TraceFlags':
        """Create TraceFlags from byte representation."""
        return cls(sampled=bool(flags & 0x01))


@dataclass
class TraceSpan:
    """Represents a span in the distributed trace."""
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    def finish(self) -> None:
        """Mark span as finished."""
        if not self.end_time:
            self.end_time = time.time()
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate span duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None


class UnifiedTraceContext:
    """Unified trace context with W3C Trace Context support."""
    
    # W3C Trace Context version
    W3C_VERSION = "00"
    
    def __init__(
        self,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        request_id: Optional[str] = None,
        baggage: Optional[Dict[str, str]] = None,
        flags: Optional[TraceFlags] = None
    ):
        """Initialize unified trace context.
        
        Args:
            trace_id: 32-character hex trace identifier
            parent_span_id: 16-character hex parent span identifier
            correlation_id: Correlation ID for business operations
            user_id: User identifier
            thread_id: Thread/conversation identifier
            request_id: HTTP request identifier
            baggage: Additional context to propagate
            flags: W3C trace flags
        """
        self.trace_id = trace_id or self._generate_trace_id()
        self.parent_span_id = parent_span_id
        self.span_stack: List[TraceSpan] = []
        self.correlation_id = correlation_id or str(uuid4())
        self.user_id = user_id
        self.thread_id = thread_id
        self.request_id = request_id
        self.baggage = baggage or {}
        self.flags = flags or TraceFlags()
        
        # Track current span
        self._current_span: Optional[TraceSpan] = None
        
        logger.debug(
            f"Created UnifiedTraceContext: trace_id={self.trace_id}, "
            f"correlation_id={self.correlation_id}, user_id={self.user_id}"
        )
    
    @staticmethod
    def _generate_trace_id() -> str:
        """Generate a 32-character hex trace ID."""
        # W3C spec: 32 hex characters (128 bits)
        return format(random.getrandbits(128), '032x')
    
    @staticmethod
    def _generate_span_id() -> str:
        """Generate a 16-character hex span ID."""
        # W3C spec: 16 hex characters (64 bits)
        return format(random.getrandbits(64), '016x')
    
    def start_span(
        self,
        operation_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> TraceSpan:
        """Start a new span in the current trace.
        
        Args:
            operation_name: Name of the operation
            attributes: Optional span attributes
            
        Returns:
            The created span
        """
        span_id = self._generate_span_id()
        parent_span_id = self._current_span.span_id if self._current_span else self.parent_span_id
        
        span = TraceSpan(
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            attributes=attributes or {}
        )
        
        self.span_stack.append(span)
        self._current_span = span
        
        logger.debug(
            f"Started span: operation={operation_name}, "
            f"span_id={span_id}, parent={parent_span_id}"
        )
        
        return span
    
    def finish_span(self, span: Optional[TraceSpan] = None) -> None:
        """Finish a span.
        
        Args:
            span: Span to finish (defaults to current)
        """
        target_span = span or self._current_span
        if target_span:
            target_span.finish()
            
            # Update current span to parent if finishing current
            if target_span == self._current_span and self.span_stack:
                # Find parent span in stack
                for s in reversed(self.span_stack[:-1]):
                    if not s.end_time:
                        self._current_span = s
                        break
                else:
                    self._current_span = None
            
            logger.debug(
                f"Finished span: operation={target_span.operation_name}, "
                f"duration_ms={target_span.duration_ms}"
            )
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the current span.
        
        Args:
            name: Event name
            attributes: Event attributes
        """
        if self._current_span:
            event = {
                "name": name,
                "timestamp": time.time(),
                "attributes": attributes or {}
            }
            self._current_span.events.append(event)
    
    def propagate_to_child(self) -> 'UnifiedTraceContext':
        """Create a child context for sub-agent propagation.
        
        Returns:
            New context with parent references
        """
        current_span_id = self._current_span.span_id if self._current_span else self._generate_span_id()
        
        child = UnifiedTraceContext(
            trace_id=self.trace_id,
            parent_span_id=current_span_id,
            correlation_id=self.correlation_id,
            user_id=self.user_id,
            thread_id=self.thread_id,
            request_id=self.request_id,
            baggage=self.baggage.copy(),
            flags=self.flags
        )
        
        logger.debug(
            f"Created child context: trace_id={child.trace_id}, "
            f"parent_span={current_span_id}"
        )
        
        return child
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to W3C Trace Context headers.
        
        Returns:
            Dictionary of HTTP headers
        """
        # W3C traceparent header format:
        # version-trace_id-span_id-trace_flags
        current_span_id = self._current_span.span_id if self._current_span else self._generate_span_id()
        traceparent = f"{self.W3C_VERSION}-{self.trace_id}-{current_span_id}-{self.flags.to_byte():02x}"
        
        headers = {
            "traceparent": traceparent,
        }
        
        # Add tracestate if we have baggage
        if self.baggage:
            # Simplified tracestate - in production would need proper encoding
            tracestate_items = []
            for key, value in self.baggage.items():
                if key and value:  # Skip empty keys/values
                    # Basic validation - keys should be vendor-specific
                    safe_key = key.replace(" ", "_").replace(",", "_")
                    safe_value = value.replace(" ", "_").replace(",", "_")
                    tracestate_items.append(f"netra@{safe_key}={safe_value}")
            
            if tracestate_items:
                headers["tracestate"] = ",".join(tracestate_items)
        
        # Add custom headers for internal context
        if self.correlation_id:
            headers["x-correlation-id"] = self.correlation_id
        if self.user_id:
            headers["x-user-id"] = self.user_id
        if self.thread_id:
            headers["x-thread-id"] = self.thread_id
        if self.request_id:
            headers["x-request-id"] = self.request_id
        
        return headers
    
    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> 'UnifiedTraceContext':
        """Reconstruct context from HTTP headers.
        
        Args:
            headers: Dictionary of HTTP headers
            
        Returns:
            Reconstructed trace context
        """
        # Parse W3C traceparent header
        traceparent = headers.get("traceparent", "")
        trace_id = None
        parent_span_id = None
        flags = TraceFlags()
        
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 4:
                # version = parts[0]  # Not used but could validate
                trace_id = parts[1]
                parent_span_id = parts[2]
                try:
                    flags = TraceFlags.from_byte(int(parts[3], 16))
                except (ValueError, IndexError):
                    pass
        
        # Parse tracestate for baggage
        baggage = {}
        tracestate = headers.get("tracestate", "")
        if tracestate:
            # Parse our vendor-specific entries
            for item in tracestate.split(","):
                if item.strip().startswith("netra@"):
                    try:
                        vendor_data = item.strip()[6:]  # Remove "netra@"
                        key_value = vendor_data.split("=", 1)
                        if len(key_value) == 2:
                            baggage[key_value[0]] = key_value[1]
                    except Exception:
                        pass
        
        # Extract custom headers
        correlation_id = headers.get("x-correlation-id")
        user_id = headers.get("x-user-id")
        thread_id = headers.get("x-thread-id")
        request_id = headers.get("x-request-id")
        
        context = cls(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            correlation_id=correlation_id,
            user_id=user_id,
            thread_id=thread_id,
            request_id=request_id,
            baggage=baggage,
            flags=flags
        )
        
        logger.debug(f"Reconstructed context from headers: trace_id={context.trace_id}")
        
        return context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "request_id": self.request_id,
            "baggage": self.baggage,
            "flags": {"sampled": self.flags.sampled},
            "current_span_id": self._current_span.span_id if self._current_span else None,
            "span_count": len(self.span_stack)
        }
    
    def to_websocket_context(self) -> Dict[str, Any]:
        """Convert to WebSocket event context.
        
        Returns:
            Context for WebSocket events
        """
        return {
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "span_id": self._current_span.span_id if self._current_span else None,
            "parent_span_id": self.parent_span_id
        }


# Global context management functions
def get_current_trace_context() -> Optional[UnifiedTraceContext]:
    """Get the current trace context from context variables.
    
    Returns:
        Current trace context or None
    """
    return _trace_context_var.get()


def set_trace_context(context: UnifiedTraceContext) -> Token:
    """Set the current trace context.
    
    Args:
        context: Trace context to set
        
    Returns:
        Context token for restoration
    """
    return _trace_context_var.set(context)


def clear_trace_context() -> None:
    """Clear the current trace context."""
    _trace_context_var.set(None)


class TraceContextManager:
    """Context manager for trace context propagation."""
    
    def __init__(self, context: UnifiedTraceContext):
        """Initialize context manager.
        
        Args:
            context: Trace context to use
        """
        self.context = context
        self._token: Optional[Token] = None
    
    def __enter__(self) -> UnifiedTraceContext:
        """Enter context."""
        self._token = set_trace_context(self.context)
        return self.context
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context."""
        if self._token:
            _trace_context_var.reset(self._token)
    
    async def __aenter__(self) -> UnifiedTraceContext:
        """Async enter context."""
        self._token = set_trace_context(self.context)
        return self.context
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async exit context."""
        if self._token:
            _trace_context_var.reset(self._token)


def with_trace_context(context: Optional[UnifiedTraceContext] = None):
    """Decorator to add trace context to function execution.
    
    Args:
        context: Optional context to use (creates new if None)
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                ctx = context or UnifiedTraceContext()
                async with TraceContextManager(ctx):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                ctx = context or UnifiedTraceContext()
                with TraceContextManager(ctx):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator
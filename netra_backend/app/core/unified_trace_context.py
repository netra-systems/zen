"""Unified trace context for request tracking and correlation.

This module provides a simple trace context implementation to fix import errors.
"""

from typing import Optional
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class UnifiedTraceContext:
    """Trace context for request tracking."""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


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
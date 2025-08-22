"""Tracing Service Implementation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide basic tracing functionality for tests
- Value Impact: Ensures tracing tests can execute without import errors
- Strategic Impact: Enables distributed tracing validation
"""

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class SpanKind(Enum):
    """Span kinds for tracing."""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class SpanData:
    """Data for a trace span."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str] = None
    operation_name: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    kind: SpanKind = SpanKind.INTERNAL


class TracingService:
    """Service for distributed tracing."""
    
    def __init__(self):
        """Initialize tracing service."""
        self._spans: Dict[str, SpanData] = {}
        self._active_spans: Dict[str, SpanData] = {}  # task_id -> span
        self._lock = asyncio.Lock()
        self._enabled = True
    
    async def start_span(
        self,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
        kind: SpanKind = SpanKind.INTERNAL
    ) -> str:
        """Start a new span."""
        if not self._enabled:
            return ""
        
        span_id = str(uuid.uuid4())
        trace_id = parent_span_id or str(uuid.uuid4())
        
        span = SpanData(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            tags=tags or {},
            kind=kind
        )
        
        async with self._lock:
            self._spans[span_id] = span
            # Associate with current task
            task_id = str(id(asyncio.current_task()))
            self._active_spans[task_id] = span
        
        return span_id
    
    async def finish_span(self, span_id: str, status: str = "ok") -> None:
        """Finish a span."""
        if not self._enabled or not span_id:
            return
        
        async with self._lock:
            if span_id in self._spans:
                span = self._spans[span_id]
                span.end_time = datetime.now()
                span.status = status
                
                if span.start_time:
                    duration = span.end_time - span.start_time
                    span.duration_ms = duration.total_seconds() * 1000
                
                # Remove from active spans
                task_id = str(id(asyncio.current_task()))
                self._active_spans.pop(task_id, None)
    
    async def add_span_tag(self, span_id: str, key: str, value: Any) -> None:
        """Add a tag to a span."""
        if not self._enabled or not span_id:
            return
        
        async with self._lock:
            if span_id in self._spans:
                self._spans[span_id].tags[key] = value
    
    async def add_span_log(self, span_id: str, message: str, level: str = "info", **kwargs) -> None:
        """Add a log entry to a span."""
        if not self._enabled or not span_id:
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "level": level,
            **kwargs
        }
        
        async with self._lock:
            if span_id in self._spans:
                self._spans[span_id].logs.append(log_entry)
    
    async def get_active_span(self) -> Optional[SpanData]:
        """Get the currently active span for this task."""
        if not self._enabled:
            return None
        
        task_id = str(id(asyncio.current_task()))
        async with self._lock:
            return self._active_spans.get(task_id)
    
    async def get_span(self, span_id: str) -> Optional[SpanData]:
        """Get a span by ID."""
        async with self._lock:
            return self._spans.get(span_id)
    
    async def get_trace(self, trace_id: str) -> List[SpanData]:
        """Get all spans for a trace."""
        async with self._lock:
            return [span for span in self._spans.values() if span.trace_id == trace_id]
    
    async def get_traces_summary(self) -> Dict[str, Any]:
        """Get a summary of all traces."""
        async with self._lock:
            trace_groups = {}
            for span in self._spans.values():
                if span.trace_id not in trace_groups:
                    trace_groups[span.trace_id] = []
                trace_groups[span.trace_id].append(span)
            
            summary = {
                "total_traces": len(trace_groups),
                "total_spans": len(self._spans),
                "active_spans": len(self._active_spans),
                "traces": {}
            }
            
            for trace_id, spans in trace_groups.items():
                completed_spans = [s for s in spans if s.end_time is not None]
                avg_duration = 0
                if completed_spans:
                    avg_duration = sum(s.duration_ms or 0 for s in completed_spans) / len(completed_spans)
                
                summary["traces"][trace_id] = {
                    "span_count": len(spans),
                    "completed_spans": len(completed_spans),
                    "average_duration_ms": avg_duration
                }
            
            return summary
    
    @asynccontextmanager
    async def trace_operation(
        self, 
        operation_name: str, 
        tags: Optional[Dict[str, Any]] = None,
        kind: SpanKind = SpanKind.INTERNAL
    ):
        """Context manager for tracing an operation."""
        span_id = await self.start_span(operation_name, tags=tags, kind=kind)
        try:
            yield span_id
            await self.finish_span(span_id, "ok")
        except Exception as e:
            await self.add_span_tag(span_id, "error", True)
            await self.add_span_tag(span_id, "error.message", str(e))
            await self.finish_span(span_id, "error")
            raise
    
    async def clear_traces(self) -> None:
        """Clear all trace data."""
        async with self._lock:
            self._spans.clear()
            self._active_spans.clear()
    
    def enable_tracing(self) -> None:
        """Enable tracing."""
        self._enabled = True
    
    def disable_tracing(self) -> None:
        """Disable tracing."""
        self._enabled = False


# Global tracing service instance
default_tracing_service = TracingService()
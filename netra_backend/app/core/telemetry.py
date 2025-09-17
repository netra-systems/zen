"""
Core telemetry and observability system.
Provides distributed tracing, metrics collection, and monitoring capabilities.
"""

from typing import Any, Dict, Optional, List, Union
from datetime import datetime, timedelta, UTC
import uuid
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TelemetryLevel(Enum):
    """Telemetry collection levels."""
    OFF = "off"
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"


@dataclass
class Span:
    """Represents a span in distributed tracing."""
    span_id: str
    trace_id: str
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str = "active"
    tags: Dict[str, Any] = None
    logs: List[Dict[str, Any]] = None
    parent_span_id: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.logs is None:
            self.logs = []
    
    def add_tag(self, key: str, value: Any) -> None:
        """Add a tag to the span."""
        self.tags[key] = value
    
    def add_log(self, message: str, level: str = "info", **kwargs) -> None:
        """Add a log entry to the span."""
        log_entry = {
            "timestamp": datetime.now(UTC),
            "message": message,
            "level": level,
            **kwargs
        }
        self.logs.append(log_entry)
    
    def finish(self, status: str = "success") -> None:
        """Mark span as finished."""
        if self.end_time is None:
            self.end_time = datetime.now(UTC)
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
            self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
            "logs": self.logs,
            "parent_span_id": self.parent_span_id
        }


class TelemetryCollector:
    """Collects and manages telemetry data."""
    
    def __init__(self, level: TelemetryLevel = TelemetryLevel.INFO):
        self.level = level
        self._spans: Dict[str, Span] = {}
        self._active_spans: List[str] = []
        self._metrics: List[Dict[str, Any]] = []
        self._trace_context: Dict[str, str] = {}
        
        logger.debug(f"Initialized TelemetryCollector with level: {level.value}")
    
    def create_span(self, 
                   operation_name: str,
                   trace_id: Optional[str] = None,
                   parent_span_id: Optional[str] = None,
                   tags: Optional[Dict[str, Any]] = None) -> Span:
        """Create a new span."""
        span_id = str(uuid.uuid4())
        
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            operation_name=operation_name,
            start_time=datetime.now(UTC),
            parent_span_id=parent_span_id,
            tags=tags or {}
        )
        
        self._spans[span_id] = span
        self._active_spans.append(span_id)
        
        logger.debug(f"Created span: {operation_name} (id: {span_id}, trace: {trace_id})")
        return span
    
    def finish_span(self, span_id: str, status: str = "success") -> None:
        """Finish a span."""
        if span_id in self._spans:
            self._spans[span_id].finish(status)
            if span_id in self._active_spans:
                self._active_spans.remove(span_id)
            logger.debug(f"Finished span: {span_id} with status: {status}")
    
    def get_span(self, span_id: str) -> Optional[Span]:
        """Get a span by ID."""
        return self._spans.get(span_id)
    
    def get_active_spans(self) -> List[Span]:
        """Get all currently active spans."""
        return [self._spans[span_id] for span_id in self._active_spans if span_id in self._spans]
    
    def record_metric(self, 
                     name: str,
                     value: Union[int, float],
                     tags: Optional[Dict[str, Any]] = None,
                     timestamp: Optional[datetime] = None) -> None:
        """Record a metric."""
        metric = {
            "name": name,
            "value": value,
            "tags": tags or {},
            "timestamp": timestamp or datetime.now(UTC)
        }
        
        self._metrics.append(metric)
        
        # Keep only last 10000 metrics to prevent memory issues
        if len(self._metrics) > 10000:
            self._metrics = self._metrics[-10000:]
        
        if self.level.value in ["debug", "trace"]:
            logger.debug(f"Recorded metric: {name} = {value}")
    
    def get_metrics(self, name: Optional[str] = None, hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics, optionally filtered by name and time."""
        from datetime import timedelta
        
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        filtered_metrics = [
            m for m in self._metrics 
            if m.get("timestamp", datetime.min) > cutoff_time
        ]
        
        if name:
            filtered_metrics = [m for m in filtered_metrics if m.get("name") == name]
        
        return filtered_metrics
    
    def set_trace_context(self, context: Dict[str, str]) -> None:
        """Set trace context for correlation."""
        self._trace_context.update(context)
    
    def get_trace_context(self) -> Dict[str, str]:
        """Get current trace context."""
        return self._trace_context.copy()
    
    def get_trace_summary(self, trace_id: str) -> Dict[str, Any]:
        """Get summary for a specific trace."""
        trace_spans = [span for span in self._spans.values() if span.trace_id == trace_id]
        
        if not trace_spans:
            return {"trace_id": trace_id, "spans": [], "summary": "No spans found"}
        
        # Calculate trace statistics
        total_duration = sum(span.duration_ms or 0 for span in trace_spans if span.duration_ms)
        successful_spans = len([span for span in trace_spans if span.status == "success"])
        failed_spans = len([span for span in trace_spans if span.status == "error"])
        
        return {
            "trace_id": trace_id,
            "total_spans": len(trace_spans),
            "successful_spans": successful_spans,
            "failed_spans": failed_spans,
            "total_duration_ms": total_duration,
            "spans": [span.to_dict() for span in trace_spans],
            "start_time": min(span.start_time for span in trace_spans),
            "end_time": max(span.end_time or datetime.now(UTC) for span in trace_spans)
        }
    
    @contextmanager
    def trace_operation(self, operation_name: str, **tags):
        """Context manager for tracing an operation."""
        span = self.create_span(operation_name, tags=tags)
        try:
            yield span
            self.finish_span(span.span_id, "success")
        except Exception as e:
            span.add_log(f"Operation failed: {str(e)}", level="error")
            self.finish_span(span.span_id, "error")
            raise
    
    def clear_old_data(self, hours: int = 24) -> Dict[str, int]:
        """Clear old telemetry data."""
        from datetime import timedelta
        
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        
        # Clear old spans
        old_spans = [
            span_id for span_id, span in self._spans.items()
            if span.end_time and span.end_time < cutoff_time
        ]
        
        for span_id in old_spans:
            del self._spans[span_id]
            if span_id in self._active_spans:
                self._active_spans.remove(span_id)
        
        # Clear old metrics
        initial_metric_count = len(self._metrics)
        self._metrics = [
            m for m in self._metrics
            if m.get("timestamp", datetime.min) > cutoff_time
        ]
        
        cleared_metrics = initial_metric_count - len(self._metrics)
        
        logger.info(f"Cleared {len(old_spans)} old spans and {cleared_metrics} old metrics")
        
        return {
            "cleared_spans": len(old_spans),
            "cleared_metrics": cleared_metrics,
            "remaining_spans": len(self._spans),
            "remaining_metrics": len(self._metrics)
        }


class TelemetryManager:
    """Main telemetry manager."""
    
    def __init__(self, level: TelemetryLevel = TelemetryLevel.INFO):
        self.collector = TelemetryCollector(level)
        self._enabled = True
        logger.debug("Initialized TelemetryManager")
    
    def enable(self) -> None:
        """Enable telemetry collection."""
        self._enabled = True
        logger.info("Telemetry collection enabled")
    
    def disable(self) -> None:
        """Disable telemetry collection."""
        self._enabled = False
        logger.info("Telemetry collection disabled")
    
    def is_enabled(self) -> bool:
        """Check if telemetry is enabled."""
        return self._enabled
    
    def start_span(self, operation_name: str, **kwargs) -> Optional[Span]:
        """Start a new span if telemetry is enabled."""
        if not self._enabled:
            return None
        return self.collector.create_span(operation_name, **kwargs)
    
    def finish_span(self, span_id: str, status: str = "success") -> None:
        """Finish a span if telemetry is enabled."""
        if self._enabled and span_id:
            self.collector.finish_span(span_id, status)
    
    def record_metric(self, name: str, value: Union[int, float], **kwargs) -> None:
        """Record a metric if telemetry is enabled."""
        if self._enabled:
            self.collector.record_metric(name, value, **kwargs)
    
    def trace_operation(self, operation_name: str, **tags):
        """Context manager for tracing operations."""
        if not self._enabled:
            return NullContext()
        return self.collector.trace_operation(operation_name, **tags)
    
    def start_agent_span(self, agent_name: str, operation: str, attributes: Optional[Dict[str, Any]] = None):
        """Start an agent span with proper async context management."""
        return AgentSpanContext(self, agent_name, operation, attributes or {})
    
    def add_event(self, span: Optional[Span], event_name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to a span."""
        if not self._enabled or not span:
            return
        
        # Extract message from attributes if present, otherwise use event_name
        attrs = dict(attributes or {})  # Create a copy to avoid mutating original
        message = attrs.pop("message", event_name)
        span.add_log(message, level="info", **attrs)
    
    def record_exception(self, span: Optional[Span], exception: Exception, attributes: Optional[Dict[str, Any]] = None):
        """Record an exception on a span."""
        if not self._enabled or not span:
            return
        
        span.add_log(f"Exception: {str(exception)}", level="error", **attributes or {})
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health from telemetry data."""
        active_spans = self.collector.get_active_spans()
        recent_metrics = self.collector.get_metrics(hours=1)
        
        # Analyze for potential issues
        issues = []
        if len(active_spans) > 100:
            issues.append(f"High number of active spans: {len(active_spans)}")
        
        # Calculate error rate from recent spans
        recent_finished_spans = [
            span for span in self.collector._spans.values()
            if span.end_time and (datetime.now(UTC) - span.end_time).total_seconds() < 3600
        ]
        
        if recent_finished_spans:
            error_rate = len([span for span in recent_finished_spans if span.status == "error"]) / len(recent_finished_spans)
            if error_rate > 0.1:  # More than 10% errors
                issues.append(f"High error rate: {error_rate:.1%}")
        
        health_status = "healthy" if not issues else "degraded"
        
        return {
            "status": health_status,
            "issues": issues,
            "active_spans": len(active_spans),
            "total_spans": len(self.collector._spans),
            "recent_metrics": len(recent_metrics),
            "enabled": self._enabled,
            "timestamp": datetime.now(UTC)
        }


class NullContext:
    """Null context manager for when telemetry is disabled."""
    def __enter__(self):
        return None
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class AgentSpanContext:
    """Async context manager for agent spans."""
    
    def __init__(self, telemetry_manager: 'TelemetryManager', agent_name: str, operation: str, attributes: Dict[str, Any]):
        self.telemetry_manager = telemetry_manager
        self.agent_name = agent_name
        self.operation = operation
        self.attributes = attributes
        self.span: Optional[Span] = None
    
    async def __aenter__(self) -> Optional[Span]:
        if not self.telemetry_manager._enabled:
            return None
        
        # Create span with agent-specific naming
        operation_name = f"{self.agent_name}.{self.operation}"
        self.span = self.telemetry_manager.collector.create_span(operation_name, tags=self.attributes)
        return self.span
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            if exc_type:
                self.span.add_log(f"Agent execution error: {str(exc_val)}", level="error")
                self.span.finish(status="error")
            else:
                self.span.finish(status="success")


# Global instances
telemetry_manager = TelemetryManager()
agent_tracer = telemetry_manager  # Alias for agent-specific tracing


__all__ = [
    "TelemetryManager",
    "TelemetryCollector",
    "Span",
    "TelemetryLevel",
    "telemetry_manager",
    "agent_tracer",
]
"""Trace Collector - SSOT for Distributed Tracing

This module provides distributed tracing capabilities for the Netra platform,
enabling comprehensive request tracing and performance monitoring.

Business Value Justification (BVJ):
- Segment: Platform/Internal + Enterprise customers  
- Business Goal: Enable detailed performance analysis and debugging
- Value Impact: Faster issue resolution and improved system performance
- Strategic Impact: Critical for maintaining SLA compliance and customer satisfaction

SSOT Compliance:
- Integrates with existing observability pipeline
- Uses standardized trace data structures
- Provides unified interface for trace collection
"""

import asyncio
import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)


@dataclass
class TraceSpan:
    """Individual trace span data structure."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    operation_name: str = "unknown"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    
    def finish(self) -> None:
        """Finish the span and calculate duration."""
        if self.end_time is None:
            self.end_time = datetime.now(timezone.utc)
        
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.duration_ms = delta.total_seconds() * 1000


@dataclass 
class TraceStats:
    """Statistics for trace collector."""
    total_traces: int = 0
    active_traces: int = 0
    completed_traces: int = 0
    failed_traces: int = 0
    average_duration_ms: float = 0.0
    last_trace_time: Optional[datetime] = None


class TraceCollector:
    """SSOT Trace Collector for distributed tracing.
    
    This class provides comprehensive distributed tracing capabilities,
    enabling detailed performance monitoring and request tracking across
    the entire Netra platform.
    
    Key Features:
    - Start and end trace collection
    - Span management and hierarchy tracking
    - Real-time trace statistics  
    - Integration with observability pipeline
    - Redis-backed trace storage for real services
    """
    
    def __init__(self):
        """Initialize the trace collector."""
        self.active_traces: Dict[str, TraceSpan] = {}
        self.stats = TraceStats()
        self.redis_key_prefix = "netra:traces"
        logger.info("TraceCollector initialized for distributed tracing")
    
    async def start_trace(
        self,
        operation_name: str = "unknown_operation",
        parent_trace_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Start a new trace.
        
        Args:
            operation_name: Name of the operation being traced
            parent_trace_id: Optional parent trace ID for nested operations
            tags: Optional tags to attach to the trace
            
        Returns:
            Unique trace ID
        """
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_trace_id,
            operation_name=operation_name,
            start_time=datetime.now(timezone.utc),
            tags=tags or {},
            status="started"
        )
        
        self.active_traces[trace_id] = span
        self.stats.total_traces += 1
        self.stats.active_traces += 1
        self.stats.last_trace_time = datetime.now(timezone.utc)
        
        # Store in Redis for real services integration
        try:
            redis_key = f"{self.redis_key_prefix}:active:{trace_id}"
            trace_data = {
                "trace_id": trace_id,
                "span_id": span_id,
                "operation_name": operation_name,
                "start_time": span.start_time.isoformat(),
                "tags": tags or {},
                "status": "started"
            }
            await redis_manager.set_json(redis_key, trace_data, expire=3600)  # 1 hour TTL
            logger.debug(f"Started trace {trace_id} for operation: {operation_name}")
        except Exception as e:
            logger.warning(f"Failed to store trace {trace_id} in Redis: {e}")
        
        return trace_id
    
    async def end_trace(
        self,
        trace_id: str,
        status: str = "ok",
        final_tags: Optional[Dict[str, str]] = None
    ) -> Optional[TraceSpan]:
        """End a trace.
        
        Args:
            trace_id: Trace ID to end
            status: Final status of the trace ("ok", "error", "timeout")  
            final_tags: Optional final tags to add to the trace
            
        Returns:
            Completed TraceSpan if successful, None if trace not found
        """
        span = self.active_traces.get(trace_id)
        if not span:
            logger.warning(f"Attempted to end non-existent trace: {trace_id}")
            return None
        
        # Finish the span
        span.finish()
        span.status = status
        
        if final_tags:
            span.tags.update(final_tags)
        
        # Update statistics
        self.stats.active_traces -= 1
        if status == "ok":
            self.stats.completed_traces += 1
        else:
            self.stats.failed_traces += 1
        
        # Calculate average duration
        if span.duration_ms is not None:
            total_completed = self.stats.completed_traces + self.stats.failed_traces
            if total_completed > 0:
                current_avg = self.stats.average_duration_ms
                self.stats.average_duration_ms = (
                    (current_avg * (total_completed - 1) + span.duration_ms) / total_completed
                )
        
        # Store completed trace in Redis
        try:
            # Remove from active
            active_key = f"{self.redis_key_prefix}:active:{trace_id}"
            await redis_manager.delete_key(active_key)
            
            # Store as completed
            completed_key = f"{self.redis_key_prefix}:completed:{trace_id}"
            trace_data = {
                "trace_id": span.trace_id,
                "span_id": span.span_id,
                "operation_name": span.operation_name,
                "start_time": span.start_time.isoformat() if span.start_time else None,
                "end_time": span.end_time.isoformat() if span.end_time else None,
                "duration_ms": span.duration_ms,
                "tags": span.tags,
                "status": span.status,
                "logs": span.logs
            }
            await redis_manager.set_json(completed_key, trace_data, expire=86400)  # 24 hours TTL
            
            logger.debug(
                f"Completed trace {trace_id}: {span.operation_name} "
                f"({span.duration_ms:.2f}ms, status: {status})"
            )
        except Exception as e:
            logger.warning(f"Failed to store completed trace {trace_id} in Redis: {e}")
        
        # Remove from active traces
        del self.active_traces[trace_id]
        
        return span
    
    async def add_trace_log(
        self,
        trace_id: str, 
        level: str,
        message: str,
        fields: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a log entry to an active trace.
        
        Args:
            trace_id: Trace ID to add log to
            level: Log level (info, warning, error, debug)
            message: Log message
            fields: Optional additional fields
            
        Returns:
            True if log was added successfully, False otherwise
        """
        span = self.active_traces.get(trace_id)
        if not span:
            return False
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "fields": fields or {}
        }
        
        span.logs.append(log_entry)
        logger.debug(f"Added log to trace {trace_id}: {level} - {message}")
        return True
    
    async def get_trace_stats(self) -> TraceStats:
        """Get current trace collection statistics.
        
        Returns:
            Current trace statistics
        """
        return self.stats
    
    async def get_active_traces(self) -> List[Dict[str, Any]]:
        """Get list of currently active traces.
        
        Returns:
            List of active trace summaries
        """
        traces = []
        for trace_id, span in self.active_traces.items():
            current_time = datetime.now(timezone.utc)
            duration = None
            if span.start_time:
                duration = (current_time - span.start_time).total_seconds() * 1000
            
            traces.append({
                "trace_id": trace_id,
                "operation_name": span.operation_name,
                "start_time": span.start_time.isoformat() if span.start_time else None,
                "duration_ms": duration,
                "status": span.status,
                "tags": span.tags
            })
        
        return traces
    
    async def cleanup_stale_traces(self, max_age_minutes: int = 60) -> int:
        """Clean up stale traces that have been active too long.
        
        Args:
            max_age_minutes: Maximum age in minutes before a trace is considered stale
            
        Returns:
            Number of traces cleaned up
        """
        if not self.active_traces:
            return 0
        
        current_time = datetime.now(timezone.utc)
        max_age = timedelta(minutes=max_age_minutes)
        stale_traces = []
        
        for trace_id, span in self.active_traces.items():
            if span.start_time and (current_time - span.start_time) > max_age:
                stale_traces.append(trace_id)
        
        cleaned_count = 0
        for trace_id in stale_traces:
            await self.end_trace(trace_id, status="timeout")
            cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} stale traces")
        
        return cleaned_count
    
    async def get_trace_by_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get trace details by ID (active or completed).
        
        Args:
            trace_id: Trace ID to retrieve
            
        Returns:
            Trace data if found, None otherwise
        """
        # Check active traces first
        active_span = self.active_traces.get(trace_id)
        if active_span:
            current_time = datetime.now(timezone.utc)
            duration = None
            if active_span.start_time:
                duration = (current_time - active_span.start_time).total_seconds() * 1000
            
            return {
                "trace_id": trace_id,
                "span_id": active_span.span_id,
                "operation_name": active_span.operation_name,
                "start_time": active_span.start_time.isoformat() if active_span.start_time else None,
                "duration_ms": duration,
                "tags": active_span.tags,
                "logs": active_span.logs,
                "status": active_span.status,
                "is_active": True
            }
        
        # Check completed traces in Redis
        try:
            completed_key = f"{self.redis_key_prefix}:completed:{trace_id}"
            trace_data = await redis_manager.get_json(completed_key)
            if trace_data:
                trace_data["is_active"] = False
                return trace_data
        except Exception as e:
            logger.warning(f"Failed to retrieve completed trace {trace_id} from Redis: {e}")
        
        return None


# Create global instance for SSOT access
trace_collector = TraceCollector()

# Export for direct module access
__all__ = ["TraceCollector", "TraceSpan", "TraceStats", "trace_collector"]
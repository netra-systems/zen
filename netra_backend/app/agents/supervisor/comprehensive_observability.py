"""Comprehensive Observability for Supervisor.

Implements complete observability with metrics, logs, and traces.
Business Value: Enables real-time monitoring and performance optimization.
"""

import time
import json
from typing import Dict, Any, Optional
from datetime import datetime

from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult

logger = central_logger.get_logger(__name__)


class SupervisorObservability:
    """Comprehensive observability for supervisor operations."""
    
    def __init__(self):
        self._metrics: Dict[str, Any] = self._initialize_metrics()
        self._traces: Dict[str, Dict[str, Any]] = {}
        self._performance_history: list = []
    
    def _initialize_metrics(self) -> Dict[str, Any]:
        """Initialize metrics tracking."""
        return {
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "average_latency_ms": 0.0,
            "agent_execution_counts": {},
            "error_counts_by_agent": {},
            "circuit_breaker_trips": 0
        }
    
    def start_workflow_trace(self, context: ExecutionContext) -> None:
        """Start distributed trace for workflow."""
        self._traces[context.run_id] = {
            "trace_id": context.run_id,
            "start_time": time.time(),
            "agent_name": context.agent_name,
            "user_id": context.user_id,
            "thread_id": context.thread_id,
            "spans": [],
            "status": "started"
        }
        
        self._log_trace_event("workflow_started", context.run_id, {
            "agent_name": context.agent_name,
            "user_id": context.user_id,
            "thread_id": context.thread_id
        })
    
    def add_span(self, trace_id: str, span_name: str, 
                duration_ms: float, metadata: Dict[str, Any]) -> None:
        """Add span to trace."""
        if trace_id not in self._traces:
            return
        
        span = {
            "span_name": span_name,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
            "metadata": metadata
        }
        
        self._traces[trace_id]["spans"].append(span)
        self._log_trace_event("span_added", trace_id, span)
    
    def complete_workflow_trace(self, context: ExecutionContext, 
                               result: ExecutionResult) -> None:
        """Complete workflow trace."""
        if context.run_id not in self._traces:
            return
        
        trace = self._traces[context.run_id]
        trace["end_time"] = time.time()
        trace["total_duration_ms"] = (trace["end_time"] - trace["start_time"]) * 1000
        trace["status"] = "completed" if result.success else "failed"
        trace["error"] = result.error if not result.success else None
        
        self._update_metrics_from_trace(trace)
        self._log_trace_event("workflow_completed", context.run_id, {
            "success": result.success,
            "total_duration_ms": trace["total_duration_ms"],
            "span_count": len(trace["spans"])
        })
        
        # Clean up trace after logging
        del self._traces[context.run_id]
    
    def _update_metrics_from_trace(self, trace: Dict[str, Any]) -> None:
        """Update metrics from completed trace."""
        self._metrics["total_workflows"] += 1
        
        if trace["status"] == "completed":
            self._metrics["successful_workflows"] += 1
        else:
            self._metrics["failed_workflows"] += 1
        
        # Update average latency
        self._update_average_latency(trace["total_duration_ms"])
        
        # Update agent execution counts
        for span in trace["spans"]:
            agent_name = span["metadata"].get("agent_name", "unknown")
            self._metrics["agent_execution_counts"][agent_name] = \
                self._metrics["agent_execution_counts"].get(agent_name, 0) + 1
    
    def _update_average_latency(self, duration_ms: float) -> None:
        """Update average latency calculation."""
        total_workflows = self._metrics["total_workflows"]
        current_avg = self._metrics["average_latency_ms"]
        
        # Incremental average calculation
        self._metrics["average_latency_ms"] = \
            ((current_avg * (total_workflows - 1)) + duration_ms) / total_workflows
    
    def record_agent_error(self, agent_name: str, error: str) -> None:
        """Record agent execution error."""
        if agent_name not in self._metrics["error_counts_by_agent"]:
            self._metrics["error_counts_by_agent"][agent_name] = 0
        
        self._metrics["error_counts_by_agent"][agent_name] += 1
        
        self._log_error_event(agent_name, error)
    
    def record_circuit_breaker_trip(self, agent_name: str) -> None:
        """Record circuit breaker trip."""
        self._metrics["circuit_breaker_trips"] += 1
        
        logger.warning(f"Circuit breaker tripped for agent: {agent_name}")
    
    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": self._metrics.copy(),
            "active_traces": len(self._traces),
            "performance_percentiles": self._calculate_performance_percentiles()
        }
    
    def _calculate_performance_percentiles(self) -> Dict[str, float]:
        """Calculate performance percentiles from history."""
        if not self._performance_history:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        
        sorted_times = sorted(self._performance_history)
        n = len(sorted_times)
        
        return {
            "p50": sorted_times[int(n * 0.5)],
            "p95": sorted_times[int(n * 0.95)],
            "p99": sorted_times[int(n * 0.99)]
        }
    
    def _log_trace_event(self, event: str, trace_id: str, data: Dict[str, Any]) -> None:
        """Log trace event with structured data."""
        log_data = {
            "event": event,
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat(),
            **data
        }
        logger.info(f"Supervisor trace event: {json.dumps(log_data)}")
    
    def _log_error_event(self, agent_name: str, error: str) -> None:
        """Log error event with structured data."""
        log_data = {
            "event": "agent_error",
            "agent_name": agent_name,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.error(f"Supervisor agent error: {json.dumps(log_data)}")
    
    def reset_metrics(self) -> None:
        """Reset metrics for fresh start."""
        self._metrics = self._initialize_metrics()
        self._traces.clear()
        self._performance_history.clear()
        logger.info("Supervisor observability metrics reset")

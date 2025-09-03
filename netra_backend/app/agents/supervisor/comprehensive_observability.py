"""Comprehensive Observability for Supervisor.

Implements complete observability with metrics, logs, and traces.
Enhanced with detailed performance timing and metrics aggregation.
Business Value: Enables real-time monitoring and performance optimization.
BVJ: Platform | Development Velocity | 30% performance improvement through visibility
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.core.serialization.unified_json_handler import backend_json_handler
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.performance_metrics import (
    EnhancedExecutionTimingCollector,
    PerformanceMetric,
    MetricType,
    TimingBreakdown,
    PerformanceAnalyzer
)
from netra_backend.app.monitoring.metrics_aggregator import (
    get_global_aggregator,
    AggregationWindow,
    ResourceMetrics
)

logger = central_logger.get_logger(__name__)


class SupervisorObservability:
    """Comprehensive observability for supervisor operations."""
    
    def __init__(self):
        self._metrics: Dict[str, Any] = self._initialize_metrics()
        self._traces: Dict[str, Dict[str, Any]] = {}
        self._performance_history: list = []
        self._timing_collectors: Dict[str, EnhancedExecutionTimingCollector] = {}
        self._performance_analyzer = PerformanceAnalyzer()
        self._metrics_aggregator = get_global_aggregator()
    
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
        """Start distributed trace for workflow with enhanced timing."""
        self._traces[context.run_id] = {
            "trace_id": context.run_id,
            "start_time": time.time(),
            "agent_name": context.agent_name,
            "user_id": context.user_id,
            "thread_id": context.thread_id,
            "spans": [],
            "status": "started"
        }
        
        # Initialize enhanced timing collector for this execution
        execution_id = UUID(context.run_id) if isinstance(context.run_id, str) else context.run_id
        timing_collector = EnhancedExecutionTimingCollector(
            execution_id=execution_id,
            agent_name=context.agent_name
        )
        self._timing_collectors[context.run_id] = timing_collector
        
        # Start initialization phase
        timing_collector.start_phase("initialization")
        
        # Get thread_id safely
        thread_id = None
        if hasattr(context, '_thread_id'):
            thread_id = context._thread_id
        elif context.state and hasattr(context.state, 'thread_id'):
            thread_id = context.state.thread_id
        
        self._log_trace_event("workflow_started", context.run_id, {
            "agent_name": context.agent_name,
            "user_id": context.user_id,
            "thread_id": thread_id
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
        """Complete workflow trace with enhanced metrics."""
        if context.run_id not in self._traces:
            return
        
        trace = self._traces[context.run_id]
        trace["end_time"] = time.time()
        trace["total_duration_ms"] = (trace["end_time"] - trace["start_time"]) * 1000
        trace["status"] = "completed" if result.success else "failed"
        trace["error"] = result.error if not result.success else None
        
        # Complete timing collection
        if context.run_id in self._timing_collectors:
            timing_collector = self._timing_collectors[context.run_id]
            
            # Get timing breakdown
            breakdown = timing_collector.get_breakdown()
            trace["timing_breakdown"] = breakdown.to_dict()
            
            # Add timing breakdown to aggregator
            self._metrics_aggregator.add_timing_breakdown(breakdown)
            
            # Analyze performance
            analysis = self._performance_analyzer.analyze_timing_breakdown(breakdown)
            if analysis["bottlenecks"]:
                logger.warning(f"Performance bottlenecks detected: {analysis['bottlenecks']}")
            
            # Export metrics to aggregator
            for metric in timing_collector.metrics:
                self._metrics_aggregator.add_metric(metric)
            
            # Clean up collector
            del self._timing_collectors[context.run_id]
        
        self._update_metrics_from_trace(trace)
        self._log_trace_event("workflow_completed", context.run_id, {
            "success": result.success,
            "total_duration_ms": trace["total_duration_ms"],
            "span_count": len(trace["spans"]),
            "timing_breakdown": trace.get("timing_breakdown", {})
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data
        }
        logger.info(f"Supervisor trace event: {backend_json_handler.dumps(log_data)}")
    
    def _log_error_event(self, agent_name: str, error: str) -> None:
        """Log error event with structured data."""
        log_data = {
            "event": "agent_error",
            "agent_name": agent_name,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        logger.error(f"Supervisor agent error: {backend_json_handler.dumps(log_data)}")
    
    def reset_metrics(self) -> None:
        """Reset metrics for fresh start."""
        self._metrics = self._initialize_metrics()
        self._traces.clear()
        self._performance_history.clear()
        self._timing_collectors.clear()
        logger.info("Supervisor observability metrics reset")
    
    # Enhanced timing methods
    def start_phase(self, trace_id: str, phase_name: str, 
                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """Start a timing phase for an execution.
        
        Args:
            trace_id: Trace/execution ID
            phase_name: Name of the phase (e.g., 'tool_execution', 'llm_processing')
            metadata: Optional metadata for the phase
        """
        if trace_id in self._timing_collectors:
            self._timing_collectors[trace_id].start_phase(phase_name, metadata)
            logger.debug(f"Started phase '{phase_name}' for trace {trace_id}")
    
    def stop_phase(self, trace_id: str, phase_name: str) -> Optional[float]:
        """Stop a timing phase and return duration.
        
        Args:
            trace_id: Trace/execution ID
            phase_name: Name of the phase to stop
            
        Returns:
            Duration in milliseconds or None if not found
        """
        if trace_id in self._timing_collectors:
            duration = self._timing_collectors[trace_id].stop_phase(phase_name)
            if duration:
                logger.debug(f"Completed phase '{phase_name}' for trace {trace_id}: {duration:.2f}ms")
            return duration
        return None
    
    def record_first_token(self, trace_id: str) -> Optional[float]:
        """Record time to first token for an execution.
        
        Args:
            trace_id: Trace/execution ID
            
        Returns:
            TTFT in milliseconds or None
        """
        if trace_id in self._timing_collectors:
            ttft = self._timing_collectors[trace_id].record_first_token()
            logger.info(f"Time to First Token for {trace_id}: {ttft:.2f}ms")
            return ttft
        return None
    
    def add_performance_metric(self, trace_id: str, metric_type: MetricType, 
                              value: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a custom performance metric.
        
        Args:
            trace_id: Trace/execution ID
            metric_type: Type of metric
            value: Metric value
            metadata: Optional metadata
        """
        if trace_id in self._timing_collectors:
            self._timing_collectors[trace_id].add_metric(metric_type, value, metadata)
        
        # Also add directly to aggregator for immediate availability
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            correlation_id=trace_id,
            metadata=metadata or {}
        )
        self._metrics_aggregator.add_metric(metric)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary.
        
        Returns:
            Performance summary including timing breakdowns and trends
        """
        base_metrics = self.get_metrics_snapshot()
        perf_summary = self._metrics_aggregator.get_performance_summary()
        
        return {
            **base_metrics,
            "performance": perf_summary,
            "bottlenecks": self._metrics_aggregator.get_bottlenecks(),
            "active_timings": len(self._timing_collectors)
        }
    
    def get_timing_breakdown(self, trace_id: str) -> Optional[TimingBreakdown]:
        """Get timing breakdown for a specific execution.
        
        Args:
            trace_id: Trace/execution ID
            
        Returns:
            TimingBreakdown or None if not found
        """
        if trace_id in self._timing_collectors:
            return self._timing_collectors[trace_id].get_breakdown()
        return None
    
    def record_resource_metrics(self, cpu_percent: float, memory_mb: float, 
                               thread_count: int) -> None:
        """Record system resource metrics.
        
        Args:
            cpu_percent: CPU utilization percentage
            memory_mb: Memory usage in MB
            thread_count: Number of active threads
        """
        metrics = ResourceMetrics(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            memory_percent=(memory_mb / 16384) * 100,  # Assume 16GB total
            thread_count=thread_count
        )
        self._metrics_aggregator.add_resource_metrics(metrics)

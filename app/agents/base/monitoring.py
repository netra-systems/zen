"""Execution Monitoring and Telemetry System

Comprehensive monitoring for agent execution performance:
- Execution time tracking
- Error rate monitoring  
- Health status reporting
- Performance metrics collection
- WebSocket notification patterns

Business Value: Enables 15-20% performance optimization through monitoring.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque

from app.logging_config import central_logger
from app.agents.base.interface import ExecutionContext, ExecutionResult

logger = central_logger.get_logger(__name__)


@dataclass
class ExecutionMetrics:
    """Execution metrics data structure."""
    execution_time_ms: float = 0.0
    llm_tokens_used: int = 0
    database_queries: int = 0
    websocket_messages_sent: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    retry_count: int = 0
    circuit_breaker_trips: int = 0


@dataclass
class PerformanceStats:
    """Performance statistics for monitoring."""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_execution_time_ms: float = 0.0
    p95_execution_time_ms: float = 0.0
    error_rate: float = 0.0
    last_execution_time: Optional[datetime] = None
    execution_times: deque = field(default_factory=lambda: deque(maxlen=1000))


class ExecutionMonitor:
    """Monitors agent execution performance and health.
    
    Tracks execution metrics, performance statistics, and health indicators
    across all agent executions for optimization insights.
    """
    
    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        self._agent_stats: Dict[str, PerformanceStats] = defaultdict(PerformanceStats)
        self._active_executions: Dict[str, float] = {}
        self._global_metrics = ExecutionMetrics()
        self._health_indicators = self._initialize_health_indicators()
        
    def _initialize_health_indicators(self) -> Dict[str, Any]:
        """Initialize health indicator tracking."""
        return {
            "system_start_time": datetime.utcnow(),
            "total_executions": 0,
            "active_executions": 0,
            "circuit_breaker_status": "healthy",
            "error_rate_threshold": 0.05  # 5%
        }
    
    def start_execution(self, context: ExecutionContext) -> None:
        """Record execution start."""
        self._active_executions[context.run_id] = time.time()
        self._health_indicators["active_executions"] += 1
        self._log_execution_start(context)
    
    def complete_execution(self, context: ExecutionContext, 
                         result: ExecutionResult) -> None:
        """Record execution completion with metrics."""
        self._record_execution_completion(context, result)
        self._update_agent_stats(context, result)
        self._update_global_metrics(result)
        self._cleanup_active_execution(context)
    
    def record_execution_time(self, context: ExecutionContext, 
                            execution_time: float) -> None:
        """Record execution time for performance tracking."""
        stats = self._agent_stats[context.agent_name]
        stats.execution_times.append(execution_time * 1000)  # Convert to ms
        self._update_timing_statistics(stats)
    
    def record_error(self, context: ExecutionContext, error: Exception) -> None:
        """Record execution error for monitoring."""
        stats = self._agent_stats[context.agent_name]
        stats.failed_executions += 1
        self._update_error_rate(stats)
        self._log_execution_error(context, error)
    
    def get_execution_metrics(self, context: ExecutionContext) -> Dict[str, Any]:
        """Get execution metrics for specific context."""
        stats = self._agent_stats[context.agent_name]
        return {
            "execution_time_ms": self._get_current_execution_time(context),
            "total_executions": stats.total_executions,
            "success_rate": self._calculate_success_rate(stats),
            "average_time_ms": stats.average_execution_time_ms,
            "error_rate": stats.error_rate
        }
    
    def get_agent_performance_stats(self, agent_name: str) -> Dict[str, Any]:
        """Get comprehensive performance stats for agent."""
        stats = self._agent_stats[agent_name]
        return {
            "agent_name": agent_name,
            "total_executions": stats.total_executions,
            "successful_executions": stats.successful_executions,
            "failed_executions": stats.failed_executions,
            "success_rate": self._calculate_success_rate(stats),
            "error_rate": stats.error_rate,
            "average_execution_time_ms": stats.average_execution_time_ms,
            "p95_execution_time_ms": stats.p95_execution_time_ms,
            "last_execution": stats.last_execution_time
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        return {
            "status": self._determine_overall_health(),
            "metrics": self._get_health_metrics(),
            "indicators": self._health_indicators.copy(),
            "agent_health": self._get_agent_health_summary()
        }
    
    def get_global_metrics(self) -> ExecutionMetrics:
        """Get global execution metrics."""
        return self._global_metrics
    
    def reset_metrics(self, agent_name: Optional[str] = None) -> None:
        """Reset metrics for specific agent or all agents."""
        if agent_name:
            self._agent_stats[agent_name] = PerformanceStats()
        else:
            self._agent_stats.clear()
            self._global_metrics = ExecutionMetrics()
            self._health_indicators = self._initialize_health_indicators()
    
    def _record_execution_completion(self, context: ExecutionContext,
                                   result: ExecutionResult) -> None:
        """Record execution completion details."""
        stats = self._agent_stats[context.agent_name]
        stats.total_executions += 1
        stats.last_execution_time = datetime.utcnow()
        
        if result.success:
            stats.successful_executions += 1
        else:
            stats.failed_executions += 1
    
    def _update_agent_stats(self, context: ExecutionContext,
                          result: ExecutionResult) -> None:
        """Update agent-specific statistics."""
        stats = self._agent_stats[context.agent_name]
        self._update_error_rate(stats)
        
        if result.execution_time_ms > 0:
            stats.execution_times.append(result.execution_time_ms)
            self._update_timing_statistics(stats)
    
    def _update_global_metrics(self, result: ExecutionResult) -> None:
        """Update global execution metrics."""
        self._health_indicators["total_executions"] += 1
        
        if result.metrics:
            self._accumulate_metrics(result.metrics)
        
        # Update circuit breaker metrics if present
        if result.metrics and result.metrics.get("circuit_breaker_trips", 0) > 0:
            self._global_metrics.circuit_breaker_trips += 1
    
    def _accumulate_metrics(self, metrics: Dict[str, Any]) -> None:
        """Accumulate metrics from execution result."""
        if "llm_tokens_used" in metrics:
            self._global_metrics.llm_tokens_used += metrics["llm_tokens_used"]
        if "database_queries" in metrics:
            self._global_metrics.database_queries += metrics["database_queries"]
        if "websocket_messages_sent" in metrics:
            self._global_metrics.websocket_messages_sent += metrics["websocket_messages_sent"]
    
    def _cleanup_active_execution(self, context: ExecutionContext) -> None:
        """Clean up active execution tracking."""
        if context.run_id in self._active_executions:
            del self._active_executions[context.run_id]
        self._health_indicators["active_executions"] -= 1
    
    def _update_timing_statistics(self, stats: PerformanceStats) -> None:
        """Update timing statistics for performance analysis."""
        times = list(stats.execution_times)
        if times:
            stats.average_execution_time_ms = sum(times) / len(times)
            stats.p95_execution_time_ms = self._calculate_percentile(times, 95)
    
    def _update_error_rate(self, stats: PerformanceStats) -> None:
        """Update error rate calculation."""
        if stats.total_executions > 0:
            stats.error_rate = stats.failed_executions / stats.total_executions
    
    def _calculate_success_rate(self, stats: PerformanceStats) -> float:
        """Calculate success rate for agent."""
        if stats.total_executions == 0:
            return 0.0
        return stats.successful_executions / stats.total_executions
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value from list."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _get_current_execution_time(self, context: ExecutionContext) -> float:
        """Get current execution time for active execution."""
        start_time = self._active_executions.get(context.run_id)
        if start_time:
            return (time.time() - start_time) * 1000
        return 0.0
    
    def _determine_overall_health(self) -> str:
        """Determine overall system health status."""
        total_executions = self._health_indicators["total_executions"]
        if total_executions == 0:
            return "healthy"
        
        # Calculate global error rate
        total_errors = sum(stats.failed_executions for stats in self._agent_stats.values())
        global_error_rate = total_errors / total_executions
        
        threshold = self._health_indicators["error_rate_threshold"]
        if global_error_rate > threshold:
            return "degraded"
        
        return "healthy"
    
    def _get_health_metrics(self) -> Dict[str, float]:
        """Get key health metrics."""
        total_executions = self._health_indicators["total_executions"]
        if total_executions == 0:
            return {"global_error_rate": 0.0, "avg_execution_time_ms": 0.0}
        
        total_errors = sum(stats.failed_executions for stats in self._agent_stats.values())
        all_times = []
        for stats in self._agent_stats.values():
            all_times.extend(stats.execution_times)
        
        return {
            "global_error_rate": total_errors / total_executions,
            "avg_execution_time_ms": sum(all_times) / len(all_times) if all_times else 0.0,
            "active_executions": self._health_indicators["active_executions"]
        }
    
    def _get_agent_health_summary(self) -> Dict[str, str]:
        """Get health summary for all agents."""
        summary = {}
        for agent_name, stats in self._agent_stats.items():
            if stats.error_rate > self._health_indicators["error_rate_threshold"]:
                summary[agent_name] = "degraded"
            else:
                summary[agent_name] = "healthy"
        return summary
    
    def _log_execution_start(self, context: ExecutionContext) -> None:
        """Log execution start details."""
        logger.debug(f"Starting execution for {context.agent_name} (run_id: {context.run_id})")
    
    def _log_execution_error(self, context: ExecutionContext, error: Exception) -> None:
        """Log execution error details."""
        logger.error(f"Execution error in {context.agent_name}: {error}")


# Import MetricsCollector from canonical location - CONSOLIDATED
from app.monitoring.metrics_collector import MetricsCollector as CoreMetricsCollector

class MetricsCollector:
    """Agent-specific metrics collector with ExecutionMonitor aggregation."""
    
    def __init__(self):
        self.monitors: List[ExecutionMonitor] = []
        self.core_collector = CoreMetricsCollector()
        
    def add_monitor(self, monitor: ExecutionMonitor) -> None:
        """Add monitor to collection."""
        self.monitors.append(monitor)
    
    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics from all monitors and core collector."""
        agent_metrics = self._get_agent_specific_metrics()
        
        # Get core system metrics
        try:
            core_metrics = self.core_collector.get_metric_summary("system.cpu_percent")
            agent_metrics["system_metrics"] = core_metrics
        except Exception:
            # Core collector may not be started yet
            pass
        
        return agent_metrics
    
    def _get_agent_specific_metrics(self) -> Dict[str, Any]:
        """Get agent-specific metrics from monitors."""
        if not self.monitors:
            return {}
        
        # Aggregate metrics across all monitors
        total_metrics = ExecutionMetrics()
        for monitor in self.monitors:
            global_metrics = monitor.get_global_metrics()
            total_metrics.llm_tokens_used += global_metrics.llm_tokens_used
            total_metrics.database_queries += global_metrics.database_queries
            total_metrics.websocket_messages_sent += global_metrics.websocket_messages_sent
            total_metrics.circuit_breaker_trips += global_metrics.circuit_breaker_trips
        
        return {
            "total_llm_tokens": total_metrics.llm_tokens_used,
            "total_db_queries": total_metrics.database_queries,
            "total_websocket_messages": total_metrics.websocket_messages_sent,
            "total_circuit_breaker_trips": total_metrics.circuit_breaker_trips,
            "monitors_count": len(self.monitors)
        }
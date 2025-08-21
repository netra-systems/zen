"""
Metric aggregator module for calculating and updating metrics.
Handles aggregation operations with 25-line function limit.
"""

from collections import defaultdict, deque
from typing import Any, Dict

from netra_backend.app.services.metrics.agent_metrics_models import (
    AgentMetrics,
    AgentOperationRecord,
)


class MetricAggregator:
    """Handles metric aggregation and calculations."""
    
    def __init__(self, agent_metrics: Dict[str, AgentMetrics], performance_windows: Dict[str, deque]):
        self._agent_metrics = agent_metrics
        self._performance_windows = performance_windows
    
    def update_execution_time_avg(self, agent_name: str, execution_time_ms: float) -> None:
        """Update rolling average execution time."""
        window_key = self._get_execution_time_key(agent_name)
        self._add_to_performance_window(window_key, execution_time_ms)
        self._calculate_and_update_avg(agent_name, window_key)
    
    def _get_execution_time_key(self, agent_name: str) -> str:
        """Get performance window key for execution time."""
        return f"{agent_name}:execution_time"
    
    def _add_to_performance_window(self, window_key: str, value: float) -> None:
        """Add value to performance window."""
        self._performance_windows[window_key].append(value)
    
    def _calculate_and_update_avg(self, agent_name: str, window_key: str) -> None:
        """Calculate new average and update agent metrics."""
        times = list(self._performance_windows[window_key])
        if times:
            self._agent_metrics[agent_name].avg_execution_time_ms = sum(times) / len(times)
    
    def calculate_operation_stats(self) -> Dict[str, Any]:
        """Calculate operation-related statistics."""
        total_ops = self._sum_metric_across_agents('total_operations')
        total_failures = self._sum_metric_across_agents('failed_operations')
        error_rate = self._calculate_system_error_rate(total_ops, total_failures)
        return self._build_operation_stats_dict(total_ops, total_failures, error_rate)
    
    def _sum_metric_across_agents(self, metric_name: str) -> int:
        """Sum a metric value across all agents."""
        return sum(getattr(m, metric_name) for m in self._agent_metrics.values())
    
    def _calculate_system_error_rate(self, total_ops: int, total_failures: int) -> float:
        """Calculate system-wide error rate."""
        return total_failures / total_ops if total_ops > 0 else 0.0
    
    def _build_operation_stats_dict(self, total_ops: int, total_failures: int, error_rate: float) -> Dict[str, Any]:
        """Build operation statistics dictionary."""
        return {
            "total_operations": total_ops,
            "total_failures": total_failures,
            "system_error_rate": error_rate
        }
    
    def calculate_agent_stats(self) -> Dict[str, Any]:
        """Calculate agent-related statistics."""
        from .metric_reader import MetricReader
        reader = MetricReader(deque(), self._agent_metrics)
        active_agents = reader.count_active_agents()
        unhealthy_agents = reader.count_unhealthy_agents()
        return {"active_agents": active_agents, "unhealthy_agents": unhealthy_agents}
    
    def calculate_system_stats(self, active_operations_count: int, buffer_utilization: float) -> Dict[str, Any]:
        """Calculate system-level statistics."""
        return {
            "active_operations": active_operations_count,
            "buffer_utilization": buffer_utilization
        }
    
    def get_or_init_agent_metrics(self, agent_name: str) -> AgentMetrics:
        """Get or initialize agent metrics."""
        metrics = self._agent_metrics[agent_name]
        if not metrics.agent_name:
            metrics.agent_name = agent_name
        return metrics
"""WebSocket Performance Monitor Metrics Processing.

Handles metrics calculation and summary generation.
"""

import statistics
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, List

from netra_backend.app.logging_config import central_logger
from netra_backend.app.performance_monitor_collector import MetricCollector

logger = central_logger.get_logger(__name__)


class PerformanceMetricsProcessor:
    """Processes and summarizes performance metrics."""
    
    def __init__(self, metric_collector: MetricCollector):
        self.metric_collector = metric_collector
        self.message_response_times: deque = deque(maxlen=1000)
        self.throughput_tracker = deque(maxlen=60)
        self.connection_stats = defaultdict(dict)
        self.error_counts = defaultdict(int)
    
    def get_core_performance_metrics(self) -> Dict[str, Any]:
        """Get core performance metrics."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_time": self._get_response_time_stats(),
            "throughput_messages_per_second": self._calculate_current_throughput(),
            "total_connections": len(self.connection_stats)
        }
    
    def get_supplemental_performance_metrics(self, alert_summary: Dict[str, Any], 
                                           monitoring_active: bool, 
                                           coverage_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Get supplemental performance metrics."""
        return {
            "active_alerts": alert_summary,
            "system_metrics": self._get_system_metrics(),
            "error_counts": dict(self.error_counts),
            "monitoring_active": monitoring_active,
            "monitoring_coverage": coverage_summary
        }
    
    def _get_response_time_stats(self) -> Dict[str, float]:
        """Get response time statistics."""
        if not self.message_response_times:
            return {}
        times = list(self.message_response_times)
        return self._calculate_response_time_metrics(times)
    
    def _calculate_response_time_metrics(self, times: List[float]) -> Dict[str, float]:
        """Calculate response time metrics from times list."""
        return {
            "average_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": sorted(times)[int(len(times) * 0.95)],
            "max_ms": max(times)
        }
    
    def _calculate_current_throughput(self) -> float:
        """Calculate current message throughput."""
        if not self.throughput_tracker:
            return 0.0
        recent_throughput = self._get_recent_throughput()
        return sum(recent_throughput) / 60.0 if recent_throughput else 0.0
    
    def _get_recent_throughput(self) -> List[int]:
        """Get throughput data from last minute."""
        return [count for timestamp, count in self.throughput_tracker 
                if timestamp > time.time() - 60]
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics summary."""
        return {
            "memory_usage_mb": self.metric_collector.get_metric_stats("system.memory_usage", 1),
            "cpu_usage_percent": self.metric_collector.get_metric_stats("system.cpu_usage", 1)
        }
    
    def collect_metrics_summary(self, duration_minutes: int) -> Dict[str, Any]:
        """Collect summary of all metrics."""
        metrics_summary = {}
        for metric_name in self.metric_collector.metrics.keys():
            stats = self.metric_collector.get_metric_stats(metric_name, duration_minutes)
            if stats:
                metrics_summary[metric_name] = self._format_metric_data(metric_name, stats, duration_minutes)
        return metrics_summary
    
    def _format_metric_data(self, metric_name: str, stats: Dict[str, float], duration_minutes: int) -> Dict[str, Any]:
        """Format metric data for export."""
        return {
            "type": self.metric_collector.metric_types.get(metric_name, "unknown").value,
            "stats": stats,
            "values": self.metric_collector.get_metric_values(metric_name, duration_minutes)[-100:]
        }
    
    def count_total_metrics(self) -> int:
        """Count total metrics collected."""
        return sum(len(points) for points in self.metric_collector.metrics.values())
    
    def reset_metrics_tracking(self) -> None:
        """Reset performance tracking structures."""
        self.connection_stats.clear()
        self.message_response_times.clear()
        self.error_counts.clear()
        self.throughput_tracker.clear()
"""WebSocket Memory Metrics Collection and Health Monitoring.

Handles memory metrics collection, health checking, and statistics reporting
for WebSocket memory management system.
"""

import time
from datetime import datetime, timezone
from typing import Dict, List, Any
from dataclasses import dataclass, field

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class MemoryMetrics:
    """Memory usage metrics."""
    total_memory_mb: float = 0.0
    connection_memory_mb: float = 0.0
    message_buffer_mb: float = 0.0
    active_connections: int = 0
    total_allocations: int = 0
    gc_collections: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryMetricsCollector:
    """Collects and manages memory metrics for WebSocket connections."""
    
    def __init__(self, memory_tracker):
        self.memory_tracker = memory_tracker
        self.metrics_history: List[MemoryMetrics] = []
        
    def collect_current_metrics(self) -> MemoryMetrics:
        """Collect current memory metrics efficiently."""
        connection_memory_mb, total_memory_mb = self._calculate_memory_values()
        return self._create_memory_metrics_object(connection_memory_mb, total_memory_mb)
    
    def _calculate_memory_values(self) -> tuple[float, float]:
        """Calculate connection and total memory values."""
        connection_memory_mb = sum(self.memory_tracker.buffer_sizes.values())
        total_memory_mb = connection_memory_mb + (len(self.memory_tracker.message_buffers) * 0.1)
        return connection_memory_mb, total_memory_mb
    
    def _create_memory_metrics_object(self, connection_memory_mb: float, 
                                    total_memory_mb: float) -> MemoryMetrics:
        """Create MemoryMetrics object with current values."""
        import gc
        return MemoryMetrics(
            total_memory_mb=total_memory_mb, connection_memory_mb=connection_memory_mb,
            active_connections=len(self.memory_tracker.message_buffers),
            total_allocations=len(self.memory_tracker.connection_refs),
            gc_collections=sum(gc.get_count())
        )
    
    def add_metrics(self, metrics: MemoryMetrics) -> None:
        """Add metrics to history."""
        self.metrics_history.append(metrics)
    
    def get_current_metrics(self) -> MemoryMetrics:
        """Get current memory metrics or default if none available."""
        return self.metrics_history[-1] if self.metrics_history else MemoryMetrics()


class MemoryHealthChecker:
    """Checks memory health and identifies potential issues."""
    
    def __init__(self, metrics_collector: MemoryMetricsCollector):
        self.metrics_collector = metrics_collector
    
    def check_memory_health(self) -> Dict[str, Any]:
        """Check memory health and identify issues."""
        if not self.metrics_collector.metrics_history:
            return {"status": "no_data", "issues": []}
        current = self.metrics_collector.metrics_history[-1]
        issues = self._collect_memory_health_issues(current)
        return self._build_health_report(current, issues)
    
    def _collect_memory_health_issues(self, current) -> List[Dict[str, Any]]:
        """Collect all memory health issues."""
        issues = []
        self._check_high_memory_usage(current, issues)
        self._check_high_connection_count(current, issues)
        self._check_memory_growth_trend(issues)
        return issues
    
    def _check_high_memory_usage(self, current, issues: List[Dict[str, Any]]) -> None:
        """Check for high memory usage issues."""
        if current.connection_memory_mb > 100:
            issues.append({
                "type": "high_memory_usage", "severity": "high",
                "message": f"Connection memory usage: {current.connection_memory_mb:.1f}MB"
            })
    
    def _check_high_connection_count(self, current, issues: List[Dict[str, Any]]) -> None:
        """Check for high connection count issues."""
        if current.active_connections > 1000:
            issues.append({
                "type": "high_connection_count", "severity": "medium",
                "message": f"Active connections: {current.active_connections}"
            })
    
    def _check_memory_growth_trend(self, issues: List[Dict[str, Any]]) -> None:
        """Check for memory growth trend issues."""
        if len(self.metrics_collector.metrics_history) >= 2:
            growth_rate = self._calculate_memory_growth_rate()
            if growth_rate > 0.1:
                issues.append({
                    "type": "memory_growth", "severity": "medium",
                    "message": f"Memory growth rate: {growth_rate:.1%}"
                })
    
    def _calculate_memory_growth_rate(self) -> float:
        """Calculate memory growth rate between last two metrics."""
        current = self.metrics_collector.metrics_history[-1]
        prev = self.metrics_collector.metrics_history[-2]
        return (current.total_memory_mb - prev.total_memory_mb) / prev.total_memory_mb
    
    def _build_health_report(self, current, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build final health report."""
        status = "healthy" if not issues else "issues_detected"
        return {
            "status": status, "issues": issues, "total_issues": len(issues),
            "current_memory_mb": current.total_memory_mb
        }


class MemoryStatsCollector:
    """Collects comprehensive memory statistics."""
    
    def __init__(self, memory_tracker, metrics_collector: MemoryMetricsCollector):
        self.memory_tracker = memory_tracker
        self.metrics_collector = metrics_collector
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        current_metrics = self.metrics_collector.get_current_metrics()
        connection_stats = self._collect_connection_stats()
        return self._build_memory_stats_dict(current_metrics, connection_stats)
    
    def _collect_connection_stats(self) -> Dict[str, Dict[str, Any]]:
        """Collect memory statistics for all tracked connections."""
        connection_stats = {}
        for connection_id in self.memory_tracker.message_buffers.keys():
            connection_stats[connection_id] = self.memory_tracker.get_connection_memory_info(connection_id)
        return connection_stats
    
    def _build_memory_stats_dict(self, current_metrics: MemoryMetrics, 
                               connection_stats: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Build final memory statistics dictionary."""
        current_metrics_dict = self._build_current_metrics_dict(current_metrics)
        return self._combine_stats_components(current_metrics_dict, connection_stats)
    
    def _build_current_metrics_dict(self, current_metrics: MemoryMetrics) -> Dict[str, Any]:
        """Build current metrics dictionary from MemoryMetrics object."""
        return {
            "total_memory_mb": current_metrics.total_memory_mb,
            "connection_memory_mb": current_metrics.connection_memory_mb,
            "active_connections": current_metrics.active_connections,
            "total_allocations": current_metrics.total_allocations,
            "gc_collections": current_metrics.gc_collections
        }
    
    def _combine_stats_components(self, current_metrics_dict: Dict[str, Any],
                                connection_stats: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Combine all statistics components into final result."""
        return {
            "current_metrics": current_metrics_dict, "connection_details": connection_stats,
            "buffer_limits": self.memory_tracker.buffer_limits,
            "metrics_history_count": len(self.metrics_collector.metrics_history),
            "monitoring_active": True
        }
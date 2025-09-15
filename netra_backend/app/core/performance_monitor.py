"""
Performance Monitor Module - Compatibility Layer for Integration Tests

This module provides a compatibility layer for integration tests that expect
a performance monitoring implementation. This is a minimal implementation for test compatibility.

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER for integration tests
- Provides minimal implementation for test collection compatibility
- DO NOT use in production - this is test infrastructure only

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Stability
- Value Impact: Enables integration test collection and execution
- Strategic Impact: Maintains test coverage during system evolution
"""

from typing import Any, Dict, List, Optional, Union, Callable
import time
import psutil
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from contextlib import contextmanager
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class PerformanceMetricType(Enum):
    """Types of performance metrics."""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"


@dataclass
class PerformanceMetric:
    """A performance metric measurement."""
    metric_type: PerformanceMetricType
    value: float
    timestamp: float
    component: str
    labels: Dict[str, str] = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


class PerformanceMonitor:
    """
    Simple performance monitor for test compatibility.

    This is a minimal implementation to satisfy integration test imports.
    Not intended for production use.
    """

    def __init__(self, max_samples: int = 100):
        """Initialize performance monitor."""
        self.max_samples = max_samples
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self.active_timers: Dict[str, float] = {}
        self.performance_stats: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self.monitoring_active = False

        logger.info("Performance monitor initialized (test compatibility mode)")

    def start_monitoring(self):
        """Start performance monitoring."""
        self.monitoring_active = True
        logger.info("Performance monitoring started")

    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring_active = False
        logger.info("Performance monitoring stopped")

    def record_metric(self, metric_type: PerformanceMetricType, value: float,
                     component: str, labels: Dict[str, str] = None):
        """Record a performance metric."""
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            timestamp=time.time(),
            component=component,
            labels=labels or {}
        )

        with self._lock:
            key = f"{component}_{metric_type.value}"
            self.metrics[key].append(metric)

    def start_timer(self, operation_name: str) -> str:
        """Start a timer for an operation."""
        timer_id = f"{operation_name}_{time.time()}"
        self.active_timers[timer_id] = time.time()
        return timer_id

    def stop_timer(self, timer_id: str) -> float:
        """Stop a timer and record the duration."""
        if timer_id not in self.active_timers:
            logger.warning(f"Timer {timer_id} not found")
            return 0.0

        start_time = self.active_timers.pop(timer_id)
        duration = time.time() - start_time

        # Extract operation name from timer_id
        operation_name = "_".join(timer_id.split("_")[:-1])
        self.record_metric(
            PerformanceMetricType.RESPONSE_TIME,
            duration,
            operation_name
        )

        return duration

    @contextmanager
    def time_operation(self, operation_name: str):
        """Context manager for timing operations."""
        timer_id = self.start_timer(operation_name)
        try:
            yield
        finally:
            self.stop_timer(timer_id)

    def get_system_metrics(self) -> Dict[str, float]:
        """Get current system performance metrics."""
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)

            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Get disk I/O
            disk_io = psutil.disk_io_counters()
            disk_read_bytes = disk_io.read_bytes if disk_io else 0
            disk_write_bytes = disk_io.write_bytes if disk_io else 0

            # Get network I/O
            network_io = psutil.net_io_counters()
            network_sent_bytes = network_io.bytes_sent if network_io else 0
            network_recv_bytes = network_io.bytes_recv if network_io else 0

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "memory_available_mb": memory.available / (1024 * 1024),
                "disk_read_bytes": disk_read_bytes,
                "disk_write_bytes": disk_write_bytes,
                "network_sent_bytes": network_sent_bytes,
                "network_recv_bytes": network_recv_bytes
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}

    def record_system_snapshot(self):
        """Record a snapshot of current system metrics."""
        system_metrics = self.get_system_metrics()
        timestamp = time.time()

        for metric_name, value in system_metrics.items():
            if "cpu" in metric_name:
                metric_type = PerformanceMetricType.CPU_USAGE
            elif "memory" in metric_name:
                metric_type = PerformanceMetricType.MEMORY_USAGE
            elif "disk" in metric_name:
                metric_type = PerformanceMetricType.DISK_IO
            elif "network" in metric_name:
                metric_type = PerformanceMetricType.NETWORK_IO
            else:
                continue

            self.record_metric(metric_type, value, "system", {"metric_name": metric_name})

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of performance metrics."""
        with self._lock:
            summary = {}

            for key, metrics_deque in self.metrics.items():
                if not metrics_deque:
                    continue

                values = [m.value for m in metrics_deque]
                summary[key] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values),
                    "latest": values[-1],
                    "latest_timestamp": metrics_deque[-1].timestamp
                }

            return summary

    def get_component_metrics(self, component: str) -> Dict[str, List[PerformanceMetric]]:
        """Get all metrics for a specific component."""
        with self._lock:
            component_metrics = {}
            for key, metrics_deque in self.metrics.items():
                if key.startswith(component):
                    component_metrics[key] = list(metrics_deque)
            return component_metrics

    def clear_metrics(self):
        """Clear all performance metrics."""
        with self._lock:
            self.metrics.clear()
            self.active_timers.clear()
            self.performance_stats.clear()
            logger.info("All performance metrics cleared")

    def export_metrics(self, format_type: str = "json") -> Union[str, Dict[str, Any]]:
        """Export metrics in specified format."""
        summary = self.get_performance_summary()

        if format_type.lower() == "json":
            return summary
        elif format_type.lower() == "prometheus":
            lines = []
            for key, stats in summary.items():
                lines.append(f"# TYPE {key} gauge")
                lines.append(f"{key}_current {stats['latest']}")
                lines.append(f"{key}_min {stats['min']}")
                lines.append(f"{key}_max {stats['max']}")
                lines.append(f"{key}_mean {stats['mean']}")
            return "\n".join(lines)
        else:
            return summary


# Global instance for compatibility
performance_monitor = PerformanceMonitor()

__all__ = [
    "PerformanceMonitor",
    "PerformanceMetric",
    "PerformanceMetricType",
    "performance_monitor"
]
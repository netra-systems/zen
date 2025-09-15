"""
Metrics Collector Module - Compatibility Layer for Integration Tests

This module provides a compatibility layer for integration tests that expect
a metrics collection implementation. This is a minimal implementation for test compatibility.

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
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """A metric value."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    Simple metrics collector for test compatibility.

    This is a minimal implementation to satisfy integration test imports.
    Not intended for production use.
    """

    def __init__(self, max_metrics: int = 1000):
        """Initialize metrics collector."""
        self.max_metrics = max_metrics
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

        logger.info("Metrics collector initialized (test compatibility mode)")

    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric."""
        with self._lock:
            self.counters[name] += value
            self._store_metric(name, value, MetricType.COUNTER, labels)

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric."""
        with self._lock:
            self.gauges[name] = value
            self._store_metric(name, value, MetricType.GAUGE, labels)

    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram metric."""
        with self._lock:
            self.histograms[name].append(value)
            # Keep only recent values to prevent memory growth
            if len(self.histograms[name]) > 100:
                self.histograms[name] = self.histograms[name][-100:]
            self._store_metric(name, value, MetricType.HISTOGRAM, labels)

    def record_timer(self, name: str, duration: float, labels: Dict[str, str] = None):
        """Record a timer metric."""
        with self._lock:
            self.timers[name].append(duration)
            # Keep only recent values to prevent memory growth
            if len(self.timers[name]) > 100:
                self.timers[name] = self.timers[name][-100:]
            self._store_metric(name, duration, MetricType.TIMER, labels)

    def _store_metric(self, name: str, value: float, metric_type: MetricType, labels: Dict[str, str] = None):
        """Store a metric value."""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=time.time(),
            labels=labels or {}
        )
        self.metrics[name].append(metric)

    def get_counter(self, name: str) -> float:
        """Get counter value."""
        return self.counters.get(name, 0.0)

    def get_gauge(self, name: str) -> Optional[float]:
        """Get gauge value."""
        return self.gauges.get(name)

    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get histogram statistics."""
        values = self.histograms.get(name, [])
        if not values:
            return {}

        values_sorted = sorted(values)
        count = len(values)
        return {
            "count": count,
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / count,
            "p50": values_sorted[count // 2],
            "p95": values_sorted[int(count * 0.95)] if count > 1 else values_sorted[0],
            "p99": values_sorted[int(count * 0.99)] if count > 1 else values_sorted[0],
        }

    def get_timer_stats(self, name: str) -> Dict[str, float]:
        """Get timer statistics."""
        return self.get_histogram_stats(name)  # Same calculation

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        with self._lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {name: self.get_histogram_stats(name) for name in self.histograms},
                "timers": {name: self.get_timer_stats(name) for name in self.timers}
            }

    def clear_metrics(self):
        """Clear all metrics."""
        with self._lock:
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.timers.clear()
            self.metrics.clear()
            logger.info("All metrics cleared")

    def get_metric_names(self) -> List[str]:
        """Get all metric names."""
        return list(set(
            list(self.counters.keys()) +
            list(self.gauges.keys()) +
            list(self.histograms.keys()) +
            list(self.timers.keys())
        ))

    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format (simplified)."""
        lines = []

        # Counters
        for name, value in self.counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")

        # Gauges
        for name, value in self.gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")

        return "\n".join(lines)


# Global instance for compatibility
metrics_collector = MetricsCollector()

__all__ = [
    "MetricsCollector",
    "Metric",
    "MetricType",
    "metrics_collector"
]
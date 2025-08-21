"""WebSocket Performance Monitor Metric Collector.

Optimized metric collection with 25-line function limit compliance.
"""

import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from collections import deque, defaultdict

from netra_backend.app.performance_monitor_types import MetricPoint, MetricType


class MetricCollector:
    """Collects and stores performance metrics with micro-functions."""
    
    def __init__(self, max_points: int = 10000):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self.metric_types: Dict[str, MetricType] = {}
        self.max_points = max_points
    
    def record_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a counter metric."""
        self._record_metric(name, MetricType.COUNTER, value, tags or {})
    
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric."""
        self._record_metric(name, MetricType.GAUGE, value, tags or {})
    
    def record_timer(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timer metric."""
        self._record_metric(name, MetricType.TIMER, duration_ms, tags or {})
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram metric."""
        self._record_metric(name, MetricType.HISTOGRAM, value, tags or {})
    
    def _record_metric(self, name: str, metric_type: MetricType, value: float, tags: Dict[str, str]) -> None:
        """Internal method to record a metric."""
        point = self._create_metric_point(value, tags)
        self.metrics[name].append(point)
        self.metric_types[name] = metric_type
    
    def _create_metric_point(self, value: float, tags: Dict[str, str]) -> MetricPoint:
        """Create metric point with current timestamp."""
        return MetricPoint(
            timestamp=datetime.now(timezone.utc),
            value=value,
            tags=tags
        )
    
    def get_metric_values(self, name: str, duration_minutes: Optional[int] = None) -> List[float]:
        """Get metric values for analysis."""
        if name not in self.metrics:
            return []
        points = self._get_filtered_points(name, duration_minutes)
        return [p.value for p in points]
    
    def _get_filtered_points(self, name: str, duration_minutes: Optional[int]) -> List[MetricPoint]:
        """Get filtered metric points by duration."""
        points = list(self.metrics[name])
        if duration_minutes:
            points = self._filter_points_by_time(points, duration_minutes)
        return points
    
    def _filter_points_by_time(self, points: List[MetricPoint], duration_minutes: int) -> List[MetricPoint]:
        """Filter points by time duration."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=duration_minutes)
        return [p for p in points if p.timestamp >= cutoff_time]
    
    def get_metric_stats(self, name: str, duration_minutes: Optional[int] = None) -> Dict[str, float]:
        """Get statistical summary of a metric."""
        values = self.get_metric_values(name, duration_minutes)
        if not values:
            return {}
        return self._calculate_statistics(values)
    
    def _calculate_statistics(self, values: List[float]) -> Dict[str, float]:
        """Calculate statistical metrics for values."""
        basic_stats = self._get_basic_stats(values)
        advanced_stats = self._get_advanced_stats(values)
        return {**basic_stats, **advanced_stats}
    
    def _get_basic_stats(self, values: List[float]) -> Dict[str, float]:
        """Get basic statistical measures."""
        return {
            "count": len(values),
            "sum": sum(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values)
        }
    
    def _get_advanced_stats(self, values: List[float]) -> Dict[str, float]:
        """Get advanced statistical measures."""
        return {
            "min": min(values),
            "max": max(values),
            "stddev": statistics.stdev(values) if len(values) > 1 else 0.0
        }
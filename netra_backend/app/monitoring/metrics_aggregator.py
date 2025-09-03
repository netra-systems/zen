"""Metrics Aggregator for Performance Data

Aggregates and analyzes performance metrics across:
- Multiple agent executions
- Time windows (minute, hour, day)
- Percentile calculations (p50, p95, p99)
- Trend detection
- Resource utilization

Business Value: Enables data-driven performance optimization decisions.
BVJ: Platform | Development Velocity | Performance insights for optimization
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Deque, Tuple, Any
from datetime import datetime, timedelta, timezone
from enum import Enum
import statistics
import threading

from netra_backend.app.core.performance_metrics import (
    PerformanceMetric, MetricType, TimingBreakdown
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AggregationWindow(Enum):
    """Time windows for metric aggregation."""
    MINUTE = 60
    FIVE_MINUTES = 300
    HOUR = 3600
    DAY = 86400
    WEEK = 604800


@dataclass
class MetricWindow:
    """Sliding window for metric aggregation."""
    
    window_size: AggregationWindow
    metrics: Deque[PerformanceMetric] = field(default_factory=deque)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_metric(self, metric: PerformanceMetric) -> None:
        """Add metric to window and prune old metrics."""
        self.metrics.append(metric)
        self._prune_old_metrics()
    
    def _prune_old_metrics(self) -> None:
        """Remove metrics outside the time window."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.window_size.value)
        while self.metrics and self.metrics[0].timestamp < cutoff_time:
            self.metrics.popleft()
    
    def get_metrics(self) -> List[PerformanceMetric]:
        """Get all metrics in the window."""
        self._prune_old_metrics()
        return list(self.metrics)


@dataclass
class AggregatedMetrics:
    """Aggregated performance metrics."""
    
    metric_type: MetricType
    window: AggregationWindow
    count: int = 0
    mean: float = 0.0
    median: float = 0.0
    min_value: float = float('inf')
    max_value: float = 0.0
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    std_dev: float = 0.0
    total: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "metric_type": self.metric_type.value,
            "window": self.window.name,
            "count": self.count,
            "mean": self.mean,
            "median": self.median,
            "min": self.min_value,
            "max": self.max_value,
            "p50": self.p50,
            "p95": self.p95,
            "p99": self.p99,
            "std_dev": self.std_dev,
            "total": self.total,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ResourceMetrics:
    """System resource utilization metrics."""
    
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    thread_count: int = 0
    connection_pool_size: int = 0
    queue_depth: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MetricsAggregator:
    """Aggregates and analyzes performance metrics."""
    
    def __init__(self, retention_hours: int = 24):
        """Initialize metrics aggregator.
        
        Args:
            retention_hours: Hours to retain metrics history
        """
        self.retention_hours = retention_hours
        self.metric_windows: Dict[Tuple[MetricType, AggregationWindow], MetricWindow] = {}
        self.resource_history: Deque[ResourceMetrics] = deque(maxlen=1000)
        self.timing_breakdowns: Deque[TimingBreakdown] = deque(maxlen=500)
        self._lock = threading.Lock()
        
        # Initialize windows for all metric types and aggregation periods
        self._initialize_windows()
        
        # Cached aggregations
        self._cached_aggregations: Dict[str, Tuple[datetime, AggregatedMetrics]] = {}
        self._cache_ttl = 10  # seconds
        
    def _initialize_windows(self) -> None:
        """Initialize metric windows for all combinations."""
        for metric_type in MetricType:
            for window in AggregationWindow:
                key = (metric_type, window)
                self.metric_windows[key] = MetricWindow(window_size=window)
    
    def add_metric(self, metric: PerformanceMetric) -> None:
        """Add a performance metric to aggregation.
        
        Args:
            metric: Performance metric to add
        """
        with self._lock:
            # Add to appropriate windows
            for window in AggregationWindow:
                key = (metric.metric_type, window)
                if key in self.metric_windows:
                    self.metric_windows[key].add_metric(metric)
            
            logger.debug(f"Added metric: {metric.metric_type.value} = {metric.value:.2f}")
    
    def add_timing_breakdown(self, breakdown: TimingBreakdown) -> None:
        """Add a timing breakdown for analysis.
        
        Args:
            breakdown: Timing breakdown to add
        """
        with self._lock:
            self.timing_breakdowns.append(breakdown)
            
            # Convert breakdown to individual metrics
            self._breakdown_to_metrics(breakdown)
    
    def add_resource_metrics(self, metrics: ResourceMetrics) -> None:
        """Add resource utilization metrics.
        
        Args:
            metrics: Resource metrics to add
        """
        with self._lock:
            self.resource_history.append(metrics)
    
    def get_aggregated_metrics(self, metric_type: MetricType, 
                              window: AggregationWindow) -> Optional[AggregatedMetrics]:
        """Get aggregated metrics for a specific type and window.
        
        Args:
            metric_type: Type of metric
            window: Aggregation window
            
        Returns:
            Aggregated metrics or None if no data
        """
        # Check cache
        cache_key = f"{metric_type.value}_{window.value}"
        if cache_key in self._cached_aggregations:
            cached_time, cached_result = self._cached_aggregations[cache_key]
            if (datetime.now(timezone.utc) - cached_time).total_seconds() < self._cache_ttl:
                return cached_result
        
        with self._lock:
            key = (metric_type, window)
            if key not in self.metric_windows:
                return None
            
            metrics = self.metric_windows[key].get_metrics()
            if not metrics:
                return None
            
            values = [m.value for m in metrics]
            
            # Calculate aggregations
            aggregated = AggregatedMetrics(
                metric_type=metric_type,
                window=window,
                count=len(values),
                mean=statistics.mean(values),
                median=statistics.median(values),
                min_value=min(values),
                max_value=max(values),
                total=sum(values)
            )
            
            # Calculate percentiles
            if len(values) >= 2:
                aggregated.p50 = self._calculate_percentile(values, 50)
                aggregated.p95 = self._calculate_percentile(values, 95)
                aggregated.p99 = self._calculate_percentile(values, 99)
                aggregated.std_dev = statistics.stdev(values)
            
            # Update cache
            self._cached_aggregations[cache_key] = (datetime.now(timezone.utc), aggregated)
            
            return aggregated
    
    def get_all_aggregations(self, window: AggregationWindow) -> Dict[str, AggregatedMetrics]:
        """Get all metric aggregations for a specific window.
        
        Args:
            window: Aggregation window
            
        Returns:
            Dictionary of metric type to aggregated metrics
        """
        results = {}
        
        for metric_type in MetricType:
            aggregated = self.get_aggregated_metrics(metric_type, window)
            if aggregated:
                results[metric_type.value] = aggregated
        
        return results
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary.
        
        Returns:
            Performance summary with key metrics
        """
        # Get recent aggregations
        minute_metrics = self.get_all_aggregations(AggregationWindow.MINUTE)
        hour_metrics = self.get_all_aggregations(AggregationWindow.HOUR)
        
        # Calculate average breakdown
        avg_breakdown = self._calculate_average_breakdown()
        
        # Get resource utilization
        resource_summary = self._get_resource_summary()
        
        # Detect trends
        trends = self._detect_trends()
        
        return {
            "current_metrics": {
                metric_type: agg.to_dict() 
                for metric_type, agg in minute_metrics.items()
            },
            "hourly_metrics": {
                metric_type: agg.to_dict()
                for metric_type, agg in hour_metrics.items()
            },
            "average_breakdown": avg_breakdown,
            "resource_utilization": resource_summary,
            "trends": trends,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_bottlenecks(self, threshold_percentile: int = 95) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks.
        
        Args:
            threshold_percentile: Percentile threshold for bottleneck detection
            
        Returns:
            List of identified bottlenecks
        """
        bottlenecks = []
        
        # Check each metric type
        for metric_type in MetricType:
            aggregated = self.get_aggregated_metrics(metric_type, AggregationWindow.HOUR)
            if not aggregated:
                continue
            
            # Get threshold value
            threshold = getattr(aggregated, f"p{threshold_percentile}", aggregated.max_value)
            
            # Find recent metrics exceeding threshold
            with self._lock:
                key = (metric_type, AggregationWindow.MINUTE)
                if key in self.metric_windows:
                    recent_metrics = self.metric_windows[key].get_metrics()
                    
                    exceeding = [m for m in recent_metrics if m.value > threshold]
                    if exceeding:
                        bottlenecks.append({
                            "metric_type": metric_type.value,
                            "threshold": threshold,
                            "violations": len(exceeding),
                            "max_value": max(m.value for m in exceeding),
                            "impact": "high" if len(exceeding) > 5 else "medium"
                        })
        
        return bottlenecks
    
    def _breakdown_to_metrics(self, breakdown: TimingBreakdown) -> None:
        """Convert timing breakdown to individual metrics.
        
        Args:
            breakdown: Timing breakdown to convert
        """
        # Map breakdown fields to metric types
        field_mapping = {
            "initialization_ms": MetricType.INITIALIZATION,
            "tool_execution_ms": MetricType.TOOL_EXECUTION,
            "llm_processing_ms": MetricType.LLM_PROCESSING,
            "websocket_notification_ms": MetricType.WEBSOCKET_LATENCY,
            "database_query_ms": MetricType.DATABASE_QUERY,
            "external_api_ms": MetricType.EXTERNAL_API,
            "queue_wait_ms": MetricType.QUEUE_WAIT,
            "time_to_first_token_ms": MetricType.TTFT
        }
        
        for field, metric_type in field_mapping.items():
            value = getattr(breakdown, field, None)
            if value is not None and value > 0:
                metric = PerformanceMetric(
                    metric_type=metric_type,
                    value=value
                )
                # Add to windows without lock (called from locked context)
                for window in AggregationWindow:
                    key = (metric_type, window)
                    if key in self.metric_windows:
                        self.metric_windows[key].add_metric(metric)
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value.
        
        Args:
            values: List of values
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Percentile value
        """
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (len(sorted_values) - 1) * (percentile / 100)
        lower = int(index)
        upper = min(lower + 1, len(sorted_values) - 1)
        weight = index - lower
        
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
    
    def _calculate_average_breakdown(self) -> Optional[Dict[str, float]]:
        """Calculate average timing breakdown.
        
        Returns:
            Average breakdown or None if no data
        """
        if not self.timing_breakdowns:
            return None
        
        totals = defaultdict(float)
        count = len(self.timing_breakdowns)
        
        for breakdown in self.timing_breakdowns:
            totals["initialization"] += breakdown.initialization_ms
            totals["tool_execution"] += breakdown.tool_execution_ms
            totals["llm_processing"] += breakdown.llm_processing_ms
            totals["websocket_notification"] += breakdown.websocket_notification_ms
            totals["database_query"] += breakdown.database_query_ms
            totals["external_api"] += breakdown.external_api_ms
            totals["queue_wait"] += breakdown.queue_wait_ms
            totals["overhead"] += breakdown.overhead_ms
            totals["total"] += breakdown.total_ms
        
        return {key: value / count for key, value in totals.items()}
    
    def _get_resource_summary(self) -> Dict[str, Any]:
        """Get resource utilization summary.
        
        Returns:
            Resource summary statistics
        """
        if not self.resource_history:
            return {}
        
        recent_metrics = list(self.resource_history)
        
        return {
            "cpu": {
                "current": recent_metrics[-1].cpu_percent if recent_metrics else 0,
                "avg": statistics.mean(m.cpu_percent for m in recent_metrics),
                "max": max(m.cpu_percent for m in recent_metrics)
            },
            "memory": {
                "current_mb": recent_metrics[-1].memory_mb if recent_metrics else 0,
                "avg_mb": statistics.mean(m.memory_mb for m in recent_metrics),
                "max_mb": max(m.memory_mb for m in recent_metrics)
            },
            "threads": {
                "current": recent_metrics[-1].thread_count if recent_metrics else 0,
                "avg": statistics.mean(m.thread_count for m in recent_metrics),
                "max": max(m.thread_count for m in recent_metrics)
            }
        }
    
    def _detect_trends(self) -> Dict[str, str]:
        """Detect performance trends.
        
        Returns:
            Dictionary of metric types to trend directions
        """
        trends = {}
        
        for metric_type in MetricType:
            # Compare minute average to hour average
            minute_agg = self.get_aggregated_metrics(metric_type, AggregationWindow.MINUTE)
            hour_agg = self.get_aggregated_metrics(metric_type, AggregationWindow.HOUR)
            
            if minute_agg and hour_agg and hour_agg.mean > 0:
                change_percent = ((minute_agg.mean - hour_agg.mean) / hour_agg.mean) * 100
                
                if change_percent > 20:
                    trends[metric_type.value] = "degrading"
                elif change_percent < -20:
                    trends[metric_type.value] = "improving"
                else:
                    trends[metric_type.value] = "stable"
        
        return trends
    
    def export_metrics(self, window: AggregationWindow) -> List[Dict[str, Any]]:
        """Export metrics for a specific window.
        
        Args:
            window: Aggregation window to export
            
        Returns:
            List of metric dictionaries
        """
        exported = []
        
        with self._lock:
            for metric_type in MetricType:
                key = (metric_type, window)
                if key in self.metric_windows:
                    metrics = self.metric_windows[key].get_metrics()
                    for metric in metrics:
                        exported.append({
                            "type": metric.metric_type.value,
                            "value": metric.value,
                            "timestamp": metric.timestamp.isoformat(),
                            "agent": metric.agent_name,
                            "correlation_id": metric.correlation_id,
                            "metadata": metric.metadata
                        })
        
        return exported
    
    def clear_old_metrics(self) -> int:
        """Clear metrics older than retention period.
        
        Returns:
            Number of metrics cleared
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        cleared = 0
        
        with self._lock:
            for window in self.metric_windows.values():
                initial_count = len(window.metrics)
                window._prune_old_metrics()
                cleared += initial_count - len(window.metrics)
        
        logger.info(f"Cleared {cleared} old metrics")
        return cleared


# Global aggregator instance
_global_aggregator: Optional[MetricsAggregator] = None
_aggregator_lock = threading.Lock()


def get_global_aggregator() -> MetricsAggregator:
    """Get or create the global metrics aggregator.
    
    Returns:
        Global MetricsAggregator instance
    """
    global _global_aggregator
    
    if _global_aggregator is None:
        with _aggregator_lock:
            if _global_aggregator is None:
                _global_aggregator = MetricsAggregator()
                logger.info("Initialized global metrics aggregator")
    
    return _global_aggregator
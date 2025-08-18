"""Database Observability Metrics

Data classes and metric structures for database monitoring.
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque


@dataclass
class DatabaseMetrics:
    """Comprehensive database metrics."""
    timestamp: datetime
    
    # Connection metrics
    active_connections: int = 0
    idle_connections: int = 0
    total_connections: int = 0
    pool_size: int = 0
    pool_overflow: int = 0
    connection_errors: int = 0
    connection_timeouts: int = 0
    
    # Query metrics
    total_queries: int = 0
    slow_queries: int = 0
    failed_queries: int = 0
    avg_query_time: float = 0.0
    max_query_time: float = 0.0
    
    # Transaction metrics
    active_transactions: int = 0
    committed_transactions: int = 0
    rolled_back_transactions: int = 0
    deadlocks: int = 0
    
    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_size: int = 0
    cache_hit_rate: float = 0.0
    
    # Performance metrics
    queries_per_second: float = 0.0
    connections_per_second: float = 0.0
    avg_response_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class AlertThresholds:
    """Alert thresholds for database monitoring."""
    max_connection_usage: float = 0.8  # 80% of pool
    max_avg_query_time: float = 1.0  # 1 second
    max_slow_query_rate: float = 0.1  # 10% of queries
    min_cache_hit_rate: float = 0.5  # 50%
    max_active_transactions: int = 50
    max_deadlock_rate: float = 0.01  # 1% of transactions


class MetricsStorage:
    """Storage and retrieval for database metrics."""
    
    def __init__(self, max_history: int = 1440):
        self.metrics_history: deque = deque(maxlen=max_history)
        self.alerts: deque = deque(maxlen=100)
        self.query_times: deque = deque(maxlen=1000)
        self.connection_events: deque = deque(maxlen=1000)

    def store_metrics(self, metrics: DatabaseMetrics) -> None:
        """Store metrics in history."""
        self.metrics_history.append(metrics)

    def store_alert(self, alert: Dict[str, Any]) -> None:
        """Store alert in history."""
        self.alerts.append(alert)

    def get_recent_metrics(self, count: int = 60) -> List[DatabaseMetrics]:
        """Get recent metrics."""
        return list(self.metrics_history)[-count:]

    def get_metrics_since(self, cutoff: datetime) -> List[DatabaseMetrics]:
        """Get metrics since cutoff time."""
        return [
            m for m in self.metrics_history
            if m.timestamp >= cutoff
        ]

    def get_alerts_since(self, cutoff_iso: str) -> List[Dict[str, Any]]:
        """Get alerts since cutoff time."""
        return [
            alert for alert in self.alerts
            if alert.get('timestamp', '') >= cutoff_iso
        ]

    def record_query_time(self, duration: float) -> None:
        """Record query execution time."""
        self.query_times.append(duration)

    def record_connection_event(self, event_type: str, details: Dict[str, Any] = None) -> None:
        """Record connection event."""
        event = {
            'timestamp': time.time(),
            'type': event_type,
            'details': details or {}
        }
        self.connection_events.append(event)


class PerformanceCalculator:
    """Calculate derived performance metrics."""
    
    @staticmethod
    def calculate_queries_per_second(current: DatabaseMetrics, previous: DatabaseMetrics) -> float:
        """Calculate queries per second rate."""
        time_diff = (current.timestamp - previous.timestamp).total_seconds()
        if time_diff <= 0:
            return 0.0
        query_diff = current.total_queries - previous.total_queries
        return query_diff / time_diff

    @staticmethod
    def calculate_connections_per_second(current: DatabaseMetrics, previous: DatabaseMetrics) -> float:
        """Calculate connection rate."""
        time_diff = (current.timestamp - previous.timestamp).total_seconds()
        if time_diff <= 0:
            return 0.0
        conn_diff = current.total_connections - previous.total_connections
        return abs(conn_diff) / time_diff

    @staticmethod
    def calculate_average_response_time(query_times: deque) -> float:
        """Calculate average response time."""
        if not query_times:
            return 0.0
        return sum(query_times) / len(query_times)

    @staticmethod
    def calculate_trends(recent_metrics: List[DatabaseMetrics]) -> Dict[str, float]:
        """Calculate performance trends."""
        if len(recent_metrics) < 2:
            return {'query_time_trend': 0.0, 'connection_trend': 0.0}
        
        mid_point = len(recent_metrics) // 2
        first_half = recent_metrics[:mid_point]
        second_half = recent_metrics[mid_point:]
        
        query_time_trend = (
            sum(m.avg_query_time for m in second_half) / len(second_half) -
            sum(m.avg_query_time for m in first_half) / len(first_half)
        )
        
        connection_trend = (
            sum(m.active_connections for m in second_half) / len(second_half) -
            sum(m.active_connections for m in first_half) / len(first_half)
        )
        
        return {
            'query_time_trend': query_time_trend,
            'connection_trend': connection_trend
        }


class MetricsSummaryBuilder:
    """Build performance summaries from metrics."""
    
    @staticmethod
    def build_performance_summary(recent_metrics: List[DatabaseMetrics]) -> Dict[str, Any]:
        """Build comprehensive performance summary."""
        if not recent_metrics:
            return {}
        
        # Calculate averages
        avg_query_time = sum(m.avg_query_time for m in recent_metrics) / len(recent_metrics)
        avg_connections = sum(m.active_connections for m in recent_metrics) / len(recent_metrics)
        avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
        
        # Calculate trends
        trends = PerformanceCalculator.calculate_trends(recent_metrics)
        
        return {
            'avg_query_time': avg_query_time,
            'avg_connections': avg_connections,
            'avg_cache_hit_rate': avg_cache_hit_rate,
            'query_time_trend': trends['query_time_trend'],
            'connection_trend': trends['connection_trend'],
            'total_queries': sum(m.total_queries for m in recent_metrics),
            'slow_queries': sum(m.slow_queries for m in recent_metrics),
            'cache_hits': sum(m.cache_hits for m in recent_metrics),
            'cache_misses': sum(m.cache_misses for m in recent_metrics)
        }

    @staticmethod
    def build_dashboard_data(
        current_metrics: DatabaseMetrics,
        metrics_history: List[DatabaseMetrics],
        alerts: List[Dict[str, Any]],
        cache_metrics: Dict[str, Any],
        transaction_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build comprehensive dashboard data."""
        performance_summary = MetricsSummaryBuilder.build_performance_summary(metrics_history)
        
        return {
            'current_metrics': current_metrics.to_dict(),
            'metrics_history': [m.to_dict() for m in metrics_history],
            'recent_alerts': alerts,
            'performance_summary': performance_summary,
            'cache_metrics': cache_metrics,
            'transaction_stats': transaction_stats
        }
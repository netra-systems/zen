"""Database Observability Metrics

Data classes and metric structures for database monitoring.
"""

import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


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
    def _split_metrics_by_time(recent_metrics: List[DatabaseMetrics]) -> tuple:
        """Split metrics into first and second half by time."""
        mid_point = len(recent_metrics) // 2
        first_half = recent_metrics[:mid_point]
        second_half = recent_metrics[mid_point:]
        return first_half, second_half
    
    @staticmethod
    def _calculate_query_time_trend(first_half: List[DatabaseMetrics], second_half: List[DatabaseMetrics]) -> float:
        """Calculate query time trend between periods."""
        first_avg = sum(m.avg_query_time for m in first_half) / len(first_half)
        second_avg = sum(m.avg_query_time for m in second_half) / len(second_half)
        return second_avg - first_avg
    
    @staticmethod
    def _calculate_connection_trend(first_half: List[DatabaseMetrics], second_half: List[DatabaseMetrics]) -> float:
        """Calculate connection trend between periods."""
        first_avg = sum(m.active_connections for m in first_half) / len(first_half)
        second_avg = sum(m.active_connections for m in second_half) / len(second_half)
        return second_avg - first_avg
    
    @staticmethod
    def _build_trends_result(query_time_trend: float, connection_trend: float) -> Dict[str, float]:
        """Build trends result dictionary."""
        return {
            'query_time_trend': query_time_trend,
            'connection_trend': connection_trend
        }
    
    @staticmethod
    def calculate_trends(recent_metrics: List[DatabaseMetrics]) -> Dict[str, float]:
        """Calculate performance trends."""
        if len(recent_metrics) < 2:
            return {'query_time_trend': 0.0, 'connection_trend': 0.0}
        first_half, second_half = PerformanceCalculator._split_metrics_by_time(recent_metrics)
        query_time_trend = PerformanceCalculator._calculate_query_time_trend(first_half, second_half)
        connection_trend = PerformanceCalculator._calculate_connection_trend(first_half, second_half)
        return PerformanceCalculator._build_trends_result(query_time_trend, connection_trend)


class MetricsSummaryBuilder:
    """Build performance summaries from metrics."""
    
    @staticmethod
    def _gather_summary_components(recent_metrics: List[DatabaseMetrics]) -> tuple:
        """Gather all summary components."""
        averages = MetricsSummaryBuilder._calculate_averages(recent_metrics)
        trends = PerformanceCalculator.calculate_trends(recent_metrics)
        totals = MetricsSummaryBuilder._calculate_totals(recent_metrics)
        return averages, trends, totals
    
    @staticmethod
    def build_performance_summary(recent_metrics: List[DatabaseMetrics]) -> Dict[str, Any]:
        """Build comprehensive performance summary."""
        if not recent_metrics:
            return {}
        
        averages, trends, totals = MetricsSummaryBuilder._gather_summary_components(recent_metrics)
        return MetricsSummaryBuilder._build_summary_dict(averages, trends, totals)
    
    @staticmethod
    def _calculate_averages(recent_metrics: List[DatabaseMetrics]) -> Dict[str, float]:
        """Calculate average metrics from recent data."""
        count = len(recent_metrics)
        return {
            'avg_query_time': sum(m.avg_query_time for m in recent_metrics) / count,
            'avg_connections': sum(m.active_connections for m in recent_metrics) / count,
            'avg_cache_hit_rate': sum(m.cache_hit_rate for m in recent_metrics) / count
        }
    
    @staticmethod
    def _calculate_totals(recent_metrics: List[DatabaseMetrics]) -> Dict[str, int]:
        """Calculate total metrics from recent data."""
        return {
            'total_queries': sum(m.total_queries for m in recent_metrics),
            'slow_queries': sum(m.slow_queries for m in recent_metrics),
            'cache_hits': sum(m.cache_hits for m in recent_metrics),
            'cache_misses': sum(m.cache_misses for m in recent_metrics)
        }
    
    @staticmethod
    def _build_summary_dict(averages: Dict[str, float], trends: Dict[str, float], totals: Dict[str, int]) -> Dict[str, Any]:
        """Build final summary dictionary."""
        summary = {**averages, **totals}
        summary.update({
            'query_time_trend': trends['query_time_trend'],
            'connection_trend': trends['connection_trend']
        })
        return summary

    @staticmethod
    def _build_dashboard_base_data(current_metrics: DatabaseMetrics, metrics_history: List[DatabaseMetrics], alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build base dashboard data components."""
        return {
            'current_metrics': current_metrics.to_dict(),
            'metrics_history': [m.to_dict() for m in metrics_history],
            'recent_alerts': alerts
        }
    
    @staticmethod
    def _add_dashboard_extras(base_data: Dict[str, Any], performance_summary: Dict[str, Any], cache_metrics: Dict[str, Any], transaction_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Add extra components to dashboard data."""
        base_data.update({
            'performance_summary': performance_summary,
            'cache_metrics': cache_metrics,
            'transaction_stats': transaction_stats
        })
        return base_data
    
    @staticmethod
    def build_dashboard_data(current_metrics: DatabaseMetrics, metrics_history: List[DatabaseMetrics], alerts: List[Dict[str, Any]], cache_metrics: Dict[str, Any], transaction_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive dashboard data."""
        performance_summary = MetricsSummaryBuilder.build_performance_summary(metrics_history)
        base_data = MetricsSummaryBuilder._build_dashboard_base_data(current_metrics, metrics_history, alerts)
        return MetricsSummaryBuilder._add_dashboard_extras(base_data, performance_summary, cache_metrics, transaction_stats)


class MetricsCollector:
    """Main metrics collection and aggregation system."""
    
    def __init__(self):
        self.storage = MetricsStorage()
        self.calculator = PerformanceCalculator()
        self.summary_builder = MetricsSummaryBuilder()
        self.thresholds = AlertThresholds()
    
    def collect_database_metrics(self) -> DatabaseMetrics:
        """Collect current database metrics."""
        return DatabaseMetrics(timestamp=datetime.now())
    
    def store_metrics(self, metrics: DatabaseMetrics) -> None:
        """Store collected metrics."""
        self.storage.store_metrics(metrics)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard."""
        if not self.storage.metrics_history:
            return {}
        
        current_metrics = list(self.storage.metrics_history)[-1]
        metrics_history = self.storage.get_recent_metrics(60)
        alerts = list(self.storage.alerts)
        
        return self.summary_builder.build_dashboard_data(
            current_metrics=current_metrics,
            metrics_history=metrics_history,
            alerts=alerts,
            cache_metrics={},
            transaction_stats={}
        )
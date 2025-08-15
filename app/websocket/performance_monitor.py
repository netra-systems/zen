"""WebSocket Performance Monitoring and Metrics Collection.

Comprehensive monitoring system for WebSocket performance, health,
and operational metrics with real-time tracking and alerting.
"""

import asyncio
import time
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MetricType(str, Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """Performance alert."""
    metric_name: str
    severity: AlertSeverity
    message: str
    threshold: float
    current_value: float
    timestamp: datetime
    resolved: bool = False
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceThresholds:
    """Performance monitoring thresholds."""
    max_response_time_ms: float = 1000.0
    max_memory_usage_mb: float = 500.0
    max_connection_errors_per_minute: int = 10
    max_message_queue_size: int = 1000
    min_throughput_messages_per_second: float = 10.0
    max_cpu_usage_percent: float = 80.0
    max_heartbeat_failures_per_minute: int = 5


class MetricCollector:
    """Collects and stores performance metrics."""
    
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
        point = MetricPoint(
            timestamp=datetime.now(timezone.utc),
            value=value,
            tags=tags
        )
        self.metrics[name].append(point)
        self.metric_types[name] = metric_type
    
    def get_metric_values(self, name: str, duration_minutes: Optional[int] = None) -> List[float]:
        """Get metric values for analysis."""
        if name not in self.metrics:
            return []
        
        points = list(self.metrics[name])
        
        if duration_minutes:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=duration_minutes)
            points = [p for p in points if p.timestamp >= cutoff_time]
        
        return [p.value for p in points]
    
    def get_metric_stats(self, name: str, duration_minutes: Optional[int] = None) -> Dict[str, float]:
        """Get statistical summary of a metric."""
        values = self.get_metric_values(name, duration_minutes)
        
        if not values:
            return {}
        
        return {
            "count": len(values),
            "sum": sum(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "stddev": statistics.stdev(values) if len(values) > 1 else 0.0
        }


class PerformanceMonitor:
    """Monitors WebSocket performance and generates alerts."""
    
    def __init__(self, thresholds: Optional[PerformanceThresholds] = None):
        self.thresholds = thresholds or PerformanceThresholds()
        self.metric_collector = MetricCollector()
        self.alerts: List[Alert] = []
        self.alert_callbacks: Set[Callable] = set()
        self.monitoring_active = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.connection_stats = defaultdict(dict)
        self.message_response_times: deque = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.throughput_tracker = deque(maxlen=60)  # Track per-second throughput
    
    async def start_monitoring(self) -> None:
        """Start performance monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("WebSocket performance monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self.monitoring_active = False
        
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("WebSocket performance monitoring stopped")
    
    def register_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register callback for alert notifications."""
        self.alert_callbacks.add(callback)
    
    def record_connection_event(self, connection_id: str, event: str, value: float = 1.0) -> None:
        """Record a connection-related event."""
        self.metric_collector.record_counter(f"connection.{event}", value, {"connection_id": connection_id})
        
        if event == "error":
            self.error_counts[connection_id] += 1
    
    def record_message_response_time(self, connection_id: str, response_time_ms: float) -> None:
        """Record message response time."""
        self.metric_collector.record_timer("message.response_time", response_time_ms, {"connection_id": connection_id})
        self.message_response_times.append(response_time_ms)
    
    def record_message_throughput(self, messages_count: int) -> None:
        """Record message throughput per second."""
        self.throughput_tracker.append((time.time(), messages_count))
        self.metric_collector.record_gauge("message.throughput", messages_count)
    
    def record_memory_usage(self, memory_mb: float) -> None:
        """Record memory usage."""
        self.metric_collector.record_gauge("system.memory_usage", memory_mb)
    
    def record_cpu_usage(self, cpu_percent: float) -> None:
        """Record CPU usage."""
        self.metric_collector.record_gauge("system.cpu_usage", cpu_percent)
    
    def record_queue_size(self, queue_name: str, size: int) -> None:
        """Record message queue size."""
        self.metric_collector.record_gauge(f"queue.{queue_name}.size", size)
    
    def record_heartbeat_event(self, connection_id: str, event: str) -> None:
        """Record heartbeat-related event."""
        self.metric_collector.record_counter(f"heartbeat.{event}", 1.0, {"connection_id": connection_id})
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_performance_thresholds()
                await self._cleanup_old_alerts()
                await asyncio.sleep(5)  # Check every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Performance monitoring loop error: {e}")
                await asyncio.sleep(10)
    
    async def _check_performance_thresholds(self) -> None:
        """Check performance metrics against thresholds."""
        # Check response time
        if self.message_response_times:
            avg_response_time = statistics.mean(self.message_response_times)
            if avg_response_time > self.thresholds.max_response_time_ms:
                await self._trigger_alert(
                    "high_response_time",
                    AlertSeverity.HIGH,
                    f"Average response time {avg_response_time:.1f}ms exceeds threshold {self.thresholds.max_response_time_ms}ms",
                    self.thresholds.max_response_time_ms,
                    avg_response_time
                )
        
        # Check memory usage
        memory_stats = self.metric_collector.get_metric_stats("system.memory_usage", 5)
        if memory_stats and memory_stats.get("mean", 0) > self.thresholds.max_memory_usage_mb:
            await self._trigger_alert(
                "high_memory_usage",
                AlertSeverity.HIGH,
                f"Memory usage {memory_stats['mean']:.1f}MB exceeds threshold {self.thresholds.max_memory_usage_mb}MB",
                self.thresholds.max_memory_usage_mb,
                memory_stats["mean"]
            )
        
        # Check error rate
        error_counts = self.metric_collector.get_metric_values("connection.error", 1)
        if len(error_counts) > self.thresholds.max_connection_errors_per_minute:
            await self._trigger_alert(
                "high_error_rate",
                AlertSeverity.CRITICAL,
                f"Connection errors {len(error_counts)}/min exceeds threshold {self.thresholds.max_connection_errors_per_minute}/min",
                self.thresholds.max_connection_errors_per_minute,
                len(error_counts)
            )
        
        # Check throughput
        throughput_stats = self.metric_collector.get_metric_stats("message.throughput", 5)
        if throughput_stats and throughput_stats.get("mean", 0) < self.thresholds.min_throughput_messages_per_second:
            await self._trigger_alert(
                "low_throughput",
                AlertSeverity.MEDIUM,
                f"Message throughput {throughput_stats['mean']:.1f}/s below threshold {self.thresholds.min_throughput_messages_per_second}/s",
                self.thresholds.min_throughput_messages_per_second,
                throughput_stats["mean"]
            )
        
        # Check CPU usage
        cpu_stats = self.metric_collector.get_metric_stats("system.cpu_usage", 5)
        if cpu_stats and cpu_stats.get("mean", 0) > self.thresholds.max_cpu_usage_percent:
            await self._trigger_alert(
                "high_cpu_usage",
                AlertSeverity.HIGH,
                f"CPU usage {cpu_stats['mean']:.1f}% exceeds threshold {self.thresholds.max_cpu_usage_percent}%",
                self.thresholds.max_cpu_usage_percent,
                cpu_stats["mean"]
            )
    
    async def _trigger_alert(self, metric_name: str, severity: AlertSeverity, 
                           message: str, threshold: float, current_value: float) -> None:
        """Trigger a performance alert."""
        # Check if we already have an active alert for this metric
        active_alerts = [a for a in self.alerts if a.metric_name == metric_name and not a.resolved]
        if active_alerts:
            return  # Don't spam with duplicate alerts
        
        alert = Alert(
            metric_name=metric_name,
            severity=severity,
            message=message,
            threshold=threshold,
            current_value=current_value,
            timestamp=datetime.now(timezone.utc)
        )
        
        self.alerts.append(alert)
        logger.warning(f"Performance alert: {message}")
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    async def _cleanup_old_alerts(self) -> None:
        """Clean up old resolved alerts."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        self.alerts = [a for a in self.alerts if a.timestamp >= cutoff_time or not a.resolved]
    
    def resolve_alert(self, metric_name: str) -> bool:
        """Resolve alerts for a specific metric."""
        resolved_count = 0
        for alert in self.alerts:
            if alert.metric_name == metric_name and not alert.resolved:
                alert.resolved = True
                resolved_count += 1
        
        if resolved_count > 0:
            logger.info(f"Resolved {resolved_count} alerts for metric {metric_name}")
        
        return resolved_count > 0
    
    def get_current_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary."""
        now = datetime.now(timezone.utc)
        
        # Response time stats
        response_time_stats = {}
        if self.message_response_times:
            response_time_stats = {
                "average_ms": statistics.mean(self.message_response_times),
                "median_ms": statistics.median(self.message_response_times),
                "p95_ms": sorted(self.message_response_times)[int(len(self.message_response_times) * 0.95)],
                "max_ms": max(self.message_response_times)
            }
        
        # Throughput calculation
        current_throughput = 0.0
        if self.throughput_tracker:
            recent_throughput = [count for timestamp, count in self.throughput_tracker 
                               if timestamp > time.time() - 60]  # Last minute
            current_throughput = sum(recent_throughput) / 60.0 if recent_throughput else 0.0
        
        # Active alerts
        active_alerts = [a for a in self.alerts if not a.resolved]
        alert_summary = {
            "total": len(active_alerts),
            "by_severity": {
                severity.value: len([a for a in active_alerts if a.severity == severity])
                for severity in AlertSeverity
            }
        }
        
        return {
            "timestamp": now.isoformat(),
            "response_time": response_time_stats,
            "throughput_messages_per_second": current_throughput,
            "total_connections": len(self.connection_stats),
            "active_alerts": alert_summary,
            "system_metrics": {
                "memory_usage_mb": self.metric_collector.get_metric_stats("system.memory_usage", 1),
                "cpu_usage_percent": self.metric_collector.get_metric_stats("system.cpu_usage", 1)
            },
            "error_counts": dict(self.error_counts),
            "monitoring_active": self.monitoring_active
        }
    
    def get_detailed_metrics(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """Get detailed metrics for a specific time period."""
        metrics_summary = {}
        
        for metric_name in self.metric_collector.metrics.keys():
            stats = self.metric_collector.get_metric_stats(metric_name, duration_minutes)
            if stats:
                metrics_summary[metric_name] = {
                    "type": self.metric_collector.metric_types.get(metric_name, "unknown").value,
                    "stats": stats,
                    "values": self.metric_collector.get_metric_values(metric_name, duration_minutes)[-100:]  # Last 100 values
                }
        
        return {
            "duration_minutes": duration_minutes,
            "metrics": metrics_summary,
            "alerts": [
                {
                    "metric_name": alert.metric_name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "resolved": alert.resolved
                }
                for alert in self.alerts
                if alert.timestamp >= datetime.now(timezone.utc) - timedelta(minutes=duration_minutes)
            ]
        }
    
    def export_metrics(self, format_type: str = "json") -> Dict[str, Any]:
        """Export metrics in specified format."""
        if format_type == "json":
            return {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "thresholds": self.thresholds.__dict__,
                "current_summary": self.get_current_performance_summary(),
                "detailed_metrics": self.get_detailed_metrics(60),
                "total_metrics_collected": sum(len(points) for points in self.metric_collector.metrics.values())
            }
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def reset_metrics(self) -> None:
        """Reset all metrics and alerts."""
        self.metric_collector = MetricCollector()
        self.alerts.clear()
        self.connection_stats.clear()
        self.message_response_times.clear()
        self.error_counts.clear()
        self.throughput_tracker.clear()
        logger.info("Performance metrics reset")
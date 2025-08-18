"""WebSocket Performance Monitor Core.

Main performance monitoring with micro-functions and threshold checking.
"""

import asyncio
import time
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from collections import deque, defaultdict

from app.logging_config import central_logger
from .performance_monitor_types import PerformanceThresholds, AlertSeverity
from .performance_monitor_collector import MetricCollector
from .performance_monitor_alerts import PerformanceAlertManager

logger = central_logger.get_logger(__name__)


class PerformanceMonitor:
    """Monitors WebSocket performance with micro-functions."""
    
    def __init__(self, thresholds: Optional[PerformanceThresholds] = None):
        self.thresholds = thresholds or PerformanceThresholds()
        self.metric_collector = MetricCollector()
        self.alert_manager = PerformanceAlertManager()
        self._init_monitoring_state()
        self._init_performance_tracking()
    
    def _init_monitoring_state(self) -> None:
        """Initialize monitoring state variables."""
        self.monitoring_active = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    def _init_performance_tracking(self) -> None:
        """Initialize performance tracking structures."""
        self.connection_stats = defaultdict(dict)
        self.message_response_times: deque = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.throughput_tracker = deque(maxlen=60)
    
    async def start_monitoring(self) -> None:
        """Start performance monitoring."""
        if self.monitoring_active:
            return
        self._activate_monitoring()
        logger.info("WebSocket performance monitoring started")
    
    def _activate_monitoring(self) -> None:
        """Activate monitoring loop."""
        self.monitoring_active = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self.monitoring_active = False
        if self._monitor_task and not self._monitor_task.done():
            await self._cancel_monitor_task()
        logger.info("WebSocket performance monitoring stopped")
    
    async def _cancel_monitor_task(self) -> None:
        """Cancel monitoring task safely."""
        self._monitor_task.cancel()
        try:
            await self._monitor_task
        except asyncio.CancelledError:
            pass
    
    def register_alert_callback(self, callback) -> None:
        """Register callback for alert notifications."""
        self.alert_manager.register_alert_callback(callback)
    
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
                await self._execute_monitoring_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Performance monitoring loop error: {e}")
                await asyncio.sleep(10)
    
    async def _execute_monitoring_cycle(self) -> None:
        """Execute single monitoring cycle."""
        await self._check_performance_thresholds()
        await self.alert_manager.cleanup_old_alerts()
        await asyncio.sleep(5)
    
    async def _check_performance_thresholds(self) -> None:
        """Check performance metrics against thresholds."""
        await self._check_response_time_threshold()
        await self._check_memory_threshold()
        await self._check_error_rate_threshold()
        await self._check_throughput_threshold()
        await self._check_cpu_threshold()
    
    async def _check_response_time_threshold(self) -> None:
        """Check response time threshold."""
        if not self.message_response_times:
            return
        avg_response_time = statistics.mean(self.message_response_times)
        if avg_response_time > self.thresholds.max_response_time_ms:
            await self._trigger_response_time_alert(avg_response_time)
    
    async def _trigger_response_time_alert(self, avg_response_time: float) -> None:
        """Trigger response time alert."""
        await self.alert_manager.trigger_alert(
            "high_response_time",
            AlertSeverity.HIGH,
            f"Average response time {avg_response_time:.1f}ms exceeds threshold {self.thresholds.max_response_time_ms}ms",
            self.thresholds.max_response_time_ms,
            avg_response_time
        )
    
    async def _check_memory_threshold(self) -> None:
        """Check memory usage threshold."""
        memory_stats = self.metric_collector.get_metric_stats("system.memory_usage", 5)
        if memory_stats and memory_stats.get("mean", 0) > self.thresholds.max_memory_usage_mb:
            await self._trigger_memory_alert(memory_stats["mean"])
    
    async def _trigger_memory_alert(self, memory_usage: float) -> None:
        """Trigger memory usage alert."""
        await self.alert_manager.trigger_alert(
            "high_memory_usage",
            AlertSeverity.HIGH,
            f"Memory usage {memory_usage:.1f}MB exceeds threshold {self.thresholds.max_memory_usage_mb}MB",
            self.thresholds.max_memory_usage_mb,
            memory_usage
        )
    
    async def _check_error_rate_threshold(self) -> None:
        """Check error rate threshold."""
        error_counts = self.metric_collector.get_metric_values("connection.error", 1)
        if len(error_counts) > self.thresholds.max_connection_errors_per_minute:
            await self._trigger_error_rate_alert(len(error_counts))
    
    async def _trigger_error_rate_alert(self, error_count: int) -> None:
        """Trigger error rate alert."""
        await self.alert_manager.trigger_alert(
            "high_error_rate",
            AlertSeverity.CRITICAL,
            f"Connection errors {error_count}/min exceeds threshold {self.thresholds.max_connection_errors_per_minute}/min",
            self.thresholds.max_connection_errors_per_minute,
            error_count
        )
    
    async def _check_throughput_threshold(self) -> None:
        """Check throughput threshold."""
        throughput_stats = self.metric_collector.get_metric_stats("message.throughput", 5)
        if throughput_stats and throughput_stats.get("mean", 0) < self.thresholds.min_throughput_messages_per_second:
            await self._trigger_throughput_alert(throughput_stats["mean"])
    
    async def _trigger_throughput_alert(self, throughput: float) -> None:
        """Trigger throughput alert."""
        await self.alert_manager.trigger_alert(
            "low_throughput",
            AlertSeverity.MEDIUM,
            f"Message throughput {throughput:.1f}/s below threshold {self.thresholds.min_throughput_messages_per_second}/s",
            self.thresholds.min_throughput_messages_per_second,
            throughput
        )
    
    async def _check_cpu_threshold(self) -> None:
        """Check CPU usage threshold."""
        cpu_stats = self.metric_collector.get_metric_stats("system.cpu_usage", 5)
        if cpu_stats and cpu_stats.get("mean", 0) > self.thresholds.max_cpu_usage_percent:
            await self._trigger_cpu_alert(cpu_stats["mean"])
    
    async def _trigger_cpu_alert(self, cpu_usage: float) -> None:
        """Trigger CPU usage alert."""
        await self.alert_manager.trigger_alert(
            "high_cpu_usage",
            AlertSeverity.HIGH,
            f"CPU usage {cpu_usage:.1f}% exceeds threshold {self.thresholds.max_cpu_usage_percent}%",
            self.thresholds.max_cpu_usage_percent,
            cpu_usage
        )
    
    def resolve_alert(self, metric_name: str) -> bool:
        """Resolve alerts for a specific metric."""
        return self.alert_manager.resolve_alert(metric_name)
    
    def get_current_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary."""
        return self._build_performance_summary_dict()
    
    def _build_performance_summary_dict(self) -> Dict[str, Any]:
        """Build performance summary dictionary."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_time": self._get_response_time_stats(),
            "throughput_messages_per_second": self._calculate_current_throughput(),
            "total_connections": len(self.connection_stats),
            "active_alerts": self.alert_manager.get_alert_summary(),
            "system_metrics": self._get_system_metrics(),
            "error_counts": dict(self.error_counts),
            "monitoring_active": self.monitoring_active
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
    
    def get_detailed_metrics(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """Get detailed metrics for a specific time period."""
        return {
            "duration_minutes": duration_minutes,
            "metrics": self._collect_metrics_summary(duration_minutes),
            "alerts": self.alert_manager.get_recent_alerts(duration_minutes)
        }
    
    def _collect_metrics_summary(self, duration_minutes: int) -> Dict[str, Any]:
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
    
    def export_metrics(self, format_type: str = "json") -> Dict[str, Any]:
        """Export metrics in specified format."""
        if format_type != "json":
            raise ValueError(f"Unsupported export format: {format_type}")
        return self._create_export_data()
    
    def _create_export_data(self) -> Dict[str, Any]:
        """Create complete export data."""
        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "thresholds": self.thresholds.__dict__,
            "current_summary": self.get_current_performance_summary(),
            "detailed_metrics": self.get_detailed_metrics(60),
            "total_metrics_collected": self._count_total_metrics()
        }
    
    def _count_total_metrics(self) -> int:
        """Count total metrics collected."""
        return sum(len(points) for points in self.metric_collector.metrics.values())
    
    def reset_metrics(self) -> None:
        """Reset all metrics and alerts."""
        self.metric_collector = MetricCollector()
        self.alert_manager = PerformanceAlertManager()
        self._reset_tracking_structures()
        logger.info("Performance metrics reset")
    
    def _reset_tracking_structures(self) -> None:
        """Reset performance tracking structures."""
        self.connection_stats.clear()
        self.message_response_times.clear()
        self.error_counts.clear()
        self.throughput_tracker.clear()
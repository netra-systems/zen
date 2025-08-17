"""Comprehensive performance monitoring for Netra platform.

This module provides real-time performance monitoring capabilities including:
- Database performance tracking
- Memory usage monitoring  
- WebSocket connection metrics
- LLM request performance
- System resource utilization
"""

import asyncio
import psutil
import time
import gc
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
from collections import deque, defaultdict
from contextlib import asynccontextmanager

from app.logging_config import central_logger
from app.core.performance_optimization_manager import performance_manager
from app.db.observability_metrics import DatabaseMetrics

logger = central_logger.get_logger(__name__)


@dataclass
class PerformanceMetric:
    """Single performance metric measurement."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class SystemResourceMetrics:
    """System resource utilization metrics."""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_connections: int
    timestamp: datetime = field(default_factory=datetime.now)


# DatabaseMetrics imported from app.db.observability_metrics


@dataclass
class WebSocketMetrics:
    """WebSocket performance metrics."""
    active_connections: int
    total_connections: int
    messages_sent: int
    messages_received: int
    failed_sends: int
    avg_message_size: float
    batch_efficiency: float
    timestamp: datetime = field(default_factory=datetime.now)


class MetricsCollector:
    """Collects and aggregates performance metrics."""
    
    def __init__(self, retention_period: int = 3600):  # 1 hour retention
        self.retention_period = retention_period
        self._metrics_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._collection_tasks: List[asyncio.Task] = []
        self._shutdown = False
        self._last_system_stats = None
        self._collection_interval = 5.0  # seconds
    
    async def start_collection(self) -> None:
        """Start metric collection tasks."""
        self._collection_tasks = [
            asyncio.create_task(self._collect_system_metrics()),
            asyncio.create_task(self._collect_database_metrics()),
            asyncio.create_task(self._collect_websocket_metrics()),
            asyncio.create_task(self._collect_memory_metrics()),
            asyncio.create_task(self._cleanup_old_metrics())
        ]
        logger.info("Performance metrics collection started")
    
    async def stop_collection(self) -> None:
        """Stop metric collection."""
        self._shutdown = True
        
        for task in self._collection_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance metrics collection stopped")
    
    async def _collect_system_metrics(self) -> None:
        """Collect system resource metrics."""
        while not self._shutdown:
            try:
                # CPU and Memory
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                
                # Disk I/O
                disk_io = psutil.disk_io_counters()
                disk_read_mb = disk_io.read_bytes / (1024 * 1024) if disk_io else 0
                disk_write_mb = disk_io.write_bytes / (1024 * 1024) if disk_io else 0
                
                # Network I/O
                net_io = psutil.net_io_counters()
                net_sent = net_io.bytes_sent if net_io else 0
                net_recv = net_io.bytes_recv if net_io else 0
                
                # Active network connections
                connections = len(psutil.net_connections())
                
                metrics = SystemResourceMetrics(
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_available_mb=memory.available / (1024 * 1024),
                    disk_io_read_mb=disk_read_mb,
                    disk_io_write_mb=disk_write_mb,
                    network_bytes_sent=net_sent,
                    network_bytes_recv=net_recv,
                    active_connections=connections
                )
                
                self._record_metric("system.cpu_percent", cpu_percent)
                self._record_metric("system.memory_percent", memory.percent)
                self._record_metric("system.memory_available_mb", memory.available / (1024 * 1024))
                self._record_metric("system.active_connections", connections)
                
                # Store complete metrics object
                self._metrics_buffer["system_resources"].append(metrics)
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
            
            await asyncio.sleep(self._collection_interval)
    
    async def _collect_database_metrics(self) -> None:
        """Collect database performance metrics."""
        while not self._shutdown:
            try:
                # Get database pool status
                from app.db.postgres import get_pool_status
                pool_status = get_pool_status()
                
                # Get query optimizer stats
                perf_stats = performance_manager.get_performance_stats()
                query_stats = perf_stats.get("query_optimizer", {})
                
                sync_pool = pool_status.get("sync", {})
                async_pool = pool_status.get("async", {})
                
                metrics = DatabaseMetrics(
                    active_connections=(sync_pool.get("total", 0) + async_pool.get("total", 0)),
                    pool_size=(sync_pool.get("size", 0) + async_pool.get("size", 0)),
                    pool_overflow=(sync_pool.get("overflow", 0) + async_pool.get("overflow", 0)),
                    query_count=query_stats.get("total_queries", 0),
                    avg_query_time=0.0,  # Would need to calculate from query metrics
                    slow_query_count=query_stats.get("slow_queries", 0),
                    cache_hit_ratio=self._calculate_cache_hit_ratio(perf_stats)
                )
                
                self._record_metric("database.active_connections", metrics.active_connections)
                self._record_metric("database.pool_utilization", 
                                  metrics.active_connections / max(metrics.pool_size, 1))
                self._record_metric("database.cache_hit_ratio", metrics.cache_hit_ratio)
                
                self._metrics_buffer["database_metrics"].append(metrics)
                
            except Exception as e:
                logger.error(f"Error collecting database metrics: {e}")
            
            await asyncio.sleep(self._collection_interval)
    
    async def _collect_websocket_metrics(self) -> None:
        """Collect WebSocket performance metrics."""
        while not self._shutdown:
            try:
                # Get WebSocket manager stats
                from app.websocket.connection import connection_manager
                from app.websocket.broadcast import BroadcastManager
                
                conn_stats = connection_manager.get_stats()
                
                metrics = WebSocketMetrics(
                    active_connections=conn_stats.get("active_connections", 0),
                    total_connections=conn_stats.get("total_connections", 0),
                    messages_sent=0,  # Would need to track this
                    messages_received=0,  # Would need to track this
                    failed_sends=0,  # Would need to track this
                    avg_message_size=0.0,  # Would need to track this
                    batch_efficiency=0.0  # Would calculate from batching stats
                )
                
                self._record_metric("websocket.active_connections", metrics.active_connections)
                self._record_metric("websocket.connection_efficiency", 
                                  metrics.active_connections / max(metrics.total_connections, 1))
                
                self._metrics_buffer["websocket_metrics"].append(metrics)
                
            except Exception as e:
                logger.error(f"Error collecting WebSocket metrics: {e}")
            
            await asyncio.sleep(self._collection_interval)
    
    async def _collect_memory_metrics(self) -> None:
        """Collect Python memory usage metrics."""
        while not self._shutdown:
            try:
                # Garbage collection stats
                gc_stats = gc.get_stats()
                gc_counts = gc.get_count()
                
                # Object counts by type
                object_counts = {}
                for obj_type in [dict, list, tuple, str, int, float]:
                    object_counts[obj_type.__name__] = len(gc.get_objects())
                
                self._record_metric("memory.gc_generation_0", gc_counts[0])
                self._record_metric("memory.gc_generation_1", gc_counts[1])
                self._record_metric("memory.gc_generation_2", gc_counts[2])
                
                # Force garbage collection periodically
                if time.time() % 300 < self._collection_interval:  # Every 5 minutes
                    collected = gc.collect()
                    self._record_metric("memory.gc_collected", collected)
                
            except Exception as e:
                logger.error(f"Error collecting memory metrics: {e}")
            
            await asyncio.sleep(self._collection_interval)
    
    async def _cleanup_old_metrics(self) -> None:
        """Clean up old metrics data."""
        while not self._shutdown:
            try:
                cutoff_time = datetime.now() - timedelta(seconds=self.retention_period)
                
                for metric_name, metric_buffer in self._metrics_buffer.items():
                    # Remove old metrics
                    while metric_buffer and hasattr(metric_buffer[0], 'timestamp'):
                        if metric_buffer[0].timestamp < cutoff_time:
                            metric_buffer.popleft()
                        else:
                            break
                
                await asyncio.sleep(60)  # Clean up every minute
                
            except Exception as e:
                logger.error(f"Error cleaning up metrics: {e}")
    
    def _record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a single metric value."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self._metrics_buffer[name].append(metric)
    
    def _calculate_cache_hit_ratio(self, perf_stats: Dict[str, Any]) -> float:
        """Calculate overall cache hit ratio."""
        cache_stats = perf_stats.get("cache_stats", {})
        total_hits = cache_stats.get("total_hits", 0)
        cache_size = cache_stats.get("size", 0)
        
        if cache_size > 0:
            return total_hits / cache_size
        return 0.0
    
    def get_recent_metrics(self, metric_name: str, duration_seconds: int = 300) -> List[PerformanceMetric]:
        """Get recent metrics for a specific metric name."""
        cutoff_time = datetime.now() - timedelta(seconds=duration_seconds)
        
        if metric_name not in self._metrics_buffer:
            return []
        
        return [
            metric for metric in self._metrics_buffer[metric_name]
            if metric.timestamp > cutoff_time
        ]
    
    def get_metric_summary(self, metric_name: str, duration_seconds: int = 300) -> Dict[str, float]:
        """Get statistical summary of a metric."""
        metrics = self.get_recent_metrics(metric_name, duration_seconds)
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "current": values[-1] if values else 0.0
        }


class PerformanceAlertManager:
    """Manages performance-related alerts and thresholds."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alert_rules = self._initialize_alert_rules()
        self._alert_callbacks: List[Callable] = []
        self._last_alerts: Dict[str, datetime] = {}
        self._alert_cooldown = 300  # 5 minutes between same alerts
    
    def _initialize_alert_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize performance alert rules."""
        return {
            "high_cpu": {
                "metric": "system.cpu_percent",
                "threshold": 80.0,
                "operator": ">",
                "duration": 60,  # seconds
                "severity": "warning"
            },
            "high_memory": {
                "metric": "system.memory_percent", 
                "threshold": 85.0,
                "operator": ">",
                "duration": 60,
                "severity": "warning"
            },
            "low_memory": {
                "metric": "system.memory_available_mb",
                "threshold": 512.0,
                "operator": "<",
                "duration": 30,
                "severity": "critical"
            },
            "database_pool_exhaustion": {
                "metric": "database.pool_utilization",
                "threshold": 0.9,
                "operator": ">",
                "duration": 30,
                "severity": "critical"
            },
            "low_cache_hit_ratio": {
                "metric": "database.cache_hit_ratio",
                "threshold": 0.5,
                "operator": "<",
                "duration": 300,
                "severity": "warning",
                "min_samples": 10  # Require minimum samples before alerting
            }
        }
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Add callback function for alert notifications."""
        self._alert_callbacks.append(callback)
    
    async def check_alerts(self) -> List[Dict[str, Any]]:
        """Check all alert rules and return triggered alerts."""
        triggered_alerts = []
        
        for alert_name, rule in self.alert_rules.items():
            try:
                if await self._evaluate_alert_rule(alert_name, rule):
                    alert_data = {
                        "name": alert_name,
                        "rule": rule,
                        "timestamp": datetime.now(),
                        "metric_summary": self.metrics_collector.get_metric_summary(rule["metric"])
                    }
                    triggered_alerts.append(alert_data)
                    
                    # Notify callbacks
                    for callback in self._alert_callbacks:
                        try:
                            callback(alert_name, alert_data)
                        except Exception as e:
                            logger.error(f"Error in alert callback: {e}")
                            
            except Exception as e:
                logger.error(f"Error evaluating alert rule {alert_name}: {e}")
        
        return triggered_alerts
    
    async def _evaluate_alert_rule(self, alert_name: str, rule: Dict[str, Any]) -> bool:
        """Evaluate a single alert rule."""
        # Check cooldown
        if alert_name in self._last_alerts:
            time_since_last = (datetime.now() - self._last_alerts[alert_name]).total_seconds()
            if time_since_last < self._alert_cooldown:
                return False
        
        # Get recent metrics
        metrics = self.metrics_collector.get_recent_metrics(
            rule["metric"], 
            rule.get("duration", 60)
        )
        
        if not metrics:
            return False
        
        # Check minimum samples requirement
        min_samples = rule.get("min_samples", 0)
        if len(metrics) < min_samples:
            return False
        
        # Check if threshold is exceeded for the duration
        threshold = rule["threshold"]
        operator = rule["operator"]
        
        violation_count = 0
        for metric in metrics:
            if operator == ">" and metric.value > threshold:
                violation_count += 1
            elif operator == "<" and metric.value < threshold:
                violation_count += 1
            elif operator == "==" and metric.value == threshold:
                violation_count += 1
        
        # Alert if violations exceed 50% of the duration samples
        violation_ratio = violation_count / len(metrics)
        if violation_ratio > 0.5:
            self._last_alerts[alert_name] = datetime.now()
            return True
        
        return False


class SystemPerformanceMonitor:
    """Main performance monitoring orchestrator."""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = PerformanceAlertManager(self.metrics_collector)
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown = False
    
    async def start_monitoring(self) -> None:
        """Start performance monitoring."""
        await self.metrics_collector.start_collection()
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Add default alert callback
        self.alert_manager.add_alert_callback(self._log_alert)
        
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self._shutdown = True
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        await self.metrics_collector.stop_collection()
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self._shutdown:
            try:
                # Check alerts every 30 seconds
                alerts = await self.alert_manager.check_alerts()
                
                if alerts:
                    logger.warning(f"Performance alerts triggered: {len(alerts)}")
                
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)
    
    def _log_alert(self, alert_name: str, alert_data: Dict[str, Any]) -> None:
        """Default alert callback that logs alerts."""
        severity = alert_data["rule"]["severity"]
        metric_summary = alert_data["metric_summary"]
        
        log_func = logger.critical if severity == "critical" else logger.warning
        log_func(
            f"Performance Alert [{severity.upper()}]: {alert_name} "
            f"- Current: {metric_summary.get('current', 'N/A')}, "
            f"Avg: {metric_summary.get('avg', 'N/A')}, "
            f"Threshold: {alert_data['rule']['threshold']}"
        )
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data."""
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "system": self.metrics_collector.get_metric_summary("system.cpu_percent"),
            "memory": self.metrics_collector.get_metric_summary("system.memory_percent"),
            "database": {
                "connections": self.metrics_collector.get_metric_summary("database.active_connections"),
                "cache_hit_ratio": self.metrics_collector.get_metric_summary("database.cache_hit_ratio")
            },
            "websockets": self.metrics_collector.get_metric_summary("websocket.active_connections"),
            "performance_optimization": performance_manager.get_performance_stats()
        }
        return dashboard
    
    @asynccontextmanager
    async def measure_operation(self, operation_name: str):
        """Context manager to measure operation performance."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            end_memory = psutil.Process().memory_info().rss
            memory_delta = (end_memory - start_memory) / (1024 * 1024)  # MB
            
            self.metrics_collector._record_metric(
                f"operation.{operation_name}.duration", 
                duration,
                {"unit": "seconds"}
            )
            self.metrics_collector._record_metric(
                f"operation.{operation_name}.memory_delta",
                memory_delta,
                {"unit": "mb"}
            )


# Global performance monitor instance
performance_monitor = SystemPerformanceMonitor()
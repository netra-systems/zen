"""Metrics collection and aggregation for Netra platform performance monitoring.

This module provides comprehensive metrics collection capabilities including:
- System resource monitoring (CPU, memory, disk, network)
- Database performance tracking  
- WebSocket connection metrics
- Memory usage and garbage collection monitoring
"""

import asyncio
import psutil
import time
import gc
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque, defaultdict

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
        self._collection_tasks = self._create_collection_tasks()
        logger.info("Performance metrics collection started")
    
    def _create_collection_tasks(self) -> List[asyncio.Task]:
        """Create all collection tasks."""
        return [
            asyncio.create_task(self._collect_system_metrics()),
            asyncio.create_task(self._collect_database_metrics()),
            asyncio.create_task(self._collect_websocket_metrics()),
            asyncio.create_task(self._collect_memory_metrics()),
            asyncio.create_task(self._cleanup_old_metrics())
        ]
    
    async def stop_collection(self) -> None:
        """Stop metric collection."""
        self._shutdown = True
        await self._cancel_collection_tasks()
        logger.info("Performance metrics collection stopped")
    
    async def _cancel_collection_tasks(self) -> None:
        """Cancel all collection tasks."""
        for task in self._collection_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    async def _collect_system_metrics(self) -> None:
        """Collect system resource metrics."""
        while not self._shutdown:
            try:
                metrics = self._gather_system_metrics()
                self._record_system_metrics(metrics)
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
            await asyncio.sleep(self._collection_interval)
    
    def _gather_system_metrics(self) -> SystemResourceMetrics:
        """Gather system resource metrics from psutil."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()
        connections = len(psutil.net_connections())
        
        return SystemResourceMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available_mb=memory.available / (1024 * 1024),
            disk_io_read_mb=disk_io.read_bytes / (1024 * 1024) if disk_io else 0,
            disk_io_write_mb=disk_io.write_bytes / (1024 * 1024) if disk_io else 0,
            network_bytes_sent=net_io.bytes_sent if net_io else 0,
            network_bytes_recv=net_io.bytes_recv if net_io else 0,
            active_connections=connections
        )
    
    def _record_system_metrics(self, metrics: SystemResourceMetrics) -> None:
        """Record system metrics to buffer."""
        self._record_metric("system.cpu_percent", metrics.cpu_percent)
        self._record_metric("system.memory_percent", metrics.memory_percent)
        self._record_metric("system.memory_available_mb", metrics.memory_available_mb)
        self._record_metric("system.active_connections", metrics.active_connections)
        self._metrics_buffer["system_resources"].append(metrics)
    
    async def _collect_database_metrics(self) -> None:
        """Collect database performance metrics."""
        while not self._shutdown:
            try:
                metrics = self._gather_database_metrics()
                self._record_database_metrics(metrics)
            except Exception as e:
                logger.error(f"Error collecting database metrics: {e}")
            await asyncio.sleep(self._collection_interval)
    
    def _gather_database_metrics(self) -> DatabaseMetrics:
        """Gather database metrics from pools and performance manager."""
        from app.db.postgres import get_pool_status
        pool_status = get_pool_status()
        perf_stats = performance_manager.get_performance_stats()
        query_stats = perf_stats.get("query_optimizer", {})
        
        sync_pool = pool_status.get("sync", {})
        async_pool = pool_status.get("async", {})
        
        return DatabaseMetrics(
            active_connections=(sync_pool.get("total", 0) + async_pool.get("total", 0)),
            pool_size=(sync_pool.get("size", 0) + async_pool.get("size", 0)),
            pool_overflow=(sync_pool.get("overflow", 0) + async_pool.get("overflow", 0)),
            query_count=query_stats.get("total_queries", 0),
            avg_query_time=0.0,  # Would need to calculate from query metrics
            slow_query_count=query_stats.get("slow_queries", 0),
            cache_hit_ratio=self._calculate_cache_hit_ratio(perf_stats)
        )
    
    def _record_database_metrics(self, metrics: DatabaseMetrics) -> None:
        """Record database metrics to buffer."""
        self._record_metric("database.active_connections", metrics.active_connections)
        pool_utilization = metrics.active_connections / max(metrics.pool_size, 1)
        self._record_metric("database.pool_utilization", pool_utilization)
        self._record_metric("database.cache_hit_ratio", metrics.cache_hit_ratio)
        self._metrics_buffer["database_metrics"].append(metrics)
    
    async def _collect_websocket_metrics(self) -> None:
        """Collect WebSocket performance metrics."""
        while not self._shutdown:
            try:
                metrics = self._gather_websocket_metrics()
                self._record_websocket_metrics(metrics)
            except Exception as e:
                logger.error(f"Error collecting WebSocket metrics: {e}")
            await asyncio.sleep(self._collection_interval)
    
    def _gather_websocket_metrics(self) -> WebSocketMetrics:
        """Gather WebSocket metrics from connection manager."""
        from app.websocket.connection import connection_manager
        conn_stats = connection_manager.get_stats()
        
        return WebSocketMetrics(
            active_connections=conn_stats.get("active_connections", 0),
            total_connections=conn_stats.get("total_connections", 0),
            messages_sent=0,  # Would need to track this
            messages_received=0,  # Would need to track this
            failed_sends=0,  # Would need to track this
            avg_message_size=0.0,  # Would need to track this
            batch_efficiency=0.0  # Would calculate from batching stats
        )
    
    def _record_websocket_metrics(self, metrics: WebSocketMetrics) -> None:
        """Record WebSocket metrics to buffer."""
        self._record_metric("websocket.active_connections", metrics.active_connections)
        efficiency = metrics.active_connections / max(metrics.total_connections, 1)
        self._record_metric("websocket.connection_efficiency", efficiency)
        self._metrics_buffer["websocket_metrics"].append(metrics)
    
    async def _collect_memory_metrics(self) -> None:
        """Collect Python memory usage metrics."""
        while not self._shutdown:
            try:
                self._gather_and_record_memory_metrics()
            except Exception as e:
                logger.error(f"Error collecting memory metrics: {e}")
            await asyncio.sleep(self._collection_interval)
    
    def _gather_and_record_memory_metrics(self) -> None:
        """Gather and record memory metrics."""
        gc_counts = gc.get_count()
        self._record_metric("memory.gc_generation_0", gc_counts[0])
        self._record_metric("memory.gc_generation_1", gc_counts[1])
        self._record_metric("memory.gc_generation_2", gc_counts[2])
        self._perform_periodic_gc()
    
    def _perform_periodic_gc(self) -> None:
        """Perform periodic garbage collection."""
        if time.time() % 300 < self._collection_interval:  # Every 5 minutes
            collected = gc.collect()
            self._record_metric("memory.gc_collected", collected)
    
    async def _cleanup_old_metrics(self) -> None:
        """Clean up old metrics data."""
        while not self._shutdown:
            try:
                self._remove_expired_metrics()
                await asyncio.sleep(60)  # Clean up every minute
            except Exception as e:
                logger.error(f"Error cleaning up metrics: {e}")
    
    def _remove_expired_metrics(self) -> None:
        """Remove expired metrics from all buffers."""
        cutoff_time = datetime.now() - timedelta(seconds=self.retention_period)
        
        for metric_name, metric_buffer in self._metrics_buffer.items():
            self._clean_buffer(metric_buffer, cutoff_time)
    
    def _clean_buffer(self, metric_buffer: deque, cutoff_time: datetime) -> None:
        """Clean expired metrics from a specific buffer."""
        while metric_buffer and hasattr(metric_buffer[0], 'timestamp'):
            if metric_buffer[0].timestamp < cutoff_time:
                metric_buffer.popleft()
            else:
                break
    
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
        return self._calculate_summary_stats(values)
    
    def _calculate_summary_stats(self, values: List[float]) -> Dict[str, float]:
        """Calculate summary statistics for metric values."""
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "current": values[-1] if values else 0.0
        }
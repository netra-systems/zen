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

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.performance_optimization_manager import performance_manager
from netra_backend.app.db.observability_metrics import DatabaseMetrics

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
        task_creators = self._get_task_creators()
        return [asyncio.create_task(creator()) for creator in task_creators]

    def _get_task_creators(self) -> List:
        """Get list of task creator functions."""
        return [
            self._collect_system_metrics, self._collect_database_metrics,
            self._collect_websocket_metrics, self._collect_memory_metrics,
            self._cleanup_old_metrics
        ]
    
    async def stop_collection(self) -> None:
        """Stop metric collection."""
        self._shutdown = True
        await self._cancel_collection_tasks()
        logger.info("Performance metrics collection stopped")
    
    async def _cancel_collection_tasks(self) -> None:
        """Cancel all collection tasks."""
        for task in self._collection_tasks:
            await self._cancel_single_task(task)

    async def _cancel_single_task(self, task: asyncio.Task) -> None:
        """Cancel a single collection task."""
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    async def _collect_system_metrics(self) -> None:
        """Collect system resource metrics."""
        while not self._shutdown:
            await self._collect_single_system_metrics_cycle()
            await asyncio.sleep(self._collection_interval)

    async def _collect_single_system_metrics_cycle(self) -> None:
        """Collect system metrics for one cycle."""
        try:
            metrics = self._gather_system_metrics()
            self._record_system_metrics(metrics)
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _gather_system_metrics(self) -> SystemResourceMetrics:
        """Gather system resource metrics from psutil."""
        system_stats = self._collect_system_stats()
        return self._build_system_metrics(system_stats)

    def _collect_system_stats(self) -> Dict[str, Any]:
        """Collect raw system statistics."""
        return self._gather_all_system_stats()

    def _gather_all_system_stats(self) -> Dict[str, Any]:
        """Gather all system statistics from psutil."""
        cpu_data = self._get_cpu_data()
        io_data = self._get_io_data()
        return {**cpu_data, **io_data}

    def _get_cpu_data(self) -> Dict[str, Any]:
        """Get CPU and memory data."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory()
        }

    def _get_io_data(self) -> Dict[str, Any]:
        """Get I/O and network data."""
        return {
            "disk_io": psutil.disk_io_counters(),
            "net_io": psutil.net_io_counters(),
            "connections": len(psutil.net_connections())
        }

    def _build_system_metrics(self, stats: Dict[str, Any]) -> SystemResourceMetrics:
        """Build SystemResourceMetrics from raw stats."""
        memory = stats["memory"]
        disk_io = stats["disk_io"]
        net_io = stats["net_io"]
        return self._create_system_metrics(stats, memory, disk_io, net_io)

    def _create_system_metrics(self, stats: Dict, memory, disk_io, net_io) -> SystemResourceMetrics:
        """Create SystemResourceMetrics from extracted components."""
        basic_metrics = self._get_basic_system_metrics(stats, memory)
        io_metrics = self._get_io_system_metrics(disk_io, net_io)
        return SystemResourceMetrics(**basic_metrics, **io_metrics, active_connections=stats["connections"])

    def _get_basic_system_metrics(self, stats: Dict, memory) -> Dict[str, float]:
        """Get basic system metrics (CPU and memory)."""
        return {
            "cpu_percent": stats["cpu_percent"], 
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available / (1024 * 1024)
        }

    def _get_io_system_metrics(self, disk_io, net_io) -> Dict[str, float]:
        """Get I/O system metrics (disk and network)."""
        return {
            "disk_io_read_mb": disk_io.read_bytes / (1024 * 1024) if disk_io else 0,
            "disk_io_write_mb": disk_io.write_bytes / (1024 * 1024) if disk_io else 0,
            "network_bytes_sent": net_io.bytes_sent if net_io else 0,
            "network_bytes_recv": net_io.bytes_recv if net_io else 0
        }
    
    def _record_system_metrics(self, metrics: SystemResourceMetrics) -> None:
        """Record system metrics to buffer."""
        self._record_individual_system_metrics(metrics)
        self._metrics_buffer["system_resources"].append(metrics)

    def _record_individual_system_metrics(self, metrics: SystemResourceMetrics) -> None:
        """Record individual system metric values."""
        self._record_metric("system.cpu_percent", metrics.cpu_percent)
        self._record_metric("system.memory_percent", metrics.memory_percent)
        self._record_metric("system.memory_available_mb", metrics.memory_available_mb)
        self._record_metric("system.active_connections", metrics.active_connections)
    
    async def _collect_database_metrics(self) -> None:
        """Collect database performance metrics."""
        while not self._shutdown:
            await self._collect_single_database_metrics_cycle()
            await asyncio.sleep(self._collection_interval)

    async def _collect_single_database_metrics_cycle(self) -> None:
        """Collect database metrics for one cycle."""
        try:
            metrics = self._gather_database_metrics()
            self._record_database_metrics(metrics)
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")
    
    def _gather_database_metrics(self) -> DatabaseMetrics:
        """Gather database metrics from pools and performance manager."""
        db_stats = self._collect_database_stats()
        return self._build_database_metrics(db_stats)

    def _collect_database_stats(self) -> Dict[str, Any]:
        """Collect raw database statistics."""
        from netra_backend.app.db.postgres import get_pool_status
        pool_status = get_pool_status()
        perf_stats = performance_manager.get_performance_stats()
        return self._build_db_stats_dict(pool_status, perf_stats)

    def _build_db_stats_dict(self, pool_status: Dict, perf_stats: Dict) -> Dict[str, Any]:
        """Build database statistics dictionary."""
        return {
            "pool_status": pool_status, "perf_stats": perf_stats,
            "query_stats": perf_stats.get("query_optimizer", {})
        }

    def _build_database_metrics(self, stats: Dict[str, Any]) -> DatabaseMetrics:
        """Build DatabaseMetrics from raw stats."""
        pool_data = self._extract_pool_data(stats)
        query_data = self._extract_query_data(stats)
        return self._create_database_metrics(pool_data, query_data, stats)
        
    def _extract_pool_data(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pool status data from stats."""
        pool_status = stats["pool_status"]
        sync_pool = pool_status.get("sync", {})
        async_pool = pool_status.get("async", {})
        return {"sync_pool": sync_pool, "async_pool": async_pool}
        
    def _extract_query_data(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Extract query statistics from stats."""
        return stats["query_stats"]
        
    def _create_database_metrics(self, pool_data: Dict, query_data: Dict, stats: Dict) -> DatabaseMetrics:
        """Create DatabaseMetrics from extracted data."""
        sync_pool, async_pool = pool_data["sync_pool"], pool_data["async_pool"]
        connection_data = self._calculate_connection_data(sync_pool, async_pool)
        return self._build_database_metrics_instance(connection_data, query_data, stats)

    def _calculate_connection_data(self, sync_pool: Dict, async_pool: Dict) -> Dict[str, int]:
        """Calculate connection data from pool information."""
        return {
            "active_connections": sync_pool.get("total", 0) + async_pool.get("total", 0),
            "pool_size": sync_pool.get("size", 0) + async_pool.get("size", 0),
            "pool_overflow": sync_pool.get("overflow", 0) + async_pool.get("overflow", 0)
        }

    def _build_database_metrics_instance(self, connection_data: Dict, query_data: Dict, stats: Dict) -> DatabaseMetrics:
        """Build DatabaseMetrics instance from processed data."""
        return DatabaseMetrics(
            timestamp=datetime.now(), **connection_data,
            total_queries=query_data.get("total_queries", 0), avg_query_time=0.0,
            slow_queries=query_data.get("slow_queries", 0),
            cache_hit_rate=self._calculate_cache_hit_ratio(stats["perf_stats"])
        )
    
    def _record_database_metrics(self, metrics: DatabaseMetrics) -> None:
        """Record database metrics to buffer."""
        self._record_metric("database.active_connections", metrics.active_connections)
        pool_utilization = metrics.active_connections / max(metrics.pool_size, 1)
        self._record_metric("database.pool_utilization", pool_utilization)
        self._record_metric("database.cache_hit_ratio", metrics.cache_hit_rate)
        self._metrics_buffer["database_metrics"].append(metrics)
    
    async def _collect_websocket_metrics(self) -> None:
        """Collect WebSocket performance metrics."""
        while not self._shutdown:
            await self._collect_single_websocket_metrics_cycle()
            await asyncio.sleep(self._collection_interval)

    async def _collect_single_websocket_metrics_cycle(self) -> None:
        """Collect WebSocket metrics for one cycle."""
        try:
            metrics = await self._gather_websocket_metrics()
            self._record_websocket_metrics(metrics)
        except Exception as e:
            logger.error(f"Error collecting WebSocket metrics: {e}")
    
    async def _gather_websocket_metrics(self) -> WebSocketMetrics:
        """Gather WebSocket metrics from connection manager."""
        try:
            from netra_backend.app.websocket.connection_manager import get_connection_manager
            conn_manager = get_connection_manager()
            if conn_manager is None:
                return self._build_empty_websocket_metrics()
            conn_stats = await conn_manager.get_stats()
            return self._build_websocket_metrics(conn_stats)
        except Exception as e:
            logger.warning(f"Failed to gather WebSocket metrics: {e}")
            return self._build_empty_websocket_metrics()

    def _build_websocket_metrics(self, conn_stats: Dict[str, Any]) -> WebSocketMetrics:
        """Build WebSocketMetrics from connection stats."""
        return WebSocketMetrics(
            active_connections=conn_stats.get("active_connections", 0),
            total_connections=conn_stats.get("total_connections", 0),
            messages_sent=0, messages_received=0, failed_sends=0,
            avg_message_size=0.0, batch_efficiency=0.0
        )
    
    def _build_empty_websocket_metrics(self) -> WebSocketMetrics:
        """Build empty WebSocketMetrics when connection manager unavailable."""
        return WebSocketMetrics(
            active_connections=0, total_connections=0,
            messages_sent=0, messages_received=0, failed_sends=0,
            avg_message_size=0.0, batch_efficiency=0.0
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
        
        return self._filter_metrics_by_time(
            self._metrics_buffer[metric_name], cutoff_time
        )

    def _filter_metrics_by_time(
        self, metrics: deque, cutoff_time: datetime
    ) -> List[PerformanceMetric]:
        """Filter metrics by timestamp."""
        return [
            metric for metric in metrics
            if metric.timestamp > cutoff_time
        ]
    
    def get_metric_summary(self, metric_name: str, duration_seconds: int = 300) -> Dict[str, float]:
        """Get statistical summary of a metric."""
        metrics = self.get_recent_metrics(metric_name, duration_seconds)
        return self._build_metric_summary(metrics)

    def _build_metric_summary(self, metrics: List[PerformanceMetric]) -> Dict[str, float]:
        """Build summary statistics from metrics."""
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        return self._calculate_summary_stats(values)
    
    def _calculate_summary_stats(self, values: List[float]) -> Dict[str, float]:
        """Calculate summary statistics for metric values."""
        basic_stats = self._get_basic_stats(values)
        extended_stats = self._get_extended_stats(values)
        return {**basic_stats, **extended_stats}

    def _get_basic_stats(self, values: List[float]) -> Dict[str, float]:
        """Get basic statistical measures."""
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values)
        }

    def _get_extended_stats(self, values: List[float]) -> Dict[str, float]:
        """Get extended statistical measures."""
        return {
            "avg": sum(values) / len(values),
            "current": values[-1] if values else 0.0
        }
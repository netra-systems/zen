"""Performance dashboard and reporting functionality for Netra platform.

This module provides comprehensive dashboard capabilities including:
- Performance dashboard data aggregation
- System overview reporting
- Operation performance measurement
- Real-time performance analytics
"""

import time
import psutil
from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.performance_optimization_manager import performance_manager

logger = central_logger.get_logger(__name__)


class PerformanceDashboard:
    """Provides performance dashboard and reporting functionality."""
    
    def __init__(self, metrics_collector):
        """Initialize dashboard with metrics collector."""
        self.metrics_collector = metrics_collector
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data."""
        core_data = self._get_core_dashboard_data()
        service_data = self._get_service_dashboard_data()
        return {**core_data, **service_data}

    def _get_core_dashboard_data(self) -> Dict[str, Any]:
        """Get core dashboard data components."""
        return {
            "timestamp": self._get_current_timestamp(),
            "system": self._get_system_dashboard_data(),
            "memory": self._get_memory_dashboard_data()
        }

    def _get_service_dashboard_data(self) -> Dict[str, Any]:
        """Get service-related dashboard data."""
        return {
            "database": self._get_database_dashboard_data(),
            "websockets": self._get_websocket_dashboard_data(),
            "performance_optimization": self._get_optimization_data()
        }
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()
    
    def _get_system_dashboard_data(self) -> Dict[str, Any]:
        """Get system metrics for dashboard."""
        return self.metrics_collector.get_metric_summary("system.cpu_percent")
    
    def _get_memory_dashboard_data(self) -> Dict[str, Any]:
        """Get memory metrics for dashboard."""
        return self.metrics_collector.get_metric_summary("system.memory_percent")
    
    def _get_database_dashboard_data(self) -> Dict[str, Any]:
        """Get database metrics for dashboard."""
        return {
            "connections": self._get_db_connections_data(),
            "cache_hit_ratio": self._get_cache_hit_data()
        }
    
    def _get_db_connections_data(self) -> Dict[str, Any]:
        """Get database connections data."""
        return self.metrics_collector.get_metric_summary("database.active_connections")
    
    def _get_cache_hit_data(self) -> Dict[str, Any]:
        """Get cache hit ratio data."""
        return self.metrics_collector.get_metric_summary("database.cache_hit_ratio")
    
    def _get_websocket_dashboard_data(self) -> Dict[str, Any]:
        """Get WebSocket metrics for dashboard."""
        return self.metrics_collector.get_metric_summary("websocket.active_connections")
    
    def _get_optimization_data(self) -> Dict[str, Any]:
        """Get performance optimization data."""
        return performance_manager.get_performance_stats()


class OperationMeasurement:
    """Provides operation performance measurement capabilities."""
    
    def __init__(self, metrics_collector):
        """Initialize with metrics collector."""
        self.metrics_collector = metrics_collector
    
    @asynccontextmanager
    async def measure_operation(self, operation_name: str):
        """Context manager to measure operation performance."""
        start_metrics = self._capture_start_metrics()
        
        try:
            yield
        finally:
            await self._record_operation_metrics(operation_name, start_metrics)
    
    def _capture_start_metrics(self) -> Dict[str, Any]:
        """Capture starting metrics for operation."""
        return {
            "start_time": time.time(),
            "start_memory": self._get_current_memory_usage()
        }
    
    def _get_current_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        return psutil.Process().memory_info().rss
    
    async def _record_operation_metrics(self, operation_name: str, start_metrics: Dict[str, Any]) -> None:
        """Record operation completion metrics."""
        duration = self._calculate_duration(start_metrics["start_time"])
        memory_delta = self._calculate_memory_delta(start_metrics["start_memory"])
        self._record_both_operation_metrics(operation_name, duration, memory_delta)

    def _record_both_operation_metrics(self, operation_name: str, duration: float, memory_delta: float) -> None:
        """Record both duration and memory metrics for operation."""
        self._record_duration_metric(operation_name, duration)
        self._record_memory_metric(operation_name, memory_delta)
    
    def _calculate_duration(self, start_time: float) -> float:
        """Calculate operation duration in seconds."""
        return time.time() - start_time
    
    def _calculate_memory_delta(self, start_memory: int) -> float:
        """Calculate memory usage delta in MB."""
        end_memory = self._get_current_memory_usage()
        return (end_memory - start_memory) / (1024 * 1024)
    
    def _record_duration_metric(self, operation_name: str, duration: float) -> None:
        """Record operation duration metric."""
        self.metrics_collector._record_metric(
            f"operation.{operation_name}.duration", 
            duration,
            {"unit": "seconds"}
        )
    
    def _record_memory_metric(self, operation_name: str, memory_delta: float) -> None:
        """Record operation memory delta metric."""
        self.metrics_collector._record_metric(
            f"operation.{operation_name}.memory_delta",
            memory_delta,
            {"unit": "mb"}
        )


class SystemOverview:
    """Provides system overview and health reporting."""
    
    def __init__(self, metrics_collector):
        """Initialize with metrics collector."""
        self.metrics_collector = metrics_collector
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health overview."""
        status_data = self._get_status_data()
        metrics_data = self._get_metrics_data()
        return {**status_data, **metrics_data}

    def _get_status_data(self) -> Dict[str, Any]:
        """Get status-related health data."""
        return {
            "overall_status": self._determine_overall_status(),
            "resource_utilization": self._get_resource_utilization()
        }

    def _get_metrics_data(self) -> Dict[str, Any]:
        """Get metrics-related health data."""
        return {
            "performance_metrics": self._get_performance_metrics(),
            "service_health": self._get_service_health()
        }
    
    def _determine_overall_status(self) -> str:
        """Determine overall system health status."""
        cpu_summary = self.metrics_collector.get_metric_summary("system.cpu_percent")
        memory_summary = self.metrics_collector.get_metric_summary("system.memory_percent")
        return self._evaluate_system_metrics(cpu_summary, memory_summary)

    def _evaluate_system_metrics(
        self, cpu_summary: Optional[Dict[str, float]], memory_summary: Optional[Dict[str, float]]
    ) -> str:
        """Evaluate system metrics for health status."""
        if not cpu_summary or not memory_summary:
            return "unknown"
        return self._calculate_health_status(cpu_summary, memory_summary)
    
    def _calculate_health_status(self, cpu_summary: Dict[str, float], memory_summary: Dict[str, float]) -> str:
        """Calculate health status from metrics."""
        cpu_current = cpu_summary.get("current", 0)
        memory_current = memory_summary.get("current", 0)
        return self._classify_health_level(cpu_current, memory_current)

    def _classify_health_level(self, cpu_current: float, memory_current: float) -> str:
        """Classify health level based on resource usage."""
        if cpu_current > 90 or memory_current > 90:
            return "critical"
        elif cpu_current > 75 or memory_current > 75:
            return "warning"
        return "healthy"
    
    def _get_resource_utilization(self) -> Dict[str, Any]:
        """Get current resource utilization."""
        cpu_data = self.metrics_collector.get_metric_summary("system.cpu_percent")
        memory_data = self.metrics_collector.get_metric_summary("system.memory_percent")
        connection_data = self.metrics_collector.get_metric_summary("system.active_connections")
        return {"cpu": cpu_data, "memory": memory_data, "connections": connection_data}
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance-related metrics."""
        db_pool = self.metrics_collector.get_metric_summary("database.pool_utilization")
        cache_ratio = self.metrics_collector.get_metric_summary("database.cache_hit_ratio")
        ws_connections = self.metrics_collector.get_metric_summary("websocket.active_connections")
        return {"database_pool": db_pool, "cache_efficiency": cache_ratio, "websocket_connections": ws_connections}
    
    def _get_service_health(self) -> Dict[str, Any]:
        """Get service health indicators."""
        return {
            "database_status": self._get_database_status(),
            "websocket_status": self._get_websocket_status(),
            "memory_status": self._get_memory_status()
        }
    
    def _get_database_status(self) -> str:
        """Get database service status."""
        pool_summary = self.metrics_collector.get_metric_summary("database.pool_utilization")
        if not pool_summary:
            return "unknown"
        return self._evaluate_database_utilization(pool_summary)

    def _evaluate_database_utilization(self, pool_summary: Dict[str, float]) -> str:
        """Evaluate database utilization for status."""
        utilization = pool_summary.get("current", 0)
        return "critical" if utilization > 0.9 else "healthy"
    
    def _get_websocket_status(self) -> str:
        """Get WebSocket service status."""
        ws_summary = self.metrics_collector.get_metric_summary("websocket.active_connections")
        return "healthy" if ws_summary else "unknown"
    
    def _get_memory_status(self) -> str:
        """Get memory service status."""
        memory_summary = self.metrics_collector.get_metric_summary("system.memory_available_mb")
        if not memory_summary:
            return "unknown"
        return self._evaluate_memory_availability(memory_summary)

    def _evaluate_memory_availability(self, memory_summary: Dict[str, float]) -> str:
        """Evaluate memory availability for status."""
        available_mb = memory_summary.get("current", 0)
        return "critical" if available_mb < 512 else "healthy"
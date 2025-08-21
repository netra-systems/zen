"""Performance monitoring module for Netra platform.

This module provides the main performance monitoring interface expected by tests
and other parts of the system. It aggregates functionality from the existing 
monitoring components into a unified interface.

Business Value Justification (BVJ):
1. Segment: Mid & Enterprise (performance critical)
2. Business Goal: Monitor AI workload optimization performance
3. Value Impact: Performance monitoring = 20-30% better optimization
4. Revenue Impact: Better performance = Higher value capture
"""

import asyncio
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from datetime import datetime

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.metrics_collector import MetricsCollector, PerformanceMetric
from netra_backend.app.monitoring.performance_alerting import PerformanceAlertManager
from netra_backend.app.monitoring.dashboard import PerformanceDashboard

logger = central_logger.get_logger(__name__)


class PerformanceMonitor:
    """Main performance monitor interface for unified monitoring."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self._init_components()
        self._init_state()
    
    def _init_components(self) -> None:
        """Initialize monitoring components."""
        self.metrics_collector = MetricsCollector()
        self._alert_manager = PerformanceAlertManager(self.metrics_collector)
        self._dashboard = PerformanceDashboard(self.metrics_collector)
    
    def _init_state(self) -> None:
        """Initialize monitoring state."""
        self._monitoring_active = False
        self._alert_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self) -> None:
        """Start performance monitoring."""
        if self._monitoring_active:
            return
        await self._start_monitoring_components()

    async def _start_monitoring_components(self) -> None:
        """Start all monitoring components."""
        await self.metrics_collector.start_collection()
        self._alert_task = asyncio.create_task(self._alert_monitoring_loop())
        self._monitoring_active = True
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        if not self._monitoring_active:
            return
        await self._stop_monitoring_components()

    async def _stop_monitoring_components(self) -> None:
        """Stop all monitoring components."""
        self._monitoring_active = False
        await self._stop_alert_task()
        await self.metrics_collector.stop_collection()
        logger.info("Performance monitoring stopped")
    
    async def _stop_alert_task(self) -> None:
        """Stop alert monitoring task."""
        if self._alert_task:
            self._alert_task.cancel()
            try:
                await self._alert_task
            except asyncio.CancelledError:
                pass
    
    async def _alert_monitoring_loop(self) -> None:
        """Alert monitoring loop."""
        while self._monitoring_active:
            await self._execute_alert_check_cycle()

    async def _execute_alert_check_cycle(self) -> None:
        """Execute single alert check cycle."""
        try:
            await self._alert_manager.check_alerts()
            await asyncio.sleep(30)  # Check every 30 seconds
        except asyncio.CancelledError:
            return
        except Exception as e:
            await self._handle_alert_error(e)

    async def _handle_alert_error(self, error: Exception) -> None:
        """Handle alert monitoring error."""
        logger.error(f"Error in alert monitoring: {error}")
        await asyncio.sleep(30)
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get performance dashboard data."""
        dashboard_data = self._dashboard.get_dashboard_data()
        enhanced_data = self._enhance_dashboard_data(dashboard_data)
        return {**enhanced_data, **dashboard_data}

    def _enhance_dashboard_data(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance dashboard data with required fields."""
        return {
            "timestamp": dashboard_data.get("timestamp", datetime.now().isoformat()),
            "system": self._get_system_metrics(),
            "memory": self._get_memory_metrics()
        }
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        cpu_metrics = self.metrics_collector.get_recent_metrics("system.cpu_percent", 60)
        return {
            "cpu_usage": cpu_metrics[-1].value if cpu_metrics else 0.0,
            "load_average": self._calculate_load_average()
        }
    
    def _get_memory_metrics(self) -> Dict[str, Any]:
        """Get memory performance metrics."""
        memory_metrics = self.metrics_collector.get_recent_metrics("system.memory_percent", 60)
        available_metrics = self.metrics_collector.get_recent_metrics("system.memory_available_mb", 60)
        return self._build_memory_metrics_dict(memory_metrics, available_metrics)

    def _build_memory_metrics_dict(self, memory_metrics: List, available_metrics: List) -> Dict[str, Any]:
        """Build memory metrics dictionary from collected metrics."""
        return {
            "usage_percent": memory_metrics[-1].value if memory_metrics else 0.0,
            "available_mb": available_metrics[-1].value if available_metrics else 0.0
        }
    
    def _calculate_load_average(self) -> float:
        """Calculate system load average."""
        cpu_metrics = self.metrics_collector.get_recent_metrics("system.cpu_percent", 300)
        if not cpu_metrics:
            return 0.0
        
        return sum(m.value for m in cpu_metrics) / len(cpu_metrics)
    
    @asynccontextmanager
    async def measure_operation(self, operation_name: str):
        """Context manager to measure operation performance."""
        start_time = asyncio.get_event_loop().time()
        try:
            yield
        finally:
            await self._finalize_operation_measurement(operation_name, start_time)

    async def _finalize_operation_measurement(self, operation_name: str, start_time: float) -> None:
        """Finalize operation measurement and record metric."""
        duration = asyncio.get_event_loop().time() - start_time
        self._record_operation_metric(operation_name, duration)
    
    def _record_operation_metric(self, operation_name: str, duration: float) -> None:
        """Record operation performance metric."""
        metric_name = f"operation.{operation_name}.duration"
        self.metrics_collector._record_metric(metric_name, duration * 1000)  # Convert to ms
    
    def add_alert_callback(self, callback) -> None:
        """Add alert callback to alert manager."""
        self._alert_manager.add_alert_callback(callback)
    
    def get_metric_summary(self, metric_name: str, duration_seconds: int = 300) -> Dict[str, float]:
        """Get metric summary statistics."""
        return self.metrics_collector.get_metric_summary(metric_name, duration_seconds)


# Export the existing classes with expected names
__all__ = [
    "MetricsCollector",
    "PerformanceMonitor", 
    "PerformanceAlertManager"
]
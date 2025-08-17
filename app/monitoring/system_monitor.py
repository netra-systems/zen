"""Main system performance monitoring orchestrator for Netra platform.

This module provides the main SystemPerformanceMonitor class that orchestrates
all monitoring components including metrics collection, alerting, and dashboard reporting.
"""

import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from app.logging_config import central_logger
from .metrics_collector import MetricsCollector
from .performance_alerting import PerformanceAlertManager  
from .dashboard import PerformanceDashboard, OperationMeasurement, SystemOverview

logger = central_logger.get_logger(__name__)


class SystemPerformanceMonitor:
    """Main performance monitoring orchestrator."""
    
    def __init__(self):
        """Initialize system performance monitor."""
        self._init_core_components()
        self._init_monitoring_state()
    
    def _init_core_components(self) -> None:
        """Initialize core monitoring components."""
        self.metrics_collector = MetricsCollector()
        self.alert_manager = PerformanceAlertManager(self.metrics_collector)
        self.dashboard = PerformanceDashboard(self.metrics_collector)
        self.operation_measurement = OperationMeasurement(self.metrics_collector)
        self.system_overview = SystemOverview(self.metrics_collector)
    
    def _init_monitoring_state(self) -> None:
        """Initialize monitoring state variables."""
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown = False
    
    async def start_monitoring(self) -> None:
        """Start performance monitoring."""
        await self._start_metrics_collection()
        await self._start_alert_monitoring()
        self._add_default_alert_handlers()
        logger.info("Performance monitoring started")
    
    async def _start_metrics_collection(self) -> None:
        """Start metrics collection process."""
        await self.metrics_collector.start_collection()
    
    async def _start_alert_monitoring(self) -> None:
        """Start alert monitoring loop."""
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    def _add_default_alert_handlers(self) -> None:
        """Add default alert callback handlers."""
        self.alert_manager.add_alert_callback(self._log_alert)
    
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self._shutdown = True
        await self._stop_monitoring_task()
        await self._stop_metrics_collection()
        logger.info("Performance monitoring stopped")
    
    async def _stop_monitoring_task(self) -> None:
        """Stop monitoring task gracefully."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _stop_metrics_collection(self) -> None:
        """Stop metrics collection process."""
        await self.metrics_collector.stop_collection()
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self._shutdown:
            try:
                await self._execute_monitoring_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._handle_monitoring_error(e)
    
    async def _execute_monitoring_cycle(self) -> None:
        """Execute one monitoring cycle."""
        alerts = await self.alert_manager.check_alerts()
        self._log_triggered_alerts(alerts)
        await asyncio.sleep(30)  # Check alerts every 30 seconds
    
    def _log_triggered_alerts(self, alerts: list) -> None:
        """Log any triggered alerts."""
        if alerts:
            logger.warning(f"Performance alerts triggered: {len(alerts)}")
    
    async def _handle_monitoring_error(self, error: Exception) -> None:
        """Handle monitoring loop errors."""
        logger.error(f"Error in monitoring loop: {error}")
        await asyncio.sleep(30)
    
    def _log_alert(self, alert_name: str, alert_data: Dict[str, Any]) -> None:
        """Default alert callback that logs alerts."""
        severity = alert_data["rule"]["severity"]
        metric_summary = alert_data["metric_summary"]
        
        self._log_alert_details(alert_name, severity, metric_summary, alert_data)
    
    def _log_alert_details(self, alert_name: str, severity: str, metric_summary: Dict, alert_data: Dict) -> None:
        """Log detailed alert information."""
        log_func = logger.critical if severity == "critical" else logger.warning
        log_func(
            f"Performance Alert [{severity.upper()}]: {alert_name} "
            f"- Current: {metric_summary.get('current', 'N/A')}, "
            f"Avg: {metric_summary.get('avg', 'N/A')}, "
            f"Threshold: {alert_data['rule']['threshold']}"
        )
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data."""
        return self.dashboard.get_dashboard_data()
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health overview."""
        return self.system_overview.get_system_health()
    
    @asynccontextmanager
    async def measure_operation(self, operation_name: str):
        """Context manager to measure operation performance."""
        async with self.operation_measurement.measure_operation(operation_name):
            yield
    
    def add_alert_callback(self, callback) -> None:
        """Add custom alert callback."""
        self.alert_manager.add_alert_callback(callback)
    
    def get_metrics_summary(self, metric_name: str, duration_seconds: int = 300) -> Dict[str, float]:
        """Get statistical summary of a specific metric."""
        return self.metrics_collector.get_metric_summary(metric_name, duration_seconds)
    
    def get_recent_metrics(self, metric_name: str, duration_seconds: int = 300):
        """Get recent metrics for a specific metric name.""" 
        return self.metrics_collector.get_recent_metrics(metric_name, duration_seconds)


class MonitoringManager:
    """High-level monitoring manager for easy integration."""
    
    def __init__(self):
        """Initialize monitoring manager."""
        self.monitor = SystemPerformanceMonitor()
        self._started = False
    
    async def start(self) -> None:
        """Start monitoring if not already started."""
        if not self._started:
            await self.monitor.start_monitoring()
            self._started = True
    
    async def stop(self) -> None:
        """Stop monitoring if currently started."""
        if self._started:
            await self.monitor.stop_monitoring()
            self._started = False
    
    async def restart(self) -> None:
        """Restart monitoring system."""
        await self.stop()
        await self.start()
    
    def get_dashboard(self) -> Dict[str, Any]:
        """Get performance dashboard data."""
        return self.monitor.get_performance_dashboard()
    
    def get_health(self) -> Dict[str, Any]:
        """Get system health status."""
        return self.monitor.get_system_health()
    
    @asynccontextmanager
    async def measure(self, operation_name: str):
        """Measure operation performance."""
        async with self.monitor.measure_operation(operation_name):
            yield
    
    def is_running(self) -> bool:
        """Check if monitoring is currently running."""
        return self._started


# Global performance monitor instance
performance_monitor = SystemPerformanceMonitor()
monitoring_manager = MonitoringManager()
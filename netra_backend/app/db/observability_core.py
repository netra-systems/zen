"""Database Observability Core

Main coordination class for database monitoring.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.db.observability_alerts import AlertOrchestrator
from netra_backend.app.db.observability_collectors import (
    MetricsCollectionOrchestrator,
    MonitoringCycleManager,
)
from netra_backend.app.db.observability_metrics import (
    AlertThresholds,
    DatabaseMetrics,
    MetricsStorage,
    MetricsSummaryBuilder,
)


class ObservabilityCore:
    """Core observability coordination class - main interface for database monitoring."""
    
    def __init__(self):
        """Initialize observability core with all components."""
        self.alert_orchestrator = AlertOrchestrator()
        self.metrics_collector = MetricsCollectionOrchestrator()
        self.cycle_manager = MonitoringCycleManager()
        self.metrics_storage = MetricsStorage()
        self.summary_builder = MetricsSummaryBuilder()
    
    async def initialize_monitoring(self) -> None:
        """Initialize all monitoring systems."""
        await self.metrics_collector.initialize()
        await self.alert_orchestrator.initialize()
    
    async def collect_all_metrics(self) -> DatabaseMetrics:
        """Collect all database metrics."""
        return await self.metrics_collector.collect_metrics()
    
    async def check_alerts(self, metrics: DatabaseMetrics) -> None:
        """Check and process any alerts based on metrics."""
        await self.alert_orchestrator.process_metrics(metrics)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DatabaseObservability:
    """Database observability and monitoring system."""
    
    def __init__(self, alert_thresholds: Optional[AlertThresholds] = None):
        """Initialize observability system."""
        self._initialize_alert_system(alert_thresholds)
        self._initialize_monitoring_state()
        self._initialize_metrics_and_callbacks()

    def _initialize_alert_system(self, alert_thresholds: Optional[AlertThresholds]) -> None:
        """Initialize alert system components."""
        self.alert_thresholds = alert_thresholds or AlertThresholds()
        self.storage = MetricsStorage()

    def _initialize_monitoring_state(self) -> None:
        """Initialize monitoring state variables."""
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        self._collection_interval = 60  # 1 minute

    def _initialize_metrics_and_callbacks(self) -> None:
        """Initialize current metrics and callback settings."""
        self.current_metrics = DatabaseMetrics(timestamp=datetime.now())
        self.alert_callback: Optional[callable] = None

    async def start_monitoring(self) -> None:
        """Start background monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Database observability monitoring started")

    async def _cancel_monitoring_task(self) -> None:
        """Cancel the monitoring task if it exists."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._running = False
        await self._cancel_monitoring_task()
        logger.info("Database observability monitoring stopped")

    async def _collect_metrics(self) -> None:
        """Collect comprehensive database metrics."""
        metrics = await MetricsCollectionOrchestrator.collect_comprehensive_metrics(
            self.storage.metrics_history, 
            self.storage.query_times
        )
        self.current_metrics = metrics
        self.storage.store_metrics(metrics)

    async def _check_alerts(self) -> None:
        """Check for alert conditions."""
        await AlertOrchestrator.check_and_process_alerts(
            self.current_metrics,
            self.alert_thresholds,
            self.storage,
            self.alert_callback
        )

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        await MonitoringCycleManager.run_monitoring_cycle(
            self._collect_metrics,
            self._check_alerts,
            self._collection_interval,
            lambda: self._running
        )

    def record_query_time(self, duration: float) -> None:
        """Record query execution time."""
        self.storage.record_query_time(duration)

    def record_connection_event(self, event_type: str, details: Dict[str, Any] = None) -> None:
        """Record connection event."""
        self.storage.record_connection_event(event_type, details)

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current database metrics."""
        return self.current_metrics.to_dict()

    def get_metrics_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics history for specified hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        metrics_list = self.storage.get_metrics_since(cutoff)
        return [metrics.to_dict() for metrics in metrics_list]

    def get_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alerts from specified time period."""
        cutoff = datetime.now() - timedelta(hours=hours)
        cutoff_iso = cutoff.isoformat()
        return self.storage.get_alerts_since(cutoff_iso)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        recent_metrics = self.storage.get_recent_metrics(60)  # Last hour
        return MetricsSummaryBuilder.build_performance_summary(recent_metrics)

    def set_alert_callback(self, callback: callable) -> None:
        """Set callback function for alerts."""
        self.alert_callback = callback


# Global observability instance
database_observability = DatabaseObservability()


async def setup_database_observability(alert_callback: Optional[callable] = None) -> None:
    """Setup database observability monitoring."""
    if alert_callback:
        database_observability.set_alert_callback(alert_callback)
    
    await database_observability.start_monitoring()
    logger.info("Database observability setup complete")


async def get_database_dashboard() -> Dict[str, Any]:
    """Get comprehensive database dashboard data."""
    current_metrics = database_observability.current_metrics
    metrics_history = database_observability.storage.get_recent_metrics(60)
    alerts = database_observability.get_alerts(hours=1)
    
    # Import here to avoid circular imports
    from netra_backend.app.db.query_cache import query_cache
    from netra_backend.app.db.transaction_manager import transaction_manager
    
    return MetricsSummaryBuilder.build_dashboard_data(
        current_metrics,
        metrics_history,
        alerts,
        query_cache.get_metrics(),
        transaction_manager.get_transaction_stats()
    )
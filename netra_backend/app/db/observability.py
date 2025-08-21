"""Database Observability Dashboard

Provides comprehensive monitoring and metrics for database operations,
connection pools, and performance optimization.

This module has been refactored into focused sub-modules for maintainability.
"""

# Import all components from the refactored modules
from netra_backend.app.db.observability_metrics import (
    DatabaseMetrics, AlertThresholds, MetricsStorage, 
    PerformanceCalculator, MetricsSummaryBuilder
)
from netra_backend.app.db.observability_collectors import (
    ConnectionMetricsCollector, QueryMetricsCollector, 
    TransactionMetricsCollector, CacheMetricsCollector,
    PerformanceMetricsCollector, MetricsCollectionOrchestrator,
    MonitoringCycleManager
)
from netra_backend.app.db.observability_alerts import (
    ConnectionAlertChecker, QueryAlertChecker, CacheAlertChecker,
    TransactionAlertChecker, AlertHandler, AlertOrchestrator
)
from netra_backend.app.db.observability_core import (
    DatabaseObservability, database_observability,
    setup_database_observability, get_database_dashboard
)

# Maintain backward compatibility exports
__all__ = [
    'DatabaseMetrics',
    'AlertThresholds', 
    'DatabaseObservability',
    'database_observability',
    'setup_database_observability',
    'get_database_dashboard'
]
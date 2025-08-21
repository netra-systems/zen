"""Database Observability Dashboard

Provides comprehensive monitoring and metrics for database operations,
connection pools, and performance optimization.

This module has been refactored into focused sub-modules for maintainability.
"""

# Import all components from the refactored modules
from netra_backend.app.db.observability_alerts import (
    AlertHandler,
    AlertOrchestrator,
    CacheAlertChecker,
    ConnectionAlertChecker,
    QueryAlertChecker,
    TransactionAlertChecker,
)
from netra_backend.app.db.observability_collectors import (
    CacheMetricsCollector,
    ConnectionMetricsCollector,
    MetricsCollectionOrchestrator,
    MonitoringCycleManager,
    PerformanceMetricsCollector,
    QueryMetricsCollector,
    TransactionMetricsCollector,
)
from netra_backend.app.db.observability_core import (
    DatabaseObservability,
    database_observability,
    get_database_dashboard,
    setup_database_observability,
)
from netra_backend.app.db.observability_metrics import (
    AlertThresholds,
    DatabaseMetrics,
    MetricsStorage,
    MetricsSummaryBuilder,
    PerformanceCalculator,
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
"""
Modular monitoring and alerting system for Netra AI platform.
Provides comprehensive monitoring, alerting, dashboard, and notification capabilities.

Architecture:
- metrics_collector: Core metrics collection and aggregation
- performance_alerting: Performance-based alerting and threshold management  
- dashboard: Performance dashboard and reporting functionality
- system_monitor: Main orchestrator and high-level monitoring management
- alert_manager_*: Alert management and notification system
"""

# Core monitoring components
from netra_backend.app.monitoring.alert_evaluator import AlertEvaluator

# Alert management system
from netra_backend.app.monitoring.alert_manager_compact import (
    CompactAlertManager,
    alert_manager,
)
from netra_backend.app.monitoring.alert_models import (
    Alert,
    AlertLevel,
    AlertRule,
    NotificationChannel,
)
from netra_backend.app.monitoring.alert_notifications import NotificationDeliveryManager
from netra_backend.app.monitoring.dashboard import (
    OperationMeasurement,
    PerformanceDashboard,
    SystemOverview,
)
from netra_backend.app.monitoring.health_calculator import HealthScoreCalculator
from netra_backend.app.monitoring.metrics_collector import (
    PerformanceMetric,
    SystemResourceMetrics,
    WebSocketMetrics,
)

# Monitoring models
from netra_backend.app.monitoring.models import (
    HealthCheck,
    Metric,
    MetricDataPoint,
    MetricsCollector,
    MetricSeries,
    MetricType,
    MetricUnit,
    MonitoringDashboard,
)
from netra_backend.app.monitoring.performance_alerting import PerformanceAlertManager
# PerformanceMonitor removed - use PerformanceMetric from metrics_collector or SystemPerformanceMonitor
from netra_backend.app.monitoring.system_monitor import (
    MonitoringManager,
    SystemPerformanceMonitor,
    monitoring_manager,
    performance_monitor,
)

__all__ = [
    # Core monitoring
    "MetricsCollector",
    "PerformanceMetric", 
    "SystemResourceMetrics",
    "WebSocketMetrics",
    "PerformanceAlertManager",
    "PerformanceDashboard",
    "OperationMeasurement", 
    "SystemOverview",
    "SystemPerformanceMonitor",
    "MonitoringManager",
    "performance_monitor",
    "monitoring_manager",
    
    # Alert management
    "CompactAlertManager",
    "alert_manager", 
    "AlertLevel",
    "NotificationChannel",
    "AlertRule",
    "Alert",
    "AlertEvaluator",
    "NotificationDeliveryManager",
    "HealthScoreCalculator",
    
    # Monitoring models
    "MetricType",
    "MetricUnit", 
    "Metric",
    "MetricDataPoint",
    "MetricSeries",
    "MonitoringDashboard",
    "HealthCheck"
]
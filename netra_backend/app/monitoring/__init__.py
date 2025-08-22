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
from .alert_evaluator import AlertEvaluator

# Alert management system
from .alert_manager_compact import (
    CompactAlertManager,
    alert_manager,
)
from .alert_models import (
    Alert,
    AlertLevel,
    AlertRule,
    NotificationChannel,
)
from .alert_notifications import NotificationDeliveryManager
from .dashboard import (
    OperationMeasurement,
    PerformanceDashboard,
    SystemOverview,
)
from .health_calculator import HealthScoreCalculator
from .metrics_collector import (
    PerformanceMetric,
    SystemResourceMetrics,
    WebSocketMetrics,
)

# Monitoring models
from .models import (
    HealthCheck,
    Metric,
    MetricDataPoint,
    MetricsCollector,
    MetricSeries,
    MetricType,
    MetricUnit,
    MonitoringDashboard,
)
from .performance_alerting import PerformanceAlertManager
from .performance_monitor import PerformanceMonitor
from .system_monitor import (
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
    "PerformanceMonitor",
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
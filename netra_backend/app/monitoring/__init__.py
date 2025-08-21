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
from netra_backend.app.metrics_collector import MetricsCollector, PerformanceMetric, SystemResourceMetrics, WebSocketMetrics
from netra_backend.app.performance_alerting import PerformanceAlertManager
from netra_backend.app.dashboard import PerformanceDashboard, OperationMeasurement, SystemOverview
from netra_backend.app.system_monitor import SystemPerformanceMonitor, MonitoringManager, performance_monitor, monitoring_manager

# Alert management system
from netra_backend.app.alert_manager_compact import CompactAlertManager, alert_manager
from netra_backend.app.alert_models import AlertLevel, NotificationChannel, AlertRule, Alert
from netra_backend.app.alert_evaluator import AlertEvaluator  
from netra_backend.app.alert_notifications import NotificationDeliveryManager

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
    "NotificationDeliveryManager"
]
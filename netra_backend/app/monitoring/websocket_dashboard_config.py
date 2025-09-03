"""
WebSocket Monitoring Dashboard Configuration

This module provides configuration for monitoring dashboards that track WebSocket
notification health and detect silent failures.

DASHBOARD OBJECTIVES:
1. Real-time visibility into notification delivery status
2. Early warning indicators for system degradation
3. User-specific diagnostics and troubleshooting
4. Performance trending and capacity planning
5. Automated alert configuration and escalation

DASHBOARD CATEGORIES:
- Executive Summary: High-level system health for leadership
- Operations Dashboard: Detailed metrics for operations team
- User Diagnostics: Per-user notification health analysis  
- Performance Analytics: Trends and capacity planning
- Alert Management: Alert configuration and escalation
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.websocket_notification_monitor import get_websocket_notification_monitor, WebSocketNotificationMonitor
from netra_backend.app.monitoring.websocket_health_checks import get_websocket_health_checker, WebSocketHealthChecker

logger = central_logger.get_logger(__name__)


class DashboardType(Enum):
    """Types of monitoring dashboards."""
    EXECUTIVE_SUMMARY = "executive_summary"
    OPERATIONS_DASHBOARD = "operations_dashboard"
    USER_DIAGNOSTICS = "user_diagnostics"
    PERFORMANCE_ANALYTICS = "performance_analytics"
    ALERT_MANAGEMENT = "alert_management"


class MetricType(Enum):
    """Types of metrics for dashboard widgets."""
    GAUGE = "gauge"
    COUNTER = "counter"
    RATE = "rate"
    HISTOGRAM = "histogram"
    TIME_SERIES = "time_series"
    STATUS_INDICATOR = "status_indicator"
    ALERT_LIST = "alert_list"
    USER_TABLE = "user_table"


@dataclass
class DashboardWidget:
    """Configuration for a dashboard widget."""
    widget_id: str
    title: str
    description: str
    metric_type: MetricType
    
    # Data source configuration
    data_source: str
    query_params: Dict[str, Any] = field(default_factory=dict)
    refresh_interval_seconds: int = 30
    
    # Display configuration
    display_config: Dict[str, Any] = field(default_factory=dict)
    alert_thresholds: Dict[str, Any] = field(default_factory=dict)
    
    # Size and position
    width: int = 6  # Grid columns (1-12)
    height: int = 4  # Grid rows
    row: Optional[int] = None
    column: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert widget to dictionary for dashboard config."""
        return {
            "widget_id": self.widget_id,
            "title": self.title,
            "description": self.description,
            "metric_type": self.metric_type.value,
            "data_source": self.data_source,
            "query_params": self.query_params,
            "refresh_interval_seconds": self.refresh_interval_seconds,
            "display_config": self.display_config,
            "alert_thresholds": self.alert_thresholds,
            "layout": {
                "width": self.width,
                "height": self.height,
                "row": self.row,
                "column": self.column
            }
        }


@dataclass  
class DashboardConfig:
    """Configuration for a monitoring dashboard."""
    dashboard_id: str
    title: str
    description: str
    dashboard_type: DashboardType
    
    widgets: List[DashboardWidget] = field(default_factory=list)
    refresh_interval_seconds: int = 30
    auto_refresh: bool = True
    
    # Access control
    required_permissions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert dashboard to dictionary for configuration."""
        return {
            "dashboard_id": self.dashboard_id,
            "title": self.title,
            "description": self.description,
            "dashboard_type": self.dashboard_type.value,
            "widgets": [w.to_dict() for w in self.widgets],
            "refresh_interval_seconds": self.refresh_interval_seconds,
            "auto_refresh": self.auto_refresh,
            "required_permissions": self.required_permissions,
            "created_at": datetime.now(timezone.utc).isoformat()
        }


class DashboardConfigManager:
    """Manages configuration for WebSocket monitoring dashboards."""
    
    def __init__(self):
        """Initialize dashboard config manager."""
        self.dashboards: Dict[str, DashboardConfig] = {}
        self._initialize_default_dashboards()
        
        logger.info("📊 WebSocket Dashboard Config Manager initialized")
    
    def _initialize_default_dashboards(self) -> None:
        """Initialize default dashboard configurations."""
        self.dashboards = {
            DashboardType.EXECUTIVE_SUMMARY.value: self._create_executive_dashboard(),
            DashboardType.OPERATIONS_DASHBOARD.value: self._create_operations_dashboard(),
            DashboardType.USER_DIAGNOSTICS.value: self._create_user_diagnostics_dashboard(),
            DashboardType.PERFORMANCE_ANALYTICS.value: self._create_performance_dashboard(),
            DashboardType.ALERT_MANAGEMENT.value: self._create_alert_management_dashboard()
        }
    
    def _create_executive_dashboard(self) -> DashboardConfig:
        """Create executive summary dashboard."""
        dashboard = DashboardConfig(
            dashboard_id="websocket_executive",
            title="WebSocket System Health - Executive Summary",
            description="High-level WebSocket notification system health for leadership",
            dashboard_type=DashboardType.EXECUTIVE_SUMMARY,
            required_permissions=["admin", "executive"]
        )
        
        # System status indicator
        dashboard.widgets.append(DashboardWidget(
            widget_id="system_status",
            title="System Status",
            description="Overall WebSocket notification system health",
            metric_type=MetricType.STATUS_INDICATOR,
            data_source="websocket_monitor.get_system_health_status",
            display_config={
                "show_uptime": True,
                "show_success_rate": True,
                "status_colors": {
                    "healthy": "#28a745",
                    "degraded": "#ffc107", 
                    "unhealthy": "#fd7e14",
                    "critical": "#dc3545"
                }
            },
            width=4,
            height=3
        ))
        
        # Notification success rate gauge
        dashboard.widgets.append(DashboardWidget(
            widget_id="success_rate_gauge",
            title="Notification Success Rate",
            description="Overall notification delivery success rate",
            metric_type=MetricType.GAUGE,
            data_source="websocket_monitor.system_metrics.overall_success_rate",
            display_config={
                "min_value": 0.0,
                "max_value": 1.0,
                "target_value": 0.95,
                "format": "percentage",
                "gauge_colors": [
                    {"range": [0, 0.90], "color": "#dc3545"},
                    {"range": [0.90, 0.95], "color": "#fd7e14"},
                    {"range": [0.95, 1.0], "color": "#28a745"}
                ]
            },
            alert_thresholds={
                "critical": 0.90,
                "warning": 0.95
            },
            width=4,
            height=3
        ))
        
        # Silent failures counter
        dashboard.widgets.append(DashboardWidget(
            widget_id="silent_failures_counter",
            title="Silent Failures",
            description="Critical silent notification failures requiring immediate attention",
            metric_type=MetricType.COUNTER,
            data_source="websocket_monitor.system_metrics.total_silent_failures",
            display_config={
                "show_trend": True,
                "counter_color": "#dc3545",
                "target_value": 0
            },
            alert_thresholds={
                "critical": 1,  # Any silent failure is critical
                "warning": 0
            },
            width=4,
            height=3
        ))
        
        # Active users indicator
        dashboard.widgets.append(DashboardWidget(
            widget_id="active_users",
            title="Active Users",
            description="Number of users currently receiving notifications",
            metric_type=MetricType.COUNTER,
            data_source="websocket_monitor.get_user_metrics",
            query_params={"transform": "count"},
            display_config={
                "show_capacity": True,
                "capacity_limit": 100
            },
            width=6,
            height=2
        ))
        
        # Critical alerts list
        dashboard.widgets.append(DashboardWidget(
            widget_id="critical_alerts",
            title="Critical Alerts",
            description="Active critical alerts requiring immediate attention",
            metric_type=MetricType.ALERT_LIST,
            data_source="alert_manager.get_critical_alerts",
            query_params={"level": "critical", "limit": 10},
            display_config={
                "show_timestamp": True,
                "show_severity": True,
                "auto_refresh": True
            },
            width=6,
            height=4
        ))
        
        return dashboard
    
    def _create_operations_dashboard(self) -> DashboardConfig:
        """Create detailed operations dashboard."""
        dashboard = DashboardConfig(
            dashboard_id="websocket_operations",
            title="WebSocket Operations Dashboard", 
            description="Detailed metrics for operations team monitoring and troubleshooting",
            dashboard_type=DashboardType.OPERATIONS_DASHBOARD,
            required_permissions=["admin", "operations"]
        )
        
        # Notification metrics grid
        metrics_widgets = [
            ("notifications_attempted", "Notifications Attempted", "total_notifications_attempted"),
            ("notifications_delivered", "Notifications Delivered", "total_notifications_delivered"),
            ("notifications_failed", "Notifications Failed", "total_notifications_failed"),
            ("bridge_initializations", "Bridge Initializations", "total_bridge_initializations"),
            ("connection_drops", "Connection Drops", "total_connection_drops"),
            ("isolation_violations", "Isolation Violations", "user_isolation_violations")
        ]
        
        for i, (widget_id, title, metric) in enumerate(metrics_widgets):
            dashboard.widgets.append(DashboardWidget(
                widget_id=widget_id,
                title=title,
                description=f"Total count of {title.lower()}",
                metric_type=MetricType.COUNTER,
                data_source=f"websocket_monitor.system_metrics.{metric}",
                display_config={"show_trend": True, "show_rate": True},
                width=4,
                height=2,
                row=i // 3,
                column=(i % 3) * 4
            ))
        
        # Performance metrics
        dashboard.widgets.append(DashboardWidget(
            widget_id="delivery_latency_histogram",
            title="Notification Delivery Latency",
            description="Distribution of notification delivery times",
            metric_type=MetricType.HISTOGRAM,
            data_source="websocket_monitor.get_recent_events",
            query_params={"event_type": "notification_delivered", "limit": 1000},
            display_config={
                "bins": [0, 100, 500, 1000, 2000, 5000, 10000],
                "y_axis_label": "Count",
                "x_axis_label": "Latency (ms)"
            },
            width=6,
            height=4
        ))
        
        # Connection health time series
        dashboard.widgets.append(DashboardWidget(
            widget_id="connection_health_timeseries",
            title="Connection Health Over Time",
            description="Active connections and connection drops over time",
            metric_type=MetricType.TIME_SERIES,
            data_source="websocket_monitor.get_performance_metrics",
            query_params={"metric": "active_connections", "time_range": "24h"},
            display_config={
                "y_axis_label": "Count",
                "show_events": True,
                "overlay_connection_drops": True
            },
            width=6,
            height=4
        ))
        
        # Recent events table
        dashboard.widgets.append(DashboardWidget(
            widget_id="recent_events",
            title="Recent WebSocket Events",
            description="Live stream of WebSocket notification events",
            metric_type=MetricType.TIME_SERIES,
            data_source="websocket_monitor.get_recent_events",
            query_params={"limit": 50},
            display_config={
                "table_columns": ["timestamp", "event_type", "user_id", "success", "duration_ms"],
                "auto_scroll": True,
                "highlight_failures": True
            },
            width=12,
            height=4
        ))
        
        return dashboard
    
    def _create_user_diagnostics_dashboard(self) -> DashboardConfig:
        """Create user-specific diagnostics dashboard."""
        dashboard = DashboardConfig(
            dashboard_id="websocket_user_diagnostics",
            title="User WebSocket Diagnostics",
            description="Per-user notification delivery analysis and troubleshooting",
            dashboard_type=DashboardType.USER_DIAGNOSTICS,
            required_permissions=["admin", "support"]
        )
        
        # User selection widget
        dashboard.widgets.append(DashboardWidget(
            widget_id="user_selector",
            title="User Selection",
            description="Select user for detailed analysis",
            metric_type=MetricType.USER_TABLE,
            data_source="websocket_monitor.get_user_metrics",
            display_config={
                "selectable": True,
                "show_health_status": True,
                "columns": ["user_id", "success_rate", "health_status", "last_activity"]
            },
            width=6,
            height=4
        ))
        
        # User notification success rate
        dashboard.widgets.append(DashboardWidget(
            widget_id="user_success_rate",
            title="User Success Rate",
            description="Notification delivery success rate for selected user",
            metric_type=MetricType.GAUGE,
            data_source="websocket_monitor.get_user_metrics",
            query_params={"user_filter": "selected_user"},
            display_config={
                "min_value": 0.0,
                "max_value": 1.0,
                "target_value": 0.95,
                "format": "percentage"
            },
            width=3,
            height=3
        ))
        
        # User failure count
        dashboard.widgets.append(DashboardWidget(
            widget_id="user_failures",
            title="User Failures",
            description="Total notification failures for selected user",
            metric_type=MetricType.COUNTER,
            data_source="websocket_monitor.get_user_metrics",
            query_params={"user_filter": "selected_user", "metric": "notifications_failed"},
            display_config={"alert_on_increase": True},
            width=3,
            height=3
        ))
        
        # User event timeline
        dashboard.widgets.append(DashboardWidget(
            widget_id="user_event_timeline",
            title="User Event Timeline",
            description="Timeline of notification events for selected user",
            metric_type=MetricType.TIME_SERIES,
            data_source="websocket_monitor.get_recent_events",
            query_params={"user_filter": "selected_user", "limit": 100},
            display_config={
                "timeline_view": True,
                "event_types": ["notification_attempted", "notification_delivered", "notification_failed"],
                "color_by_success": True
            },
            width=12,
            height=6
        ))
        
        return dashboard
    
    def _create_performance_dashboard(self) -> DashboardConfig:
        """Create performance analytics dashboard.""" 
        dashboard = DashboardConfig(
            dashboard_id="websocket_performance",
            title="WebSocket Performance Analytics",
            description="Performance trends, capacity planning, and optimization insights",
            dashboard_type=DashboardType.PERFORMANCE_ANALYTICS,
            required_permissions=["admin", "engineering"]
        )
        
        # Performance overview metrics
        dashboard.widgets.append(DashboardWidget(
            widget_id="performance_overview",
            title="Performance Overview",
            description="Key performance indicators at a glance",
            metric_type=MetricType.STATUS_INDICATOR,
            data_source="websocket_health_checker.get_health_summary",
            display_config={
                "metrics": [
                    "avg_notification_delivery_time_ms",
                    "avg_bridge_init_time_ms", 
                    "active_connections",
                    "memory_usage_mb"
                ],
                "thresholds": {
                    "avg_notification_delivery_time_ms": {"warning": 1000, "critical": 5000},
                    "avg_bridge_init_time_ms": {"warning": 500, "critical": 1000},
                    "active_connections": {"warning": 5, "critical": 1}
                }
            },
            width=12,
            height=2
        ))
        
        # Latency trends 
        dashboard.widgets.append(DashboardWidget(
            widget_id="latency_trends",
            title="Notification Latency Trends",
            description="Notification delivery latency over time",
            metric_type=MetricType.TIME_SERIES,
            data_source="websocket_monitor.get_performance_metrics",
            query_params={"metric": "delivery_latency", "time_range": "24h"},
            display_config={
                "y_axis_label": "Latency (ms)",
                "show_percentiles": [50, 95, 99],
                "alert_lines": [1000, 5000]
            },
            width=6,
            height=4
        ))
        
        # Throughput metrics
        dashboard.widgets.append(DashboardWidget(
            widget_id="notification_throughput",
            title="Notification Throughput",
            description="Notifications per minute delivered successfully",
            metric_type=MetricType.TIME_SERIES,
            data_source="websocket_monitor.get_recent_events",
            query_params={"event_type": "notification_delivered", "time_range": "24h", "aggregate": "rate"},
            display_config={
                "y_axis_label": "Notifications/min",
                "show_trend_line": True
            },
            width=6,
            height=4
        ))
        
        # Memory usage trends
        dashboard.widgets.append(DashboardWidget(
            widget_id="memory_usage_trends",
            title="Memory Usage Trends",
            description="WebSocket system memory usage over time",
            metric_type=MetricType.TIME_SERIES,
            data_source="websocket_monitor.get_performance_metrics",
            query_params={"metric": "memory_usage", "time_range": "24h"},
            display_config={
                "y_axis_label": "Memory (MB)",
                "show_baseline": True,
                "alert_on_growth": True
            },
            width=6,
            height=4
        ))
        
        # Resource utilization
        dashboard.widgets.append(DashboardWidget(
            widget_id="resource_utilization", 
            title="Resource Utilization",
            description="System resource usage metrics",
            metric_type=MetricType.STATUS_INDICATOR,
            data_source="websocket_monitor.get_performance_metrics",
            display_config={
                "metrics": [
                    "cpu_usage_percent",
                    "memory_usage_percent", 
                    "active_connections_percent",
                    "queue_utilization_percent"
                ],
                "format": "percentage",
                "warning_threshold": 80,
                "critical_threshold": 95
            },
            width=6,
            height=4
        ))
        
        return dashboard
    
    def _create_alert_management_dashboard(self) -> DashboardConfig:
        """Create alert management dashboard."""
        dashboard = DashboardConfig(
            dashboard_id="websocket_alerts",
            title="WebSocket Alert Management",
            description="Configuration and management of WebSocket notification alerts",
            dashboard_type=DashboardType.ALERT_MANAGEMENT,
            required_permissions=["admin"]
        )
        
        # Active alerts
        dashboard.widgets.append(DashboardWidget(
            widget_id="active_alerts",
            title="Active Alerts",
            description="Currently active WebSocket alerts requiring attention",
            metric_type=MetricType.ALERT_LIST,
            data_source="alert_manager.get_active_alerts",
            query_params={"component": "websocket", "resolved": False},
            display_config={
                "columns": ["level", "title", "timestamp", "component", "actions"],
                "sortable": True,
                "filterable": True,
                "actions": ["acknowledge", "resolve", "escalate"]
            },
            width=12,
            height=6
        ))
        
        # Alert frequency trends
        dashboard.widgets.append(DashboardWidget(
            widget_id="alert_frequency",
            title="Alert Frequency",
            description="Alert frequency over time by severity level",
            metric_type=MetricType.TIME_SERIES,
            data_source="alert_manager.get_alert_history",
            query_params={"component": "websocket", "time_range": "7d"},
            display_config={
                "stack_by": "alert_level",
                "y_axis_label": "Alerts/hour",
                "colors": {
                    "critical": "#dc3545",
                    "error": "#fd7e14", 
                    "warning": "#ffc107",
                    "info": "#17a2b8"
                }
            },
            width=6,
            height=4
        ))
        
        # Alert configuration
        dashboard.widgets.append(DashboardWidget(
            widget_id="alert_thresholds",
            title="Alert Thresholds",
            description="Current alert threshold configuration",
            metric_type=MetricType.STATUS_INDICATOR,
            data_source="websocket_health_checker.thresholds",
            display_config={
                "editable": True,
                "show_current_values": True,
                "validation": True
            },
            width=6,
            height=4
        ))
        
        return dashboard
    
    # Dashboard data providers
    
    async def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Get live data for a dashboard."""
        dashboard = self.dashboards.get(dashboard_id)
        if not dashboard:
            raise ValueError(f"Dashboard not found: {dashboard_id}")
        
        dashboard_data = {
            "config": dashboard.to_dict(),
            "widgets": {},
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        # Get data for each widget
        for widget in dashboard.widgets:
            try:
                widget_data = await self._get_widget_data(widget)
                dashboard_data["widgets"][widget.widget_id] = widget_data
            except Exception as e:
                logger.error(f"Failed to get data for widget {widget.widget_id}: {e}")
                dashboard_data["widgets"][widget.widget_id] = {
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        
        return dashboard_data
    
    async def _get_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for a specific widget."""
        monitor = get_websocket_notification_monitor()
        health_checker = get_websocket_health_checker()
        
        # Route data source calls
        if widget.data_source.startswith("websocket_monitor."):
            return await self._get_monitor_data(monitor, widget)
        elif widget.data_source.startswith("websocket_health_checker."):
            return await self._get_health_checker_data(health_checker, widget)
        else:
            # Generic data source
            return await self._get_generic_data(widget)
    
    async def _get_monitor_data(self, monitor: WebSocketNotificationMonitor, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data from WebSocket monitor."""
        source = widget.data_source.replace("websocket_monitor.", "")
        
        if source == "get_system_health_status":
            return monitor.get_system_health_status()
        elif source == "get_user_metrics":
            user_filter = widget.query_params.get("user_filter")
            return monitor.get_user_metrics(user_filter)
        elif source == "get_recent_events":
            limit = widget.query_params.get("limit", 100)
            event_type_str = widget.query_params.get("event_type")
            event_type = None
            if event_type_str:
                from netra_backend.app.monitoring.websocket_notification_monitor import NotificationEventType
                try:
                    event_type = NotificationEventType(event_type_str)
                except ValueError:
                    pass
            return monitor.get_recent_events(limit, event_type)
        elif source == "get_performance_metrics":
            return monitor.get_performance_metrics()
        elif source.startswith("system_metrics."):
            metric_name = source.replace("system_metrics.", "")
            metrics_dict = monitor.system_metrics.to_dict()
            return {"value": metrics_dict.get(metric_name), "timestamp": datetime.now(timezone.utc).isoformat()}
        else:
            return {"error": f"Unknown monitor data source: {source}"}
    
    async def _get_health_checker_data(self, health_checker: WebSocketHealthChecker, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data from health checker."""
        source = widget.data_source.replace("websocket_health_checker.", "")
        
        if source == "get_health_summary":
            return health_checker.get_health_summary()
        elif source == "thresholds":
            return health_checker.thresholds
        else:
            return {"error": f"Unknown health checker data source: {source}"}
    
    async def _get_generic_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data from generic sources."""
        return {
            "message": f"Generic data source not implemented: {widget.data_source}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # Configuration management
    
    def get_dashboard_list(self) -> List[Dict[str, Any]]:
        """Get list of available dashboards."""
        return [
            {
                "dashboard_id": config.dashboard_id,
                "title": config.title,
                "description": config.description,
                "dashboard_type": config.dashboard_type.value,
                "widget_count": len(config.widgets)
            }
            for config in self.dashboards.values()
        ]
    
    def get_dashboard_config(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific dashboard."""
        dashboard = self.dashboards.get(dashboard_id)
        return dashboard.to_dict() if dashboard else None
    
    def update_dashboard_config(self, dashboard_id: str, config: Dict[str, Any]) -> bool:
        """Update dashboard configuration."""
        try:
            # Validate configuration
            self._validate_dashboard_config(config)
            
            # Update dashboard
            dashboard_type = DashboardType(config["dashboard_type"])
            updated_dashboard = DashboardConfig(
                dashboard_id=dashboard_id,
                title=config["title"],
                description=config["description"],
                dashboard_type=dashboard_type,
                refresh_interval_seconds=config.get("refresh_interval_seconds", 30),
                auto_refresh=config.get("auto_refresh", True),
                required_permissions=config.get("required_permissions", [])
            )
            
            # Update widgets
            for widget_config in config.get("widgets", []):
                widget = self._create_widget_from_config(widget_config)
                updated_dashboard.widgets.append(widget)
            
            self.dashboards[dashboard_id] = updated_dashboard
            logger.info(f"📊 Dashboard config updated: {dashboard_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update dashboard config: {e}")
            return False
    
    def _validate_dashboard_config(self, config: Dict[str, Any]) -> None:
        """Validate dashboard configuration."""
        required_fields = ["dashboard_id", "title", "description", "dashboard_type"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate dashboard type
        try:
            DashboardType(config["dashboard_type"])
        except ValueError:
            raise ValueError(f"Invalid dashboard type: {config['dashboard_type']}")
    
    def _create_widget_from_config(self, config: Dict[str, Any]) -> DashboardWidget:
        """Create widget from configuration dictionary."""
        return DashboardWidget(
            widget_id=config["widget_id"],
            title=config["title"],
            description=config["description"],
            metric_type=MetricType(config["metric_type"]),
            data_source=config["data_source"],
            query_params=config.get("query_params", {}),
            refresh_interval_seconds=config.get("refresh_interval_seconds", 30),
            display_config=config.get("display_config", {}),
            alert_thresholds=config.get("alert_thresholds", {}),
            width=config.get("layout", {}).get("width", 6),
            height=config.get("layout", {}).get("height", 4),
            row=config.get("layout", {}).get("row"),
            column=config.get("layout", {}).get("column")
        )
    
    # Export and import configuration
    
    def export_dashboard_configs(self) -> Dict[str, Any]:
        """Export all dashboard configurations."""
        return {
            "version": "1.0",
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "dashboards": {
                dashboard_id: config.to_dict()
                for dashboard_id, config in self.dashboards.items()
            }
        }
    
    def import_dashboard_configs(self, config_data: Dict[str, Any]) -> bool:
        """Import dashboard configurations."""
        try:
            dashboards_config = config_data.get("dashboards", {})
            
            for dashboard_id, dashboard_config in dashboards_config.items():
                self.update_dashboard_config(dashboard_id, dashboard_config)
            
            logger.info(f"📊 Imported {len(dashboards_config)} dashboard configurations")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import dashboard configs: {e}")
            return False
    
    def save_configs_to_file(self, file_path: str) -> bool:
        """Save dashboard configurations to file."""
        try:
            config_data = self.export_dashboard_configs()
            with open(file_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"📊 Dashboard configs saved to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save dashboard configs: {e}")
            return False
    
    def load_configs_from_file(self, file_path: str) -> bool:
        """Load dashboard configurations from file."""
        try:
            with open(file_path, 'r') as f:
                config_data = json.load(f)
            
            return self.import_dashboard_configs(config_data)
            
        except Exception as e:
            logger.error(f"Failed to load dashboard configs: {e}")
            return False


# Global dashboard config manager
_dashboard_config_manager: Optional[DashboardConfigManager] = None


def get_dashboard_config_manager() -> DashboardConfigManager:
    """Get or create the global dashboard config manager."""
    global _dashboard_config_manager
    if _dashboard_config_manager is None:
        _dashboard_config_manager = DashboardConfigManager()
    return _dashboard_config_manager


async def initialize_monitoring_dashboards() -> None:
    """Initialize monitoring dashboards with default configurations."""
    config_manager = get_dashboard_config_manager()
    
    # Save default configurations
    config_file = "websocket_dashboard_configs.json"
    config_manager.save_configs_to_file(config_file)
    
    logger.info(f"📊 Monitoring dashboards initialized with {len(config_manager.dashboards)} dashboards")


def get_dashboard_config_for_api(dashboard_id: str) -> Optional[Dict[str, Any]]:
    """Get dashboard configuration for API endpoints.""" 
    config_manager = get_dashboard_config_manager()
    return config_manager.get_dashboard_config(dashboard_id)


async def get_dashboard_data_for_api(dashboard_id: str) -> Dict[str, Any]:
    """Get live dashboard data for API endpoints."""
    config_manager = get_dashboard_config_manager() 
    return await config_manager.get_dashboard_data(dashboard_id)
"""
Request Isolation Monitoring Dashboard Configuration

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Real-time visibility into system isolation health
- Value Impact: Enables proactive detection and resolution of isolation issues
- Revenue Impact: Critical for Enterprise SLA monitoring and customer confidence

CRITICAL OBJECTIVES:
1. Provide real-time isolation health visibility
2. Enable quick identification of violation patterns  
3. Support proactive issue resolution
4. Maintain 30-day historical data retention
5. Generate actionable alerts for operations team

DASHBOARD SECTIONS:
- Overview: Key isolation metrics and health status
- Violations: Recent violations with severity breakdown
- Performance: Factory performance and resource usage
- Trends: Historical patterns and anomaly detection
- Alerts: Active alerts requiring immediate attention
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.isolation_metrics import (
    IsolationViolationSeverity,
    get_isolation_metrics_collector
)
from netra_backend.app.monitoring.isolation_health_checks import (
    HealthCheckSeverity,
    get_isolation_health_checker
)

logger = central_logger.get_logger(__name__)

class DashboardTimeRange(Enum):
    """Time ranges for dashboard data."""
    LAST_HOUR = "1h"
    LAST_4_HOURS = "4h"  
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"

class MetricType(Enum):
    """Types of metrics displayed on dashboard."""
    ISOLATION_SCORE = "isolation_score"
    FAILURE_CONTAINMENT = "failure_containment_rate"
    CONCURRENT_USERS = "concurrent_users"
    ACTIVE_REQUESTS = "active_requests"
    INSTANCE_CREATION_TIME = "instance_creation_time_ms"
    WEBSOCKET_VIOLATIONS = "websocket_isolation_violations"
    SESSION_LEAKS = "session_leak_count"
    SINGLETON_VIOLATIONS = "singleton_violations"

@dataclass
class DashboardWidget:
    """Configuration for a dashboard widget."""
    widget_id: str
    title: str
    widget_type: str  # "metric", "chart", "table", "status", "alert"
    metric_type: Optional[MetricType] = None
    time_range: DashboardTimeRange = DashboardTimeRange.LAST_HOUR
    refresh_interval_seconds: int = 30
    alert_thresholds: Dict[str, Union[int, float]] = field(default_factory=dict)
    display_options: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DashboardSection:
    """Configuration for a dashboard section."""
    section_id: str
    title: str
    description: str
    widgets: List[DashboardWidget] = field(default_factory=list)
    collapsible: bool = False
    default_expanded: bool = True

@dataclass
class DashboardConfig:
    """Complete dashboard configuration."""
    dashboard_id: str
    title: str
    description: str
    sections: List[DashboardSection] = field(default_factory=list)
    global_refresh_interval: int = 30
    auto_refresh: bool = True
    alert_sound: bool = True
    theme: str = "dark"

class IsolationDashboardConfigManager:
    """
    Manages configuration for the isolation monitoring dashboard.
    
    CRITICAL: This dashboard must provide immediate visibility into any
    isolation violations and enable rapid response to system issues.
    """
    
    def __init__(self):
        """Initialize dashboard configuration manager."""
        self._default_config: Optional[DashboardConfig] = None
        self._custom_configs: Dict[str, DashboardConfig] = {}
        logger.info("IsolationDashboardConfigManager initialized")
        
    def get_default_config(self) -> DashboardConfig:
        """Get default dashboard configuration."""
        if self._default_config is None:
            self._default_config = self._create_default_config()
        return self._default_config
        
    def _create_default_config(self) -> DashboardConfig:
        """Create default isolation monitoring dashboard configuration."""
        
        # Overview Section
        overview_section = DashboardSection(
            section_id="overview",
            title="System Overview",
            description="Key isolation metrics and overall system health",
            widgets=[
                DashboardWidget(
                    widget_id="isolation_score",
                    title="Request Isolation Score",
                    widget_type="metric",
                    metric_type=MetricType.ISOLATION_SCORE,
                    time_range=DashboardTimeRange.LAST_HOUR,
                    alert_thresholds={"critical": 99.9, "warning": 99.95},
                    display_options={
                        "format": "percentage",
                        "target": 100.0,
                        "color_critical": "#dc3545",
                        "color_warning": "#ffc107",
                        "color_healthy": "#28a745",
                        "size": "large"
                    }
                ),
                DashboardWidget(
                    widget_id="failure_containment",
                    title="Failure Containment Rate",
                    widget_type="metric",
                    metric_type=MetricType.FAILURE_CONTAINMENT,
                    time_range=DashboardTimeRange.LAST_HOUR,
                    alert_thresholds={"critical": 99.0, "warning": 99.5},
                    display_options={
                        "format": "percentage",
                        "target": 100.0,
                        "size": "large"
                    }
                ),
                DashboardWidget(
                    widget_id="concurrent_users",
                    title="Concurrent Users",
                    widget_type="metric",
                    metric_type=MetricType.CONCURRENT_USERS,
                    time_range=DashboardTimeRange.LAST_HOUR,
                    alert_thresholds={"warning": 50, "critical": 100},
                    display_options={
                        "format": "number",
                        "size": "medium",
                        "icon": "users"
                    }
                ),
                DashboardWidget(
                    widget_id="active_requests",
                    title="Active Requests",
                    widget_type="metric",
                    metric_type=MetricType.ACTIVE_REQUESTS,
                    time_range=DashboardTimeRange.LAST_HOUR,
                    alert_thresholds={"warning": 100, "critical": 200},
                    display_options={
                        "format": "number",
                        "size": "medium",
                        "icon": "activity"
                    }
                ),
                DashboardWidget(
                    widget_id="system_health",
                    title="Overall System Health",
                    widget_type="status",
                    time_range=DashboardTimeRange.LAST_HOUR,
                    display_options={
                        "status_map": {
                            "healthy": {"color": "#28a745", "icon": "check-circle"},
                            "warning": {"color": "#ffc107", "icon": "alert-triangle"},
                            "error": {"color": "#fd7e14", "icon": "alert-circle"},
                            "critical": {"color": "#dc3545", "icon": "x-circle"}
                        }
                    }
                )
            ]
        )
        
        # Violations Section
        violations_section = DashboardSection(
            section_id="violations",
            title="Isolation Violations",
            description="Recent violations with severity breakdown and trends",
            widgets=[
                DashboardWidget(
                    widget_id="violation_summary",
                    title="Violations Last Hour",
                    widget_type="chart",
                    time_range=DashboardTimeRange.LAST_HOUR,
                    display_options={
                        "chart_type": "donut",
                        "breakdown_by": "severity",
                        "colors": {
                            "critical": "#dc3545",
                            "error": "#fd7e14", 
                            "warning": "#ffc107",
                            "info": "#17a2b8"
                        }
                    }
                ),
                DashboardWidget(
                    widget_id="violation_trend",
                    title="Violation Trend (24h)",
                    widget_type="chart",
                    time_range=DashboardTimeRange.LAST_24_HOURS,
                    display_options={
                        "chart_type": "line",
                        "group_by": "hour",
                        "stack_by": "severity",
                        "show_threshold_lines": True
                    }
                ),
                DashboardWidget(
                    widget_id="violation_types",
                    title="Violations by Type",
                    widget_type="table",
                    time_range=DashboardTimeRange.LAST_HOUR,
                    display_options={
                        "columns": ["type", "count", "last_seen", "severity"],
                        "sort_by": "count",
                        "sort_order": "desc",
                        "max_rows": 10
                    }
                )
            ]
        )
        
        # Performance Section  
        performance_section = DashboardSection(
            section_id="performance",
            title="Performance Metrics",
            description="Factory performance, resource usage, and system efficiency",
            widgets=[
                DashboardWidget(
                    widget_id="instance_creation_time",
                    title="Agent Instance Creation Time",
                    widget_type="chart",
                    metric_type=MetricType.INSTANCE_CREATION_TIME,
                    time_range=DashboardTimeRange.LAST_HOUR,
                    alert_thresholds={"warning": 100, "critical": 1000},  # ms
                    display_options={
                        "chart_type": "line",
                        "format": "milliseconds",
                        "target_line": 50,
                        "show_percentiles": [50, 95, 99]
                    }
                ),
                DashboardWidget(
                    widget_id="resource_usage",
                    title="Resource Usage",
                    widget_type="chart",
                    time_range=DashboardTimeRange.LAST_HOUR,
                    display_options={
                        "chart_type": "multi_line",
                        "metrics": ["memory_percent", "cpu_percent", "active_connections"],
                        "y_axis_max": 100
                    }
                ),
                DashboardWidget(
                    widget_id="singleton_violations",
                    title="Singleton Violations",
                    widget_type="metric",
                    metric_type=MetricType.SINGLETON_VIOLATIONS,
                    time_range=DashboardTimeRange.LAST_HOUR,
                    alert_thresholds={"critical": 1},  # Any singleton violation is critical
                    display_options={
                        "format": "number",
                        "color_scheme": "red_on_nonzero",
                        "size": "medium",
                        "icon": "alert-triangle"
                    }
                ),
                DashboardWidget(
                    widget_id="websocket_violations",
                    title="WebSocket Isolation Violations",
                    widget_type="metric", 
                    metric_type=MetricType.WEBSOCKET_VIOLATIONS,
                    time_range=DashboardTimeRange.LAST_HOUR,
                    alert_thresholds={"critical": 1},  # Any WebSocket violation is critical
                    display_options={
                        "format": "number",
                        "color_scheme": "red_on_nonzero",
                        "size": "medium",
                        "icon": "wifi"
                    }
                )
            ]
        )
        
        # Alerts Section
        alerts_section = DashboardSection(
            section_id="alerts",
            title="Active Alerts",
            description="Critical alerts requiring immediate attention",
            widgets=[
                DashboardWidget(
                    widget_id="critical_alerts",
                    title="Critical Alerts",
                    widget_type="alert",
                    time_range=DashboardTimeRange.LAST_HOUR,
                    display_options={
                        "severity_filter": ["critical"],
                        "auto_refresh": 10,  # Refresh every 10 seconds
                        "sound_alerts": True,
                        "max_alerts": 20
                    }
                ),
                DashboardWidget(
                    widget_id="remediation_actions",
                    title="Recommended Actions",
                    widget_type="table",
                    time_range=DashboardTimeRange.LAST_HOUR,
                    display_options={
                        "columns": ["alert", "action", "priority", "timestamp"],
                        "show_action_buttons": True,
                        "sort_by": "priority"
                    }
                )
            ]
        )
        
        # Trends Section (Historical Analysis)
        trends_section = DashboardSection(
            section_id="trends",
            title="Historical Trends",
            description="Long-term patterns and trend analysis",
            widgets=[
                DashboardWidget(
                    widget_id="isolation_score_trend",
                    title="Isolation Score Trend (7 days)",
                    widget_type="chart",
                    metric_type=MetricType.ISOLATION_SCORE,
                    time_range=DashboardTimeRange.LAST_7_DAYS,
                    display_options={
                        "chart_type": "line",
                        "group_by": "hour",
                        "show_target_line": True,
                        "target_value": 100.0,
                        "anomaly_detection": True
                    }
                ),
                DashboardWidget(
                    widget_id="user_load_pattern",
                    title="User Load Pattern (7 days)", 
                    widget_type="chart",
                    metric_type=MetricType.CONCURRENT_USERS,
                    time_range=DashboardTimeRange.LAST_7_DAYS,
                    display_options={
                        "chart_type": "heatmap",
                        "group_by": "hour_of_day",
                        "breakdown_by": "day_of_week"
                    }
                )
            ],
            collapsible=True,
            default_expanded=False
        )
        
        return DashboardConfig(
            dashboard_id="isolation_monitoring",
            title="Request Isolation Monitoring Dashboard",
            description="Real-time monitoring of request isolation and system health",
            sections=[
                overview_section,
                violations_section, 
                performance_section,
                alerts_section,
                trends_section
            ],
            global_refresh_interval=30,
            auto_refresh=True,
            alert_sound=True,
            theme="dark"
        )
        
    def get_config_for_user(self, user_id: str, role: str = "operator") -> DashboardConfig:
        """Get dashboard configuration customized for specific user role."""
        base_config = self.get_default_config()
        
        if role == "admin":
            # Admin gets full configuration
            return base_config
        elif role == "developer":
            # Developer gets technical details
            dev_config = self._customize_for_developer(base_config)
            return dev_config
        elif role == "operator":
            # Operator gets operational view
            ops_config = self._customize_for_operator(base_config)
            return ops_config
        else:
            # Default to operator view
            return self._customize_for_operator(base_config)
            
    def _customize_for_developer(self, base_config: DashboardConfig) -> DashboardConfig:
        """Customize dashboard for developer role."""
        # Add technical widgets for developers
        for section in base_config.sections:
            if section.section_id == "performance":
                # Add garbage collection widget
                gc_widget = DashboardWidget(
                    widget_id="gc_performance",
                    title="Garbage Collection",
                    widget_type="chart",
                    time_range=DashboardTimeRange.LAST_HOUR,
                    display_options={
                        "chart_type": "line",
                        "metrics": ["gc_gen0", "gc_gen1", "gc_gen2"],
                        "format": "number"
                    }
                )
                section.widgets.append(gc_widget)
                
        return base_config
        
    def _customize_for_operator(self, base_config: DashboardConfig) -> DashboardConfig:
        """Customize dashboard for operator role."""
        # Simplify view for operators - focus on actionable alerts
        simplified_config = DashboardConfig(
            dashboard_id="isolation_monitoring_ops",
            title="Isolation Monitoring - Operations View",
            description="Simplified view focused on alerts and system health",
            sections=[],
            global_refresh_interval=15,  # More frequent updates for ops
            auto_refresh=True,
            alert_sound=True,
            theme="light"
        )
        
        # Only include overview and alerts sections
        for section in base_config.sections:
            if section.section_id in ["overview", "alerts"]:
                simplified_config.sections.append(section)
                
        return simplified_config
        
    def create_custom_config(self, config_id: str, base_config: DashboardConfig) -> DashboardConfig:
        """Create and store custom dashboard configuration."""
        self._custom_configs[config_id] = base_config
        return base_config
        
    def get_custom_config(self, config_id: str) -> Optional[DashboardConfig]:
        """Get stored custom dashboard configuration."""
        return self._custom_configs.get(config_id)
        
    def export_config(self, config: DashboardConfig) -> Dict[str, Any]:
        """Export dashboard configuration to JSON-serializable format."""
        return {
            "dashboard_id": config.dashboard_id,
            "title": config.title,
            "description": config.description,
            "global_refresh_interval": config.global_refresh_interval,
            "auto_refresh": config.auto_refresh,
            "alert_sound": config.alert_sound,
            "theme": config.theme,
            "sections": [
                {
                    "section_id": section.section_id,
                    "title": section.title,
                    "description": section.description,
                    "collapsible": section.collapsible,
                    "default_expanded": section.default_expanded,
                    "widgets": [
                        {
                            "widget_id": widget.widget_id,
                            "title": widget.title,
                            "widget_type": widget.widget_type,
                            "metric_type": widget.metric_type.value if widget.metric_type else None,
                            "time_range": widget.time_range.value,
                            "refresh_interval_seconds": widget.refresh_interval_seconds,
                            "alert_thresholds": widget.alert_thresholds,
                            "display_options": widget.display_options
                        }
                        for widget in section.widgets
                    ]
                }
                for section in config.sections
            ]
        }
        
    def get_widget_data_source(self, widget: DashboardWidget) -> str:
        """Get API endpoint for widget data."""
        base_path = "/monitoring/isolation"
        
        if widget.widget_type == "alert":
            return f"{base_path}/alerts"
        elif widget.metric_type:
            return f"{base_path}/metrics"
        elif widget.widget_id == "violation_summary":
            return f"{base_path}/violations?hours={self._parse_hours(widget.time_range)}"
        elif widget.widget_id == "system_health":
            return f"{base_path}/health"
        else:
            return f"{base_path}/dashboard"
            
    def _parse_hours(self, time_range: DashboardTimeRange) -> int:
        """Convert time range to hours."""
        time_map = {
            DashboardTimeRange.LAST_HOUR: 1,
            DashboardTimeRange.LAST_4_HOURS: 4,
            DashboardTimeRange.LAST_24_HOURS: 24,
            DashboardTimeRange.LAST_7_DAYS: 168,  # 7 * 24
            DashboardTimeRange.LAST_30_DAYS: 720   # 30 * 24
        }
        return time_map.get(time_range, 1)

# Singleton instance
_dashboard_config_manager: Optional[IsolationDashboardConfigManager] = None

def get_dashboard_config_manager() -> IsolationDashboardConfigManager:
    """Get or create dashboard configuration manager."""
    global _dashboard_config_manager
    
    if _dashboard_config_manager is None:
        _dashboard_config_manager = IsolationDashboardConfigManager()
        
    return _dashboard_config_manager

__all__ = [
    'DashboardTimeRange',
    'MetricType', 
    'DashboardWidget',
    'DashboardSection',
    'DashboardConfig',
    'IsolationDashboardConfigManager',
    'get_dashboard_config_manager'
]
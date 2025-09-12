"""
WebSocket Dashboard Configuration Manager

This module provides comprehensive dashboard configuration management for WebSocket
monitoring, including widget configuration, data source mapping, and dashboard
customization for different user roles.

BUSINESS VALUE:
- Executive visibility through customizable dashboards
- Role-based dashboard views (admin, operator, developer)
- Real-time configuration updates for monitoring displays
- Business metrics integration for WebSocket health
- Compliance and audit dashboard support

DASHBOARD TYPES:
1. Executive Dashboard: High-level KPIs and business metrics
2. Operations Dashboard: Real-time health and incident management
3. Developer Dashboard: Technical metrics and debugging information
4. Compliance Dashboard: SLA tracking and audit logs

CONFIGURATION FEATURES:
- Widget-based dashboard composition
- Real-time metric data source binding
- User role-based access controls
- Dashboard state persistence
- Configuration import/export
- Dynamic dashboard updates
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DashboardRole(Enum):
    """User roles for dashboard access."""
    ADMIN = "admin"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    EXECUTIVE = "executive"


class WidgetType(Enum):
    """Types of dashboard widgets."""
    METRIC_CHART = "metric_chart"
    STATUS_INDICATOR = "status_indicator"
    EVENT_LOG = "event_log"
    CONNECTION_MAP = "connection_map"
    ALERT_PANEL = "alert_panel"
    PERFORMANCE_GAUGE = "performance_gauge"
    USER_TABLE = "user_table"
    SYSTEM_HEALTH = "system_health"


@dataclass
class DashboardWidget:
    """Configuration for individual dashboard widget."""
    
    widget_id: str
    widget_type: WidgetType
    title: str
    description: str = ""
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "width": 4, "height": 3})
    refresh_interval: int = 30  # seconds
    data_source: str = ""
    configuration: Dict[str, Any] = field(default_factory=dict)
    visible: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert widget to dictionary representation."""
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type.value,
            "title": self.title,
            "description": self.description,
            "position": self.position,
            "refresh_interval": self.refresh_interval,
            "data_source": self.data_source,
            "configuration": self.configuration,
            "visible": self.visible
        }


@dataclass
class DashboardSection:
    """Dashboard section containing related widgets."""
    
    section_id: str
    title: str
    widgets: List[DashboardWidget] = field(default_factory=list)
    collapsed: bool = False
    role_access: List[DashboardRole] = field(default_factory=lambda: [DashboardRole.ADMIN])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert section to dictionary representation."""
        return {
            "section_id": self.section_id,
            "title": self.title,
            "widgets": [w.to_dict() for w in self.widgets],
            "collapsed": self.collapsed,
            "role_access": [r.value for r in self.role_access]
        }


@dataclass
class WebSocketDashboardConfig:
    """Complete dashboard configuration."""
    
    dashboard_id: str
    name: str
    description: str = ""
    sections: List[DashboardSection] = field(default_factory=list)
    role_access: List[DashboardRole] = field(default_factory=lambda: [DashboardRole.ADMIN])
    auto_refresh: bool = True
    global_refresh_interval: int = 30
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert dashboard config to dictionary."""
        return {
            "dashboard_id": self.dashboard_id,
            "name": self.name,
            "description": self.description,
            "sections": [s.to_dict() for s in self.sections],
            "role_access": [r.value for r in self.role_access],
            "auto_refresh": self.auto_refresh,
            "global_refresh_interval": self.global_refresh_interval,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class WebSocketDashboardConfigManager:
    """
    Manages WebSocket monitoring dashboard configurations.
    
    Provides comprehensive dashboard management including:
    - Role-based dashboard configurations
    - Widget management and data source binding
    - Configuration persistence and import/export
    - Real-time dashboard updates
    """
    
    def __init__(self):
        """Initialize the WebSocket dashboard config manager."""
        self.dashboards: Dict[str, WebSocketDashboardConfig] = {}
        self.default_dashboards: Dict[DashboardRole, WebSocketDashboardConfig] = {}
        self._initialize_default_dashboards()
        logger.info("[U+1F39B][U+FE0F] WebSocket Dashboard Config Manager initialized")
    
    def _initialize_default_dashboards(self) -> None:
        """Initialize default dashboard configurations for different roles."""
        
        # Executive Dashboard
        executive_dashboard = self._create_executive_dashboard()
        self.default_dashboards[DashboardRole.EXECUTIVE] = executive_dashboard
        self.dashboards[executive_dashboard.dashboard_id] = executive_dashboard
        
        # Operations Dashboard
        operations_dashboard = self._create_operations_dashboard()
        self.default_dashboards[DashboardRole.OPERATOR] = operations_dashboard
        self.dashboards[operations_dashboard.dashboard_id] = operations_dashboard
        
        # Developer Dashboard
        developer_dashboard = self._create_developer_dashboard()
        self.default_dashboards[DashboardRole.DEVELOPER] = developer_dashboard
        self.dashboards[developer_dashboard.dashboard_id] = developer_dashboard
        
        # Admin Dashboard (comprehensive)
        admin_dashboard = self._create_admin_dashboard()
        self.default_dashboards[DashboardRole.ADMIN] = admin_dashboard
        self.dashboards[admin_dashboard.dashboard_id] = admin_dashboard
    
    def _create_executive_dashboard(self) -> WebSocketDashboardConfig:
        """Create executive dashboard with business-focused metrics."""
        dashboard = WebSocketDashboardConfig(
            dashboard_id="executive_websocket",
            name="WebSocket Executive Dashboard",
            description="High-level business metrics for WebSocket system health",
            role_access=[DashboardRole.EXECUTIVE, DashboardRole.ADMIN]
        )
        
        # Business Metrics Section
        business_section = DashboardSection(
            section_id="business_metrics",
            title="Business Impact Metrics",
            role_access=[DashboardRole.EXECUTIVE, DashboardRole.ADMIN]
        )
        
        business_section.widgets = [
            DashboardWidget(
                widget_id="user_satisfaction",
                widget_type=WidgetType.PERFORMANCE_GAUGE,
                title="User Experience Score",
                description="Overall user satisfaction with real-time features",
                position={"x": 0, "y": 0, "width": 3, "height": 3},
                data_source="/monitoring/websocket/metrics/satisfaction"
            ),
            DashboardWidget(
                widget_id="system_availability",
                widget_type=WidgetType.STATUS_INDICATOR,
                title="System Availability",
                description="WebSocket system uptime and availability",
                position={"x": 3, "y": 0, "width": 3, "height": 3},
                data_source="/monitoring/websocket/health/availability"
            ),
            DashboardWidget(
                widget_id="business_continuity",
                widget_type=WidgetType.METRIC_CHART,
                title="Business Continuity",
                description="Revenue impact and business continuity metrics",
                position={"x": 6, "y": 0, "width": 6, "height": 3},
                data_source="/monitoring/websocket/metrics/business-impact"
            )
        ]
        
        dashboard.sections.append(business_section)
        return dashboard
    
    def _create_operations_dashboard(self) -> WebSocketDashboardConfig:
        """Create operations dashboard for system monitoring."""
        dashboard = WebSocketDashboardConfig(
            dashboard_id="operations_websocket",
            name="WebSocket Operations Dashboard",
            description="Real-time operational monitoring and incident management",
            role_access=[DashboardRole.OPERATOR, DashboardRole.ADMIN]
        )
        
        # System Health Section
        health_section = DashboardSection(
            section_id="system_health",
            title="System Health Overview",
            role_access=[DashboardRole.OPERATOR, DashboardRole.ADMIN]
        )
        
        health_section.widgets = [
            DashboardWidget(
                widget_id="connection_status",
                widget_type=WidgetType.CONNECTION_MAP,
                title="Connection Status",
                description="Real-time WebSocket connection health",
                position={"x": 0, "y": 0, "width": 6, "height": 4},
                data_source="/monitoring/websocket/metrics/connections",
                refresh_interval=10
            ),
            DashboardWidget(
                widget_id="active_alerts",
                widget_type=WidgetType.ALERT_PANEL,
                title="Active Alerts",
                description="Current system alerts and their status",
                position={"x": 6, "y": 0, "width": 6, "height": 4},
                data_source="/monitoring/websocket/alerts/active",
                refresh_interval=5
            ),
            DashboardWidget(
                widget_id="event_throughput",
                widget_type=WidgetType.METRIC_CHART,
                title="Event Throughput",
                description="Real-time event processing rates",
                position={"x": 0, "y": 4, "width": 12, "height": 3},
                data_source="/monitoring/websocket/metrics/throughput",
                refresh_interval=15
            )
        ]
        
        dashboard.sections.append(health_section)
        return dashboard
    
    def _create_developer_dashboard(self) -> WebSocketDashboardConfig:
        """Create developer dashboard with technical metrics."""
        dashboard = WebSocketDashboardConfig(
            dashboard_id="developer_websocket",
            name="WebSocket Developer Dashboard", 
            description="Technical metrics and debugging information",
            role_access=[DashboardRole.DEVELOPER, DashboardRole.ADMIN]
        )
        
        # Technical Metrics Section
        technical_section = DashboardSection(
            section_id="technical_metrics",
            title="Technical Performance Metrics",
            role_access=[DashboardRole.DEVELOPER, DashboardRole.ADMIN]
        )
        
        technical_section.widgets = [
            DashboardWidget(
                widget_id="latency_distribution",
                widget_type=WidgetType.METRIC_CHART,
                title="Latency Distribution",
                description="Message delivery latency percentiles",
                position={"x": 0, "y": 0, "width": 6, "height": 4},
                data_source="/monitoring/websocket/metrics/latency"
            ),
            DashboardWidget(
                widget_id="error_rates",
                widget_type=WidgetType.METRIC_CHART,
                title="Error Rates",
                description="WebSocket error rates by type",
                position={"x": 6, "y": 0, "width": 6, "height": 4},
                data_source="/monitoring/websocket/metrics/errors"
            ),
            DashboardWidget(
                widget_id="debug_logs",
                widget_type=WidgetType.EVENT_LOG,
                title="Debug Event Log",
                description="Recent WebSocket events and debug information",
                position={"x": 0, "y": 4, "width": 12, "height": 4},
                data_source="/monitoring/websocket/logs/debug",
                refresh_interval=10
            )
        ]
        
        dashboard.sections.append(technical_section)
        return dashboard
    
    def _create_admin_dashboard(self) -> WebSocketDashboardConfig:
        """Create comprehensive admin dashboard."""
        dashboard = WebSocketDashboardConfig(
            dashboard_id="admin_websocket",
            name="WebSocket Administrator Dashboard",
            description="Comprehensive system administration and monitoring",
            role_access=[DashboardRole.ADMIN]
        )
        
        # User Management Section
        user_section = DashboardSection(
            section_id="user_management",
            title="User Management",
            role_access=[DashboardRole.ADMIN]
        )
        
        user_section.widgets = [
            DashboardWidget(
                widget_id="user_connections",
                widget_type=WidgetType.USER_TABLE,
                title="User Connections",
                description="Active user connections and their status",
                position={"x": 0, "y": 0, "width": 12, "height": 4},
                data_source="/monitoring/websocket/metrics/users"
            )
        ]
        
        # System Administration Section
        admin_section = DashboardSection(
            section_id="system_administration",
            title="System Administration",
            role_access=[DashboardRole.ADMIN]
        )
        
        admin_section.widgets = [
            DashboardWidget(
                widget_id="system_health_detailed",
                widget_type=WidgetType.SYSTEM_HEALTH,
                title="Detailed System Health",
                description="Comprehensive system health metrics",
                position={"x": 0, "y": 0, "width": 8, "height": 4},
                data_source="/monitoring/websocket/health/detailed"
            ),
            DashboardWidget(
                widget_id="configuration_status",
                widget_type=WidgetType.STATUS_INDICATOR,
                title="Configuration Status",
                description="System configuration health and status",
                position={"x": 8, "y": 0, "width": 4, "height": 4},
                data_source="/monitoring/websocket/config/status"
            )
        ]
        
        dashboard.sections.extend([user_section, admin_section])
        return dashboard
    
    def get_config_for_user(self, user_id: str, role: str) -> WebSocketDashboardConfig:
        """
        Get dashboard configuration for specific user and role.
        
        Args:
            user_id: User identifier
            role: User role (admin, operator, developer, executive)
            
        Returns:
            Dashboard configuration for the user role
        """
        try:
            user_role = DashboardRole(role.lower())
            if user_role in self.default_dashboards:
                dashboard = self.default_dashboards[user_role]
                logger.debug(f"Retrieved dashboard for user {user_id} with role {role}")
                return dashboard
        except ValueError:
            logger.warning(f"Invalid role specified: {role}, defaulting to operator")
        
        # Default to operator dashboard
        return self.default_dashboards.get(DashboardRole.OPERATOR, 
                                         list(self.dashboards.values())[0])
    
    def get_widget_data_source(self, widget: DashboardWidget) -> str:
        """
        Get the data source URL for a widget.
        
        Args:
            widget: Dashboard widget
            
        Returns:
            Data source URL
        """
        return widget.data_source or f"/monitoring/websocket/metrics/{widget.widget_id}"
    
    def export_config(self, dashboard: WebSocketDashboardConfig) -> Dict[str, Any]:
        """
        Export dashboard configuration to dictionary format.
        
        Args:
            dashboard: Dashboard configuration to export
            
        Returns:
            Dictionary representation of dashboard
        """
        return dashboard.to_dict()
    
    def export_dashboard_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Export all dashboard configurations.
        
        Returns:
            Dictionary of all dashboard configurations
        """
        return {
            dashboard_id: dashboard.to_dict()
            for dashboard_id, dashboard in self.dashboards.items()
        }
    
    def import_dashboard_configs(self, configs: Dict[str, Dict[str, Any]]) -> None:
        """
        Import dashboard configurations from dictionary.
        
        Args:
            configs: Dictionary of dashboard configurations to import
        """
        try:
            for dashboard_id, config in configs.items():
                # Convert back to dashboard config object
                dashboard = self._dict_to_dashboard_config(config)
                self.dashboards[dashboard_id] = dashboard
                
            logger.info(f" CHART:  Imported {len(configs)} dashboard configurations")
            
        except Exception as e:
            logger.error(f"Failed to import dashboard configurations: {e}")
            raise
    
    def _dict_to_dashboard_config(self, config: Dict[str, Any]) -> WebSocketDashboardConfig:
        """Convert dictionary back to dashboard config object."""
        # This is a simplified conversion - in production would need full serialization
        return WebSocketDashboardConfig(
            dashboard_id=config.get("dashboard_id", "unknown"),
            name=config.get("name", "Imported Dashboard"),
            description=config.get("description", ""),
            role_access=[DashboardRole(role) for role in config.get("role_access", ["admin"])],
            auto_refresh=config.get("auto_refresh", True),
            global_refresh_interval=config.get("global_refresh_interval", 30)
        )


# Global instance for SSOT compliance
_dashboard_config_manager: Optional[WebSocketDashboardConfigManager] = None


def get_dashboard_config_manager() -> WebSocketDashboardConfigManager:
    """
    Get the singleton WebSocket dashboard config manager instance.
    
    Returns:
        WebSocketDashboardConfigManager instance
    """
    global _dashboard_config_manager
    if _dashboard_config_manager is None:
        _dashboard_config_manager = WebSocketDashboardConfigManager()
        logger.info(" PASS:  WebSocket Dashboard Config Manager singleton created")
    return _dashboard_config_manager


async def initialize_monitoring_dashboards() -> None:
    """
    Initialize WebSocket monitoring dashboards.
    
    This function sets up the dashboard infrastructure and prepares
    all dashboard configurations for use by the monitoring system.
    """
    try:
        manager = get_dashboard_config_manager()
        
        # Ensure all default dashboards are initialized
        if not manager.dashboards:
            manager._initialize_default_dashboards()
        
        # Log dashboard initialization
        dashboard_count = len(manager.dashboards)
        role_count = len(manager.default_dashboards)
        
        logger.info(f"[U+1F39B][U+FE0F] Initialized {dashboard_count} WebSocket monitoring dashboards")
        logger.info(f" CHART:  Created default dashboards for {role_count} user roles")
        
        # Log available dashboards
        for dashboard_id, dashboard in manager.dashboards.items():
            widget_count = sum(len(section.widgets) for section in dashboard.sections)
            logger.info(f"  [U+1F4C8] {dashboard.name}: {widget_count} widgets across {len(dashboard.sections)} sections")
        
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket monitoring dashboards: {e}")
        raise


async def get_dashboard_data_for_api(dashboard_id: str) -> Optional[Dict[str, Any]]:
    """
    Get dashboard data formatted for API consumption.
    
    Args:
        dashboard_id: Dashboard identifier
        
    Returns:
        Dashboard data dictionary for API response, or None if not found
    """
    try:
        manager = get_dashboard_config_manager()
        
        if dashboard_id not in manager.dashboards:
            logger.warning(f"Dashboard not found: {dashboard_id}")
            return None
        
        dashboard = manager.dashboards[dashboard_id]
        
        # Build API response format
        dashboard_data = {
            "config": dashboard.to_dict(),
            "widgets": {},
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "metadata": {
                "dashboard_id": dashboard_id,
                "total_widgets": sum(len(section.widgets) for section in dashboard.sections),
                "total_sections": len(dashboard.sections),
                "auto_refresh": dashboard.auto_refresh,
                "refresh_interval": dashboard.global_refresh_interval
            }
        }
        
        # Add widget data sources and metadata
        for section in dashboard.sections:
            for widget in section.widgets:
                if widget.visible:
                    dashboard_data["widgets"][widget.widget_id] = {
                        "data_source": manager.get_widget_data_source(widget),
                        "refresh_interval": widget.refresh_interval,
                        "configuration": widget.configuration,
                        "type": widget.widget_type.value,
                        "title": widget.title,
                        "position": widget.position
                    }
        
        logger.debug(f"Retrieved dashboard data for: {dashboard_id}")
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Failed to get dashboard data for {dashboard_id}: {e}")
        raise


# Module initialization
logger.info("[U+1F39B][U+FE0F] WebSocket Dashboard Configuration module loaded")
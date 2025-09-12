"""
WebSocket Monitoring System Integration

This module provides the main integration point for the comprehensive WebSocket
notification monitoring system, bringing together all monitoring components.

INTEGRATION OBJECTIVES:
1. Centralized initialization and startup of all monitoring components
2. Coordinated shutdown and cleanup of monitoring systems
3. Health check endpoints for load balancers and monitoring systems
4. API endpoints for dashboard data and alert management
5. Configuration management and system administration

MONITORING SYSTEM COMPONENTS:
- WebSocketNotificationMonitor: Core monitoring and metrics collection
- WebSocketHealthChecker: Health checks and automated diagnostics
- WebSocketAlertSystem: Automated alerting and escalation
- WebSocketDashboardConfigManager: Dashboard configuration and data
- WebSocketEnhancedLogger: Enhanced logging with correlation IDs

BUSINESS VALUE:
- Zero silent failures through comprehensive monitoring
- Proactive issue detection and automated remediation
- Executive visibility into system health and user experience
- Compliance and audit support through structured logging
- Operational excellence through automated alerting
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.websocket_notification_monitor import (
    get_websocket_notification_monitor, 
    start_websocket_monitoring,
    stop_websocket_monitoring
)
from netra_backend.app.monitoring.websocket_health_checks import (
    get_websocket_health_checker,
    start_websocket_health_monitoring,
    stop_websocket_health_monitoring,
    perform_emergency_health_check
)
from netra_backend.app.monitoring.websocket_alert_system import (
    get_websocket_alert_system,
    start_websocket_alerting,
    stop_websocket_alerting,
    trigger_emergency_alert,
    AlertSeverity
)
from netra_backend.app.monitoring.websocket_dashboard_config import (
    get_dashboard_config_manager,
    initialize_monitoring_dashboards,
    get_dashboard_data_for_api
)
from netra_backend.app.monitoring.websocket_logging_enhanced import (
    log_system_startup,
    log_system_shutdown,
    get_websocket_enhanced_logger
)

logger = central_logger.get_logger(__name__)

# API Models

class HealthCheckResponse(BaseModel):
    """Health check API response model."""
    status: str = Field(..., description="Health status: healthy, degraded, unhealthy, critical")
    timestamp: str = Field(..., description="ISO timestamp of health check")
    issues: List[str] = Field(default=[], description="List of detected issues")
    system_metrics: Dict[str, Any] = Field(default={}, description="System metrics")
    monitoring_active: bool = Field(..., description="Whether monitoring is active")


class UserMetricsResponse(BaseModel):
    """User metrics API response model."""
    user_metrics: Dict[str, Any] = Field(..., description="Per-user notification metrics")
    timestamp: str = Field(..., description="ISO timestamp")


class AlertsResponse(BaseModel):
    """Alerts API response model."""
    active_alerts: List[Dict[str, Any]] = Field(..., description="Active alerts")
    alert_summary: Dict[str, Any] = Field(..., description="Alert system summary")
    timestamp: str = Field(..., description="ISO timestamp")


class DashboardDataResponse(BaseModel):
    """Dashboard data API response model."""
    config: Dict[str, Any] = Field(..., description="Dashboard configuration")
    widgets: Dict[str, Any] = Field(..., description="Widget data")
    last_updated: str = Field(..., description="Last update timestamp")


class EmergencyAlertRequest(BaseModel):
    """Emergency alert request model."""
    title: str = Field(..., min_length=1, max_length=200, description="Alert title")
    message: str = Field(..., min_length=1, max_length=1000, description="Alert message")
    severity: str = Field(default="critical", description="Alert severity level")


# WebSocket Monitoring Integration Manager

class WebSocketMonitoringIntegration:
    """
    Main integration manager for WebSocket monitoring system.
    
    Coordinates all monitoring components and provides unified API access.
    """
    
    def __init__(self):
        """Initialize monitoring integration."""
        self.monitor = get_websocket_notification_monitor()
        self.health_checker = get_websocket_health_checker()
        self.alert_system = get_websocket_alert_system()
        self.dashboard_manager = get_dashboard_config_manager()
        self.enhanced_logger = get_websocket_enhanced_logger()
        
        self.started = False
        self.startup_time: Optional[datetime] = None
        
        logger.info(" CYCLE:  WebSocket Monitoring Integration initialized")
    
    async def start_all_monitoring(self) -> None:
        """Start all monitoring components."""
        if self.started:
            logger.warning("Monitoring already started")
            return
        
        try:
            # Log startup
            await log_system_startup()
            
            # Start components in order
            await start_websocket_monitoring()
            await start_websocket_health_monitoring() 
            await start_websocket_alerting()
            await initialize_monitoring_dashboards()
            
            self.started = True
            self.startup_time = datetime.now(timezone.utc)
            
            logger.info(" PASS:  All WebSocket monitoring components started")
            
            # Log successful startup
            from netra_backend.app.monitoring.websocket_logging_enhanced import LogLevel
            self.enhanced_logger.log_structured(
                LogLevel.INFO,
                "WebSocket monitoring system fully operational",
                metadata={
                    "startup_complete": True,
                    "components_started": [
                        "notification_monitor",
                        "health_checker",
                        "alert_system", 
                        "dashboard_manager"
                    ]
                }
            )
            
        except Exception as e:
            logger.error(f" ALERT:  Failed to start monitoring system: {e}")
            await self.stop_all_monitoring()  # Cleanup on failure
            raise
    
    async def stop_all_monitoring(self) -> None:
        """Stop all monitoring components."""
        if not self.started:
            return
        
        try:
            # Stop components in reverse order
            await stop_websocket_alerting()
            await stop_websocket_health_monitoring()
            await stop_websocket_monitoring()
            
            self.started = False
            
            # Log shutdown
            await log_system_shutdown()
            
            logger.info(" PASS:  All WebSocket monitoring components stopped")
            
        except Exception as e:
            logger.error(f" ALERT:  Error stopping monitoring system: {e}")
    
    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive monitoring system status."""
        if not self.started:
            return {
                "system_status": "stopped",
                "message": "Monitoring system is not running"
            }
        
        try:
            # Gather status from all components
            monitor_status = self.monitor.get_system_health_status()
            health_summary = self.health_checker.get_health_summary()
            alert_summary = self.alert_system.get_alert_summary()
            performance_summary = self.enhanced_logger.get_performance_summary()
            
            return {
                "system_status": "operational",
                "startup_time": self.startup_time.isoformat() if self.startup_time else None,
                "uptime_minutes": (
                    (datetime.now(timezone.utc) - self.startup_time).total_seconds() / 60
                    if self.startup_time else 0
                ),
                "monitor_status": monitor_status,
                "health_summary": health_summary,
                "alert_summary": alert_summary,
                "performance_summary": performance_summary,
                "components": {
                    "notification_monitor": monitor_status.get("monitoring_active", False),
                    "health_checker": health_summary.get("monitoring_active", False),
                    "alert_system": alert_summary.get("monitoring_active", False),
                    "enhanced_logging": True
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting comprehensive status: {e}")
            return {
                "system_status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _get_health_trends(self, health_checker) -> Dict[str, Any]:
        """Get health trends for multiple check types."""
        from netra_backend.app.monitoring.websocket_health_checks import HealthCheckType
        
        trends = {}
        check_types = [
            HealthCheckType.SYSTEM_OVERALL,
            HealthCheckType.NOTIFICATION_DELIVERY,
            HealthCheckType.SILENT_FAILURE_DETECTION
        ]
        
        for check_type in check_types:
            try:
                trends[check_type.value] = health_checker.get_health_trends(check_type, 6)
            except Exception as e:
                logger.warning(f"Failed to get trends for {check_type.value}: {e}")
                trends[check_type.value] = {"error": str(e)}
        
        return trends
    
    @asynccontextmanager
    async def emergency_mode(self, reason: str):
        """Enter emergency mode for critical system recovery."""
        logger.critical(f" ALERT:  ENTERING EMERGENCY MODE: {reason}")
        
        try:
            # Trigger emergency alert
            await trigger_emergency_alert(
                "System Emergency Mode Activated",
                f"WebSocket monitoring system entered emergency mode: {reason}",
                AlertSeverity.CRITICAL
            )
            
            # Perform emergency health assessment
            emergency_assessment = await perform_emergency_health_check()
            
            yield emergency_assessment
            
        finally:
            logger.critical(" ALERT:  EXITING EMERGENCY MODE")
            
            # Log emergency mode completion
            from netra_backend.app.monitoring.websocket_logging_enhanced import LogLevel
            self.enhanced_logger.log_structured(
                LogLevel.INFO,
                f"Emergency mode completed: {reason}",
                metadata={
                    "emergency_mode": True,
                    "emergency_reason": reason,
                    "emergency_completed": True
                }
            )


# FastAPI Router for Monitoring Endpoints

monitoring_router = APIRouter(prefix="/monitoring/websocket", tags=["websocket-monitoring"])


@monitoring_router.get("/health", response_model=HealthCheckResponse)
async def get_health_status():
    """Get WebSocket monitoring system health status."""
    try:
        integration = get_websocket_monitoring_integration()
        status = await integration.get_comprehensive_status()
        
        health_summary = status.get("health_summary", {})
        
        return HealthCheckResponse(
            status=health_summary.get("overall_status", "unknown"),
            timestamp=status.get("timestamp", datetime.now(timezone.utc).isoformat()),
            issues=health_summary.get("critical_issues", []),
            system_metrics=status.get("monitor_status", {}).get("system_metrics", {}),
            monitoring_active=status.get("system_status") == "operational"
        )
        
    except Exception as e:
        logger.error(f"Health check endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")


@monitoring_router.get("/metrics/users", response_model=UserMetricsResponse)
async def get_user_metrics(user_id: Optional[str] = Query(None, description="Specific user ID")):
    """Get user-specific notification metrics."""
    try:
        monitor = get_websocket_notification_monitor()
        user_metrics = monitor.get_user_metrics(user_id)
        
        return UserMetricsResponse(
            user_metrics=user_metrics,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"User metrics endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user metrics: {e}")


@monitoring_router.get("/alerts", response_model=AlertsResponse)
async def get_alerts_status():
    """Get current alerts status."""
    try:
        alert_system = get_websocket_alert_system()
        
        active_alerts = alert_system.get_active_alerts()
        alert_summary = alert_system.get_alert_summary()
        
        return AlertsResponse(
            active_alerts=active_alerts,
            alert_summary=alert_summary,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Alerts endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {e}")


@monitoring_router.get("/dashboard/{dashboard_id}", response_model=DashboardDataResponse)
async def get_dashboard_data(dashboard_id: str):
    """Get dashboard data for monitoring UI."""
    try:
        dashboard_data = await get_dashboard_data_for_api(dashboard_id)
        
        if not dashboard_data:
            raise HTTPException(status_code=404, detail=f"Dashboard not found: {dashboard_id}")
        
        return DashboardDataResponse(**dashboard_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dashboard data endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {e}")


@monitoring_router.post("/emergency/alert")
async def trigger_emergency_alert_endpoint(request: EmergencyAlertRequest):
    """Trigger emergency alert for critical situations."""
    try:
        severity = AlertSeverity(request.severity)
        await trigger_emergency_alert(request.title, request.message, severity)
        
        return {
            "success": True,
            "message": "Emergency alert triggered",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid severity level: {request.severity}")
    except Exception as e:
        logger.error(f"Emergency alert endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger emergency alert: {e}")


@monitoring_router.post("/emergency/health-check")
async def emergency_health_check():
    """Perform emergency health check for critical diagnostics."""
    try:
        assessment = await perform_emergency_health_check()
        return assessment
        
    except Exception as e:
        logger.error(f"Emergency health check endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency health check failed: {e}")


@monitoring_router.get("/system/status")
async def get_monitoring_system_status():
    """Get monitoring system operational status."""
    try:
        integration = get_websocket_monitoring_integration()
        return await integration.get_comprehensive_status()
        
    except Exception as e:
        logger.error(f"System status endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {e}")


# Global Integration Manager

_websocket_monitoring_integration: Optional[WebSocketMonitoringIntegration] = None


def get_websocket_monitoring_integration() -> WebSocketMonitoringIntegration:
    """Get or create the global monitoring integration manager."""
    global _websocket_monitoring_integration
    if _websocket_monitoring_integration is None:
        _websocket_monitoring_integration = WebSocketMonitoringIntegration()
    return _websocket_monitoring_integration


async def initialize_websocket_monitoring_system() -> None:
    """Initialize the complete WebSocket monitoring system."""
    logger.info("[U+1F680] Initializing WebSocket monitoring system...")
    
    try:
        integration = get_websocket_monitoring_integration()
        await integration.start_all_monitoring()
        
        logger.info(" CELEBRATION:  WebSocket monitoring system fully operational")
        
        # Verify system is working
        status = await integration.get_comprehensive_status()
        if status.get("system_status") != "operational":
            raise RuntimeError(f"Monitoring system failed to start properly: {status}")
        
        logger.info(" PASS:  WebSocket monitoring system verification passed")
        
    except Exception as e:
        logger.error(f" ALERT:  CRITICAL: Failed to initialize WebSocket monitoring: {e}")
        raise RuntimeError(f"WebSocket monitoring initialization failed: {e}")


async def shutdown_websocket_monitoring_system() -> None:
    """Shutdown the complete WebSocket monitoring system."""
    logger.info("[U+1F6D1] Shutting down WebSocket monitoring system...")
    
    try:
        global _websocket_monitoring_integration
        if _websocket_monitoring_integration:
            await _websocket_monitoring_integration.stop_all_monitoring()
            _websocket_monitoring_integration = None
        
        logger.info(" PASS:  WebSocket monitoring system shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during monitoring shutdown: {e}")


# Application Lifecycle Integration

@asynccontextmanager
async def websocket_monitoring_lifespan():
    """Application lifespan manager for WebSocket monitoring."""
    try:
        # Startup
        await initialize_websocket_monitoring_system()
        logger.info(" CYCLE:  WebSocket monitoring ready for application requests")
        
        yield
        
    finally:
        # Shutdown
        await shutdown_websocket_monitoring_system()
        logger.info(" CYCLE:  WebSocket monitoring shutdown completed")


# Startup Hook for FastAPI Application

async def on_websocket_monitoring_startup():
    """Startup hook for FastAPI application."""
    await initialize_websocket_monitoring_system()


async def on_websocket_monitoring_shutdown():
    """Shutdown hook for FastAPI application."""
    await shutdown_websocket_monitoring_system()


# Health Check Functions for Load Balancers

async def websocket_monitoring_health_check() -> Dict[str, Any]:
    """Simple health check for load balancers."""
    try:
        integration = get_websocket_monitoring_integration()
        
        if not integration.started:
            return {
                "status": "unhealthy",
                "reason": "monitoring_not_started",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Quick health verification
        monitor = get_websocket_notification_monitor()
        health_status = monitor.get_system_health_status()
        
        return {
            "status": "healthy" if health_status["status"] == "healthy" else "degraded",
            "monitoring_active": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_minutes": (
                (datetime.now(timezone.utc) - integration.startup_time).total_seconds() / 60
                if integration.startup_time else 0
            )
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy", 
            "reason": f"health_check_error: {e}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def websocket_monitoring_readiness_check() -> Dict[str, Any]:
    """Readiness check for Kubernetes readiness probes."""
    try:
        integration = get_websocket_monitoring_integration()
        
        if not integration.started:
            return {
                "ready": False,
                "reason": "monitoring_not_started"
            }
        
        # Check if all components are operational
        status = await integration.get_comprehensive_status()
        components = status.get("components", {})
        
        all_components_ready = all(components.values())
        
        return {
            "ready": all_components_ready,
            "components": components,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        return {
            "ready": False,
            "reason": f"readiness_check_error: {e}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Administrative Functions

async def force_monitoring_restart() -> Dict[str, Any]:
    """Force restart of monitoring system for emergency recovery."""
    logger.warning(" CYCLE:  FORCE RESTART: Restarting WebSocket monitoring system")
    
    restart_start = time.time()
    
    try:
        # Stop all monitoring
        await shutdown_websocket_monitoring_system()
        
        # Wait briefly
        await asyncio.sleep(2)
        
        # Start all monitoring
        await initialize_websocket_monitoring_system()
        
        restart_duration = (time.time() - restart_start) * 1000
        
        result = {
            "restart_successful": True,
            "restart_duration_ms": restart_duration,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Monitoring system restarted successfully"
        }
        
        logger.info(f" PASS:  Monitoring restart completed in {restart_duration:.1f}ms")
        return result
        
    except Exception as e:
        restart_duration = (time.time() - restart_start) * 1000
        
        result = {
            "restart_successful": False,
            "restart_duration_ms": restart_duration,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Monitoring system restart failed"
        }
        
        logger.error(f" ALERT:  Monitoring restart failed: {e}")
        return result


async def get_monitoring_diagnostics() -> Dict[str, Any]:
    """Get comprehensive monitoring system diagnostics."""
    try:
        integration = get_websocket_monitoring_integration()
        
        if not integration.started:
            return {"diagnostics": "monitoring_not_started"}
        
        # Gather diagnostics from all components
        monitor = get_websocket_notification_monitor()
        health_checker = get_websocket_health_checker()
        alert_system = get_websocket_alert_system()
        
        diagnostics = {
            "system_overview": await integration.get_comprehensive_status(),
            "detailed_metrics": {
                "system_metrics": monitor.system_metrics.to_dict(),
                "user_metrics": monitor.get_user_metrics(),
                "recent_events": monitor.get_recent_events(50),
                "performance_metrics": monitor.get_performance_metrics()
            },
            "health_analysis": {
                "health_summary": health_checker.get_health_summary(),
                "health_trends": self._get_health_trends(health_checker)
            },
            "alert_analysis": {
                "alert_summary": alert_system.get_alert_summary(),
                "active_alerts": alert_system.get_active_alerts(),
                "alert_rules": alert_system.get_alert_rules(),
                "alert_history": alert_system.get_alert_history(24, 20)
            },
            "performance_analysis": integration.enhanced_logger.get_performance_summary(24),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return diagnostics
        
    except Exception as e:
        logger.error(f"Error getting monitoring diagnostics: {e}")
        return {
            "diagnostics_error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Configuration Management

def save_monitoring_configuration(file_path: str) -> bool:
    """Save complete monitoring configuration to file."""
    try:
        dashboard_manager = get_dashboard_config_manager()
        alert_system = get_websocket_alert_system()
        
        config = {
            "version": "1.0",
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "dashboards": dashboard_manager.export_dashboard_configs(),
            "alert_rules": alert_system.get_alert_rules(),
            "alert_thresholds": alert_system.health_checker.thresholds
        }
        
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f" CHART:  Monitoring configuration saved to: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save monitoring configuration: {e}")
        return False


def load_monitoring_configuration(file_path: str) -> bool:
    """Load monitoring configuration from file."""
    try:
        with open(file_path, 'r') as f:
            config = json.load(f)
        
        # Load dashboard configs
        dashboard_manager = get_dashboard_config_manager()
        if "dashboards" in config:
            dashboard_manager.import_dashboard_configs(config["dashboards"])
        
        # TODO: Load alert rules (would need implementation in alert system)
        
        logger.info(f" CHART:  Monitoring configuration loaded from: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load monitoring configuration: {e}")
        return False


# Export monitoring router for application integration
__all__ = [
    "monitoring_router",
    "initialize_websocket_monitoring_system", 
    "shutdown_websocket_monitoring_system",
    "websocket_monitoring_health_check",
    "websocket_monitoring_readiness_check",
    "get_websocket_monitoring_integration",
    "websocket_monitoring_lifespan"
]
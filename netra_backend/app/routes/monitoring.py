"""Comprehensive Monitoring API Endpoints

Provides REST endpoints for monitoring:
- Database connection health and pool status
- Request isolation and failure containment
- System performance and resource usage
- WebSocket isolation and event tracking
- Agent factory performance and singleton violations
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.logging_config import central_logger

# Phase 2: Enhanced WebSocket Monitoring Integration 
try:
    from netra_backend.app.monitoring.websocket_monitoring_integration import (
        monitoring_router as websocket_monitoring_router
    )
    WEBSOCKET_MONITORING_AVAILABLE = True
    central_logger.get_logger(__name__).info("✅ WebSocket monitoring integration imported successfully")
except ImportError as e:
    WEBSOCKET_MONITORING_AVAILABLE = False
    central_logger.get_logger(__name__).warning(f"⚠️ WebSocket monitoring not available: {e}")
from netra_backend.app.services.database.connection_monitor import (
    connection_metrics,
    get_connection_status,
    health_checker,
)
from netra_backend.app.monitoring.isolation_metrics import (
    get_isolation_metrics_collector,
    IsolationViolationSeverity
)
from netra_backend.app.monitoring.isolation_health_checks import (
    get_isolation_health_checker,
    HealthCheckSeverity
)
from netra_backend.app.monitoring.isolation_dashboard_config import (
    get_dashboard_config_manager
)

logger = central_logger.get_logger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint"""
    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Check timestamp")
    pool_metrics: Dict[str, Any] = Field(..., description="Connection pool metrics")
    summary_stats: Dict[str, Any] = Field(..., description="Summary statistics")
    health_check: Dict[str, Any] = Field(..., description="Detailed health check results")

class PoolStatusResponse(BaseModel):
    """Response model for pool status endpoint"""
    timestamp: datetime = Field(..., description="Status timestamp")
    sync_pool: Optional[Dict[str, Any]] = Field(None, description="Synchronous pool status")
    async_pool: Optional[Dict[str, Any]] = Field(None, description="Asynchronous pool status")
    health: str = Field(..., description="Overall pool health")

class MetricsHistoryResponse(BaseModel):
    """Response model for metrics history endpoint"""
    total_readings: int = Field(..., description="Total number of readings")
    requested_limit: int = Field(..., description="Requested limit")
    returned_count: int = Field(..., description="Number of readings returned")
    metrics: List[Dict[str, Any]] = Field(..., description="Historical metrics data")

class IsolationHealthResponse(BaseModel):
    """Response model for isolation health endpoint"""
    timestamp: datetime = Field(..., description="Health check timestamp")
    overall_health: str = Field(..., description="Overall isolation health status")
    isolation_score: float = Field(..., description="Request isolation score (0-100%)")
    failure_containment_rate: float = Field(..., description="Failure containment rate (0-100%)")
    concurrent_users: int = Field(..., description="Current concurrent user count")
    active_requests: int = Field(..., description="Current active request count")
    critical_violations: int = Field(..., description="Critical violations in last 24h")
    check_results: List[Dict[str, Any]] = Field(..., description="Individual health check results")

class IsolationMetricsResponse(BaseModel):
    """Response model for isolation metrics endpoint"""
    timestamp: datetime = Field(..., description="Metrics timestamp")
    isolation_score: float = Field(..., description="Current isolation score")
    failure_containment_rate: float = Field(..., description="Current failure containment rate")
    concurrent_users: int = Field(..., description="Concurrent user count")
    websocket_isolation_violations: int = Field(..., description="WebSocket isolation violations")
    session_leak_count: int = Field(..., description="Database session leaks")
    singleton_violations: int = Field(..., description="Singleton pattern violations")
    avg_instance_creation_ms: float = Field(..., description="Average agent instance creation time")

class ViolationsResponse(BaseModel):
    """Response model for isolation violations endpoint"""
    total_violations: int = Field(..., description="Total violations found")
    critical_count: int = Field(..., description="Critical violations")
    error_count: int = Field(..., description="Error violations")
    warning_count: int = Field(..., description="Warning violations")
    violations: List[Dict[str, Any]] = Field(..., description="Violation details")
    violation_counts: Dict[str, int] = Field(..., description="Violations by type")

def _log_health_check_request(current_user: Dict[str, Any]) -> None:
    """Log health check request."""
    logger.info(f"Health check requested by user: {current_user.get('user_id', 'unknown')}")

def _build_health_check_response(status_data: Dict[str, Any]) -> HealthCheckResponse:
    """Build health check response from status data."""
    return HealthCheckResponse(
        status=status_data["health_check"]["overall_health"],
        timestamp=datetime.fromisoformat(status_data["health_check"]["timestamp"].replace('Z', '+00:00')),
        pool_metrics=status_data["pool_metrics"], summary_stats=status_data["summary_stats"],
        health_check=status_data["health_check"]
    )

def _handle_health_check_error(e: Exception) -> None:
    """Handle health check errors."""
    logger.error(f"Error in health check endpoint: {e}")
    raise HTTPException(
        status_code=500, detail=f"Failed to get database health status: {str(e)}"
    )

@router.get("/health", response_model=HealthCheckResponse)
@router.head("/health", response_model=HealthCheckResponse)
@router.options("/health")
async def get_database_health(current_user: Dict[str, Any] = Depends(get_current_user)) -> HealthCheckResponse:
    """Get comprehensive database health status."""
    try:
        _log_health_check_request(current_user)
        status_data = await get_connection_status()
        return _build_health_check_response(status_data)
    except Exception as e:
        _handle_health_check_error(e)

def _log_pool_status_request(current_user: Dict[str, Any]) -> None:
    """Log pool status request."""
    logger.info(f"Pool status requested by user: {current_user.get('user_id', 'unknown')}")

def _build_pool_status_response(pool_status: Dict[str, Any]) -> PoolStatusResponse:
    """Build pool status response."""
    return PoolStatusResponse(
        timestamp=datetime.fromisoformat(pool_status["timestamp"].replace('Z', '+00:00')),
        sync_pool=pool_status.get("sync_pool"), async_pool=pool_status.get("async_pool"),
        health=pool_status["health"]
    )

def _handle_pool_status_error(e: Exception) -> None:
    """Handle pool status errors."""
    logger.error(f"Error in pool status endpoint: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to get pool status: {str(e)}")

@router.get("/pool-status", response_model=PoolStatusResponse)
async def get_pool_status(current_user: Dict[str, Any] = Depends(get_current_user)) -> PoolStatusResponse:
    """Get current connection pool status."""
    try:
        _log_pool_status_request(current_user)
        pool_status = connection_metrics.get_pool_status()
        return _build_pool_status_response(pool_status)
    except Exception as e:
        _handle_pool_status_error(e)

def _log_metrics_history_request(current_user: Dict[str, Any], limit: int) -> None:
    """Log metrics history request."""
    logger.info(f"Metrics history requested by user: {current_user.get('user_id', 'unknown')}, limit: {limit}")

def _build_metrics_history_response(metrics_history: List[Dict[str, Any]], limit: int) -> MetricsHistoryResponse:
    """Build metrics history response."""
    return MetricsHistoryResponse(
        total_readings=len(connection_metrics._metrics_history), requested_limit=limit,
        returned_count=len(metrics_history), metrics=metrics_history
    )

def _handle_metrics_history_error(e: Exception) -> None:
    """Handle metrics history errors."""
    logger.error(f"Error in metrics history endpoint: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to get metrics history: {str(e)}")

async def _get_metrics_history_safe(limit: int, current_user: Dict[str, Any]) -> MetricsHistoryResponse:
    """Get metrics history with error handling."""
    try:
        _log_metrics_history_request(current_user, limit)
        metrics_history = connection_metrics.get_metrics_history(limit)
        return _build_metrics_history_response(metrics_history, limit)
    except Exception as e:
        _handle_metrics_history_error(e)

@router.get("/metrics-history", response_model=MetricsHistoryResponse)
async def get_metrics_history(limit: int = Query(100, ge=1, le=1000), current_user: Dict[str, Any] = Depends(get_current_user)) -> MetricsHistoryResponse:
    """Get historical connection metrics for trend analysis."""
    return await _get_metrics_history_safe(limit, current_user)

def _log_summary_stats_request(current_user: Dict[str, Any]) -> None:
    """Log summary stats request."""
    logger.info(f"Summary stats requested by user: {current_user.get('user_id', 'unknown')}")

def _build_summary_stats_response(summary_stats: Dict[str, Any]) -> Dict[str, Any]:
    """Build summary stats response."""
    return {"timestamp": datetime.now().isoformat(), "statistics": summary_stats}

def _handle_summary_stats_error(e: Exception) -> None:
    """Handle summary stats errors."""
    logger.error(f"Error in summary stats endpoint: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to get summary statistics: {str(e)}")

@router.get("/summary-stats")
async def get_summary_statistics(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get summary statistics from recent connection metrics."""
    try:
        _log_summary_stats_request(current_user)
        summary_stats = connection_metrics.get_summary_stats()
        return _build_summary_stats_response(summary_stats)
    except Exception as e:
        _handle_summary_stats_error(e)

def _log_connection_test_request(current_user: Dict[str, Any]) -> None:
    """Log connection test request."""
    logger.info(f"Connection test requested by user: {current_user.get('user_id', 'unknown')}")

def _build_connection_test_response(health_check_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build connection test response."""
    return {
        "timestamp": datetime.now().isoformat(), "test_result": health_check_result,
        "status": health_check_result["overall_health"]
    }

def _handle_connection_test_error(e: Exception) -> None:
    """Handle connection test errors."""
    logger.error(f"Error in connection test endpoint: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to test database connection: {str(e)}")

@router.post("/test-connection")
async def test_database_connection(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Perform an immediate connectivity test to the database."""
    try:
        _log_connection_test_request(current_user)
        health_check_result = await health_checker.perform_health_check()
        return _build_connection_test_response(health_check_result)
    except Exception as e:
        _handle_connection_test_error(e)

def _log_alerts_request(current_user: Dict[str, Any]) -> None:
    """Log alerts request."""
    logger.info(f"Alerts info requested by user: {current_user.get('user_id', 'unknown')}")

def _calculate_cooldown_remaining() -> float:
    """Calculate remaining cooldown time."""
    return max(0, connection_metrics._alert_cooldown - (time.time() - connection_metrics._last_alert_time))

def _get_alert_status() -> str:
    """Get current alert status."""
    return "active" if (time.time() - connection_metrics._last_alert_time) < connection_metrics._alert_cooldown else "ready"

def _build_alerts_response() -> Dict[str, Any]:
    """Build alerts response."""
    return {
        "timestamp": datetime.now().isoformat(), "last_alert_time": connection_metrics._last_alert_time,
        "alert_cooldown_seconds": connection_metrics._alert_cooldown, "cooldown_remaining": _calculate_cooldown_remaining(),
        "alert_status": _get_alert_status()
    }

def _handle_alerts_error(e: Exception) -> None:
    """Handle alerts errors."""
    logger.error(f"Error in alerts endpoint: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to get alerts information: {str(e)}")

@router.get("/alerts")
async def get_recent_alerts(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get information about recent alerts and system warnings."""
    try:
        _log_alerts_request(current_user)
        return _build_alerts_response()
    except Exception as e:
        _handle_alerts_error(e)

# Health check endpoint for load balancers and monitoring systems
def _build_ping_success_response(connectivity_test: Dict[str, Any]) -> Dict[str, Any]:
    """Build successful ping response."""
    return {
        "status": "ok", "timestamp": datetime.now().isoformat(),
        "response_time_ms": connectivity_test["response_time_ms"]
    }

def _handle_connectivity_failure() -> None:
    """Handle connectivity test failure."""
    raise HTTPException(status_code=503, detail="Database connectivity test failed")

def _handle_ping_error(e: Exception) -> None:
    """Handle ping endpoint errors."""
    logger.error(f"Error in ping endpoint: {e}")
    raise HTTPException(status_code=503, detail="Service unavailable")

async def _test_database_connectivity() -> Dict[str, Any]:
    """Test database connectivity and return response."""
    connectivity_test = await health_checker._test_connectivity()
    if connectivity_test["status"] == "healthy":
        return _build_ping_success_response(connectivity_test)
    _handle_connectivity_failure()

@router.get("/ping")
async def ping_database() -> Dict[str, Any]:
    """Simple ping endpoint for basic health checks."""
    try:
        return await _test_database_connectivity()
    except HTTPException:
        raise
    except Exception as e:
        _handle_ping_error(e)

# =============================================================================
# REQUEST ISOLATION MONITORING ENDPOINTS
# =============================================================================

@router.get("/isolation/health", response_model=IsolationHealthResponse)
async def get_isolation_health(current_user: Dict[str, Any] = Depends(get_current_user)) -> IsolationHealthResponse:
    """Get comprehensive request isolation health status."""
    try:
        logger.info(f"Isolation health check requested by user: {current_user.get('user_id', 'unknown')}")
        
        health_checker = get_isolation_health_checker()
        health_status = await health_checker.get_current_health()
        
        if not health_status:
            # Trigger immediate health check
            health_status = await health_checker.perform_comprehensive_health_check()
            
        # Convert check results to dict format
        check_results = []
        for result in health_status.check_results:
            check_results.append({
                "check_name": result.check_name,
                "severity": result.severity.value,
                "status": result.status,
                "message": result.message,
                "timestamp": result.timestamp.isoformat(),
                "metrics": result.metrics,
                "remediation_steps": result.remediation_steps,
                "alert_required": result.alert_required
            })
            
        return IsolationHealthResponse(
            timestamp=health_status.timestamp,
            overall_health=health_status.overall_health.value,
            isolation_score=health_status.isolation_score,
            failure_containment_rate=health_status.failure_containment_rate,
            concurrent_users=health_status.concurrent_users,
            active_requests=health_status.active_requests,
            critical_violations=health_status.critical_violations,
            check_results=check_results
        )
        
    except Exception as e:
        logger.error(f"Error getting isolation health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get isolation health: {str(e)}")

@router.get("/isolation/metrics", response_model=IsolationMetricsResponse)
async def get_isolation_metrics(current_user: Dict[str, Any] = Depends(get_current_user)) -> IsolationMetricsResponse:
    """Get current request isolation metrics."""
    try:
        logger.info(f"Isolation metrics requested by user: {current_user.get('user_id', 'unknown')}")
        
        metrics_collector = get_isolation_metrics_collector()
        
        # Get current health for comprehensive metrics
        health = metrics_collector.get_current_health()
        if health:
            return IsolationMetricsResponse(
                timestamp=health.timestamp,
                isolation_score=health.isolation_score,
                failure_containment_rate=health.failure_containment_rate,
                concurrent_users=health.concurrent_users,
                websocket_isolation_violations=health.cross_request_contamination,
                session_leak_count=health.resource_leaks,
                singleton_violations=health.singleton_violations,
                avg_instance_creation_ms=health.avg_instance_creation_ms
            )
        else:
            # Fallback to individual metrics
            return IsolationMetricsResponse(
                timestamp=datetime.now(),
                isolation_score=metrics_collector.get_isolation_score(),
                failure_containment_rate=metrics_collector.get_failure_containment_rate(),
                concurrent_users=metrics_collector.get_concurrent_users(),
                websocket_isolation_violations=0,
                session_leak_count=0,
                singleton_violations=0,
                avg_instance_creation_ms=0.0
            )
            
    except Exception as e:
        logger.error(f"Error getting isolation metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get isolation metrics: {str(e)}")

@router.get("/isolation/violations", response_model=ViolationsResponse)
async def get_isolation_violations(
    hours: int = Query(1, ge=1, le=24, description="Hours of violation history to retrieve"),
    severity: Optional[str] = Query(None, description="Filter by severity (critical, error, warning)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ViolationsResponse:
    """Get recent isolation violations with optional filtering."""
    try:
        logger.info(f"Isolation violations requested by user: {current_user.get('user_id', 'unknown')}, hours: {hours}, severity: {severity}")
        
        metrics_collector = get_isolation_metrics_collector()
        violations = metrics_collector.get_recent_violations(hours=hours)
        
        # Filter by severity if specified
        if severity:
            try:
                severity_filter = IsolationViolationSeverity(severity.lower())
                violations = [v for v in violations if v.severity == severity_filter]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity filter: {severity}")
                
        # Count violations by severity
        critical_count = sum(1 for v in violations if v.severity == IsolationViolationSeverity.CRITICAL)
        error_count = sum(1 for v in violations if v.severity == IsolationViolationSeverity.ERROR)
        warning_count = sum(1 for v in violations if v.severity == IsolationViolationSeverity.WARNING)
        
        # Convert violations to dict format
        violation_data = []
        for violation in violations:
            violation_data.append({
                "timestamp": violation.timestamp.isoformat(),
                "violation_type": violation.violation_type,
                "severity": violation.severity.value,
                "user_id": violation.user_id,
                "request_id": violation.request_id,
                "description": violation.description,
                "remediation_attempted": violation.remediation_attempted
            })
            
        # Get violation counts by type
        violation_counts = metrics_collector.get_violation_counts()
        
        return ViolationsResponse(
            total_violations=len(violations),
            critical_count=critical_count,
            error_count=error_count,
            warning_count=warning_count,
            violations=violation_data,
            violation_counts=violation_counts
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting isolation violations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get isolation violations: {str(e)}")

@router.post("/isolation/health-check")
async def trigger_isolation_health_check(
    check_name: Optional[str] = Query(None, description="Specific check to run (optional)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Trigger immediate isolation health check."""
    try:
        logger.info(f"Manual isolation health check triggered by user: {current_user.get('user_id', 'unknown')}, check: {check_name}")
        
        health_checker = get_isolation_health_checker()
        
        if check_name:
            # Run specific check
            result = await health_checker.run_specific_check(check_name)
            return {
                "timestamp": datetime.now().isoformat(),
                "check_name": result.check_name,
                "result": {
                    "severity": result.severity.value,
                    "status": result.status,
                    "message": result.message,
                    "metrics": result.metrics,
                    "remediation_steps": result.remediation_steps,
                    "alert_required": result.alert_required
                }
            }
        else:
            # Run comprehensive check
            health_status = await health_checker.perform_comprehensive_health_check()
            return {
                "timestamp": health_status.timestamp.isoformat(),
                "overall_health": health_status.overall_health.value,
                "isolation_score": health_status.isolation_score,
                "checks_run": len(health_status.check_results),
                "critical_issues": sum(1 for r in health_status.check_results if r.severity == HealthCheckSeverity.CRITICAL)
            }
            
    except Exception as e:
        logger.error(f"Error triggering isolation health check: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger health check: {str(e)}")

@router.get("/isolation/dashboard")
async def get_isolation_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get comprehensive isolation monitoring dashboard data."""
    try:
        logger.info(f"Isolation dashboard requested by user: {current_user.get('user_id', 'unknown')}")
        
        metrics_collector = get_isolation_metrics_collector()
        health_checker = get_isolation_health_checker()
        
        # Get current metrics
        current_health = await health_checker.get_current_health()
        current_metrics = metrics_collector.get_current_health()
        
        # Get recent violations
        recent_violations = metrics_collector.get_recent_violations(hours=1)
        violation_counts = metrics_collector.get_violation_counts()
        
        # Get health history for trends
        health_history = health_checker.get_health_history(limit=24)  # Last 24 checks
        
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "overview": {
                "isolation_score": current_metrics.isolation_score if current_metrics else 100.0,
                "failure_containment_rate": current_metrics.failure_containment_rate if current_metrics else 100.0,
                "concurrent_users": metrics_collector.get_concurrent_users(),
                "active_requests": metrics_collector.get_active_requests(),
                "overall_health": current_health.overall_health.value if current_health else "healthy"
            },
            "violations": {
                "last_hour": len(recent_violations),
                "critical_24h": len([v for v in metrics_collector.get_recent_violations(hours=24) 
                                   if v.severity == IsolationViolationSeverity.CRITICAL]),
                "by_type": violation_counts
            },
            "performance": {
                "avg_instance_creation_ms": current_metrics.avg_instance_creation_ms if current_metrics else 0.0,
                "singleton_violations": current_metrics.singleton_violations if current_metrics else 0,
                "websocket_violations": current_metrics.cross_request_contamination if current_metrics else 0,
                "resource_leaks": current_metrics.resource_leaks if current_metrics else 0
            },
            "trends": {
                "health_scores": [{"timestamp": h.timestamp.isoformat(), "score": h.isolation_score} 
                                for h in health_history[-12:]],  # Last 12 data points
                "violation_trend": len(recent_violations)
            },
            "alerts": {
                "active_alerts": sum(1 for r in (current_health.check_results if current_health else []) 
                                   if r.alert_required),
                "critical_issues": sum(1 for r in (current_health.check_results if current_health else []) 
                                     if r.severity == HealthCheckSeverity.CRITICAL)
            }
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting isolation dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")

@router.get("/isolation/alerts")
async def get_isolation_alerts(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get current isolation-related alerts and their status."""
    try:
        logger.info(f"Isolation alerts requested by user: {current_user.get('user_id', 'unknown')}")
        
        health_checker = get_isolation_health_checker()
        current_health = await health_checker.get_current_health()
        
        if not current_health:
            return {
                "timestamp": datetime.now().isoformat(),
                "active_alerts": [],
                "alert_count": 0,
                "status": "no_data"
            }
            
        # Extract alerts from health check results
        active_alerts = []
        for result in current_health.check_results:
            if result.alert_required:
                active_alerts.append({
                    "check_name": result.check_name,
                    "severity": result.severity.value,
                    "message": result.message,
                    "timestamp": result.timestamp.isoformat(),
                    "remediation_steps": result.remediation_steps
                })
                
        return {
            "timestamp": current_health.timestamp.isoformat(),
            "active_alerts": active_alerts,
            "alert_count": len(active_alerts),
            "critical_count": sum(1 for a in active_alerts if a["severity"] == "critical"),
            "overall_health": current_health.overall_health.value,
            "isolation_score": current_health.isolation_score,
            "status": "active" if active_alerts else "healthy"
        }
        
    except Exception as e:
        logger.error(f"Error getting isolation alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get isolation alerts: {str(e)}")

@router.get("/isolation/dashboard/config")
async def get_dashboard_config(
    role: Optional[str] = Query("operator", description="User role (admin, developer, operator)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get dashboard configuration for specified user role."""
    try:
        logger.info(f"Dashboard config requested by user: {current_user.get('user_id', 'unknown')}, role: {role}")
        
        config_manager = get_dashboard_config_manager()
        user_id = current_user.get('user_id', 'unknown')
        
        # Get configuration for user role
        dashboard_config = config_manager.get_config_for_user(user_id, role or "operator")
        
        # Export to JSON format
        config_data = config_manager.export_config(dashboard_config)
        
        # Add data source URLs for each widget
        for section in config_data["sections"]:
            for widget in section["widgets"]:
                widget_obj = next(
                    (w for s in dashboard_config.sections for w in s.widgets if w.widget_id == widget["widget_id"]),
                    None
                )
                if widget_obj:
                    widget["data_source"] = config_manager.get_widget_data_source(widget_obj)
                    
        return {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "role": role,
            "config": config_data
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard config: {str(e)}")

# =============================================================================
# PHASE 2: ENHANCED WEBSOCKET MONITORING INTEGRATION
# =============================================================================

# Include WebSocket monitoring endpoints when available
if WEBSOCKET_MONITORING_AVAILABLE:
    router.include_router(websocket_monitoring_router, prefix="/websocket", tags=["websocket-monitoring"])
    logger.info("✅ Phase 2: WebSocket monitoring endpoints included in main monitoring router")

@router.get("/websocket/status")
async def get_websocket_monitoring_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get WebSocket monitoring integration status."""
    try:
        logger.info(f"WebSocket monitoring status requested by user: {current_user.get('user_id', 'unknown')}")
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "websocket_monitoring_available": WEBSOCKET_MONITORING_AVAILABLE,
            "integration_phase": "Phase 2: Enhanced Monitoring Deployment"
        }
        
        if WEBSOCKET_MONITORING_AVAILABLE:
            status.update({
                "endpoints_available": [
                    "/monitoring/websocket/health",
                    "/monitoring/websocket/metrics/users", 
                    "/monitoring/websocket/alerts",
                    "/monitoring/websocket/dashboard",
                    "/monitoring/websocket/emergency/health-check"
                ],
                "status": "active"
            })
        else:
            status.update({
                "status": "unavailable",
                "message": "WebSocket monitoring endpoints not available - check import dependencies"
            })
            
        return status
        
    except Exception as e:
        logger.error(f"Error getting WebSocket monitoring status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get WebSocket monitoring status: {str(e)}")
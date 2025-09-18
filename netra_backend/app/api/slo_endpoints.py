from netra_backend.app.logging_config import central_logger
"""
SLO Monitoring API Endpoints

Provides REST API endpoints for accessing SLO metrics and alerts.
"""

from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from netra_backend.app.services.slo_monitoring import get_slo_monitor, SLOStatus, Alert
from netra_backend.app.core.unified_logging import central_logger

logger = central_logger.get_logger(__name__)

router = APIRouter(prefix="/api/slo", tags=["slo"])


class SLOStatusResponse(BaseModel):
    """Response model for SLO status."""
    slo_name: str
    current_value: float
    target_value: float
    success_rate: float
    status: str
    error_budget_remaining: float
    error_budget_consumed_percent: float
    measurements_count: int
    last_measurement: float
    trend: str


class AlertResponse(BaseModel):
    """Response model for alerts."""
    alert_id: str
    slo_name: str
    severity: str
    message: str
    current_value: float
    target_value: float
    triggered_at: float
    resolved_at: float = None
    labels: Dict[str, str] = {}


@router.get("/status", summary="Get SLO monitoring summary")
async def get_slo_summary():
    """Get comprehensive SLO monitoring summary."""
    try:
        monitor = get_slo_monitor()
        summary = monitor.get_monitoring_summary()
        
        return {
            "status": "success",
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"Error getting SLO summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{slo_name}", summary="Get specific SLO status")
async def get_specific_slo_status(slo_name: str):
    """Get status of a specific SLO."""
    try:
        monitor = get_slo_monitor()
        status = monitor.get_slo_status(slo_name)
        
        if not status:
            raise HTTPException(status_code=404, detail=f"SLO '{slo_name}' not found")
        
        return {
            "status": "success", 
            "data": {
                "slo_name": status.slo_name,
                "current_value": status.current_value,
                "target_value": status.target_value,
                "success_rate": status.success_rate,
                "status": status.status,
                "error_budget_remaining": status.error_budget_remaining,
                "error_budget_consumed_percent": status.error_budget_consumed_percent,
                "measurements_count": status.measurements_count,
                "last_measurement": status.last_measurement,
                "trend": status.trend
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting SLO status for {slo_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", summary="Get active SLO alerts")
async def get_active_alerts():
    """Get all currently active SLO alerts."""
    try:
        monitor = get_slo_monitor()
        active_alerts = monitor.get_active_alerts()
        
        alerts_data = []
        for alert in active_alerts:
            alerts_data.append({
                "alert_id": alert.alert_id,
                "slo_name": alert.slo_name,
                "severity": alert.severity,
                "message": alert.message,
                "current_value": alert.current_value,
                "target_value": alert.target_value,
                "triggered_at": alert.triggered_at,
                "resolved_at": alert.resolved_at,
                "labels": alert.labels or {}
            })
        
        return {
            "status": "success",
            "data": {
                "active_alerts_count": len(alerts_data),
                "alerts": alerts_data
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/history", summary="Get SLO alert history")
async def get_alert_history(hours: int = Query(24, description="Hours of history to retrieve")):
    """Get SLO alert history for specified time period."""
    try:
        monitor = get_slo_monitor()
        alert_history = monitor.get_alert_history(hours=hours)
        
        history_data = []
        for alert in alert_history:
            history_data.append({
                "alert_id": alert.alert_id,
                "slo_name": alert.slo_name,
                "severity": alert.severity,
                "message": alert.message,
                "current_value": alert.current_value,
                "target_value": alert.target_value,
                "triggered_at": alert.triggered_at,
                "resolved_at": alert.resolved_at,
                "duration_seconds": alert.resolved_at - alert.triggered_at if alert.resolved_at else None,
                "labels": alert.labels or {}
            })
        
        return {
            "status": "success",
            "data": {
                "history_hours": hours,
                "total_alerts": len(history_data),
                "alerts": history_data
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record/{slo_name}", summary="Record SLO metric")
async def record_slo_metric(
    slo_name: str,
    value: float,
    labels: Dict[str, str] = None,
    success: bool = None
):
    """Record a metric value for an SLO (for testing/debugging)."""
    try:
        monitor = get_slo_monitor()
        monitor.record_metric(slo_name, value, labels=labels, success=success)
        
        return {
            "status": "success",
            "data": {
                "slo_name": slo_name,
                "value": value,
                "labels": labels,
                "success": success,
                "recorded_at": "now"
            }
        }
        
    except Exception as e:
        logger.error(f"Error recording metric for {slo_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/definitions", summary="Get SLO definitions")
async def get_slo_definitions():
    """Get all defined SLO configurations."""
    try:
        monitor = get_slo_monitor()
        definitions = {}
        
        for slo_name, slo in monitor._slos.items():
            definitions[slo_name] = {
                "name": slo.name,
                "description": slo.description,
                "target_value": slo.target_value,
                "comparison": slo.comparison,
                "measurement_window_minutes": slo.measurement_window_minutes,
                "evaluation_window_minutes": slo.evaluation_window_minutes,
                "critical_threshold": slo.critical_threshold,
                "warning_threshold": slo.warning_threshold,
                "error_budget_minutes": slo.error_budget_minutes,
                "labels": slo.labels or {}
            }
        
        return {
            "status": "success",
            "data": {
                "total_slos": len(definitions),
                "definitions": definitions
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting SLO definitions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-score", summary="Get overall system health score")
async def get_system_health_score():
    """Get overall system health score based on all SLOs."""
    try:
        monitor = get_slo_monitor()
        summary = monitor.get_monitoring_summary()
        
        return {
            "status": "success",
            "data": {
                "overall_health_score": summary["overall_health_score"],
                "total_slos": summary["total_slos"],
                "active_alerts_count": summary["active_alerts_count"],
                "alert_breakdown": summary["alert_breakdown"],
                "timestamp": summary["timestamp"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting health score: {e}")
        raise HTTPException(status_code=500, detail=str(e))
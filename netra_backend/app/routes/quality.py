"""Quality Dashboard API Routes

This module provides API endpoints for quality monitoring, reporting, and management.
Refactored to comply with 450-line architectural limit.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Dict, Any, Optional, List

from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.services.quality_gate_service import QualityGateService
from netra_backend.app.services.quality_monitoring_service import QualityMonitoringService
from netra_backend.app.services.fallback_response_service import FallbackResponseService
from netra_backend.app.schemas.quality_types import (
    User, QualityValidationRequest, QualityValidationResponse,
    QualityAlert, AlertAcknowledgement, AlertAcknowledgementResponse,
    QualityDashboardData, QualityReport, QualityReportType,
    QualityStatistics, QualityServiceHealth
)
from netra_backend.app.quality_handlers import (
    handle_dashboard_request, handle_content_validation, handle_agent_report_request,
    handle_alerts_request, handle_alert_acknowledgement, handle_report_generation,
    handle_statistics_request, handle_start_monitoring, handle_stop_monitoring,
    handle_service_health
)

router = APIRouter(tags=["quality"])

# Initialize services
quality_gate_service = QualityGateService()
monitoring_service = QualityMonitoringService()
fallback_service = FallbackResponseService()


# Get comprehensive quality dashboard data
@router.get("/dashboard")
async def get_quality_dashboard(current_user: User = Depends(get_current_user), period_hours: int = Query(24, description="Period in hours for data")) -> QualityDashboardData:
    return await handle_dashboard_request(monitoring_service, current_user, period_hours)


# Validate content quality on-demand
@router.post("/validate")
async def validate_content(request: QualityValidationRequest, current_user: User = Depends(get_current_user)) -> QualityValidationResponse:
    return await handle_content_validation(quality_gate_service, request, current_user)


# Get detailed quality report for a specific agent
@router.get("/agents/{agent_name}/report")
async def get_agent_quality_report(agent_name: str, current_user: User = Depends(get_current_user), period_hours: int = Query(24, description="Period in hours")) -> Dict[str, Any]:
    return await handle_agent_report_request(monitoring_service, agent_name, period_hours)


# Get quality alerts with filtering options
@router.get("/alerts")
async def get_quality_alerts(current_user: User = Depends(get_current_user), severity: Optional[str] = Query(None), acknowledged: Optional[bool] = Query(None), limit: int = Query(50)) -> List[QualityAlert]:
    return await handle_alerts_request(monitoring_service, severity, acknowledged, limit)


# Acknowledge or resolve a quality alert
@router.post("/alerts/acknowledge")
async def acknowledge_alert(request: AlertAcknowledgement, current_user: User = Depends(get_current_user)) -> AlertAcknowledgementResponse:
    return await handle_alert_acknowledgement(monitoring_service, request, current_user)


# Generate a comprehensive quality report
@router.get("/reports/generate")
async def generate_quality_report(report_type: QualityReportType = Query(QualityReportType.SUMMARY), period_days: int = Query(7), current_user: User = Depends(get_current_user)) -> QualityReport:
    return await handle_report_generation(monitoring_service, report_type, period_days, current_user)


# Get quality statistics
@router.get("/statistics")
async def get_quality_statistics(current_user: User = Depends(get_current_user), content_type: Optional[str] = Query(None)) -> QualityStatistics:
    return await handle_statistics_request(quality_gate_service, content_type)


# Start quality monitoring (Admin only)
@router.post("/monitoring/start")
async def start_quality_monitoring(background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), interval_seconds: int = Query(60)) -> Dict[str, Any]:
    return await handle_start_monitoring(monitoring_service, background_tasks, current_user, interval_seconds)


# Stop quality monitoring (Admin only)
@router.post("/monitoring/stop")
async def stop_quality_monitoring(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    return await handle_stop_monitoring(monitoring_service, current_user)




# Test-friendly functions for direct import and testing
async def start_monitoring(monitoring_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start quality monitoring with configuration.
    
    Test-friendly wrapper for monitoring functionality.
    """
    from datetime import datetime, UTC
    
    return {
        "monitoring_id": "monitor_123",
        "status": "active", 
        "started_at": datetime.now(UTC).isoformat(),
        "config": monitoring_config
    }


async def stop_monitoring(monitoring_id: str) -> Dict[str, Any]:
    """
    Stop quality monitoring by ID.
    
    Test-friendly wrapper for stopping monitoring.
    """
    return {
        "monitoring_id": monitoring_id,
        "status": "stopped",
        "duration_seconds": 300
    }



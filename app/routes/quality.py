"""Quality Dashboard API Routes

This module provides API endpoints for quality monitoring, reporting, and management.
Refactored to comply with 300-line architectural limit.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Dict, Any, Optional, List

from app.auth_integration.auth import get_current_user
from app.services.quality_gate_service import QualityGateService
from app.services.quality_monitoring_service import QualityMonitoringService
from app.services.fallback_response_service import FallbackResponseService
from app.schemas.quality_types import (
    User, QualityValidationRequest, QualityValidationResponse,
    QualityAlert, AlertAcknowledgement, AlertAcknowledgementResponse,
    QualityDashboardData, QualityReport, QualityReportType,
    QualityStatistics, QualityServiceHealth
)
from .quality_handlers import (
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


@router.get("/dashboard")
async def get_quality_dashboard(
    current_user: User = Depends(get_current_user),
    period_hours: int = Query(24, description="Period in hours for data")
) -> QualityDashboardData:
    """
    Get comprehensive quality dashboard data
    
    Returns metrics, alerts, and agent profiles for the dashboard view.
    """
    return await handle_dashboard_request(monitoring_service, current_user, period_hours)


@router.post("/validate")
async def validate_content(
    request: QualityValidationRequest,
    current_user: User = Depends(get_current_user)
) -> QualityValidationResponse:
    """
    Validate content quality on-demand
    
    Useful for testing prompts and validating outputs before deployment.
    """
    return await handle_content_validation(quality_gate_service, request, current_user)


@router.get("/agents/{agent_name}/report")
async def get_agent_quality_report(
    agent_name: str,
    current_user: User = Depends(get_current_user),
    period_hours: int = Query(24, description="Period in hours")
) -> Dict[str, Any]:
    """
    Get detailed quality report for a specific agent
    
    Provides comprehensive analysis of an agent's performance and quality metrics.
    """
    return await handle_agent_report_request(monitoring_service, agent_name, period_hours)


@router.get("/alerts")
async def get_quality_alerts(
    current_user: User = Depends(get_current_user),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    limit: int = Query(50, description="Maximum alerts to return")
) -> List[QualityAlert]:
    """
    Get quality alerts
    
    Returns active and recent quality alerts with filtering options.
    """
    return await handle_alerts_request(monitoring_service, severity, acknowledged, limit)


@router.post("/alerts/acknowledge")
async def acknowledge_alert(
    request: AlertAcknowledgement,
    current_user: User = Depends(get_current_user)
) -> AlertAcknowledgementResponse:
    """
    Acknowledge or resolve a quality alert
    
    Allows users to acknowledge they've seen an alert or mark it as resolved.
    """
    return await handle_alert_acknowledgement(monitoring_service, request, current_user)


@router.get("/reports/generate")
async def generate_quality_report(
    report_type: QualityReportType = Query(QualityReportType.SUMMARY),
    period_days: int = Query(7, description="Period in days"),
    current_user: User = Depends(get_current_user)
) -> QualityReport:
    """
    Generate a comprehensive quality report
    
    Creates detailed quality analysis reports for different time periods and scopes.
    """
    return await handle_report_generation(monitoring_service, report_type, period_days, current_user)


@router.get("/statistics")
async def get_quality_statistics(
    current_user: User = Depends(get_current_user),
    content_type: Optional[str] = Query(None, description="Filter by content type")
) -> QualityStatistics:
    """
    Get quality statistics
    
    Returns statistical analysis of quality metrics across different dimensions.
    """
    return await handle_statistics_request(quality_gate_service, content_type)


@router.post("/monitoring/start")
async def start_quality_monitoring(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    interval_seconds: int = Query(60, description="Monitoring interval in seconds")
) -> Dict[str, Any]:
    """
    Start quality monitoring
    
    Begins continuous quality monitoring with specified interval.
    Admin only endpoint.
    """
    return await handle_start_monitoring(monitoring_service, background_tasks, current_user, interval_seconds)


@router.post("/monitoring/stop")
async def stop_quality_monitoring(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Stop quality monitoring
    
    Stops continuous quality monitoring.
    Admin only endpoint.
    """
    return await handle_stop_monitoring(monitoring_service, current_user)


@router.get("/health")
async def quality_service_health() -> QualityServiceHealth:
    """
    Check quality service health
    
    Returns the health status of all quality services.
    """
    return handle_service_health(quality_gate_service, monitoring_service, fallback_service)



"""Quality Routes Request Handlers and Business Logic

This module provides request handlers and business logic for quality routes.
Each function is ≤8 lines as per architectural requirements.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, UTC
from fastapi import HTTPException, BackgroundTasks

from app.logging_config import central_logger
from app.services.quality_gate_service import QualityGateService
from app.services.quality_monitoring_service import QualityMonitoringService
from app.schemas.quality_types import (
    User, QualityValidationRequest, QualityDashboardData,
    QualityAlert, AlertAcknowledgement, QualityReportType,
    QualityReport, QualityStatistics, QualityServiceHealth
)
from .quality_validators import (
    map_content_type, format_validation_response, format_dashboard_data,
    _complete_dashboard_data, format_alert_list, _complete_alert_formatting,
    format_acknowledgement_response, format_quality_report, format_quality_statistics,
    _complete_statistics_formatting, format_service_health, format_error_health,
    apply_alert_filters, prepare_user_context
)
from .quality_validation_utils import (
    build_monitoring_response, build_stop_monitoring_response
)

logger = central_logger.get_logger(__name__)


async def handle_dashboard_request(monitoring_service: QualityMonitoringService, user: User, period_hours: int) -> QualityDashboardData:
    """Handle dashboard data request."""
    try:
        dashboard_data = await monitoring_service.get_dashboard_data()
        formatted_data = format_dashboard_data(dashboard_data, user, period_hours)
        return _complete_dashboard_data(formatted_data)
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")


async def handle_content_validation(quality_gate_service: QualityGateService, request: QualityValidationRequest, user: User):
    """Handle content validation request."""
    try:
        content_type = map_content_type(request.content_type)
        context = prepare_user_context(request.context, user)
        result = await _validate_content_with_service(quality_gate_service, request, content_type, context)
        return format_validation_response(result, user.id)
    except Exception as e:
        logger.error(f"Error validating content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


async def _validate_content_with_service(quality_gate_service, request, content_type, context):
    """Validate content using quality gate service."""
    return await quality_gate_service.validate_content(
        content=request.content,
        content_type=content_type,
        context=context,
        strict_mode=request.strict_mode
    )


async def handle_agent_report_request(monitoring_service: QualityMonitoringService, agent_name: str, period_hours: int) -> Dict[str, Any]:
    """Handle agent quality report request."""
    try:
        report = await monitoring_service.get_agent_report(agent_name, period_hours)
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate agent report")


async def handle_alerts_request(monitoring_service: QualityMonitoringService, severity: str, acknowledged: bool, limit: int) -> List[QualityAlert]:
    """Handle quality alerts request."""
    try:
        all_alerts = list(monitoring_service.alert_history)[-limit:]
        filtered_alerts = apply_alert_filters(all_alerts, severity, acknowledged)
        formatted_alerts = format_alert_list(filtered_alerts)
        return _complete_alert_formatting(formatted_alerts, filtered_alerts)
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


async def handle_alert_acknowledgement(monitoring_service: QualityMonitoringService, request: AlertAcknowledgement, user: User):
    """Handle alert acknowledgement request."""
    try:
        success = await _process_alert_action(monitoring_service, request)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        return format_acknowledgement_response(request.alert_id, request.action, user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


async def _process_alert_action(monitoring_service: QualityMonitoringService, request: AlertAcknowledgement) -> bool:
    """Process alert action based on request type."""
    if request.action == "acknowledge":
        return await monitoring_service.acknowledge_alert(request.alert_id)
    elif request.action == "resolve":
        return await monitoring_service.resolve_alert(request.alert_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid action")


async def handle_report_generation(monitoring_service: QualityMonitoringService, report_type: QualityReportType, period_days: int, user: User) -> QualityReport:
    """Handle quality report generation request."""
    try:
        period_hours = period_days * 24
        data = await _generate_report_data(monitoring_service, report_type, period_hours, period_days)
        return format_quality_report(report_type, data, user, period_days)
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


async def _generate_report_data(monitoring_service: QualityMonitoringService, report_type: QualityReportType, period_hours: int, period_days: int) -> Dict[str, Any]:
    """Generate report data based on report type."""
    if report_type == QualityReportType.SUMMARY:
        return await monitoring_service.get_dashboard_data()
    elif report_type == QualityReportType.DETAILED:
        return await _generate_detailed_report_data(monitoring_service, period_hours, period_days)
    elif report_type == QualityReportType.TREND_ANALYSIS:
        return await _generate_trend_analysis_data(monitoring_service, period_days)
    else:
        return {"error": "Unknown report type"}


def _get_default_agent_names() -> List[str]:
    """Get list of default agent names for reporting."""
    return ["TriageSubAgent", "DataSubAgent", "OptimizationsCoreSubAgent",
            "ActionsToMeetGoalsSubAgent", "ReportingSubAgent"]

async def _collect_agent_reports(monitoring_service: QualityMonitoringService, period_hours: int) -> Dict[str, Any]:
    """Collect reports for all agents."""
    agent_reports = {}
    for agent_name in _get_default_agent_names():
        agent_reports[agent_name] = await monitoring_service.get_agent_report(agent_name, period_hours)
    return agent_reports

async def _generate_detailed_report_data(monitoring_service: QualityMonitoringService, period_hours: int, period_days: int) -> Dict[str, Any]:
    """Generate detailed report data for all agents."""
    agent_reports = await _collect_agent_reports(monitoring_service, period_hours)
    summary = await monitoring_service.get_dashboard_data()
    return {
        "summary": summary,
        "agents": agent_reports,
        "period_days": period_days
    }


async def _create_daily_trend_entry(monitoring_service: QualityMonitoringService, day_offset: int) -> Dict[str, Any]:
    """Create single daily trend entry."""
    day_start = datetime.now(UTC) - timedelta(days=day_offset+1)
    return {
        "date": day_start.date().isoformat(),
        "data": await monitoring_service.get_dashboard_data()
    }

async def _collect_trend_data(monitoring_service: QualityMonitoringService, period_days: int) -> List[Dict[str, Any]]:
    """Collect trend data for specified period."""
    trends = []
    for i in range(period_days):
        trend_entry = await _create_daily_trend_entry(monitoring_service, i)
        trends.append(trend_entry)
    return trends

async def _generate_trend_analysis_data(monitoring_service: QualityMonitoringService, period_days: int) -> Dict[str, Any]:
    """Generate trend analysis data over time."""
    trends = await _collect_trend_data(monitoring_service, period_days)
    return {"trends": trends, "period_days": period_days}


async def handle_statistics_request(quality_gate_service: QualityGateService, content_type: str) -> QualityStatistics:
    """Handle quality statistics request."""
    try:
        ct = map_content_type(content_type) if content_type else None
        stats = await quality_gate_service.get_quality_stats(ct)
        formatted_stats = format_quality_statistics(stats, content_type)
        return _complete_statistics_formatting(formatted_stats, stats, content_type)
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


async def handle_start_monitoring(monitoring_service: QualityMonitoringService, background_tasks: BackgroundTasks, user: User, interval_seconds: int) -> Dict[str, Any]:
    """Handle start monitoring request."""
    try:
        _validate_admin_access(user)
        background_tasks.add_task(monitoring_service.start_monitoring, interval_seconds=interval_seconds)
        return build_monitoring_response(interval_seconds, user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting monitoring: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start monitoring")


async def handle_stop_monitoring(monitoring_service: QualityMonitoringService, user: User) -> Dict[str, Any]:
    """Handle stop monitoring request."""
    try:
        _validate_admin_access(user)
        await monitoring_service.stop_monitoring()
        return build_stop_monitoring_response(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping monitoring: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to stop monitoring")


def _validate_admin_access(user: User) -> None:
    """Validate user has admin access."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def handle_service_health(quality_gate_service, monitoring_service, fallback_service) -> QualityServiceHealth:
    """Handle service health check request."""
    try:
        return format_service_health(quality_gate_service, monitoring_service, fallback_service)
    except Exception as e:
        logger.error(f"Error checking health: {str(e)}")
        return format_error_health(str(e))
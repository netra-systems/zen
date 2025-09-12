"""Quality Routes Request Handlers and Business Logic

This module provides request handlers and business logic for quality routes.
Each function is  <= 8 lines as per architectural requirements.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, HTTPException

from netra_backend.app.logging_config import central_logger
from netra_backend.app.routes.quality_validation_utils import (
    build_monitoring_response,
    build_stop_monitoring_response,
)
from netra_backend.app.routes.quality_validators import (
    _complete_alert_formatting,
    _complete_dashboard_data,
    _complete_statistics_formatting,
    apply_alert_filters,
    format_acknowledgement_response,
    format_alert_list,
    format_dashboard_data,
    format_error_health,
    format_quality_report,
    format_quality_statistics,
    format_service_health,
    format_validation_response,
    map_content_type,
    prepare_user_context,
)
from netra_backend.app.schemas.quality_types import (
    AlertAcknowledgement,
    QualityAlert,
    QualityDashboardData,
    QualityReport,
    QualityReportType,
    QualityServiceHealth,
    QualityStatistics,
    QualityValidationRequest,
    User,
)
from netra_backend.app.services.quality_gate_service import QualityGateService
from netra_backend.app.services.quality_monitoring_service import (
    QualityMonitoringService,
)

logger = central_logger.get_logger(__name__)


async def handle_dashboard_request(monitoring_service: QualityMonitoringService, user: User, period_hours: int) -> QualityDashboardData:
    """Handle dashboard data request."""
    try:
        dashboard_data = await monitoring_service.get_dashboard_data()
        formatted_data = format_dashboard_data(dashboard_data, user, period_hours)
        return _complete_dashboard_data(formatted_data)
    except Exception as e:
        _handle_dashboard_error(e)


async def handle_content_validation(quality_gate_service: QualityGateService, request: QualityValidationRequest, user: User):
    """Handle content validation request."""
    try:
        prepared_data = _prepare_validation_data(request, user)
        result = await _validate_content_with_service(quality_gate_service, request, prepared_data["content_type"], prepared_data["context"])
        return format_validation_response(result, user.id)
    except Exception as e:
        _handle_validation_error(e)


def _prepare_validation_data(request: QualityValidationRequest, user: User) -> Dict[str, Any]:
    """Prepare validation data from request."""
    content_type = map_content_type(request.content_type)
    context = prepare_user_context(request.context, user)
    return {"content_type": content_type, "context": context}


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
        return await _process_agent_report_request(monitoring_service, agent_name, period_hours)
    except HTTPException:
        raise
    except Exception as e:
        _handle_agent_report_error(e)


async def _process_agent_report_request(monitoring_service: QualityMonitoringService, agent_name: str, period_hours: int) -> Dict[str, Any]:
    """Process agent report request and validate result."""
    report = await _fetch_agent_report(monitoring_service, agent_name, period_hours)
    return _validate_agent_report(report)


async def handle_alerts_request(monitoring_service: QualityMonitoringService, severity: str, acknowledged: bool, limit: int) -> List[QualityAlert]:
    """Handle quality alerts request."""
    try:
        all_alerts = _get_recent_alerts(monitoring_service, limit)
        filtered_alerts = apply_alert_filters(all_alerts, severity, acknowledged)
        return _format_and_complete_alerts(filtered_alerts)
    except Exception as e:
        _handle_alerts_error(e)


async def handle_alert_acknowledgement(monitoring_service: QualityMonitoringService, request: AlertAcknowledgement, user: User):
    """Handle alert acknowledgement request."""
    try:
        return await _process_acknowledgement_request(monitoring_service, request, user)
    except HTTPException:
        raise
    except Exception as e:
        _handle_acknowledgement_error(e)


async def _process_acknowledgement_request(monitoring_service: QualityMonitoringService, request: AlertAcknowledgement, user: User):
    """Process alert acknowledgement request."""
    success = await _process_alert_action(monitoring_service, request)
    return _build_acknowledgement_result(success, request, user)


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
        _handle_report_generation_error(e)


async def _generate_report_data(monitoring_service: QualityMonitoringService, report_type: QualityReportType, period_hours: int, period_days: int) -> Dict[str, Any]:
    """Generate report data based on report type."""
    report_handlers = _get_report_type_handlers()
    handler = report_handlers.get(report_type)
    if handler:
        return await handler(monitoring_service, period_hours, period_days)
    return _get_unknown_report_type_error()


def _get_report_type_handlers():
    """Get report type handler mapping."""
    return {
        QualityReportType.SUMMARY: _handle_summary_report,
        QualityReportType.DETAILED: _handle_detailed_report,
        QualityReportType.TREND_ANALYSIS: _handle_trend_analysis_report
    }


async def _handle_summary_report(monitoring_service, period_hours, period_days):
    """Handle summary report generation."""
    return await _generate_summary_report_data(monitoring_service)


async def _handle_detailed_report(monitoring_service, period_hours, period_days):
    """Handle detailed report generation."""
    return await _generate_detailed_report_data(monitoring_service, period_hours, period_days)


async def _handle_trend_analysis_report(monitoring_service, period_hours, period_days):
    """Handle trend analysis report generation."""
    return await _generate_trend_analysis_data(monitoring_service, period_days)


async def _generate_summary_report_data(monitoring_service: QualityMonitoringService) -> Dict[str, Any]:
    """Generate summary report data."""
    return await monitoring_service.get_dashboard_data()


def _get_unknown_report_type_error() -> Dict[str, str]:
    """Get unknown report type error response."""
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
    return _build_detailed_report_dict(summary, agent_reports, period_days)


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
        ct = _map_content_type_for_stats(content_type)
        stats = await quality_gate_service.get_quality_stats(ct)
        return _format_complete_statistics(stats, content_type)
    except Exception as e:
        _handle_statistics_error(e)


async def handle_start_monitoring(monitoring_service: QualityMonitoringService, background_tasks: BackgroundTasks, user: User, interval_seconds: int) -> Dict[str, Any]:
    """Handle start monitoring request."""
    try:
        return await _process_start_monitoring(monitoring_service, background_tasks, user, interval_seconds)
    except HTTPException:
        raise
    except Exception as e:
        _handle_start_monitoring_error(e)


async def _process_start_monitoring(monitoring_service: QualityMonitoringService, background_tasks: BackgroundTasks, user: User, interval_seconds: int) -> Dict[str, Any]:
    """Process start monitoring request with validation."""
    _validate_admin_access(user)
    _add_monitoring_task(background_tasks, monitoring_service, interval_seconds)
    return build_monitoring_response(interval_seconds, user)


async def handle_stop_monitoring(monitoring_service: QualityMonitoringService, user: User) -> Dict[str, Any]:
    """Handle stop monitoring request."""
    try:
        return await _process_stop_monitoring(monitoring_service, user)
    except HTTPException:
        raise
    except Exception as e:
        _handle_stop_monitoring_error(e)


async def _process_stop_monitoring(monitoring_service: QualityMonitoringService, user: User) -> Dict[str, Any]:
    """Process stop monitoring request with validation."""
    _validate_admin_access(user)
    await _stop_monitoring_service(monitoring_service)
    return build_stop_monitoring_response(user)


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


def _handle_dashboard_error(e: Exception) -> None:
    """Handle dashboard request error."""
    logger.error(f"Error getting dashboard data: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")


def _handle_validation_error(e: Exception) -> None:
    """Handle validation request error."""
    logger.error(f"Error validating content: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


async def _fetch_agent_report(monitoring_service: QualityMonitoringService, agent_name: str, period_hours: int) -> Dict[str, Any]:
    """Fetch agent report from monitoring service."""
    return await monitoring_service.get_agent_report(agent_name, period_hours)


def _validate_agent_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Validate agent report result."""
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    return report


def _handle_agent_report_error(e: Exception) -> None:
    """Handle agent report request error."""
    logger.error(f"Error getting agent report: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to generate agent report")


def _get_recent_alerts(monitoring_service: QualityMonitoringService, limit: int) -> List[Any]:
    """Get recent alerts from monitoring service."""
    return list(monitoring_service.alert_history)[-limit:]


def _format_and_complete_alerts(filtered_alerts: List[Any]) -> List[QualityAlert]:
    """Format and complete alert data."""
    formatted_alerts = format_alert_list(filtered_alerts)
    return _complete_alert_formatting(formatted_alerts, filtered_alerts)


def _handle_alerts_error(e: Exception) -> None:
    """Handle alerts request error."""
    logger.error(f"Error getting alerts: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


def _build_acknowledgement_result(success: bool, request: AlertAcknowledgement, user: User):
    """Build acknowledgement result response."""
    _validate_alert_success(success)
    return format_acknowledgement_response(request.alert_id, request.action, user)


def _validate_alert_success(success: bool) -> None:
    """Validate alert acknowledgement success."""
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")


def _handle_acknowledgement_error(e: Exception) -> None:
    """Handle alert acknowledgement error."""
    logger.error(f"Error acknowledging alert: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


def _handle_report_generation_error(e: Exception) -> None:
    """Handle report generation error."""
    logger.error(f"Error generating report: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to generate report")


def _build_detailed_report_dict(summary: Dict[str, Any], agent_reports: Dict[str, Any], period_days: int) -> Dict[str, Any]:
    """Build detailed report dictionary."""
    return {
        "summary": summary,
        "agents": agent_reports,
        "period_days": period_days
    }


def _map_content_type_for_stats(content_type: str):
    """Map content type for statistics request."""
    return map_content_type(content_type) if content_type else None


def _format_complete_statistics(stats: Dict[str, Any], content_type: str) -> QualityStatistics:
    """Format and complete statistics response."""
    formatted_stats = format_quality_statistics(stats, content_type)
    return _complete_statistics_formatting(formatted_stats, stats, content_type)


def _handle_statistics_error(e: Exception) -> None:
    """Handle statistics request error."""
    logger.error(f"Error getting statistics: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


def _add_monitoring_task(background_tasks: BackgroundTasks, monitoring_service: QualityMonitoringService, interval_seconds: int) -> None:
    """Add monitoring task to background tasks."""
    background_tasks.add_task(monitoring_service.start_monitoring, interval_seconds=interval_seconds)


def _handle_start_monitoring_error(e: Exception) -> None:
    """Handle start monitoring error."""
    logger.error(f"Error starting monitoring: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to start monitoring")


async def _stop_monitoring_service(monitoring_service: QualityMonitoringService) -> None:
    """Stop monitoring service."""
    await monitoring_service.stop_monitoring()


def _handle_stop_monitoring_error(e: Exception) -> None:
    """Handle stop monitoring error."""
    logger.error(f"Error stopping monitoring: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to stop monitoring")
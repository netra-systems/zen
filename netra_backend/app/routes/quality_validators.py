"""Quality Routes Input Validation and Response Formatting

This module provides validation and formatting utilities for quality routes.
Each function is  <= 8 lines as per architectural requirements.
"""

from datetime import UTC, datetime
from typing import Any, Dict, List

from netra_backend.app.routes.quality_validation_utils import (
    _build_alert_basic_fields,
    _build_alert_detail_fields,
    _build_analysis_metrics,
    _build_basic_statistics,
    _build_core_metrics,
    _build_dashboard_primary_data,
    _build_dashboard_secondary_data,
    _build_detail_statistics,
    _build_health_statistics,
    _build_quality_metrics,
    _build_score_metrics,
    _build_services_status,
    _get_content_mapping_part1,
    _get_content_mapping_part2,
    build_monitoring_response,
    build_stop_monitoring_response,
)
from netra_backend.app.schemas.quality_types import (
    AlertAcknowledgementResponse,
    QualityAlert,
    QualityDashboardData,
    QualityReport,
    QualityServiceHealth,
    QualityStatistics,
    QualityValidationResponse,
    User,
)
from netra_backend.app.services.quality_gate_service import ContentType


def map_content_type(content_type_str: str) -> ContentType:
    """Map string content type to ContentType enum."""
    content_type_map = _get_content_type_mapping()
    return content_type_map.get(content_type_str, ContentType.GENERAL)


def _get_content_type_mapping() -> Dict[str, ContentType]:
    """Get content type mapping dictionary."""
    mapping_part1 = _get_content_mapping_part1()
    mapping_part2 = _get_content_mapping_part2()
    mapping_part1.update(mapping_part2)
    return mapping_part1


def format_validation_response(result, user_id: str) -> QualityValidationResponse:
    """Format validation result into typed response."""
    metrics = _build_metrics_dict(result.metrics)
    validation_id = f"val_{int(datetime.now(UTC).timestamp())}"
    timestamp = datetime.now(UTC)
    return _build_validation_response(result, metrics, validation_id, timestamp)


def _build_metrics_dict(metrics) -> Dict[str, Any]:
    """Build metrics dictionary from validation result."""
    base_metrics = _build_base_metrics(metrics)
    extended_metrics = _extend_metrics_dict(base_metrics, metrics)
    return extended_metrics


def _build_base_metrics(metrics) -> Dict[str, Any]:
    """Build base metrics dictionary."""
    core_metrics = _build_core_metrics(metrics)
    score_metrics = _build_score_metrics(metrics)
    core_metrics.update(score_metrics)
    return core_metrics


def _extend_metrics_dict(metrics_dict: Dict[str, Any], metrics) -> Dict[str, Any]:
    """Extend metrics dictionary with additional fields."""
    additional_metrics = _build_additional_metrics(metrics)
    metrics_dict.update(additional_metrics)
    return metrics_dict


def _build_additional_metrics(metrics) -> Dict[str, Any]:
    """Build additional metrics dictionary."""
    analysis_metrics = _build_analysis_metrics(metrics)
    quality_metrics = _build_quality_metrics(metrics)
    analysis_metrics.update(quality_metrics)
    return analysis_metrics


def format_dashboard_data(dashboard_data: Dict[str, Any], user: User, period_hours: int) -> QualityDashboardData:
    """Format dashboard data into typed response."""
    base_data = _build_dashboard_base_data(dashboard_data, user, period_hours)
    extended_data = _build_dashboard_extended_data(dashboard_data, base_data)
    return extended_data


def _build_dashboard_base_data(dashboard_data: Dict[str, Any], user: User, period_hours: int) -> QualityDashboardData:
    """Build base dashboard data."""
    primary_data = _build_dashboard_primary_data(dashboard_data)
    secondary_data = _build_dashboard_secondary_data(dashboard_data, user, period_hours)
    primary_data.update(secondary_data)
    return QualityDashboardData(**primary_data)


def _build_dashboard_extended_data(dashboard_data: Dict[str, Any], base_data: QualityDashboardData) -> QualityDashboardData:
    """Build extended dashboard data."""
    return base_data


def _complete_dashboard_data(dashboard_data: QualityDashboardData) -> QualityDashboardData:
    """Complete dashboard data with timestamp."""
    dashboard_data.generated_at = datetime.now(UTC)
    return dashboard_data


def format_alert_list(all_alerts: List[Any]) -> List[QualityAlert]:
    """Format alert list into typed responses."""
    return [_format_single_alert(alert) for alert in all_alerts]


def _format_single_alert(alert) -> QualityAlert:
    """Format single alert into typed response."""
    basic_fields = _build_alert_basic_fields(alert)
    detail_fields = _build_alert_detail_fields(alert)
    basic_fields.update(detail_fields)
    return QualityAlert(**basic_fields)


def _complete_alert_formatting(alerts: List[QualityAlert], all_alerts: List[Any]) -> List[QualityAlert]:
    """Complete alert formatting with additional fields."""
    for i, alert in enumerate(alerts):
        alert.details = all_alerts[i].details
        alert.acknowledged = all_alerts[i].acknowledged
        alert.resolved = all_alerts[i].resolved
    return alerts


def format_acknowledgement_response(alert_id: str, action: str, user: User) -> AlertAcknowledgementResponse:
    """Format alert acknowledgement response."""
    timestamp = datetime.now(UTC)
    return _build_acknowledgement_response(alert_id, action, user.id, timestamp)


def format_quality_report(report_type, data: Dict[str, Any], user: User, period_days: int) -> QualityReport:
    """Format quality report response."""
    generated_at = datetime.now(UTC)
    return _build_quality_report(report_type, data, user.id, period_days, generated_at)


def format_quality_statistics(stats: Dict[str, Any], content_type: str = None) -> QualityStatistics:
    """Format quality statistics response."""
    base_stats = _build_base_statistics(stats)
    return _complete_statistics_formatting(base_stats, stats, content_type)


def _build_base_statistics(stats: Dict[str, Any]) -> QualityStatistics:
    """Build base statistics object."""
    basic_stats = _build_basic_statistics(stats)
    detail_stats = _build_detail_statistics(stats)
    basic_stats.update(detail_stats)
    return QualityStatistics(**basic_stats)


def _complete_statistics_formatting(stats: QualityStatistics, full_stats: Dict[str, Any], content_type: str = None) -> QualityStatistics:
    """Complete statistics formatting with remaining fields."""
    stats.agent_performance = full_stats.get("agent_performance", {})
    stats.timestamp = datetime.now(UTC)
    stats.content_type_filter = content_type
    return stats


def format_service_health(quality_gate_service, monitoring_service, fallback_service) -> QualityServiceHealth:
    """Format service health response."""
    return QualityServiceHealth(
        status="healthy",
        services=_build_services_status(quality_gate_service, monitoring_service, fallback_service),
        statistics=_build_health_statistics(quality_gate_service, monitoring_service),
        timestamp=datetime.now(UTC)
    )


def format_error_health(error_msg: str) -> QualityServiceHealth:
    """Format error health response."""
    timestamp = datetime.now(UTC)
    return _build_error_health_response(error_msg, timestamp)


def apply_alert_filters(all_alerts: List[Any], severity: str = None, acknowledged: bool = None) -> List[Any]:
    """Apply severity and acknowledgement filters to alerts."""
    if severity:
        all_alerts = [a for a in all_alerts if a.severity.value == severity]
    if acknowledged is not None:
        all_alerts = [a for a in all_alerts if a.acknowledged == acknowledged]
    return all_alerts


def prepare_user_context(context: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Prepare user context for validation."""
    if context is None:
        context = {}
    context["user_id"] = user.id
    return context


def _build_validation_response(result, metrics: Dict[str, Any], validation_id: str, timestamp) -> QualityValidationResponse:
    """Build validation response object."""
    response_params = _prepare_validation_response_params(result, metrics, validation_id, timestamp)
    return QualityValidationResponse(**response_params)


def _prepare_validation_response_params(result, metrics: Dict[str, Any], validation_id: str, timestamp) -> Dict[str, Any]:
    """Prepare validation response parameters."""
    base_params = _get_validation_base_params(result, metrics)
    extra_params = _get_validation_extra_params(result, validation_id, timestamp)
    base_params.update(extra_params)
    return base_params


def _get_validation_base_params(result, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Get base validation parameters."""
    return {"passed": result.passed, "metrics": metrics}


def _get_validation_extra_params(result, validation_id: str, timestamp) -> Dict[str, Any]:
    """Get extra validation parameters."""
    return {
        "retry_suggested": result.retry_suggested,
        "retry_adjustments": result.retry_prompt_adjustments,
        "validation_id": validation_id,
        "timestamp": timestamp
    }


def _build_acknowledgement_response(alert_id: str, action: str, user_id: str, timestamp) -> AlertAcknowledgementResponse:
    """Build acknowledgement response object."""
    response_params = _prepare_acknowledgement_params(alert_id, action, user_id, timestamp)
    return AlertAcknowledgementResponse(**response_params)


def _prepare_acknowledgement_params(alert_id: str, action: str, user_id: str, timestamp) -> Dict[str, Any]:
    """Prepare acknowledgement response parameters."""
    base_params = _get_acknowledgement_base_params(alert_id, action)
    extra_params = _get_acknowledgement_extra_params(user_id, timestamp)
    base_params.update(extra_params)
    return base_params


def _get_acknowledgement_base_params(alert_id: str, action: str) -> Dict[str, Any]:
    """Get base acknowledgement parameters."""
    return {"success": True, "alert_id": alert_id, "action": action}


def _get_acknowledgement_extra_params(user_id: str, timestamp) -> Dict[str, Any]:
    """Get extra acknowledgement parameters."""
    return {"user_id": user_id, "timestamp": timestamp}


def _build_quality_report(report_type, data: Dict[str, Any], user_id: str, period_days: int, generated_at) -> QualityReport:
    """Build quality report object."""
    report_params = _prepare_quality_report_params(report_type, data, user_id, period_days, generated_at)
    return QualityReport(**report_params)


def _prepare_quality_report_params(report_type, data: Dict[str, Any], user_id: str, period_days: int, generated_at) -> Dict[str, Any]:
    """Prepare quality report parameters."""
    base_params = _get_report_base_params(report_type, generated_at)
    extra_params = _get_report_extra_params(user_id, period_days, data)
    base_params.update(extra_params)
    return base_params


def _get_report_base_params(report_type, generated_at) -> Dict[str, Any]:
    """Get base report parameters."""
    return {"report_type": report_type, "generated_at": generated_at}


def _get_report_extra_params(user_id: str, period_days: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Get extra report parameters."""
    return {"generated_by": user_id, "period_days": period_days, "data": data}


def _build_error_health_response(error_msg: str, timestamp) -> QualityServiceHealth:
    """Build error health response object."""
    health_params = _prepare_error_health_params(error_msg, timestamp)
    return QualityServiceHealth(**health_params)


def _prepare_error_health_params(error_msg: str, timestamp) -> Dict[str, Any]:
    """Prepare error health response parameters."""
    base_params = _get_error_health_base_params(timestamp)
    error_params = _get_error_health_error_params(error_msg)
    base_params.update(error_params)
    return base_params


def _get_error_health_base_params(timestamp) -> Dict[str, Any]:
    """Get base error health parameters."""
    return {"status": "unhealthy", "services": {}, "statistics": {}, "timestamp": timestamp}


def _get_error_health_error_params(error_msg: str) -> Dict[str, Any]:
    """Get error health error parameters."""
    return {"error": error_msg}
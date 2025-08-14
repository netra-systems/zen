"""Quality Routes Input Validation and Response Formatting

This module provides validation and formatting utilities for quality routes.
Each function is ≤8 lines as per architectural requirements.
"""

from typing import Dict, Any, List
from datetime import datetime, UTC
from app.services.quality_gate_service import ContentType
from app.schemas.quality_types import (
    QualityValidationResponse, QualityAlert, QualityDashboardData,
    QualityStatistics, AlertAcknowledgementResponse, QualityReport,
    QualityServiceHealth, User
)


def map_content_type(content_type_str: str) -> ContentType:
    """Map string content type to ContentType enum."""
    content_type_map = {
        "optimization": ContentType.OPTIMIZATION,
        "data_analysis": ContentType.DATA_ANALYSIS,
        "action_plan": ContentType.ACTION_PLAN,
        "report": ContentType.REPORT,
        "triage": ContentType.TRIAGE,
        "error": ContentType.ERROR_MESSAGE,
        "general": ContentType.GENERAL
    }
    return content_type_map.get(content_type_str, ContentType.GENERAL)


def format_validation_response(result, user_id: str) -> QualityValidationResponse:
    """Format validation result into typed response."""
    return QualityValidationResponse(
        passed=result.passed,
        metrics=_build_metrics_dict(result.metrics),
        retry_suggested=result.retry_suggested,
        retry_adjustments=result.retry_prompt_adjustments,
        validation_id=f"val_{int(datetime.now(UTC).timestamp())}",
        timestamp=datetime.now(UTC)
    )


def _build_metrics_dict(metrics) -> Dict[str, Any]:
    """Build metrics dictionary from validation result."""
    return {
        "overall_score": metrics.overall_score,
        "quality_level": metrics.quality_level.value,
        "specificity_score": metrics.specificity_score,
        "actionability_score": metrics.actionability_score,
        "quantification_score": metrics.quantification_score,
        "relevance_score": metrics.relevance_score,
        "completeness_score": metrics.completeness_score,
        "novelty_score": metrics.novelty_score
    }


def _extend_metrics_dict(metrics_dict: Dict[str, Any], metrics) -> Dict[str, Any]:
    """Extend metrics dictionary with additional fields."""
    metrics_dict.update({
        "clarity_score": metrics.clarity_score,
        "word_count": metrics.word_count,
        "generic_phrase_count": metrics.generic_phrase_count,
        "circular_reasoning_detected": metrics.circular_reasoning_detected,
        "hallucination_risk": metrics.hallucination_risk,
        "redundancy_ratio": metrics.redundancy_ratio,
        "issues": metrics.issues,
        "suggestions": metrics.suggestions
    })
    return metrics_dict


def format_dashboard_data(dashboard_data: Dict[str, Any], user: User, period_hours: int) -> QualityDashboardData:
    """Format dashboard data into typed response."""
    return QualityDashboardData(
        summary=dashboard_data.get("summary", {}),
        recent_alerts=[QualityAlert(**alert) for alert in dashboard_data.get("recent_alerts", [])],
        agent_profiles=dashboard_data.get("agent_profiles", {}),
        quality_trends=dashboard_data.get("quality_trends", {}),
        top_issues=dashboard_data.get("top_issues", []),
        system_health=dashboard_data.get("system_health", {}),
        period_hours=period_hours,
        user_id=user.id
    )


def _complete_dashboard_data(dashboard_data: QualityDashboardData) -> QualityDashboardData:
    """Complete dashboard data with timestamp."""
    dashboard_data.generated_at = datetime.now(UTC)
    return dashboard_data


def format_alert_list(all_alerts: List[Any]) -> List[QualityAlert]:
    """Format alert list into typed responses."""
    return [
        QualityAlert(
            id=alert.id,
            timestamp=alert.timestamp,
            severity=alert.severity,
            metric_type=alert.metric_type,
            agent=alert.agent,
            message=alert.message,
            current_value=alert.current_value,
            threshold=alert.threshold
        )
        for alert in all_alerts
    ]


def _complete_alert_formatting(alerts: List[QualityAlert], all_alerts: List[Any]) -> List[QualityAlert]:
    """Complete alert formatting with additional fields."""
    for i, alert in enumerate(alerts):
        alert.details = all_alerts[i].details
        alert.acknowledged = all_alerts[i].acknowledged
        alert.resolved = all_alerts[i].resolved
    return alerts


def format_acknowledgement_response(alert_id: str, action: str, user: User) -> AlertAcknowledgementResponse:
    """Format alert acknowledgement response."""
    return AlertAcknowledgementResponse(
        success=True,
        alert_id=alert_id,
        action=action,
        user_id=user.id,
        timestamp=datetime.now(UTC)
    )


def format_quality_report(report_type, data: Dict[str, Any], user: User, period_days: int) -> QualityReport:
    """Format quality report response."""
    return QualityReport(
        report_type=report_type,
        generated_at=datetime.now(UTC),
        generated_by=user.id,
        period_days=period_days,
        data=data
    )


def format_quality_statistics(stats: Dict[str, Any], content_type: str = None) -> QualityStatistics:
    """Format quality statistics response."""
    return QualityStatistics(
        total_validations=stats.get("total_validations", 0),
        average_score=stats.get("average_score", 0.0),
        median_score=stats.get("median_score", 0.0),
        score_distribution=stats.get("score_distribution", {}),
        pass_rate=stats.get("pass_rate", 0.0),
        top_issues=stats.get("top_issues", []),
        improvement_areas=stats.get("improvement_areas", []),
        content_type_breakdown=stats.get("content_type_breakdown", {})
    )


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


def _build_services_status(quality_gate_service, monitoring_service, fallback_service) -> Dict[str, str]:
    """Build services status dictionary."""
    return {
        "quality_gate": "active" if quality_gate_service else "inactive",
        "monitoring": "active" if monitoring_service.monitoring_active else "inactive",
        "fallback": "active" if fallback_service else "inactive"
    }


def _build_health_statistics(quality_gate_service, monitoring_service) -> Dict[str, int]:
    """Build health statistics dictionary."""
    return {
        "total_validations": len(quality_gate_service.validation_cache) if quality_gate_service else 0,
        "active_alerts": len(monitoring_service.active_alerts) if monitoring_service else 0,
        "monitored_agents": len(monitoring_service.agent_profiles) if monitoring_service else 0
    }


def format_error_health(error_msg: str) -> QualityServiceHealth:
    """Format error health response."""
    return QualityServiceHealth(
        status="unhealthy",
        services={},
        statistics={},
        timestamp=datetime.now(UTC),
        error=error_msg
    )


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


def build_monitoring_response(interval_seconds: int, user: User) -> Dict[str, Any]:
    """Build monitoring start response."""
    return {
        "status": "started",
        "interval_seconds": interval_seconds,
        "started_by": user.id,
        "timestamp": datetime.now(UTC).isoformat()
    }


def build_stop_monitoring_response(user: User) -> Dict[str, Any]:
    """Build monitoring stop response."""
    return {
        "status": "stopped",
        "stopped_by": user.id,
        "timestamp": datetime.now(UTC).isoformat()
    }
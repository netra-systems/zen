"""Quality Validation Utilities

This module provides utility functions for data building and formatting.
Each function is  <= 8 lines as per architectural requirements.
"""

from datetime import UTC, datetime
from typing import Any, Dict

from netra_backend.app.schemas.quality_types import QualityAlert, User
from netra_backend.app.services.quality_gate_service import ContentType


def _get_content_mapping_part1() -> Dict[str, ContentType]:
    """Get first part of content type mapping."""
    return {
        "optimization": ContentType.OPTIMIZATION,
        "data_analysis": ContentType.DATA_ANALYSIS,
        "action_plan": ContentType.ACTION_PLAN,
        "report": ContentType.REPORT
    }


def _get_content_mapping_part2() -> Dict[str, ContentType]:
    """Get second part of content type mapping."""
    return {
        "triage": ContentType.TRIAGE,
        "error": ContentType.ERROR_MESSAGE,
        "general": ContentType.GENERAL
    }


def _build_core_metrics(metrics) -> Dict[str, Any]:
    """Build core metrics."""
    return {
        "overall_score": metrics.overall_score,
        "quality_level": metrics.quality_level.value,
        "specificity_score": metrics.specificity_score,
        "actionability_score": metrics.actionability_score
    }


def _build_score_metrics(metrics) -> Dict[str, Any]:
    """Build score metrics."""
    return {
        "quantification_score": metrics.quantification_score,
        "relevance_score": metrics.relevance_score,
        "completeness_score": metrics.completeness_score,
        "novelty_score": metrics.novelty_score
    }


def _build_analysis_metrics(metrics) -> Dict[str, Any]:
    """Build analysis metrics."""
    return {
        "clarity_score": metrics.clarity_score,
        "word_count": metrics.word_count,
        "generic_phrase_count": metrics.generic_phrase_count,
        "circular_reasoning_detected": metrics.circular_reasoning_detected
    }


def _build_quality_metrics(metrics) -> Dict[str, Any]:
    """Build quality metrics."""
    return {
        "hallucination_risk": metrics.hallucination_risk,
        "redundancy_ratio": metrics.redundancy_ratio,
        "issues": metrics.issues,
        "suggestions": metrics.suggestions
    }


def _build_dashboard_primary_data(dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build primary dashboard data."""
    return {
        "summary": dashboard_data.get("summary", {}),
        "recent_alerts": [QualityAlert(**alert) for alert in dashboard_data.get("recent_alerts", [])],
        "agent_profiles": dashboard_data.get("agent_profiles", {}),
        "quality_trends": dashboard_data.get("quality_trends", {})
    }


def _build_dashboard_secondary_data(dashboard_data: Dict[str, Any], user: User, period_hours: int) -> Dict[str, Any]:
    """Build secondary dashboard data."""
    return {
        "top_issues": dashboard_data.get("top_issues", []),
        "system_health": dashboard_data.get("system_health", {}),
        "period_hours": period_hours,
        "user_id": user.id
    }


def _build_alert_basic_fields(alert) -> Dict[str, Any]:
    """Build basic alert fields."""
    return {
        "id": alert.id,
        "timestamp": alert.timestamp,
        "severity": alert.severity,
        "metric_type": alert.metric_type
    }


def _build_alert_detail_fields(alert) -> Dict[str, Any]:
    """Build detail alert fields."""
    return {
        "agent": alert.agent,
        "message": alert.message,
        "current_value": alert.current_value,
        "threshold": alert.threshold
    }


def _build_basic_statistics(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Build basic statistics."""
    return {
        "total_validations": stats.get("total_validations", 0),
        "average_score": stats.get("average_score", 0.0),
        "median_score": stats.get("median_score", 0.0),
        "score_distribution": stats.get("score_distribution", {})
    }


def _build_detail_statistics(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Build detail statistics."""
    return {
        "pass_rate": stats.get("pass_rate", 0.0),
        "top_issues": stats.get("top_issues", []),
        "improvement_areas": stats.get("improvement_areas", []),
        "content_type_breakdown": stats.get("content_type_breakdown", {})
    }


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
        "active_alerts": len(monitoring_service.alert_manager.active_alerts) if monitoring_service else 0,
        "monitored_agents": len(monitoring_service.trend_analyzer.agent_profiles) if monitoring_service else 0
    }


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
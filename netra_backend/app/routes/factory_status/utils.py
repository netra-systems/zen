"""
Factory Status Utilities
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any
from netra_backend.app.services.factory_status.report_builder import FactoryStatusReport
from netra_backend.app.services.apex_optimizer_agent.models import ReportResponse


def _filter_by_start_date(reports: List, start_date: datetime) -> List:
    """Filter reports by start date."""
    if start_date:
        return [r for r in reports if r.generated_at >= start_date]
    return reports


def filter_reports_by_date_range(
    reports: List, start_date: datetime, end_date: datetime
) -> List:
    """Filter reports by date range if provided."""
    reports = _filter_by_start_date(reports, start_date)
    if end_date:
        reports = [r for r in reports if r.generated_at <= end_date]
    return reports


def sort_and_limit_reports(reports: List, limit: int) -> List:
    """Sort reports by date and apply limit."""
    return sorted(reports, key=lambda r: r.generated_at, reverse=True)[:limit]


def convert_reports_to_responses(reports: List) -> List[ReportResponse]:
    """Convert reports to response format."""
    return [convert_report_to_response(r) for r in reports]


def extract_core_report_fields(report: FactoryStatusReport) -> Dict[str, Any]:
    """Extract core report fields."""
    return {
        "report_id": report.report_id,
        "generated_at": report.generated_at,
        "executive_summary": serialize_summary(report.executive_summary)
    }


def _extract_performance_metrics(report: FactoryStatusReport) -> Dict[str, Any]:
    """Extract performance-related metrics."""
    return {
        "velocity_metrics": report.velocity_metrics,
        "impact_metrics": report.impact_metrics,
        "quality_metrics": report.quality_metrics
    }


def extract_metrics_fields(report: FactoryStatusReport) -> Dict[str, Any]:
    """Extract metrics fields."""
    perf_metrics = _extract_performance_metrics(report)
    return {
        **perf_metrics, "business_value_metrics": report.business_value_metrics,
        "branch_metrics": report.branch_metrics, "feature_progress": report.feature_progress,
        "recommendations": report.recommendations
    }


def convert_report_to_response(report: FactoryStatusReport) -> ReportResponse:
    """Convert report to response model."""
    core_fields = extract_core_report_fields(report)
    metrics_fields = extract_metrics_fields(report)
    return ReportResponse(**{**core_fields, **metrics_fields})


def _extract_summary_scores(summary) -> Dict[str, Any]:
    """Extract summary scores."""
    return {
        "productivity_score": summary.productivity_score,
        "business_value_score": summary.business_value_score
    }


def serialize_summary(summary) -> Dict[str, Any]:
    """Serialize executive summary."""
    scores = _extract_summary_scores(summary)
    return {
        "timestamp": summary.timestamp.isoformat(), **scores,
        "key_highlights": summary.key_highlights, "action_items": summary.action_items,
        "overall_status": summary.overall_status
    }


def calculate_trend_halves(daily_data: List[Dict]) -> tuple[int, int]:
    """Calculate first and second half commit sums."""
    midpoint = len(daily_data) // 2
    first_half = sum(d["commits"] for d in daily_data[:midpoint])
    second_half = sum(d["commits"] for d in daily_data[midpoint:])
    return first_half, second_half


def determine_trend_direction(first_half: int, second_half: int) -> str:
    """Determine trend direction from half comparisons."""
    if second_half > first_half * 1.1:
        return "increasing"
    elif second_half < first_half * 0.9:
        return "decreasing"
    return "stable"


def calculate_trend(daily_data: List[Dict]) -> str:
    """Calculate overall trend from daily data."""
    if len(daily_data) < 2:
        return "stable"
    first_half, second_half = calculate_trend_halves(daily_data)
    return determine_trend_direction(first_half, second_half)
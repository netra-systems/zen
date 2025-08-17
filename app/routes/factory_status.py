"""API routes for AI Factory Status Report.

Provides endpoints for accessing factory status reports and metrics.
Module follows 300-line limit with 8-line function limit.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
import json

from app.services.factory_status.report_builder import ReportBuilder, FactoryStatusReport
# Compliance integration available but not used in current routes
# from app.services.factory_status.factory_status_integration import (
#     init_compliance_api, ComplianceAPIHandler
# )
from app.core.exceptions import NetraException
from app.auth_integration.auth import get_current_user


router = APIRouter(
    prefix="/api/factory-status",
    tags=["factory-status"]
)


class ReportResponse(BaseModel):
    """Response model for factory status report."""
    report_id: str
    generated_at: datetime
    executive_summary: Dict[str, Any]
    velocity_metrics: Dict[str, Any]
    impact_metrics: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    business_value_metrics: Dict[str, Any]
    branch_metrics: Dict[str, Any]
    feature_progress: Dict[str, Any]
    recommendations: List[str]


class MetricResponse(BaseModel):
    """Response model for individual metrics."""
    metric_name: str
    value: Any
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class GenerateReportRequest(BaseModel):
    """Request model for report generation."""
    hours: int = Field(default=24, ge=1, le=720, description="Hours to analyze")
    include_business_value: bool = Field(default=True)
    include_recommendations: bool = Field(default=True)


class HistoryRequest(BaseModel):
    """Request model for historical reports."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    interval: str = Field(default="daily", pattern="^(hourly|daily|weekly)$")
    limit: int = Field(default=10, ge=1, le=100)


# In-memory cache for demo (replace with Redis in production)
_report_cache: Dict[str, FactoryStatusReport] = {}
_latest_report_id: Optional[str] = None
# _compliance_handler: Optional[ComplianceAPIHandler] = None  # Not used currently


@router.get("/latest", response_model=ReportResponse)
async def get_latest_report(
    current_user: Dict = Depends(get_current_user)
) -> ReportResponse:
    """Get the latest factory status report."""
    if not _latest_report_id or _latest_report_id not in _report_cache:
        # Generate new report if none exists
        report = await _generate_new_report(24)
    else:
        report = _report_cache[_latest_report_id]
    
    return _convert_report_to_response(report)


def _filter_reports_by_date_range(reports: List, start_date: Optional[datetime], end_date: Optional[datetime]) -> List:
    """Filter reports by date range if provided."""
    if start_date:
        reports = [r for r in reports if r.generated_at >= start_date]
    if end_date:
        reports = [r for r in reports if r.generated_at <= end_date]
    return reports

def _sort_and_limit_reports(reports: List, limit: int) -> List:
    """Sort reports by date and apply limit."""
    return sorted(reports, key=lambda r: r.generated_at, reverse=True)[:limit]

def _convert_reports_to_responses(reports: List) -> List[ReportResponse]:
    """Convert reports to response format."""
    return [_convert_report_to_response(r) for r in reports]

@router.get("/history", response_model=List[ReportResponse])
async def get_report_history(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    interval: str = Query("daily", pattern="^(hourly|daily|weekly)$"),
    limit: int = Query(10, ge=1, le=100),
    current_user: Dict = Depends(get_current_user)
) -> List[ReportResponse]:
    """Get historical factory status reports."""
    reports = list(_report_cache.values())
    filtered_reports = _filter_reports_by_date_range(reports, start_date, end_date)
    limited_reports = _sort_and_limit_reports(filtered_reports, limit)
    return _convert_reports_to_responses(limited_reports)


def _build_metric_response(metric_name: str, value: Any, hours: int) -> MetricResponse:
    """Build metric response with metadata."""
    return MetricResponse(
        metric_name=metric_name,
        value=value,
        timestamp=datetime.now(),
        metadata={"hours_analyzed": hours}
    )

def _handle_metric_fetch_error(e: Exception, metric_name: str):
    """Handle metric fetch errors."""
    raise HTTPException(status_code=404, detail=f"Metric not found: {metric_name}")

@router.get("/metrics/{metric_name}", response_model=MetricResponse)
async def get_specific_metric(
    metric_name: str,
    hours: int = Query(24, ge=1, le=720),
    current_user: Dict = Depends(get_current_user)
) -> MetricResponse:
    """Get a specific metric from the factory status system."""
    try:
        builder = ReportBuilder()
        value = await _fetch_metric(builder, metric_name, hours)
        return _build_metric_response(metric_name, value, hours)
    except Exception as e:
        _handle_metric_fetch_error(e, metric_name)


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: GenerateReportRequest,
    current_user: Dict = Depends(get_current_user)
) -> ReportResponse:
    """Generate a new factory status report."""
    try:
        report = await _generate_new_report(request.hours)
        return _convert_report_to_response(report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


def _build_velocity_calculator() -> Any:
    """Build velocity calculator from report builder."""
    builder = ReportBuilder()
    return builder.velocity_calc

def _calculate_entry_date(i: int) -> str:
    """Calculate entry date for velocity data."""
    return (datetime.now() - timedelta(days=i)).date().isoformat()


def _create_daily_velocity_entry(calculator, i: int) -> Dict[str, Any]:
    """Create single daily velocity entry."""
    start_hours = (i + 1) * 24
    metrics = calculator.calculate_velocity(start_hours)
    return {
        "date": _calculate_entry_date(i),
        "commits": metrics.commits_per_day,
        "velocity": metrics.velocity_trend
    }

def _collect_daily_velocities(calculator, days: int) -> List[Dict[str, Any]]:
    """Collect daily velocity data for specified period."""
    daily_velocities = []
    for i in range(days):
        entry = _create_daily_velocity_entry(calculator, i)
        daily_velocities.append(entry)
    return daily_velocities

def _build_velocity_trend_response(days: int, daily_velocities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build complete velocity trend response."""
    return {
        "period_days": days,
        "daily_data": daily_velocities,
        "overall_trend": _calculate_trend(daily_velocities)
    }

@router.get("/metrics/velocity/trend")
async def get_velocity_trend(
    days: int = Query(7, ge=1, le=30),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get velocity trend over specified days."""
    calculator = _build_velocity_calculator()
    daily_velocities = _collect_daily_velocities(calculator, days)
    return _build_velocity_trend_response(days, daily_velocities)


def _build_business_calculator() -> Any:
    """Build business value calculator."""
    builder = ReportBuilder()
    return builder.business_calc

def _build_business_objectives_response(hours: int, metrics) -> Dict[str, Any]:
    """Build business objectives response."""
    return {
        "period_hours": hours,
        "objectives": metrics.objective_scores,
        "customer_impact": metrics.customer_impact.score,
        "revenue_impact": metrics.revenue_metrics.revenue_impact_score,
        "innovation_ratio": metrics.innovation.innovation_ratio,
        "overall_score": metrics.overall_value_score
    }

@router.get("/metrics/business-value/objectives")
async def get_business_objectives(
    hours: int = Query(168, ge=1, le=720),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get business objective scores."""
    calculator = _build_business_calculator()
    metrics = calculator.calculate_business_value(hours)
    return _build_business_objectives_response(hours, metrics)


def _build_quality_calculator() -> Any:
    """Build quality calculator from report builder."""
    builder = ReportBuilder()
    return builder.quality_calc

def _determine_compliance_status(compliance) -> str:
    """Determine compliance status from violations."""
    return "compliant" if compliance.violations == 0 else "non-compliant"

def _build_compliance_details(compliance) -> Dict[str, str]:
    """Build compliance details section."""
    return {
        "300_line_rule": f"{len(compliance.files_over_limit)} violations",
        "8_line_rule": f"{len(compliance.functions_over_limit)} violations"
    }

def _build_compliance_response(compliance) -> Dict[str, Any]:
    """Build complete compliance response."""
    return {
        "violations": compliance.violations,
        "files_over_limit": compliance.files_over_limit,
        "functions_over_limit": compliance.functions_over_limit,
        "compliance_rate": compliance.compliance_rate,
        "status": _determine_compliance_status(compliance),
        "details": _build_compliance_details(compliance)
    }

@router.get("/metrics/quality/compliance")
async def get_compliance_status(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get architecture compliance status."""
    calculator = _build_quality_calculator()
    metrics = calculator.calculate_quality(24)
    return _build_compliance_response(metrics.architecture_compliance)


def _build_executive_summary_section(report) -> Dict[str, Any]:
    """Build executive summary section for dashboard."""
    return {
        "productivity_score": report.executive_summary.productivity_score,
        "business_value_score": report.executive_summary.business_value_score,
        "status": report.executive_summary.overall_status,
        "highlights": report.executive_summary.key_highlights
    }

def _build_quick_stats_section(report) -> Dict[str, Any]:
    """Build quick stats section for dashboard."""
    return {
        "commits_today": report.velocity_metrics["commits_per_day"],
        "active_branches": report.branch_metrics["active_branches"],
        "features_added": report.feature_progress["features_added"],
        "bugs_fixed": report.feature_progress["bugs_fixed"]
    }

def _build_trends_section(report) -> Dict[str, Any]:
    """Build trends section for dashboard."""
    return {
        "velocity": report.velocity_metrics["velocity_trend"],
        "quality": report.quality_metrics["quality_score"],
        "innovation": report.business_value_metrics["innovation"]["innovation_ratio"]
    }

def _build_complete_dashboard_summary(report) -> Dict[str, Any]:
    """Build complete dashboard summary response."""
    return {
        "executive_summary": _build_executive_summary_section(report),
        "quick_stats": _build_quick_stats_section(report),
        "trends": _build_trends_section(report),
        "last_updated": report.generated_at.isoformat()
    }

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get summary data for dashboard display."""
    report = await _ensure_latest_report()
    return _build_complete_dashboard_summary(report)


def _build_test_summary(report) -> Dict[str, Any]:
    """Build test summary from report."""
    return {
        "productivity_score": report.executive_summary.productivity_score,
        "business_value_score": report.executive_summary.business_value_score,
        "overall_status": report.executive_summary.overall_status
    }

def _build_test_response(report) -> Dict[str, Any]:
    """Build complete test response."""
    return {
        "status": "Factory Status API is working!",
        "report_id": report.report_id,
        "generated_at": report.generated_at.isoformat(),
        "summary": _build_test_summary(report)
    }

@router.get("/test")
async def test_factory_status() -> Dict[str, Any]:
    """Test endpoint for factory status (no auth required for testing)."""
    report = await _ensure_latest_report()
    return _build_test_response(report)


def _cache_generated_report(report: FactoryStatusReport) -> None:
    """Cache the generated report."""
    global _latest_report_id
    _report_cache[report.report_id] = report
    _latest_report_id = report.report_id

def _clean_old_reports() -> None:
    """Clean old reports from cache (keep last 100)."""
    if len(_report_cache) > 100:
        oldest = sorted(_report_cache.keys())[:len(_report_cache) - 100]
        for key in oldest:
            del _report_cache[key]

async def _generate_new_report(hours: int) -> FactoryStatusReport:
    """Generate a new factory status report."""
    builder = ReportBuilder()
    report = builder.build_report(hours)
    _cache_generated_report(report)
    _clean_old_reports()
    return report


async def _ensure_latest_report() -> FactoryStatusReport:
    """Ensure we have a latest report."""
    if not _latest_report_id or _latest_report_id not in _report_cache:
        return await _generate_new_report(24)
    return _report_cache[_latest_report_id]


def _build_metric_mapping(builder: ReportBuilder, hours: int) -> Dict[str, Any]:
    """Build metric mapping dictionary."""
    return {
        "commits_per_hour": lambda: builder.velocity_calc.calculate_velocity(hours).commits_per_hour,
        "commits_per_day": lambda: builder.velocity_calc.calculate_velocity(hours).commits_per_day,
        "velocity_trend": lambda: builder.velocity_calc.calculate_velocity(hours).velocity_trend,
        "quality_score": lambda: builder.quality_calc.calculate_quality(hours).quality_score,
        "business_value": lambda: builder.business_calc.calculate_business_value(hours).overall_value_score,
        "active_branches": lambda: builder.branch_tracker.calculate_metrics().active_branches,
        "technical_debt": lambda: builder.quality_calc.calculate_quality(hours).technical_debt.debt_ratio
    }

def _validate_metric_exists(metric_name: str, metric_map: Dict) -> None:
    """Validate metric exists in mapping."""
    if metric_name not in metric_map:
        raise ValueError(f"Unknown metric: {metric_name}")

async def _fetch_metric(builder: ReportBuilder, metric_name: str, hours: int) -> Any:
    """Fetch a specific metric value."""
    metric_map = _build_metric_mapping(builder, hours)
    _validate_metric_exists(metric_name, metric_map)
    return metric_map[metric_name]()


def _extract_core_report_fields(report: FactoryStatusReport) -> Dict[str, Any]:
    """Extract core report fields."""
    return {
        "report_id": report.report_id,
        "generated_at": report.generated_at,
        "executive_summary": _serialize_summary(report.executive_summary)
    }


def _extract_metrics_fields(report: FactoryStatusReport) -> Dict[str, Any]:
    """Extract metrics fields."""
    return {
        "velocity_metrics": report.velocity_metrics,
        "impact_metrics": report.impact_metrics,
        "quality_metrics": report.quality_metrics,
        "business_value_metrics": report.business_value_metrics,
        "branch_metrics": report.branch_metrics,
        "feature_progress": report.feature_progress,
        "recommendations": report.recommendations
    }


def _convert_report_to_response(report: FactoryStatusReport) -> ReportResponse:
    """Convert report to response model."""
    core_fields = _extract_core_report_fields(report)
    metrics_fields = _extract_metrics_fields(report)
    return ReportResponse(**{**core_fields, **metrics_fields})


def _serialize_summary(summary) -> Dict[str, Any]:
    """Serialize executive summary."""
    return {
        "timestamp": summary.timestamp.isoformat(),
        "productivity_score": summary.productivity_score,
        "key_highlights": summary.key_highlights,
        "action_items": summary.action_items,
        "business_value_score": summary.business_value_score,
        "overall_status": summary.overall_status
    }


def _calculate_trend_halves(daily_data: List[Dict]) -> tuple[int, int]:
    """Calculate first and second half commit sums."""
    midpoint = len(daily_data) // 2
    first_half = sum(d["commits"] for d in daily_data[:midpoint])
    second_half = sum(d["commits"] for d in daily_data[midpoint:])
    return first_half, second_half

def _determine_trend_direction(first_half: int, second_half: int) -> str:
    """Determine trend direction from half comparisons."""
    if second_half > first_half * 1.1:
        return "increasing"
    elif second_half < first_half * 0.9:
        return "decreasing"
    return "stable"

def _calculate_trend(daily_data: List[Dict]) -> str:
    """Calculate overall trend from daily data."""
    if len(daily_data) < 2:
        return "stable"
    first_half, second_half = _calculate_trend_halves(daily_data)
    return _determine_trend_direction(first_half, second_half)
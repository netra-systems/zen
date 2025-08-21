"""
Factory Status Metrics Routes
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any
from fastapi import HTTPException, Query, Depends
from netra_backend.app.services.factory_status.report_builder import ReportBuilder
from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.services.apex_optimizer_agent.models import MetricResponse
from netra_backend.app.routes.factory_status.business_logic import fetch_metric
from netra_backend.app.services.audit.utils import calculate_trend


def build_metric_response(metric_name: str, value: Any, hours: int) -> MetricResponse:
    """Build metric response with metadata."""
    return MetricResponse(
        metric_name=metric_name,
        value=value,
        timestamp=datetime.now(),
        metadata={"hours_analyzed": hours}
    )


def handle_metric_fetch_error(e: Exception, metric_name: str):
    """Handle metric fetch errors."""
    raise HTTPException(
        status_code=404, 
        detail=f"Metric not found: {metric_name}"
    )


async def _fetch_metric_value(metric_name: str, hours: int):
    """Fetch metric value with builder."""
    builder = ReportBuilder()
    return await fetch_metric(builder, metric_name, hours)


async def _get_metric_with_error_handling(metric_name: str, hours: int) -> Any:
    """Get metric with error handling."""
    try:
        return await _fetch_metric_value(metric_name, hours)
    except Exception as e:
        handle_metric_fetch_error(e, metric_name)

async def get_specific_metric_handler(
    metric_name: str,
    hours: int = 24,
    current_user: Dict = Depends(get_current_user)
) -> MetricResponse:
    """Get a specific metric from the factory status system."""
    value = await _get_metric_with_error_handling(metric_name, hours)
    return build_metric_response(metric_name, value, hours)


def build_velocity_calculator() -> Any:
    """Build velocity calculator from report builder."""
    builder = ReportBuilder()
    return builder.velocity_calc


def calculate_entry_date(i: int) -> str:
    """Calculate entry date for velocity data."""
    return (datetime.now() - timedelta(days=i)).date().isoformat()


def _calculate_start_hours(i: int) -> int:
    """Calculate start hours for entry."""
    return (i + 1) * 24


def _build_entry_data(i: int, metrics) -> Dict[str, Any]:
    """Build entry data dictionary."""
    return {
        "date": calculate_entry_date(i),
        "commits": metrics.commits_per_day,
        "velocity": metrics.velocity_trend
    }

def create_daily_velocity_entry(calculator, i: int) -> Dict[str, Any]:
    """Create single daily velocity entry."""
    start_hours = _calculate_start_hours(i)
    metrics = calculator.calculate_velocity(start_hours)
    return _build_entry_data(i, metrics)


def collect_daily_velocities(calculator, days: int) -> List[Dict[str, Any]]:
    """Collect daily velocity data for specified period."""
    daily_velocities = []
    for i in range(days):
        entry = create_daily_velocity_entry(calculator, i)
        daily_velocities.append(entry)
    return daily_velocities


def _calculate_overall_trend(daily_velocities: List[Dict[str, Any]]) -> str:
    """Calculate overall trend from velocities."""
    return calculate_trend(daily_velocities)


def _create_trend_data(days: int, daily_velocities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create trend data dictionary."""
    return {
        "period_days": days, "daily_data": daily_velocities,
        "overall_trend": _calculate_overall_trend(daily_velocities)
    }

def build_velocity_trend_response(
    days: int, daily_velocities: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Build complete velocity trend response."""
    return _create_trend_data(days, daily_velocities)


async def get_velocity_trend_handler(
    days: int = 7,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get velocity trend over specified days."""
    calculator = build_velocity_calculator()
    daily_velocities = collect_daily_velocities(calculator, days)
    return build_velocity_trend_response(days, daily_velocities)


def build_business_calculator() -> Any:
    """Build business value calculator."""
    builder = ReportBuilder()
    return builder.business_calc


def _extract_business_scores(metrics) -> Dict[str, Any]:
    """Extract business metrics scores."""
    return {
        "customer_impact": metrics.customer_impact.score,
        "revenue_impact": metrics.revenue_metrics.revenue_impact_score,
        "innovation_ratio": metrics.innovation.innovation_ratio
    }


def build_business_objectives_response(hours: int, metrics) -> Dict[str, Any]:
    """Build business objectives response."""
    scores = _extract_business_scores(metrics)
    return {
        "period_hours": hours, "objectives": metrics.objective_scores,
        "overall_score": metrics.overall_value_score, **scores
    }


async def get_business_objectives_handler(
    hours: int = 168,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get business objective scores."""
    calculator = build_business_calculator()
    metrics = calculator.calculate_business_value(hours)
    return build_business_objectives_response(hours, metrics)


def build_quality_calculator() -> Any:
    """Build quality calculator from report builder."""
    builder = ReportBuilder()
    return builder.quality_calc


def determine_compliance_status(compliance) -> str:
    """Determine compliance status from violations."""
    return "compliant" if compliance.violations == 0 else "non-compliant"


def build_compliance_details(compliance) -> Dict[str, str]:
    """Build compliance details section."""
    return {
        "300_line_rule": f"{len(compliance.files_over_limit)} violations",
        "8_line_rule": f"{len(compliance.functions_over_limit)} violations"
    }


def _extract_compliance_core(compliance) -> Dict[str, Any]:
    """Extract core compliance data."""
    return {
        "violations": compliance.violations,
        "files_over_limit": compliance.files_over_limit,
        "functions_over_limit": compliance.functions_over_limit
    }


def build_compliance_response(compliance) -> Dict[str, Any]:
    """Build complete compliance response."""
    core_data = _extract_compliance_core(compliance)
    return {
        **core_data, "compliance_rate": compliance.compliance_rate,
        "status": determine_compliance_status(compliance),
        "details": build_compliance_details(compliance)
    }


async def get_compliance_status_handler(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get architecture compliance status."""
    calculator = build_quality_calculator()
    metrics = calculator.calculate_quality(24)
    return build_compliance_response(metrics.architecture_compliance)
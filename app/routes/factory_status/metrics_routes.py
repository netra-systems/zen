"""
Factory Status Metrics Routes
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any
from fastapi import HTTPException, Query, Depends
from app.services.factory_status.report_builder import ReportBuilder
from app.auth_integration.auth import get_current_user
from .models import MetricResponse
from .business_logic import fetch_metric
from .utils import calculate_trend


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


async def get_specific_metric_handler(
    metric_name: str,
    hours: int = 24,
    current_user: Dict = Depends(get_current_user)
) -> MetricResponse:
    """Get a specific metric from the factory status system."""
    try:
        builder = ReportBuilder()
        value = await fetch_metric(builder, metric_name, hours)
        return build_metric_response(metric_name, value, hours)
    except Exception as e:
        handle_metric_fetch_error(e, metric_name)


def build_velocity_calculator() -> Any:
    """Build velocity calculator from report builder."""
    builder = ReportBuilder()
    return builder.velocity_calc


def calculate_entry_date(i: int) -> str:
    """Calculate entry date for velocity data."""
    return (datetime.now() - timedelta(days=i)).date().isoformat()


def create_daily_velocity_entry(calculator, i: int) -> Dict[str, Any]:
    """Create single daily velocity entry."""
    start_hours = (i + 1) * 24
    metrics = calculator.calculate_velocity(start_hours)
    return {
        "date": calculate_entry_date(i),
        "commits": metrics.commits_per_day,
        "velocity": metrics.velocity_trend
    }


def collect_daily_velocities(calculator, days: int) -> List[Dict[str, Any]]:
    """Collect daily velocity data for specified period."""
    daily_velocities = []
    for i in range(days):
        entry = create_daily_velocity_entry(calculator, i)
        daily_velocities.append(entry)
    return daily_velocities


def build_velocity_trend_response(
    days: int, daily_velocities: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Build complete velocity trend response."""
    return {
        "period_days": days,
        "daily_data": daily_velocities,
        "overall_trend": calculate_trend(daily_velocities)
    }


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


def build_business_objectives_response(hours: int, metrics) -> Dict[str, Any]:
    """Build business objectives response."""
    return {
        "period_hours": hours,
        "objectives": metrics.objective_scores,
        "customer_impact": metrics.customer_impact.score,
        "revenue_impact": metrics.revenue_metrics.revenue_impact_score,
        "innovation_ratio": metrics.innovation.innovation_ratio,
        "overall_score": metrics.overall_value_score
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


def build_compliance_response(compliance) -> Dict[str, Any]:
    """Build complete compliance response."""
    return {
        "violations": compliance.violations,
        "files_over_limit": compliance.files_over_limit,
        "functions_over_limit": compliance.functions_over_limit,
        "compliance_rate": compliance.compliance_rate,
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
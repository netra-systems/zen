"""
Factory Status Business Logic
"""
from typing import Dict, Optional, Any
from app.services.factory_status.report_builder import ReportBuilder, FactoryStatusReport

# In-memory cache for demo (replace with Redis in production)
_report_cache: Dict[str, FactoryStatusReport] = {}
_latest_report_id: Optional[str] = None


def cache_generated_report(report: FactoryStatusReport) -> None:
    """Cache the generated report."""
    global _latest_report_id
    _report_cache[report.report_id] = report
    _latest_report_id = report.report_id


def clean_old_reports() -> None:
    """Clean old reports from cache (keep last 100)."""
    if len(_report_cache) > 100:
        oldest = sorted(_report_cache.keys())[:len(_report_cache) - 100]
        for key in oldest:
            del _report_cache[key]


async def generate_new_report(hours: int) -> FactoryStatusReport:
    """Generate a new factory status report."""
    builder = ReportBuilder()
    report = builder.build_report(hours)
    cache_generated_report(report)
    clean_old_reports()
    return report


async def ensure_latest_report() -> FactoryStatusReport:
    """Ensure we have a latest report."""
    if not _latest_report_id or _latest_report_id not in _report_cache:
        return await generate_new_report(24)
    return _report_cache[_latest_report_id]


def get_cached_reports() -> Dict[str, FactoryStatusReport]:
    """Get all cached reports."""
    return _report_cache


def get_latest_report_id() -> Optional[str]:
    """Get the latest report ID."""
    return _latest_report_id


def _build_velocity_metrics(builder, hours: int) -> Dict[str, Any]:
    """Build velocity metric functions."""
    return {
        "commits_per_hour": lambda: builder.velocity_calc.calculate_velocity(hours).commits_per_hour,
        "commits_per_day": lambda: builder.velocity_calc.calculate_velocity(hours).commits_per_day,
        "velocity_trend": lambda: builder.velocity_calc.calculate_velocity(hours).velocity_trend
    }


def _build_additional_metrics(builder: ReportBuilder, hours: int) -> Dict[str, Any]:
    """Build additional metric functions."""
    return {
        "quality_score": lambda: builder.quality_calc.calculate_quality(hours).quality_score,
        "business_value": lambda: builder.business_calc.calculate_business_value(hours).overall_value_score,
        "active_branches": lambda: builder.branch_tracker.calculate_metrics().active_branches,
        "technical_debt": lambda: builder.quality_calc.calculate_quality(hours).technical_debt.debt_ratio
    }

def build_metric_mapping(builder: ReportBuilder, hours: int) -> Dict[str, Any]:
    """Build metric mapping dictionary."""
    velocity_metrics = _build_velocity_metrics(builder, hours)
    additional_metrics = _build_additional_metrics(builder, hours)
    return {**velocity_metrics, **additional_metrics}


def validate_metric_exists(metric_name: str, metric_map: Dict) -> None:
    """Validate metric exists in mapping."""
    if metric_name not in metric_map:
        raise ValueError(f"Unknown metric: {metric_name}")


async def fetch_metric(builder: ReportBuilder, metric_name: str, hours: int) -> Any:
    """Fetch a specific metric value."""
    metric_map = build_metric_mapping(builder, hours)
    validate_metric_exists(metric_name, metric_map)
    return metric_map[metric_name]()
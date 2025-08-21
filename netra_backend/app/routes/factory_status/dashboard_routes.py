"""
Factory Status Dashboard Routes
"""
from typing import Dict, Any
from fastapi import Depends
from app.auth_integration.auth import get_current_user
from netra_backend.app.business_logic import ensure_latest_report


def build_executive_summary_section(report) -> Dict[str, Any]:
    """Build executive summary section for dashboard."""
    return {
        "productivity_score": report.executive_summary.productivity_score,
        "business_value_score": report.executive_summary.business_value_score,
        "status": report.executive_summary.overall_status,
        "highlights": report.executive_summary.key_highlights
    }


def build_quick_stats_section(report) -> Dict[str, Any]:
    """Build quick stats section for dashboard."""
    return {
        "commits_today": report.velocity_metrics["commits_per_day"],
        "active_branches": report.branch_metrics["active_branches"],
        "features_added": report.feature_progress["features_added"],
        "bugs_fixed": report.feature_progress["bugs_fixed"]
    }


def build_trends_section(report) -> Dict[str, Any]:
    """Build trends section for dashboard."""
    return {
        "velocity": report.velocity_metrics["velocity_trend"],
        "quality": report.quality_metrics["quality_score"],
        "innovation": report.business_value_metrics["innovation"]["innovation_ratio"]
    }


def build_complete_dashboard_summary(report) -> Dict[str, Any]:
    """Build complete dashboard summary response."""
    return {
        "executive_summary": build_executive_summary_section(report),
        "quick_stats": build_quick_stats_section(report),
        "trends": build_trends_section(report),
        "last_updated": report.generated_at.isoformat()
    }


async def get_dashboard_summary_handler(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get summary data for dashboard display."""
    report = await ensure_latest_report()
    return build_complete_dashboard_summary(report)


def build_test_summary(report) -> Dict[str, Any]:
    """Build test summary from report."""
    return {
        "productivity_score": report.executive_summary.productivity_score,
        "business_value_score": report.executive_summary.business_value_score,
        "overall_status": report.executive_summary.overall_status
    }


def build_test_response(report) -> Dict[str, Any]:
    """Build complete test response."""
    return {
        "status": "Factory Status API is working!",
        "report_id": report.report_id,
        "generated_at": report.generated_at.isoformat(),
        "summary": build_test_summary(report)
    }


async def test_factory_status_handler() -> Dict[str, Any]:
    """Test endpoint for factory status (no auth required for testing)."""
    report = await ensure_latest_report()
    return build_test_response(report)
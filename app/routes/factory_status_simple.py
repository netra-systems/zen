"""Simplified factory status endpoint for testing.

This bypasses git operations entirely and uses mock data.
Module follows 450-line limit with 25-line function limit.
"""

from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
import uuid

router = APIRouter(
    prefix="/api/factory-status",
    tags=["factory-status"]
)


def _generate_simple_summary() -> Dict[str, Any]:
    """Generate simple summary data."""
    return {
        "productivity_score": 8.5, "business_value_score": 7.8,
        "overall_status": "healthy", "commits_today": 12,
        "active_branches": 4, "features_delivered": 3
    }


def _generate_velocity_metrics() -> Dict[str, Any]:
    """Generate velocity metrics."""
    return {
        "commits_per_day": 15, "pr_merge_time_hours": 4.2,
        "cycle_time_hours": 24.5
    }


def _generate_quality_metrics() -> Dict[str, Any]:
    """Generate quality metrics."""
    return {
        "test_coverage": 82.5, "code_review_rate": 95.0,
        "architecture_compliance": 98.2
    }


def _generate_business_value_metrics() -> Dict[str, Any]:
    """Generate business value metrics."""
    return {
        "customer_impact_score": 8.2, "innovation_ratio": 0.45,
        "technical_debt_ratio": 0.12
    }


def _generate_recommendations() -> List[str]:
    """Generate recommendation list."""
    return [
        "Maintain current velocity - team is performing well",
        "Consider increasing test coverage to 85%",
        "Schedule technical debt reduction sprint"
    ]


def _build_report_metadata(report_id: str) -> Dict[str, Any]:
    """Build report metadata section."""
    return {
        "status": "success", "report_id": report_id,
        "generated_at": datetime.now().isoformat(),
        "message": "Factory Status Report generated successfully"
    }


def _build_metrics_section() -> Dict[str, Any]:
    """Build metrics section."""
    return {
        "velocity": _generate_velocity_metrics(),
        "quality": _generate_quality_metrics(),
        "business_value": _generate_business_value_metrics()
    }


def _build_complete_report(report_id: str) -> Dict[str, Any]:
    """Build complete report structure."""
    metadata = _build_report_metadata(report_id)
    return {
        **metadata, "summary": _generate_simple_summary(),
        "metrics": _build_metrics_section(), "recommendations": _generate_recommendations()
    }

@router.post("/generate-simple")
async def generate_simple_report() -> Dict[str, Any]:
    """Generate a simplified factory status report without git operations."""
    report_id = str(uuid.uuid4())[:8]
    return _build_complete_report(report_id)


@router.get("/test-simple")
async def test_simple_endpoint() -> Dict[str, Any]:
    """Simple test endpoint that doesn't use git operations."""
    return {
        "status": "Factory Status API is working!",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "message": "Simple endpoint without git operations"
    }
"""
Factory Status API Router - Main route definitions
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, Depends

from netra_backend.app.routes.factory_status.models import ReportResponse, MetricResponse, GenerateReportRequest
from netra_backend.app.routes.factory_status.report_routes import (
    get_latest_report_handler, get_report_history_handler, generate_report_handler
)
from netra_backend.app.routes.factory_status.metrics_routes import (
    get_specific_metric_handler, get_velocity_trend_handler,
    get_business_objectives_handler, get_compliance_status_handler
)
from netra_backend.app.routes.database_monitoring.dashboard_routes import get_dashboard_summary_handler, test_factory_status_handler


router = APIRouter(
    prefix="/api/factory-status",
    tags=["factory-status"]
)


@router.get("/latest", response_model=ReportResponse)
async def get_latest_report() -> ReportResponse:
    """Get the latest factory status report."""
    return await get_latest_report_handler()


@router.get("/history", response_model=List[ReportResponse])
async def get_report_history(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    interval: str = Query("daily", pattern="^(hourly|daily|weekly)$"),
    limit: int = Query(10, ge=1, le=100)
) -> List[ReportResponse]:
    """Get historical factory status reports."""
    return await get_report_history_handler(start_date, end_date, interval, limit)


@router.get("/metrics/{metric_name}", response_model=MetricResponse)
async def get_specific_metric(
    metric_name: str,
    hours: int = Query(24, ge=1, le=720)
) -> MetricResponse:
    """Get a specific metric from the factory status system."""
    return await get_specific_metric_handler(metric_name, hours)


@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: GenerateReportRequest) -> ReportResponse:
    """Generate a new factory status report."""
    return await generate_report_handler(request)


@router.get("/metrics/velocity/trend")
async def get_velocity_trend(
    days: int = Query(7, ge=1, le=30)
) -> Dict[str, Any]:
    """Get velocity trend over specified days."""
    return await get_velocity_trend_handler(days)


@router.get("/metrics/business-value/objectives")
async def get_business_objectives(
    hours: int = Query(168, ge=1, le=720)
) -> Dict[str, Any]:
    """Get business objective scores."""
    return await get_business_objectives_handler(hours)


@router.get("/metrics/quality/compliance")
async def get_compliance_status() -> Dict[str, Any]:
    """Get architecture compliance status."""
    return await get_compliance_status_handler()


@router.get("/dashboard/summary")
async def get_dashboard_summary() -> Dict[str, Any]:
    """Get summary data for dashboard display."""
    return await get_dashboard_summary_handler()


@router.get("/test")
async def test_factory_status() -> Dict[str, Any]:
    """Test endpoint for factory status (no auth required for testing)."""
    return await test_factory_status_handler()
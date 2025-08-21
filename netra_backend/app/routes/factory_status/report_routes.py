"""
Factory Status Report Routes
"""
from datetime import datetime
from typing import List, Dict
from fastapi import HTTPException, Query, Depends
from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.services.apex_optimizer_agent.models import ReportResponse, GenerateReportRequest
from netra_backend.app.routes.factory_status.business_logic import get_cached_reports, get_latest_report_id, generate_new_report
from netra_backend.app.services.audit.utils import (
    filter_reports_by_date_range, sort_and_limit_reports, 
    convert_reports_to_responses, convert_report_to_response
)


async def _get_or_generate_latest_report():
    """Get latest report or generate new one."""
    latest_id = get_latest_report_id()
    reports_cache = get_cached_reports()
    if not latest_id or latest_id not in reports_cache:
        return await generate_new_report(24)
    return reports_cache[latest_id]


async def get_latest_report_handler(
    current_user: Dict = Depends(get_current_user)
) -> ReportResponse:
    """Get the latest factory status report."""
    report = await _get_or_generate_latest_report()
    return convert_report_to_response(report)


def _process_historical_reports(start_date, end_date, limit):
    """Process historical reports with filters."""
    reports = list(get_cached_reports().values())
    filtered_reports = filter_reports_by_date_range(reports, start_date, end_date)
    return sort_and_limit_reports(filtered_reports, limit)


async def _get_processed_historical_reports(start_date, end_date, limit):
    """Get processed historical reports."""
    return _process_historical_reports(start_date, end_date, limit)

async def get_report_history_handler(
    start_date: datetime = None,
    end_date: datetime = None,
    interval: str = "daily",
    limit: int = 10,
    current_user: Dict = Depends(get_current_user)
) -> List[ReportResponse]:
    """Get historical factory status reports."""
    limited_reports = await _get_processed_historical_reports(start_date, end_date, limit)
    return convert_reports_to_responses(limited_reports)


def _handle_generation_error(e: Exception):
    """Handle report generation error."""
    raise HTTPException(
        status_code=500, 
        detail=f"Failed to generate report: {str(e)}"
    )


async def _generate_and_convert_report(request: GenerateReportRequest):
    """Generate and convert report."""
    try:
        report = await generate_new_report(request.hours)
        return convert_report_to_response(report)
    except Exception as e:
        _handle_generation_error(e)

async def generate_report_handler(
    request: GenerateReportRequest,
    current_user: Dict = Depends(get_current_user)
) -> ReportResponse:
    """Generate a new factory status report."""
    return await _generate_and_convert_report(request)
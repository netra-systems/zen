"""
Factory Status Report Routes
"""
from datetime import datetime
from typing import List, Dict
from fastapi import HTTPException, Query, Depends
from app.auth_integration.auth import get_current_user
from .models import ReportResponse, GenerateReportRequest
from .business_logic import get_cached_reports, get_latest_report_id, generate_new_report
from .utils import (
    filter_reports_by_date_range, sort_and_limit_reports, 
    convert_reports_to_responses, convert_report_to_response
)


async def get_latest_report_handler(
    current_user: Dict = Depends(get_current_user)
) -> ReportResponse:
    """Get the latest factory status report."""
    latest_id = get_latest_report_id()
    reports_cache = get_cached_reports()
    
    if not latest_id or latest_id not in reports_cache:
        # Generate new report if none exists
        report = await generate_new_report(24)
    else:
        report = reports_cache[latest_id]
    
    return convert_report_to_response(report)


async def get_report_history_handler(
    start_date: datetime = None,
    end_date: datetime = None,
    interval: str = "daily",
    limit: int = 10,
    current_user: Dict = Depends(get_current_user)
) -> List[ReportResponse]:
    """Get historical factory status reports."""
    reports = list(get_cached_reports().values())
    filtered_reports = filter_reports_by_date_range(reports, start_date, end_date)
    limited_reports = sort_and_limit_reports(filtered_reports, limit)
    return convert_reports_to_responses(limited_reports)


async def generate_report_handler(
    request: GenerateReportRequest,
    current_user: Dict = Depends(get_current_user)
) -> ReportResponse:
    """Generate a new factory status report."""
    try:
        report = await generate_new_report(request.hours)
        return convert_report_to_response(report)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate report: {str(e)}"
        )
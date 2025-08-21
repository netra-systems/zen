"""Demo export and reporting handlers."""
from fastapi import BackgroundTasks
from typing import Optional, Dict, Any
from datetime import datetime, UTC

from netra_backend.app.services.demo_service import DemoService
from netra_backend.app.schemas.demo_schemas import ExportReportRequest


async def handle_export_report(
    request: ExportReportRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService,
    current_user: Optional[Dict]
) -> Dict[str, str]:
    """Export demo session report."""
    return await execute_export_flow(request, background_tasks, demo_service, current_user)


async def execute_export_flow(
    request: ExportReportRequest, background_tasks: BackgroundTasks,
    demo_service: DemoService, current_user: Optional[Dict]
) -> Dict[str, str]:
    """Execute complete export flow."""
    report_url = await generate_demo_report(request, demo_service, current_user)
    track_report_export(background_tasks, demo_service, request)
    return create_export_response(report_url)


async def execute_report_generation(
    request: ExportReportRequest, demo_service: DemoService, current_user: Optional[Dict]
) -> str:
    """Execute report generation."""
    user_id = current_user.get("id") if current_user else None
    params = build_report_params(request, user_id)
    return await demo_service.generate_report(**params)


def build_report_params(request: ExportReportRequest, user_id: Optional[str]) -> Dict[str, Any]:
    """Build report generation parameters."""
    return {
        "session_id": request.session_id, "format": request.format,
        "include_sections": request.include_sections, "user_id": user_id
    }


async def generate_demo_report(
    request: ExportReportRequest, demo_service: DemoService, current_user: Optional[Dict]
) -> str:
    """Generate demo report."""
    return await execute_report_with_error_handling(request, demo_service, current_user)


async def execute_report_with_error_handling(
    request: ExportReportRequest, demo_service: DemoService, current_user: Optional[Dict]
) -> str:
    """Execute report generation with error handling."""
    return await handle_report_generation(request, demo_service, current_user)


async def handle_report_generation(
    request: ExportReportRequest, demo_service: DemoService, current_user: Optional[Dict]
) -> str:
    """Handle report generation with error handling."""
    try:
        return await execute_report_generation(request, demo_service, current_user)
    except ValueError as e:
        handle_report_value_error(e)
    except Exception as e:
        handle_report_general_error(e)


def handle_report_value_error(e: ValueError) -> None:
    """Handle ValueError in report generation."""
    from netra_backend.app.routes.demo_handlers_utils import raise_not_found_error
    raise_not_found_error(str(e))


def handle_report_general_error(e: Exception) -> None:
    """Handle general exception in report generation."""
    from netra_backend.app.routes.demo_handlers_utils import log_and_raise_error
    log_and_raise_error("Failed to export report", e)


def create_export_tracking_data(request: ExportReportRequest) -> Dict[str, Any]:
    """Create tracking data for report export."""
    return {"format": request.format, "sections": request.include_sections}


def add_export_tracking_task(
    background_tasks: BackgroundTasks, demo_service: DemoService,
    session_id: str, data: Dict[str, Any]
) -> None:
    """Add export tracking task."""
    from netra_backend.app.routes.demo_handlers_utils import build_tracking_params
    params = build_tracking_params(session_id, "report_export", data)
    background_tasks.add_task(demo_service.track_demo_interaction, **params)


def track_report_export(
    background_tasks: BackgroundTasks, demo_service: DemoService, request: ExportReportRequest
) -> None:
    """Track export for analytics."""
    data = create_export_tracking_data(request)
    add_export_tracking_task(background_tasks, demo_service, request.session_id, data)


def create_export_response(report_url: str) -> Dict[str, str]:
    """Create export response with report URL."""
    return {
        "status": "success",
        "report_url": report_url,
        "expires_at": datetime.now(UTC).isoformat()
    }
"""Demo ROI calculation handlers."""
from fastapi import BackgroundTasks
from typing import Dict, Any

from app.services.demo_service import DemoService
from app.schemas.demo_schemas import ROICalculationRequest, ROICalculationResponse


async def handle_roi_calculation(
    request: ROICalculationRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService
) -> ROICalculationResponse:
    """Calculate ROI and cost savings."""
    return await execute_roi_calculation_flow(request, background_tasks, demo_service)


async def execute_roi_calculation_flow(
    request: ROICalculationRequest, background_tasks: BackgroundTasks, demo_service: DemoService
) -> ROICalculationResponse:
    """Execute complete ROI calculation flow."""
    result = await calculate_roi_metrics(request, demo_service)
    track_roi_calculation(background_tasks, demo_service, request, result)
    return ROICalculationResponse(**result)


async def execute_roi_calculation(
    request: ROICalculationRequest, demo_service: DemoService
) -> Dict[str, Any]:
    """Execute ROI calculation through service."""
    return await demo_service.calculate_roi(
        current_spend=request.current_spend, request_volume=request.request_volume,
        average_latency=request.average_latency, industry=request.industry
    )


async def calculate_roi_metrics(
    request: ROICalculationRequest, demo_service: DemoService
) -> Dict[str, Any]:
    """Calculate ROI metrics using demo service."""
    try:
        return await execute_roi_calculation(request, demo_service)
    except Exception as e:
        from app.routes.demo_handlers_utils import log_and_raise_error
        log_and_raise_error("ROI calculation failed", e)


def create_roi_tracking_data(request: ROICalculationRequest, result: Dict[str, Any]) -> Dict[str, Any]:
    """Create tracking data for ROI calculation."""
    return {"industry": request.industry, "potential_savings": result["annual_savings"]}


def add_roi_tracking_task(
    background_tasks: BackgroundTasks, demo_service: DemoService, data: Dict[str, Any]
) -> None:
    """Add ROI tracking task to background."""
    background_tasks.add_task(
        demo_service.track_demo_interaction,
        interaction_type="roi_calculation", data=data
    )


def track_roi_calculation(
    background_tasks: BackgroundTasks, demo_service: DemoService,
    request: ROICalculationRequest, result: Dict[str, Any]
) -> None:
    """Track ROI calculation in background."""
    data = create_roi_tracking_data(request, result)
    add_roi_tracking_task(background_tasks, demo_service, data)
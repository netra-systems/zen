"""Demo API routes for enterprise demonstrations."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, WebSocket

from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.routes.demo_handlers import (
    handle_demo_analytics,
    handle_demo_chat,
    handle_export_report,
    handle_industry_templates,
    handle_roi_calculation,
    handle_session_feedback,
    handle_session_status,
    handle_synthetic_metrics,
)
from netra_backend.app.schemas.demo_schemas import (
    DemoChatRequest,
    DemoChatResponse,
    DemoMetrics,
    ExportReportRequest,
    IndustryTemplate,
    ROICalculationRequest,
    ROICalculationResponse,
)
from netra_backend.app.services.demo_service import DemoService, get_demo_service

router = APIRouter(
    prefix="/api/demo",
    tags=["demo"],
    redirect_slashes=False  # Disable automatic trailing slash redirects
)


@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any], include_in_schema=False)
async def get_demo_overview(
    current_user: Optional[Dict] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get demo overview and available features."""
    return _build_demo_overview_response(current_user)


def _build_demo_overview_response(current_user: Optional[Dict]) -> Dict[str, Any]:
    """Build demo overview response data."""
    return {
        "status": "active",
        "features": _get_demo_features(),
        "message": "Welcome to Netra AI Optimization Demo",
        "user_authenticated": current_user is not None
    }


def _get_demo_features() -> List[str]:
    """Get list of available demo features."""
    return [
        "ai_optimization_chat", "roi_calculator", "industry_templates",
        "synthetic_metrics", "export_reports"
    ]


@router.post("/chat", response_model=DemoChatResponse)
async def demo_chat(
    request: DemoChatRequest, background_tasks: BackgroundTasks,
    demo_service: DemoService = Depends(get_demo_service),
    current_user: Optional[Dict] = Depends(get_current_user)
) -> DemoChatResponse:
    """Handle demo chat interactions."""
    return await handle_demo_chat(request, background_tasks, demo_service, current_user)


@router.post("/public-chat", response_model=DemoChatResponse)
async def public_demo_chat(
    request: DemoChatRequest, background_tasks: BackgroundTasks,
    demo_service: DemoService = Depends(get_demo_service)
) -> DemoChatResponse:
    """Handle public demo chat interactions without authentication."""
    # Pass None as current_user for public demo
    return await handle_demo_chat(request, background_tasks, demo_service, None)


@router.get("/industry/{industry}/templates", response_model=List[IndustryTemplate])
async def get_industry_templates(
    industry: str, demo_service: DemoService = Depends(get_demo_service)
) -> List[IndustryTemplate]:
    """Get industry-specific demo templates."""
    return await handle_industry_templates(industry, demo_service)


@router.post("/roi/calculate", response_model=ROICalculationResponse)
async def calculate_roi(
    request: ROICalculationRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService = Depends(get_demo_service)
) -> ROICalculationResponse:
    """Calculate ROI and cost savings."""
    return await handle_roi_calculation(request, background_tasks, demo_service)


@router.get("/metrics/synthetic", response_model=DemoMetrics)
async def get_synthetic_metrics(
    scenario: str = "standard",
    duration_hours: int = 24,
    demo_service: DemoService = Depends(get_demo_service)
) -> DemoMetrics:
    """Generate synthetic performance metrics."""
    metrics_data = await handle_synthetic_metrics(scenario, duration_hours, demo_service)
    return DemoMetrics(**metrics_data)


@router.post("/export/report")
async def export_demo_report(
    request: ExportReportRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService = Depends(get_demo_service),
    current_user: Optional[Dict] = Depends(get_current_user)
) -> Dict[str, str]:
    """Export demo session as report."""
    return await handle_export_report(request, background_tasks, demo_service, current_user)


@router.get("/session/{session_id}/status")
async def get_demo_session_status(
    session_id: str, demo_service: DemoService = Depends(get_demo_service)
) -> Dict[str, Any]:
    """Get demo session status."""
    return await handle_session_status(session_id, demo_service)


@router.post("/session/{session_id}/feedback")
async def submit_demo_feedback(
    session_id: str,
    feedback: Dict[str, Any],
    demo_service: DemoService = Depends(get_demo_service)
) -> Dict[str, str]:
    """Submit demo session feedback."""
    return await handle_session_feedback(session_id, feedback, demo_service)


@router.get("/analytics/summary")
async def get_demo_analytics(
    days: int = 30,
    demo_service: DemoService = Depends(get_demo_service),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get demo analytics summary."""
    return await handle_demo_analytics(days, demo_service, current_user)


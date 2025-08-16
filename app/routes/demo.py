"""Demo API routes for enterprise demonstrations."""

from fastapi import APIRouter, Depends, BackgroundTasks, WebSocket
from typing import Optional, Dict, Any, List

from app.auth.auth_dependencies import get_current_user
from app.services.demo_service import DemoService, get_demo_service
from app.schemas.demo_schemas import (
    DemoChatRequest, DemoChatResponse, ROICalculationRequest, ROICalculationResponse,
    ExportReportRequest, IndustryTemplate, DemoMetrics
)
from app.routes.demo_handlers import (
    handle_demo_chat, handle_industry_templates, handle_roi_calculation,
    handle_synthetic_metrics, handle_export_report, handle_session_status,
    handle_session_feedback, handle_demo_analytics
)
from app.routes.demo_websocket import handle_demo_websocket

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/", response_model=Dict[str, Any])
async def get_demo_overview(
    current_user: Optional[Dict] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get demo overview and available features.
    
    Returns basic demo information and available demo features.
    """
    return {
        "status": "active",
        "features": [
            "ai_optimization_chat",
            "roi_calculator", 
            "industry_templates",
            "synthetic_metrics",
            "export_reports"
        ],
        "message": "Welcome to Netra AI Optimization Demo",
        "user_authenticated": current_user is not None
    }


@router.post("/chat", response_model=DemoChatResponse)
async def demo_chat(
    request: DemoChatRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService = Depends(get_demo_service),
    current_user: Optional[Dict] = Depends(get_current_user)
) -> DemoChatResponse:
    """
    Handle demo chat interactions with industry-specific AI optimization.
    
    This endpoint simulates the multi-agent system for demonstrations,
    providing realistic optimization recommendations based on industry context.
    """
    return await handle_demo_chat(request, background_tasks, demo_service, current_user)


@router.get("/industry/{industry}/templates", response_model=List[IndustryTemplate])
async def get_industry_templates(
    industry: str,
    demo_service: DemoService = Depends(get_demo_service)
) -> List[IndustryTemplate]:
    """
    Get industry-specific demo templates and scenarios.
    
    Returns pre-configured templates for different industries including
    typical optimization scenarios and expected metrics.
    """
    return await handle_industry_templates(industry, demo_service)


@router.post("/roi/calculate", response_model=ROICalculationResponse)
async def calculate_roi(
    request: ROICalculationRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService = Depends(get_demo_service)
) -> ROICalculationResponse:
    """
    Calculate ROI and cost savings for AI optimization.
    
    Provides detailed financial projections based on current spend
    and expected optimization improvements.
    """
    return await handle_roi_calculation(request, background_tasks, demo_service)


@router.get("/metrics/synthetic", response_model=DemoMetrics)
async def get_synthetic_metrics(
    scenario: str = "standard",
    duration_hours: int = 24,
    demo_service: DemoService = Depends(get_demo_service)
) -> DemoMetrics:
    """
    Generate synthetic performance metrics for demonstrations.
    
    Creates realistic performance data showing optimization improvements
    over time for visual demonstrations.
    """
    return await handle_synthetic_metrics(scenario, duration_hours, demo_service)


@router.post("/export/report")
async def export_demo_report(
    request: ExportReportRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService = Depends(get_demo_service),
    current_user: Optional[Dict] = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Export demo session as a comprehensive report.
    
    Generates a detailed report including optimization recommendations,
    ROI calculations, and implementation roadmap.
    """
    return await handle_export_report(request, background_tasks, demo_service, current_user)


@router.get("/session/{session_id}/status")
async def get_demo_session_status(
    session_id: str,
    demo_service: DemoService = Depends(get_demo_service)
) -> Dict[str, Any]:
    """
    Get the current status of a demo session.
    
    Returns progress, completed steps, and remaining actions.
    """
    return await handle_session_status(session_id, demo_service)


@router.post("/session/{session_id}/feedback")
async def submit_demo_feedback(
    session_id: str,
    feedback: Dict[str, Any],
    demo_service: DemoService = Depends(get_demo_service)
) -> Dict[str, str]:
    """
    Submit feedback for a demo session.
    
    Collects user feedback to improve demo experience.
    """
    return await handle_session_feedback(session_id, feedback, demo_service)


@router.get("/analytics/summary")
async def get_demo_analytics(
    days: int = 30,
    demo_service: DemoService = Depends(get_demo_service),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get demo analytics summary (admin only).
    
    Provides insights into demo usage, conversion rates, and effectiveness.
    """
    return await handle_demo_analytics(days, demo_service, current_user)


@router.websocket("/ws")
async def demo_websocket_endpoint(
    websocket: WebSocket,
    demo_service: DemoService = Depends(get_demo_service)
) -> None:
    """
    WebSocket endpoint for real-time demo interactions.
    
    Provides streaming responses and live optimization feedback.
    """
    await handle_demo_websocket(websocket, demo_service)
"""Demo route handlers with ≤8 line functions for enterprise demonstrations."""

from fastapi import HTTPException, BackgroundTasks
from typing import Optional, Dict, Any, List
from datetime import datetime, UTC
import uuid

from app.services.demo_service import DemoService
from app.logging_config import central_logger
from app.schemas.demo_schemas import (
    DemoChatRequest, DemoChatResponse, ROICalculationRequest, ROICalculationResponse,
    ExportReportRequest, ExportReportResponse, IndustryTemplate, DemoMetrics,
    DemoSessionFeedbackResponse, DemoAnalytics
)


async def handle_demo_chat(
    request: DemoChatRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService,
    current_user: Optional[Dict]
) -> DemoChatResponse:
    """Handle demo chat interactions with industry-specific AI optimization."""
    session_id = _get_or_create_session_id(request.session_id)
    result = await _process_chat_request(request, session_id, demo_service, current_user)
    _track_chat_interaction(background_tasks, demo_service, session_id, request)
    return _create_chat_response(result, session_id)


def _get_or_create_session_id(session_id: Optional[str]) -> str:
    """Get existing session ID or create a new one."""
    return session_id or str(uuid.uuid4())


async def _process_chat_request(
    request: DemoChatRequest,
    session_id: str,
    demo_service: DemoService,
    current_user: Optional[Dict]
) -> Dict[str, Any]:
    """Process the demo chat request using demo service."""
    try:
        return await demo_service.process_demo_chat(
            message=request.message,
            industry=request.industry,
            session_id=session_id,
            context=request.context,
            user_id=current_user.get("id") if current_user else None
        )
    except Exception as e:
        _log_and_raise_error("Demo chat processing failed", e)


def _track_chat_interaction(
    background_tasks: BackgroundTasks,
    demo_service: DemoService,
    session_id: str,
    request: DemoChatRequest
) -> None:
    """Track demo analytics in background."""
    background_tasks.add_task(
        demo_service.track_demo_interaction,
        session_id=session_id,
        interaction_type="chat",
        data={"industry": request.industry, "message_length": len(request.message)}
    )


def _create_chat_response(result: Dict[str, Any], session_id: str) -> DemoChatResponse:
    """Create chat response from service result."""
    return DemoChatResponse(
        response=result["response"],
        agents_involved=result["agents"],
        optimization_metrics=result["metrics"],
        session_id=session_id
    )


async def handle_industry_templates(
    industry: str,
    demo_service: DemoService
) -> List[IndustryTemplate]:
    """Get industry-specific demo templates and scenarios."""
    try:
        return await demo_service.get_industry_templates(industry)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _log_and_raise_error("Failed to retrieve templates", e)


async def handle_roi_calculation(
    request: ROICalculationRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService
) -> ROICalculationResponse:
    """Calculate ROI and cost savings for AI optimization."""
    result = await _calculate_roi_metrics(request, demo_service)
    _track_roi_calculation(background_tasks, demo_service, request, result)
    return ROICalculationResponse(**result)


async def _calculate_roi_metrics(
    request: ROICalculationRequest,
    demo_service: DemoService
) -> Dict[str, Any]:
    """Calculate ROI metrics using demo service."""
    try:
        return await demo_service.calculate_roi(
            current_spend=request.current_spend,
            request_volume=request.request_volume,
            average_latency=request.average_latency,
            industry=request.industry
        )
    except Exception as e:
        _log_and_raise_error("ROI calculation failed", e)


def _track_roi_calculation(
    background_tasks: BackgroundTasks,
    demo_service: DemoService,
    request: ROICalculationRequest,
    result: Dict[str, Any]
) -> None:
    """Track ROI calculation for analytics."""
    background_tasks.add_task(
        demo_service.track_demo_interaction,
        session_id=str(uuid.uuid4()),
        interaction_type="roi_calculation",
        data={"industry": request.industry, "potential_savings": result["annual_savings"]}
    )


async def handle_synthetic_metrics(
    scenario: str,
    duration_hours: int,
    demo_service: DemoService
) -> DemoMetrics:
    """Generate synthetic performance metrics for demonstrations."""
    try:
        metrics = await demo_service.generate_synthetic_metrics(
            scenario=scenario,
            duration_hours=duration_hours
        )
        return DemoMetrics(**metrics)
    except Exception as e:
        _log_and_raise_error("Failed to generate metrics", e)


async def handle_export_report(
    request: ExportReportRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService,
    current_user: Optional[Dict]
) -> ExportReportResponse:
    """Export demo session as a comprehensive report."""
    report_url = await _generate_demo_report(request, demo_service, current_user)
    _track_report_export(background_tasks, demo_service, request)
    return _create_export_response(report_url)


async def _generate_demo_report(
    request: ExportReportRequest,
    demo_service: DemoService,
    current_user: Optional[Dict]
) -> str:
    """Generate the demo report using demo service."""
    try:
        return await demo_service.generate_report(
            session_id=request.session_id,
            format=request.format,
            include_sections=request.include_sections,
            user_id=current_user.get("id") if current_user else None
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _log_and_raise_error("Failed to export report", e)


def _track_report_export(
    background_tasks: BackgroundTasks,
    demo_service: DemoService,
    request: ExportReportRequest
) -> None:
    """Track export for analytics."""
    background_tasks.add_task(
        demo_service.track_demo_interaction,
        session_id=request.session_id,
        interaction_type="report_export",
        data={"format": request.format, "sections": request.include_sections}
    )


def _create_export_response(report_url: str) -> ExportReportResponse:
    """Create export response with report URL."""
    return ExportReportResponse(
        status="success",
        report_url=report_url,
        expires_at=datetime.now(UTC).isoformat()
    )


async def handle_session_status(
    session_id: str,
    demo_service: DemoService
) -> Dict[str, Any]:
    """Get the current status of a demo session."""
    try:
        return await demo_service.get_session_status(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _log_and_raise_error("Failed to get session status", e)


async def handle_session_feedback(
    session_id: str,
    feedback: Dict[str, Any],
    demo_service: DemoService
) -> DemoSessionFeedbackResponse:
    """Submit feedback for a demo session."""
    try:
        await demo_service.submit_feedback(session_id, feedback)
        return DemoSessionFeedbackResponse(
            status="success",
            message="Feedback received"
        )
    except Exception as e:
        _log_and_raise_error("Failed to submit feedback", e)


async def handle_demo_analytics(
    days: int,
    demo_service: DemoService,
    current_user: Dict
) -> DemoAnalytics:
    """Get demo analytics summary (admin only)."""
    _validate_admin_access(current_user)
    try:
        analytics = await demo_service.get_analytics_summary(days=days)
        return DemoAnalytics(**analytics)
    except Exception as e:
        _log_and_raise_error("Failed to get analytics", e)


def _validate_admin_access(current_user: Dict) -> None:
    """Validate user has admin access."""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")


def _log_and_raise_error(message: str, error: Exception) -> None:
    """Log error and raise HTTP exception."""
    logger = central_logger.get_logger(__name__)
    logger.error(f"{message}: {str(error)}")
    raise HTTPException(status_code=500, detail=message)
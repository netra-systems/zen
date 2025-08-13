"""Demo API routes for enterprise demonstrations."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, UTC
import uuid
import json
import asyncio

from app.auth.auth_dependencies import get_current_user
from app.services.demo_service import DemoService, get_demo_service
from app.logging_config import central_logger
from app.ws_manager import manager

router = APIRouter(prefix="/api/demo", tags=["demo"])

# Pydantic models for request/response
class DemoChatRequest(BaseModel):
    """Request model for demo chat interactions."""
    message: str = Field(..., description="User message for demo chat")
    industry: str = Field(..., description="Industry context for demo")
    session_id: Optional[str] = Field(None, description="Demo session identifier")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")

class DemoChatResponse(BaseModel):
    """Response model for demo chat interactions."""
    response: str = Field(..., description="AI response")
    agents_involved: List[str] = Field(default_factory=list, description="Agents that processed the request")
    optimization_metrics: Dict[str, Any] = Field(default_factory=dict, description="Optimization metrics")
    session_id: str = Field(..., description="Demo session identifier")

class ROICalculationRequest(BaseModel):
    """Request model for ROI calculations."""
    current_spend: float = Field(..., gt=0, description="Current AI infrastructure spend")
    request_volume: int = Field(..., gt=0, description="Monthly request volume")
    average_latency: float = Field(..., gt=0, description="Average latency in ms")
    industry: str = Field(..., description="Industry for context-specific calculations")

class ROICalculationResponse(BaseModel):
    """Response model for ROI calculations."""
    current_annual_cost: float
    optimized_annual_cost: float
    annual_savings: float
    savings_percentage: float
    roi_months: int
    three_year_tco_reduction: float
    performance_improvements: Dict[str, float]

class ExportReportRequest(BaseModel):
    """Request model for report export."""
    session_id: str = Field(..., description="Demo session to export")
    format: str = Field("pdf", pattern="^(pdf|docx|html)$", description="Export format")
    include_sections: List[str] = Field(
        default_factory=lambda: ["summary", "metrics", "recommendations", "roadmap"],
        description="Sections to include in report"
    )

class IndustryTemplate(BaseModel):
    """Industry-specific template model."""
    industry: str
    name: str
    description: str
    prompt_template: str
    optimization_scenarios: List[Dict[str, Any]]
    typical_metrics: Dict[str, Any]

class DemoMetrics(BaseModel):
    """Demo performance metrics model."""
    latency_reduction: float
    throughput_increase: float
    cost_reduction: float
    accuracy_improvement: float
    timestamps: List[datetime]
    values: Dict[str, List[float]]

@router.post("/chat", response_model=DemoChatResponse)
async def demo_chat(
    request: DemoChatRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService = Depends(get_demo_service),
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """
    Handle demo chat interactions with industry-specific AI optimization.
    
    This endpoint simulates the multi-agent system for demonstrations,
    providing realistic optimization recommendations based on industry context.
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Process the demo chat request
        result = await demo_service.process_demo_chat(
            message=request.message,
            industry=request.industry,
            session_id=session_id,
            context=request.context,
            user_id=current_user.get("id") if current_user else None
        )
        
        # Track demo analytics in background
        background_tasks.add_task(
            demo_service.track_demo_interaction,
            session_id=session_id,
            interaction_type="chat",
            data={"industry": request.industry, "message_length": len(request.message)}
        )
        
        return DemoChatResponse(
            response=result["response"],
            agents_involved=result["agents"],
            optimization_metrics=result["metrics"],
            session_id=session_id
        )
        
    except Exception as e:
        logger = central_logger.get_logger(__name__)
        logger.error(f"Demo chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Demo chat processing failed: {str(e)}")

@router.get("/industry/{industry}/templates", response_model=List[IndustryTemplate])
async def get_industry_templates(
    industry: str,
    demo_service: DemoService = Depends(get_demo_service)
):
    """
    Get industry-specific demo templates and scenarios.
    
    Returns pre-configured templates for different industries including
    typical optimization scenarios and expected metrics.
    """
    try:
        templates = await demo_service.get_industry_templates(industry)
        return templates
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger = central_logger.get_logger(__name__)
        logger.error(f"Failed to get industry templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve templates")

@router.post("/roi/calculate", response_model=ROICalculationResponse)
async def calculate_roi(
    request: ROICalculationRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService = Depends(get_demo_service)
):
    """
    Calculate ROI and cost savings for AI optimization.
    
    Provides detailed financial projections based on current spend
    and expected optimization improvements.
    """
    try:
        result = await demo_service.calculate_roi(
            current_spend=request.current_spend,
            request_volume=request.request_volume,
            average_latency=request.average_latency,
            industry=request.industry
        )
        
        # Track ROI calculation for analytics
        background_tasks.add_task(
            demo_service.track_demo_interaction,
            session_id=str(uuid.uuid4()),
            interaction_type="roi_calculation",
            data={"industry": request.industry, "potential_savings": result["annual_savings"]}
        )
        
        return ROICalculationResponse(**result)
        
    except Exception as e:
        logger = central_logger.get_logger(__name__)
        logger.error(f"ROI calculation error: {str(e)}")
        raise HTTPException(status_code=500, detail="ROI calculation failed")

@router.get("/metrics/synthetic", response_model=DemoMetrics)
async def get_synthetic_metrics(
    scenario: str = "standard",
    duration_hours: int = 24,
    demo_service: DemoService = Depends(get_demo_service)
):
    """
    Generate synthetic performance metrics for demonstrations.
    
    Creates realistic performance data showing optimization improvements
    over time for visual demonstrations.
    """
    try:
        metrics = await demo_service.generate_synthetic_metrics(
            scenario=scenario,
            duration_hours=duration_hours
        )
        return DemoMetrics(**metrics)
    except Exception as e:
        logger = central_logger.get_logger(__name__)
        logger.error(f"Synthetic metrics generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate metrics")

@router.post("/export/report")
async def export_demo_report(
    request: ExportReportRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService = Depends(get_demo_service),
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """
    Export demo session as a comprehensive report.
    
    Generates a detailed report including optimization recommendations,
    ROI calculations, and implementation roadmap.
    """
    try:
        # Generate the report
        report_url = await demo_service.generate_report(
            session_id=request.session_id,
            format=request.format,
            include_sections=request.include_sections,
            user_id=current_user.get("id") if current_user else None
        )
        
        # Track export for analytics
        background_tasks.add_task(
            demo_service.track_demo_interaction,
            session_id=request.session_id,
            interaction_type="report_export",
            data={"format": request.format, "sections": request.include_sections}
        )
        
        return {
            "status": "success",
            "report_url": report_url,
            "expires_at": datetime.now(UTC).isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger = central_logger.get_logger(__name__)
        logger.error(f"Report export error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export report")

@router.get("/session/{session_id}/status")
async def get_demo_session_status(
    session_id: str,
    demo_service: DemoService = Depends(get_demo_service)
):
    """
    Get the current status of a demo session.
    
    Returns progress, completed steps, and remaining actions.
    """
    try:
        status = await demo_service.get_session_status(session_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger = central_logger.get_logger(__name__)
        logger.error(f"Session status error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get session status")

@router.post("/session/{session_id}/feedback")
async def submit_demo_feedback(
    session_id: str,
    feedback: Dict[str, Any],
    demo_service: DemoService = Depends(get_demo_service)
):
    """
    Submit feedback for a demo session.
    
    Collects user feedback to improve demo experience.
    """
    try:
        await demo_service.submit_feedback(session_id, feedback)
        return {"status": "success", "message": "Feedback received"}
    except Exception as e:
        logger = central_logger.get_logger(__name__)
        logger.error(f"Feedback submission error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")

@router.get("/analytics/summary")
async def get_demo_analytics(
    days: int = 30,
    demo_service: DemoService = Depends(get_demo_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get demo analytics summary (admin only).
    
    Provides insights into demo usage, conversion rates, and effectiveness.
    """
    # Check admin permissions
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
        
    try:
        analytics = await demo_service.get_analytics_summary(days=days)
        return analytics
    except Exception as e:
        logger = central_logger.get_logger(__name__)
        logger.error(f"Analytics retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get analytics")

@router.websocket("/ws")
async def demo_websocket_endpoint(
    websocket: WebSocket,
    demo_service: DemoService = Depends(get_demo_service)
):
    """
    WebSocket endpoint for real-time demo interactions.
    
    Provides streaming responses and live optimization feedback.
    """
    await websocket.accept()
    logger = central_logger.get_logger(__name__)
    
    # Generate session ID for this WebSocket connection
    session_id = f"demo-ws-{uuid.uuid4()}"
    
    try:
        await websocket.send_json({
            "type": "connection_established",
            "session_id": session_id,
            "message": "Connected to Netra AI Demo WebSocket"
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle different message types
            if message_data.get("type") == "chat":
                # Send initial acknowledgment
                await websocket.send_json({
                    "type": "processing_started",
                    "agents": ["triage", "analysis", "optimization"]
                })
                
                # Simulate agent progression with real-time updates
                agents = ["triage", "analysis", "optimization", "reporting"]
                for i, agent in enumerate(agents):
                    await asyncio.sleep(0.8)  # Simulate processing time
                    await websocket.send_json({
                        "type": "agent_update",
                        "active_agent": agent,
                        "progress": (i + 1) / len(agents) * 100,
                        "message": f"Agent {agent} is processing your request..."
                    })
                
                # Process the actual chat message
                result = await demo_service.process_demo_chat(
                    message=message_data.get("message", ""),
                    industry=message_data.get("industry", "technology"),
                    session_id=session_id,
                    context=message_data.get("context", {})
                )
                
                # Send the final response
                await websocket.send_json({
                    "type": "chat_response",
                    "response": result["response"],
                    "agents_involved": result["agents"],
                    "optimization_metrics": result["metrics"],
                    "session_id": session_id
                })
                
            elif message_data.get("type") == "metrics":
                # Stream synthetic metrics
                metrics = await demo_service.generate_synthetic_metrics(
                    scenario=message_data.get("scenario", "standard"),
                    duration_hours=1
                )
                
                # Send metrics in chunks for real-time visualization
                for i in range(len(metrics["timestamps"])):
                    await websocket.send_json({
                        "type": "metrics_update",
                        "timestamp": metrics["timestamps"][i].isoformat() if hasattr(metrics["timestamps"][i], 'isoformat') else str(metrics["timestamps"][i]),
                        "values": {
                            key: values[i] if i < len(values) else 0
                            for key, values in metrics["values"].items()
                        }
                    })
                    await asyncio.sleep(0.1)  # Stream data points
                    
            elif message_data.get("type") == "ping":
                # Handle ping for connection keep-alive
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info(f"Demo WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Demo WebSocket error: {str(e)}")
        await websocket.close(code=1011, reason=str(e))
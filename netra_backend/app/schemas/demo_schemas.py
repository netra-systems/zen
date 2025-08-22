"""Demo API Pydantic models for enterprise demonstrations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class DemoSessionStatus(BaseModel):
    """Demo session status model."""
    session_id: str
    status: str
    progress: float
    completed_steps: List[str]
    remaining_actions: List[str]
    created_at: datetime
    updated_at: datetime


class DemoFeedback(BaseModel):
    """Demo feedback model."""
    session_id: str
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    comments: Optional[str] = Field(None, description="Additional feedback comments")
    helpful_features: List[str] = Field(default_factory=list, description="Features found helpful")
    improvement_suggestions: List[str] = Field(default_factory=list, description="Suggested improvements")


class DemoAnalytics(BaseModel):
    """Demo analytics summary model."""
    total_sessions: int
    unique_users: int
    completion_rate: float
    average_rating: float
    top_industries: List[Dict[str, Any]]
    engagement_metrics: Dict[str, float]
    conversion_metrics: Dict[str, float]


class DemoWSMessage(BaseModel):
    """WebSocket message model for demo interactions."""
    type: str = Field(..., description="Message type")
    session_id: Optional[str] = Field(None, description="Session identifier")
    message: Optional[str] = Field(None, description="Message content")
    industry: Optional[str] = Field(None, description="Industry context")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    scenario: Optional[str] = Field(None, description="Metrics scenario")


class DemoWSResponse(BaseModel):
    """WebSocket response model for demo interactions."""
    type: str = Field(..., description="Response type")
    session_id: Optional[str] = Field(None, description="Session identifier")
    message: Optional[str] = Field(None, description="Response message")
    response: Optional[str] = Field(None, description="Chat response")
    agents_involved: Optional[List[str]] = Field(None, description="Agents that processed request")
    optimization_metrics: Optional[Dict[str, Any]] = Field(None, description="Optimization metrics")
    active_agent: Optional[str] = Field(None, description="Currently active agent")
    progress: Optional[float] = Field(None, description="Processing progress")
    timestamp: Optional[str] = Field(None, description="Response timestamp")
    values: Optional[Dict[str, Any]] = Field(None, description="Metric values")


class ExportReportResponse(BaseModel):
    """Response model for report export."""
    status: str
    report_url: str
    expires_at: str


class DemoSessionFeedbackResponse(BaseModel):
    """Response model for demo session feedback."""
    status: str
    message: str
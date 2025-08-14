# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:48:05.517910+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to agent support files
# Git: v6 | 2c55fb99 | dirty (32 uncommitted)
# Change: Feature | Scope: Component | Risk: Medium
# Session: 3338d1f9-246a-461a-8cae-a81a10615db4 | Seq: 2
# Review: Pending | Score: 85
# ================================
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from app.agents.triage_sub_agent.models import TriageResult
from app.agents.data_sub_agent.models import DataAnalysisResponse, AnomalyDetectionResponse

class OptimizationsResult(BaseModel):
    """Typed model for optimization results."""
    optimization_type: str
    recommendations: List[str] = Field(default_factory=list)
    cost_savings: Optional[float] = None
    performance_improvement: Optional[float] = None
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.8)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionPlanResult(BaseModel):
    """Typed model for action plan results."""
    plan_steps: List[Dict[str, Any]] = Field(default_factory=list)
    priority: str = "medium"
    estimated_duration: Optional[str] = None
    required_resources: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReportResult(BaseModel):
    """Typed model for report results."""
    report_type: str
    content: str
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    attachments: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SyntheticDataResult(BaseModel):
    """Typed model for synthetic data results."""
    data_type: str
    generation_method: str
    sample_count: int = 0
    quality_score: float = Field(ge=0.0, le=1.0, default=0.8)
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SupplyResearchResult(BaseModel):
    """Typed model for supply research results."""
    research_scope: str
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    confidence_level: float = Field(ge=0.0, le=1.0, default=0.8)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeepAgentState(BaseModel):
    """Strongly typed state for the deep agent system."""
    user_request: str
    chat_thread_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Typed result fields using proper models
    triage_result: Optional[Union[TriageResult, Dict[str, Any]]] = None
    data_result: Optional[Union[DataAnalysisResponse, Dict[str, Any]]] = None
    optimizations_result: Optional[OptimizationsResult] = None
    action_plan_result: Optional[ActionPlanResult] = None
    report_result: Optional[ReportResult] = None
    synthetic_data_result: Optional[SyntheticDataResult] = None
    supply_research_result: Optional[SupplyResearchResult] = None
    
    final_report: Optional[str] = None
    step_count: int = 0  # Added for agent tracking
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('step_count')
    def validate_step_count(cls, v: int) -> int:
        """Validate step count is non-negative."""
        if v < 0:
            raise ValueError('Step count must be non-negative')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return self.model_dump(exclude_none=True)
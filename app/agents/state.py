"""Agent state management models with immutable patterns."""
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from pydantic import BaseModel, Field, validator
from datetime import datetime

# Import actual types to avoid circular dependencies
from app.agents.triage_sub_agent.models import TriageResult

# Use TYPE_CHECKING to break circular import
if TYPE_CHECKING:
    from app.agents.data_sub_agent.models import DataAnalysisResponse, AnomalyDetectionResponse


class AgentMetadata(BaseModel):
    """Metadata for agent execution tracking."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    execution_context: Dict[str, str] = Field(default_factory=dict)
    custom_fields: Dict[str, str] = Field(default_factory=dict)
    
    def update_timestamp(self) -> 'AgentMetadata':
        """Update the last updated timestamp."""
        return self.model_copy(update={'last_updated': datetime.utcnow()})


class PlanStep(BaseModel):
    """Typed model for action plan steps."""
    step_id: str
    description: str
    estimated_duration: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    resources_needed: List[str] = Field(default_factory=list)
    status: str = "pending"
    
    
class ReportSection(BaseModel):
    """Typed model for report sections."""
    section_id: str
    title: str
    content: str
    section_type: str = "standard"
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)


class OptimizationsResult(BaseModel):
    """Typed model for optimization results."""
    optimization_type: str
    recommendations: List[str] = Field(default_factory=list)
    cost_savings: Optional[float] = None
    performance_improvement: Optional[float] = None
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.8)
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)


class ActionPlanResult(BaseModel):
    """Typed model for action plan results."""
    plan_steps: List[PlanStep] = Field(default_factory=list)
    priority: str = "medium"
    estimated_duration: Optional[str] = None
    required_resources: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)


class ReportResult(BaseModel):
    """Typed model for report results."""
    report_type: str
    content: str
    sections: List[ReportSection] = Field(default_factory=list)
    attachments: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)


class SyntheticDataResult(BaseModel):
    """Typed model for synthetic data results."""
    data_type: str
    generation_method: str
    sample_count: int = 0
    quality_score: float = Field(ge=0.0, le=1.0, default=0.8)
    file_path: Optional[str] = None
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)


class SupplyResearchResult(BaseModel):
    """Typed model for supply research results."""
    research_scope: str
    findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    confidence_level: float = Field(ge=0.0, le=1.0, default=0.8)
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)


class DeepAgentState(BaseModel):
    """Strongly typed state for the deep agent system."""
    user_request: str
    chat_thread_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Typed result fields using proper models
    triage_result: Optional[TriageResult] = None
    data_result: Optional[Union["DataAnalysisResponse", "AnomalyDetectionResponse"]] = None
    optimizations_result: Optional[OptimizationsResult] = None
    action_plan_result: Optional[ActionPlanResult] = None
    report_result: Optional[ReportResult] = None
    synthetic_data_result: Optional[SyntheticDataResult] = None
    supply_research_result: Optional[SupplyResearchResult] = None
    
    final_report: Optional[str] = None
    step_count: int = 0  # Added for agent tracking
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)
    
    @validator('step_count')
    def validate_step_count(cls, v: int) -> int:
        """Validate step count is within reasonable bounds."""
        if v < 0:
            raise ValueError('Step count must be non-negative')
        if v > 10000:  # Reasonable upper bound
            raise ValueError('Step count exceeds maximum allowed value (10000)')
        return v
    
    @validator('optimizations_result')
    def validate_optimizations_result(cls, v: OptimizationsResult) -> OptimizationsResult:
        """Validate optimizations result bounds."""
        if v is None:
            return v
        
        # Check cost savings bounds
        if v.cost_savings is not None:
            if v.cost_savings < 0:
                raise ValueError('Cost savings cannot be negative')
            if v.cost_savings > 1000000:  # $1M upper bound
                raise ValueError('Cost savings exceeds reasonable limit')
        
        # Check performance improvement bounds
        if v.performance_improvement is not None:
            if v.performance_improvement < -100:
                raise ValueError('Performance improvement cannot be less than -100%')
            if v.performance_improvement > 10000:  # 100x improvement upper bound
                raise ValueError('Performance improvement exceeds reasonable limit')
        
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return self.model_dump(exclude_none=True)
    
    def copy_with_updates(self, **updates: Any) -> 'DeepAgentState':
        """Create a new instance with updated fields (immutable pattern)."""
        current_data = self.model_dump()
        current_data.update(updates)
        return DeepAgentState(**current_data)
    
    def increment_step_count(self) -> 'DeepAgentState':
        """Create a new instance with incremented step count."""
        return self.copy_with_updates(step_count=self.step_count + 1)
    
    def add_metadata(self, key: str, value: str) -> 'DeepAgentState':
        """Create a new instance with additional metadata."""
        updated_custom = self.metadata.custom_fields.copy()
        updated_custom[key] = value
        new_metadata = self.metadata.model_copy(
            update={'custom_fields': updated_custom}
        ).update_timestamp()
        return self.copy_with_updates(metadata=new_metadata)
    
    def clear_sensitive_data(self) -> 'DeepAgentState':
        """Create a new instance with sensitive data cleared."""
        return self.copy_with_updates(
            triage_result=None,
            data_result=None,
            optimizations_result=None,
            action_plan_result=None,
            report_result=None,
            synthetic_data_result=None,
            supply_research_result=None,
            final_report=None,
            metadata=AgentMetadata()
        )
    
    def merge_from(self, other_state: 'DeepAgentState') -> 'DeepAgentState':
        """Create new state with data merged from another state (immutable)."""
        if not isinstance(other_state, DeepAgentState):
            raise TypeError("other_state must be a DeepAgentState instance")
        
        # Prepare merged data
        merged_custom = self.metadata.custom_fields.copy()
        merged_context = self.metadata.execution_context.copy()
        
        if other_state.metadata:
            merged_custom.update(other_state.metadata.custom_fields)
            merged_context.update(other_state.metadata.execution_context)
        
        merged_metadata = AgentMetadata(
            execution_context=merged_context,
            custom_fields=merged_custom
        )
        
        # Create new instance with merged data
        return self.copy_with_updates(
            triage_result=other_state.triage_result or self.triage_result,
            data_result=other_state.data_result or self.data_result,
            optimizations_result=other_state.optimizations_result or self.optimizations_result,
            action_plan_result=other_state.action_plan_result or self.action_plan_result,
            report_result=other_state.report_result or self.report_result,
            synthetic_data_result=other_state.synthetic_data_result or self.synthetic_data_result,
            supply_research_result=other_state.supply_research_result or self.supply_research_result,
            final_report=other_state.final_report or self.final_report,
            step_count=max(self.step_count, other_state.step_count),
            metadata=merged_metadata
        )


def rebuild_model() -> None:
    """Rebuild the model after imports are complete."""
    try:
        DeepAgentState.model_rebuild()
    except Exception:
        # Safe to ignore - model will rebuild when needed
        pass

# Initialize model rebuild
rebuild_model()
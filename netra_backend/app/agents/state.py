"""Agent state management models with immutable patterns."""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

# Import actual types needed at runtime
from netra_backend.app.agents.triage_sub_agent.models import TriageResult
from netra_backend.app.core.json_parsing_utils import parse_string_list_field
from netra_backend.app.schemas.agent_models import AgentMetadata
from netra_backend.app.schemas.shared_types import (
    AnomalyDetectionResponse,
    DataAnalysisResponse,
)

# Import types only for type checking to avoid circular dependencies  
if TYPE_CHECKING:
    pass


# AgentMetadata is now imported from agent_models.py - single source of truth


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
    
    @field_validator('recommendations', mode='before')
    @classmethod
    def parse_recommendations(cls, v: Any) -> List[str]:
        """Parse recommendations field, converting dicts to strings"""
        return parse_string_list_field(v)


class ActionPlanResult(BaseModel):
    """Typed model for action plan results."""
    # Core action plan fields from agent implementation
    action_plan_summary: str = "Action plan generated"
    total_estimated_time: str = "To be determined"
    required_approvals: List[str] = Field(default_factory=list)
    actions: List[dict] = Field(default_factory=list)
    execution_timeline: List[dict] = Field(default_factory=list)
    supply_config_updates: List[dict] = Field(default_factory=list)
    post_implementation: dict = Field(default_factory=dict)
    cost_benefit_analysis: dict = Field(default_factory=dict)
    
    # Legacy fields for compatibility
    plan_steps: List[PlanStep] = Field(default_factory=list)
    priority: str = "medium"
    estimated_duration: Optional[str] = None
    required_resources: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
    
    # Extraction status fields
    partial_extraction: bool = False
    extracted_fields: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    
    # Metadata
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)
    
    @field_validator('required_resources', mode='before')
    @classmethod
    def parse_required_resources(cls, v: Any) -> List[str]:
        """Parse required_resources field, converting dicts to strings"""
        return parse_string_list_field(v)
    
    @field_validator('success_metrics', mode='before')
    @classmethod
    def parse_success_metrics(cls, v: Any) -> List[str]:
        """Parse success_metrics field, converting dicts to strings"""
        return parse_string_list_field(v)


class ReportResult(BaseModel):
    """Typed model for report results."""
    report_type: str
    content: str
    sections: List[ReportSection] = Field(default_factory=list)
    attachments: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)
    
    @field_validator('attachments', mode='before')
    @classmethod
    def parse_attachments(cls, v: Any) -> List[str]:
        """Parse attachments field, converting dicts to strings"""
        return parse_string_list_field(v)


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
    user_request: str = "default_request"  # Default for backward compatibility
    chat_thread_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Strongly typed result fields with proper type unions
    triage_result: Optional["TriageResult"] = None
    data_result: Optional[Union["DataAnalysisResponse", "AnomalyDetectionResponse"]] = None
    optimizations_result: Optional[OptimizationsResult] = None
    action_plan_result: Optional[ActionPlanResult] = None
    report_result: Optional[ReportResult] = None
    synthetic_data_result: Optional[SyntheticDataResult] = None
    supply_research_result: Optional[SupplyResearchResult] = None
    
    final_report: Optional[str] = None
    step_count: int = 0  # Added for agent tracking
    messages: List[Dict[str, Any]] = Field(default_factory=list)  # Added for E2E test compatibility
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)
    quality_metrics: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('step_count')
    @classmethod
    def validate_step_count(cls, v: int) -> int:
        """Validate step count is within reasonable bounds."""
        if v < 0:
            raise ValueError('Step count must be non-negative')
        if v > 10000:  # Reasonable upper bound
            raise ValueError('Step count exceeds maximum allowed value (10000)')
        return v
    
    @field_validator('optimizations_result')
    @classmethod
    def validate_optimizations_result(cls, v: OptimizationsResult) -> OptimizationsResult:
        """Validate optimizations result bounds."""
        if v is None:
            return v
        
        cls._validate_cost_savings(v.cost_savings)
        cls._validate_performance_improvement(v.performance_improvement)
        return v
    
    @classmethod
    def _validate_cost_savings(cls, cost_savings: Optional[float]) -> None:
        """Validate cost savings bounds."""
        if cost_savings is None:
            return
        if cost_savings < 0:
            raise ValueError('Cost savings cannot be negative')
        if cost_savings > 1000000:  # $1M upper bound
            raise ValueError('Cost savings exceeds reasonable limit')
    
    @classmethod
    def _validate_performance_improvement(cls, improvement: Optional[float]) -> None:
        """Validate performance improvement bounds."""
        if improvement is None:
            return
        if improvement < -100:
            raise ValueError('Performance improvement cannot be less than -100%')
        if improvement > 10000:  # 100x improvement upper bound
            raise ValueError('Performance improvement exceeds reasonable limit')
    
    def to_dict(self) -> Dict[str, Union[str, int, float, bool, None]]:
        """Convert state to dictionary with typed values."""
        return self.model_dump(exclude_none=True)
    
    def copy_with_updates(self, **updates: Union[str, int, float, bool, None]
                         ) -> 'DeepAgentState':
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
        
        merged_metadata = self._create_merged_metadata(other_state)
        merged_results = self._create_merged_results(other_state)
        return self.copy_with_updates(**merged_results, metadata=merged_metadata)
    
    def _create_merged_metadata(self, other_state: 'DeepAgentState') -> AgentMetadata:
        """Create merged metadata from current and other state."""
        merged_custom = self.metadata.custom_fields.copy()
        merged_context = self.metadata.execution_context.copy()
        
        if other_state.metadata:
            merged_custom.update(other_state.metadata.custom_fields)
            merged_context.update(other_state.metadata.execution_context)
        
        return AgentMetadata(execution_context=merged_context, custom_fields=merged_custom)
    
    def _create_merged_results(self, other_state: 'DeepAgentState') -> dict:
        """Create merged result fields from current and other state."""
        return {
            'triage_result': other_state.triage_result or self.triage_result,
            'data_result': other_state.data_result or self.data_result,
            'optimizations_result': other_state.optimizations_result or self.optimizations_result,
            'action_plan_result': other_state.action_plan_result or self.action_plan_result,
            'report_result': other_state.report_result or self.report_result,
            'synthetic_data_result': other_state.synthetic_data_result or self.synthetic_data_result,
            'supply_research_result': other_state.supply_research_result or self.supply_research_result,
            'final_report': other_state.final_report or self.final_report,
            'step_count': max(self.step_count, other_state.step_count)
        }


def rebuild_model() -> None:
    """Rebuild the model after imports are complete."""
    try:
        DeepAgentState.model_rebuild()
    except Exception:
        # Safe to ignore - model will rebuild when needed
        pass

# Initialize model rebuild
rebuild_model()

# Force model rebuild to resolve forward references
try:
    DeepAgentState.model_rebuild()
except Exception:
    # Safe to ignore - will rebuild when dependencies are available
    pass
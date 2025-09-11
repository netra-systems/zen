"""Agent state management models with immutable patterns.

DEPRECATION NOTICE: DeepAgentState is deprecated and will be removed in v3.0.0.
Use UserExecutionContext pattern for new agent implementations.
"""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
import warnings

from pydantic import BaseModel, Field, field_validator

# Import actual types needed at runtime
from netra_backend.app.agents.triage.models import TriageResult
from netra_backend.app.core.serialization.unified_json_handler import parse_list_field
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
        return parse_list_field(v)
    
    @field_validator('cost_savings')
    @classmethod
    def validate_cost_savings(cls, v: Optional[float]) -> Optional[float]:
        """Validate cost savings bounds."""
        if v is None:
            return v
        if v < 0:
            raise ValueError('Cost savings cannot be negative')
        if v > 1000000:  # $1M upper bound
            raise ValueError('Cost savings exceeds reasonable limit')
        return v
    
    @field_validator('performance_improvement')
    @classmethod
    def validate_performance_improvement(cls, v: Optional[float]) -> Optional[float]:
        """Validate performance improvement bounds."""
        if v is None:
            return v
        if v < -100:
            raise ValueError('Performance improvement cannot be less than -100%')
        if v > 10000:  # 100x improvement upper bound
            raise ValueError('Performance improvement exceeds reasonable limit')
        return v


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
        return parse_list_field(v)
    
    @field_validator('success_metrics', mode='before')
    @classmethod
    def parse_success_metrics(cls, v: Any) -> List[str]:
        """Parse success_metrics field, converting dicts to strings"""
        return parse_list_field(v)


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
        return parse_list_field(v)


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
    """DEPRECATED: Strongly typed state for the deep agent system.
    
    🚨 CRITICAL DEPRECATION WARNING: DeepAgentState creates user isolation risks
    and will be REMOVED in v3.0.0 (Q1 2025).
    
    📋 MIGRATION REQUIRED:
    - Replace with UserExecutionContext pattern for complete user isolation
    - Use context.metadata for request-specific data instead of global state
    - Access database via context.db_session instead of global sessions
    
    📖 Migration Guide: See EXECUTION_PATTERN_TECHNICAL_DESIGN.md
    ⚠️  USER DATA AT RISK: This pattern may cause data leakage between users
    
    🚀 GOLDEN PATH FIX (2025-09-10): Added thread_id property for backward compatibility.
    The supervisor agent execution was failing with "'DeepAgentState' object has no attribute 'thread_id'"
    because the model has chat_thread_id but code expects thread_id. This fix enables:
    - Property access: state.thread_id maps to state.chat_thread_id
    - Property setting: state.thread_id = value updates state.chat_thread_id
    - Constructor compatibility: thread_id parameter maps to chat_thread_id field
    - copy_with_updates compatibility: thread_id updates work correctly
    This protects the $500K+ ARR Golden Path user workflow from thread_id attribute errors.
    """
    user_request: str = "default_request"  # Default for backward compatibility
    user_prompt: str = "default_request"   # GOLDEN PATH FIX: Interface alignment for execution engines
    chat_thread_id: Optional[str] = None
    user_id: Optional[str] = None
    run_id: Optional[str] = None  # Unique identifier for this execution run
    agent_input: Optional[Dict[str, Any]] = None  # Input parameters for agent execution
    
    # Strongly typed result fields with proper type unions
    triage_result: Optional["TriageResult"] = None
    data_result: Optional[Union["DataAnalysisResponse", "AnomalyDetectionResponse"]] = None
    optimizations_result: Optional[OptimizationsResult] = None
    action_plan_result: Optional[ActionPlanResult] = None
    report_result: Optional[ReportResult] = None
    synthetic_data_result: Optional[SyntheticDataResult] = None
    supply_research_result: Optional[SupplyResearchResult] = None
    corpus_admin_result: Optional[Dict[str, Any]] = None
    corpus_admin_error: Optional[str] = None
    
    final_report: Optional[str] = None
    step_count: int = 0  # Added for agent tracking
    messages: List[Dict[str, Any]] = Field(default_factory=list)  # Added for E2E test compatibility
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)
    quality_metrics: Dict[str, Any] = Field(default_factory=dict)
    context_tracking: Dict[str, Any] = Field(default_factory=dict)  # Added for E2E test compatibility
    
    # PHASE 1 BACKWARDS COMPATIBILITY FIX: Add agent_context for UserExecutionContext compatibility
    # This field provides backwards compatibility with execution code that expects agent_context
    # from the UserExecutionContext migration. Should be removed in Phase 2 after proper migration.
    agent_context: Dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, **data):
        """Initialize DeepAgentState with deprecation warning and field synchronization."""
        # GOLDEN PATH FIX: Synchronize user_request and user_prompt fields for backward compatibility
        if 'user_prompt' in data and 'user_request' not in data:
            data['user_request'] = data['user_prompt']
        elif 'user_request' in data and 'user_prompt' not in data:
            data['user_prompt'] = data['user_request']
        elif 'user_prompt' in data and 'user_request' in data:
            # If both are provided, prefer user_prompt as it's the expected interface
            data['user_request'] = data['user_prompt']
        
        # GOLDEN PATH FIX: Handle thread_id backward compatibility
        # Map thread_id to chat_thread_id for compatibility
        if 'thread_id' in data and 'chat_thread_id' not in data:
            data['chat_thread_id'] = data.pop('thread_id')
        elif 'thread_id' in data and 'chat_thread_id' in data:
            # If both provided, use thread_id as the canonical value
            data['chat_thread_id'] = data.pop('thread_id')
        
        # Issue comprehensive deprecation warning
        warnings.warn(
            f"🚨 CRITICAL DEPRECATION: DeepAgentState usage creates user isolation risks. "
            f"This pattern will be REMOVED in v3.0.0 (Q1 2025). "
            f"\n"
            f"📋 IMMEDIATE MIGRATION REQUIRED:"
            f"\n1. Replace with UserExecutionContext pattern"
            f"\n2. Use 'context.metadata' for request data instead of DeepAgentState fields"
            f"\n3. Access database via 'context.db_session' instead of global sessions"
            f"\n4. Use 'context.user_id', 'context.thread_id', 'context.run_id' for identifiers"
            f"\n"
            f"📖 Migration Guide: See EXECUTION_PATTERN_TECHNICAL_DESIGN.md"
            f"\n⚠️  CRITICAL: Multiple users may see each other's data with this pattern",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(**data)
    
    @property
    def thread_id(self) -> Optional[str]:
        """GOLDEN PATH FIX: Property to access chat_thread_id as thread_id for backward compatibility."""
        return self.chat_thread_id
    
    @thread_id.setter
    def thread_id(self, value: Optional[str]) -> None:
        """GOLDEN PATH FIX: Setter to update chat_thread_id via thread_id for backward compatibility."""
        self.chat_thread_id = value
    
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
        """Validate optimizations result - validation is now handled by OptimizationsResult itself."""
        return v
    
    def to_dict(self) -> Dict[str, Union[str, int, float, bool, None]]:
        """Convert state to dictionary with typed values."""
        return self.model_dump(exclude_none=True, mode='json')
    
    def copy_with_updates(self, **updates: Union[str, int, float, bool, None]
                         ) -> 'DeepAgentState':
        """Create a new instance with updated fields (immutable pattern)."""
        current_data = self.model_dump()
        current_data.update(updates)
        
        # GOLDEN PATH FIX: Maintain synchronization between user_request and user_prompt
        if 'user_prompt' in updates and 'user_request' not in updates:
            current_data['user_request'] = updates['user_prompt']
        elif 'user_request' in updates and 'user_prompt' not in updates:
            current_data['user_prompt'] = updates['user_request']
        
        # GOLDEN PATH FIX: Handle thread_id backward compatibility in copy_with_updates
        if 'thread_id' in updates and 'chat_thread_id' not in updates:
            current_data['chat_thread_id'] = updates.pop('thread_id')
        elif 'thread_id' in updates and 'chat_thread_id' in updates:
            # If both provided, use thread_id as the canonical value
            current_data['chat_thread_id'] = updates.pop('thread_id')
        
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
            corpus_admin_result=None,
            corpus_admin_error=None,
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
            'corpus_admin_result': other_state.corpus_admin_result or self.corpus_admin_result,
            'corpus_admin_error': other_state.corpus_admin_error or self.corpus_admin_error,
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
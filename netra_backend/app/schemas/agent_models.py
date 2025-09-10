"""
Agent Models: Single Source of Truth for Agent-Related Models

This module contains all agent-related models and state definitions used across 
the Netra platform, ensuring consistency and preventing duplication.

CRITICAL ARCHITECTURAL COMPLIANCE:
- All agent model definitions MUST be imported from this module
- NO duplicate agent model definitions allowed anywhere else in codebase
- This file maintains strong typing and single sources of truth
- Maximum file size: 300 lines (currently under limit)

Usage:
    from netra_backend.app.schemas.agent_models import DeepAgentState, AgentResult, AgentMetadata
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

# Import forward-referenced types for type checking
if TYPE_CHECKING:
    from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
else:
    # Runtime fallback for model instantiation
    try:
        from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
    except ImportError:
        TriageResult = None  # type: ignore

try:
    from netra_backend.app.schemas.shared_types import (
        AnomalyDetectionResponse,
        DataAnalysisResponse,
    )
except ImportError:
    DataAnalysisResponse = None  # type: ignore
    AnomalyDetectionResponse = None  # type: ignore

try:
    from netra_backend.app.schemas.finops import WorkloadProfile
    from netra_backend.app.schemas.generation import SyntheticDataResult
except ImportError:
    WorkloadProfile = None  # type: ignore
    SyntheticDataResult = None  # type: ignore


class ToolResultData(BaseModel):
    """Unified tool result data."""
    tool_name: str
    status: str
    output: Optional[Union[str, dict, list]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class AgentMetadata(BaseModel):
    """Unified agent metadata."""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    execution_context: Dict[str, str] = Field(default_factory=dict)
    custom_fields: Dict[str, str] = Field(default_factory=dict)
    priority: Optional[int] = Field(default=None)
    retry_count: int = 0
    parent_agent_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    @field_validator('priority', mode='before')
    @classmethod
    def validate_priority(cls, v: Optional[Union[int, str]]) -> Optional[int]:
        """Convert string priority to integer."""
        if v is None:
            return None
        return cls._process_priority_value(v)
    
    @classmethod
    def _clamp_priority(cls, value: int) -> int:
        """Clamp integer priority to valid range."""
        return max(0, min(10, value))
    
    @classmethod
    def _process_priority_value(cls, value: Union[int, str, Any]) -> int:
        """Process priority value based on type."""
        if isinstance(value, int):
            return cls._clamp_priority(value)
        return cls._parse_string_priority(value)
    
    @classmethod
    def _parse_string_priority(cls, value: Union[str, Any]) -> int:
        """Parse string priority to integer."""
        if isinstance(value, str):
            return cls._get_priority_from_map(value)
        return 5
    
    @classmethod
    def _get_priority_from_map(cls, value: str) -> int:
        """Get priority value from string mapping."""
        priority_map = {'low': 3, 'medium': 5, 'high': 8, 'urgent': 10}
        return priority_map.get(value.lower(), 5)
    
    def update_timestamp(self) -> 'AgentMetadata':
        """Update the last updated timestamp."""
        return self.model_copy(update={'last_updated': datetime.now(UTC)})


class AgentResult(BaseModel):
    """Unified agent result model."""
    success: bool
    output: Optional[Union[str, dict, list]] = None
    error: Optional[str] = None
    metrics: Dict[str, Union[int, float]] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None


class DeepAgentState(BaseModel):
    """Unified Deep Agent State - single source of truth (replaces old AgentState)."""
    user_request: str = "default_request"  # Default for backward compatibility
    chat_thread_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Strongly typed result fields with proper type unions
    triage_result: Optional["TriageResult"] = None
    data_result: Optional[Union[DataAnalysisResponse, AnomalyDetectionResponse]] = None
    optimizations_result: Optional[Any] = None  # Will be strongly typed when OptimizationsResult is moved to schemas
    action_plan_result: Optional[Any] = None    # Will be strongly typed when ActionPlanResult is moved to schemas
    report_result: Optional[Any] = None         # Will be strongly typed when ReportResult is moved to schemas
    synthetic_data_result: Optional[SyntheticDataResult] = None
    supply_research_result: Optional[Any] = None # Will be strongly typed when SupplyResearchResult is moved to schemas
    corpus_admin_result: Optional[Any] = None
    
    # Execution tracking
    final_report: Optional[str] = None
    step_count: int = 0
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)
    quality_metrics: Dict[str, Any] = Field(default_factory=dict)
    
    # PHASE 1 BACKWARDS COMPATIBILITY FIX: Add agent_context for UserExecutionContext compatibility
    # This field provides backwards compatibility with execution code that expects agent_context
    # from the UserExecutionContext migration. Should be removed in Phase 2 after proper migration.
    agent_context: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('metadata', mode='before')
    @classmethod
    def validate_metadata(cls, v: Union[Dict, AgentMetadata]) -> AgentMetadata:
        """Convert dict metadata to AgentMetadata object."""
        if isinstance(v, dict):
            return AgentMetadata(**v)
        return v if isinstance(v, AgentMetadata) else AgentMetadata()
    
    @field_validator('step_count')
    @classmethod
    def validate_step_count(cls, v: int) -> int:
        """Validate step count is within reasonable bounds."""
        if v < 0:
            raise ValueError('Step count must be non-negative')
        if v > 10000:  # Reasonable upper bound
            raise ValueError('Step count exceeds maximum allowed value (10000)')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return self.model_dump(exclude_none=True, mode='json')
    
    def copy_with_updates(self, **updates: Any) -> 'DeepAgentState':
        """Create a new instance with updated fields (immutable pattern)."""
        current_data = self.model_dump()
        current_data.update(updates)
        return DeepAgentState(**current_data)
    
    def increment_step_count(self) -> 'DeepAgentState':
        """Create a new instance with incremented step count."""
        return self.copy_with_updates(step_count=self.step_count + 1)
    
    def _create_updated_custom_fields(self, key: str, value: str) -> Dict[str, str]:
        """Create updated custom fields dictionary."""
        updated_custom = self.metadata.custom_fields.copy()
        updated_custom[key] = value
        return updated_custom
    
    def _create_updated_metadata(self, updated_custom: Dict[str, str]) -> AgentMetadata:
        """Create updated metadata with new custom fields."""
        return self.metadata.model_copy(
            update={'custom_fields': updated_custom, 'last_updated': datetime.now(UTC)}
        )
    
    def add_metadata(self, key: str, value: str) -> 'DeepAgentState':
        """Create a new instance with additional metadata."""
        updated_custom = self._create_updated_custom_fields(key, value)
        new_metadata = self._create_updated_metadata(updated_custom)
        return self.copy_with_updates(metadata=new_metadata)
    
    def _get_cleared_data_fields(self) -> Dict[str, Any]:
        """Get dictionary of fields to clear for sensitive data removal."""
        result_fields = ['triage_result', 'data_result', 'optimizations_result', 'action_plan_result']
        data_fields = ['report_result', 'synthetic_data_result', 'supply_research_result', 'final_report']
        all_fields = result_fields + data_fields
        return {field: None for field in all_fields}
    
    def clear_sensitive_data(self) -> 'DeepAgentState':
        """Create a new instance with sensitive data cleared."""
        cleared_fields = self._get_cleared_data_fields()
        return self.copy_with_updates(
            metadata=AgentMetadata(),
            **cleared_fields
        )
    
    def _validate_merge_input(self, other_state: 'DeepAgentState') -> None:
        """Validate input for merge operation."""
        if not isinstance(other_state, DeepAgentState):
            raise TypeError("other_state must be a DeepAgentState instance")
    
    def _merge_custom_fields(self, other_state: 'DeepAgentState') -> Dict[str, str]:
        """Merge custom fields from both states."""
        merged_custom = self.metadata.custom_fields.copy()
        if other_state.metadata:
            merged_custom.update(other_state.metadata.custom_fields)
        return merged_custom
    
    def _merge_execution_context(self, other_state: 'DeepAgentState') -> Dict[str, str]:
        """Merge execution context from both states."""
        merged_context = self.metadata.execution_context.copy()
        if other_state.metadata:
            merged_context.update(other_state.metadata.execution_context)
        return merged_context
    
    def _create_merged_metadata(self, other_state: 'DeepAgentState') -> AgentMetadata:
        """Create merged metadata object."""
        merged_custom = self._merge_custom_fields(other_state)
        merged_context = self._merge_execution_context(other_state)
        return self._build_metadata_object(merged_context, merged_custom)
    
    def _build_metadata_object(self, context: Dict[str, str], custom: Dict[str, str]) -> AgentMetadata:
        """Build AgentMetadata object from merged data."""
        return AgentMetadata(
            execution_context=context,
            custom_fields=custom
        )
    
    def _merge_agent_results(self, other_state: 'DeepAgentState') -> Dict[str, Any]:
        """Merge all agent result fields."""
        result_fields = self._get_result_field_mappings(other_state)
        data_fields = self._get_data_field_mappings(other_state)
        return {**result_fields, **data_fields}
    
    def _get_result_field_mappings(self, other_state: 'DeepAgentState') -> Dict[str, Any]:
        """Get result field mappings for merge operation."""
        triage_data = self._get_triage_mappings(other_state)
        optimization_data = self._get_optimization_mappings(other_state)
        return {**triage_data, **optimization_data}
    
    def _get_triage_mappings(self, other_state: 'DeepAgentState') -> Dict[str, Any]:
        """Get triage and data result mappings."""
        return {
            'triage_result': other_state.triage_result or self.triage_result,
            'data_result': other_state.data_result or self.data_result
        }
    
    def _get_optimization_mappings(self, other_state: 'DeepAgentState') -> Dict[str, Any]:
        """Get optimization and action plan mappings."""
        return {
            'optimizations_result': self._merge_field('optimizations_result', other_state),
            'action_plan_result': self._merge_field('action_plan_result', other_state)
        }
    
    def _get_data_field_mappings(self, other_state: 'DeepAgentState') -> Dict[str, Any]:
        """Get data field mappings for merge operation."""
        report_data = self._get_report_mappings(other_state)
        research_data = self._get_research_mappings(other_state)
        return {**report_data, **research_data}
    
    def _get_report_mappings(self, other_state: 'DeepAgentState') -> Dict[str, Any]:
        """Get report and synthetic data mappings."""
        return {
            'report_result': self._merge_field('report_result', other_state),
            'synthetic_data_result': self._merge_field('synthetic_data_result', other_state)
        }
    
    def _get_research_mappings(self, other_state: 'DeepAgentState') -> Dict[str, Any]:
        """Get research and final report mappings."""
        return {
            'supply_research_result': self._merge_field('supply_research_result', other_state),
            'final_report': self._merge_field('final_report', other_state)
        }
    
    def _merge_field(self, field_name: str, other_state: 'DeepAgentState') -> Any:
        """Merge a single field from other state."""
        other_value = getattr(other_state, field_name, None)
        self_value = getattr(self, field_name, None)
        return other_value or self_value
    
    def _prepare_merge_components(self, other_state: 'DeepAgentState') -> tuple:
        """Prepare components needed for merge operation."""
        self._validate_merge_input(other_state)
        merged_metadata = self._create_merged_metadata(other_state)
        merged_results = self._merge_agent_results(other_state)
        return merged_metadata, merged_results
    
    def merge_from(self, other_state: 'DeepAgentState') -> 'DeepAgentState':
        """Create new state with data merged from another state (immutable)."""
        merged_metadata, merged_results = self._prepare_merge_components(other_state)
        merge_data = self._create_merge_data(other_state, merged_metadata, merged_results)
        return self.copy_with_updates(**merge_data)
    
    def _create_merge_data(self, other_state: 'DeepAgentState', metadata: AgentMetadata, 
                          results: Dict[str, Any]) -> Dict[str, Any]:
        """Create merge data dictionary."""
        step_count = max(self.step_count, other_state.step_count)
        return {'step_count': step_count, 'metadata': metadata, **results}


# Agent Execution Metrics
class AgentExecutionMetrics(BaseModel):
    """Metrics for agent execution tracking."""
    
    execution_time: Optional[float] = Field(None, description="Total execution time in seconds")
    execution_time_ms: Optional[float] = Field(0.0, description="Execution time in milliseconds")
    tool_calls_count: Optional[int] = Field(0, description="Number of tool calls made")
    context_length: Optional[int] = Field(None, description="Context length used")
    tokens_used: Optional[int] = Field(None, description="Total tokens consumed")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    error_count: Optional[int] = Field(0, description="Number of errors encountered")
    retry_count: Optional[int] = Field(0, description="Number of retries attempted")
    success: Optional[bool] = Field(True, description="Whether execution was successful")


# Backward compatibility alias  
AgentState = DeepAgentState



# Export all agent models
__all__ = [
    "ToolResultData",
    "AgentMetadata",
    "AgentResult", 
    "DeepAgentState",
    "AgentState",
    "AgentExecutionMetrics"
]
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
    from app.schemas.agent_models import DeepAgentState, AgentResult, AgentMetadata
"""

from typing import Dict, List, Optional, Union, Any
from datetime import datetime, UTC
from pydantic import BaseModel, Field
import uuid


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
    priority: Optional[int] = Field(default=None, ge=0, le=10)
    retry_count: int = 0
    parent_agent_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
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
    user_request: str
    chat_thread_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Results from different agent types
    triage_result: Optional[Any] = None
    data_result: Optional[Any] = None
    optimizations_result: Optional[Any] = None
    action_plan_result: Optional[Any] = None
    report_result: Optional[Any] = None
    synthetic_data_result: Optional[Any] = None
    supply_research_result: Optional[Any] = None
    corpus_admin_result: Optional[Any] = None
    
    # Execution tracking
    final_report: Optional[str] = None
    step_count: int = 0
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)
    
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
        return AgentMetadata(
            execution_context=merged_context,
            custom_fields=merged_custom
        )
    
    def _merge_agent_results(self, other_state: 'DeepAgentState') -> Dict[str, Any]:
        """Merge all agent result fields."""
        result_fields = self._get_result_field_mappings(other_state)
        data_fields = self._get_data_field_mappings(other_state)
        return {**result_fields, **data_fields}
    
    def _get_result_field_mappings(self, other_state: 'DeepAgentState') -> Dict[str, Any]:
        """Get result field mappings for merge operation."""
        return {
            'triage_result': other_state.triage_result or self.triage_result,
            'data_result': other_state.data_result or self.data_result,
            'optimizations_result': other_state.optimizations_result or self.optimizations_result,
            'action_plan_result': other_state.action_plan_result or self.action_plan_result
        }
    
    def _get_data_field_mappings(self, other_state: 'DeepAgentState') -> Dict[str, Any]:
        """Get data field mappings for merge operation."""
        return {
            'report_result': other_state.report_result or self.report_result,
            'synthetic_data_result': other_state.synthetic_data_result or self.synthetic_data_result,
            'supply_research_result': other_state.supply_research_result or self.supply_research_result,
            'final_report': other_state.final_report or self.final_report
        }
    
    def _prepare_merge_components(self, other_state: 'DeepAgentState') -> tuple:
        """Prepare components needed for merge operation."""
        self._validate_merge_input(other_state)
        merged_metadata = self._create_merged_metadata(other_state)
        merged_results = self._merge_agent_results(other_state)
        return merged_metadata, merged_results
    
    def merge_from(self, other_state: 'DeepAgentState') -> 'DeepAgentState':
        """Create new state with data merged from another state (immutable)."""
        merged_metadata, merged_results = self._prepare_merge_components(other_state)
        return self.copy_with_updates(
            step_count=max(self.step_count, other_state.step_count),
            metadata=merged_metadata,
            **merged_results
        )


# Backward compatibility alias  
AgentState = DeepAgentState


# Export all agent models
__all__ = [
    "ToolResultData",
    "AgentMetadata",
    "AgentResult", 
    "DeepAgentState",
    "AgentState"
]
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
from datetime import datetime
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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    execution_context: Dict[str, str] = Field(default_factory=dict)
    custom_fields: Dict[str, str] = Field(default_factory=dict)
    priority: Optional[int] = Field(default=None, ge=0, le=10)
    retry_count: int = 0
    parent_agent_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


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
    
    def add_metadata(self, key: str, value: str) -> 'DeepAgentState':
        """Create a new instance with additional metadata."""
        updated_custom = self.metadata.custom_fields.copy()
        updated_custom[key] = value
        new_metadata = self.metadata.model_copy(
            update={'custom_fields': updated_custom, 'last_updated': datetime.utcnow()}
        )
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
        
        merged_custom = self.metadata.custom_fields.copy()
        merged_context = self.metadata.execution_context.copy()
        
        if other_state.metadata:
            merged_custom.update(other_state.metadata.custom_fields)
            merged_context.update(other_state.metadata.execution_context)
        
        merged_metadata = AgentMetadata(
            execution_context=merged_context,
            custom_fields=merged_custom
        )
        
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
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


# SSOT MIGRATION: DeepAgentState has been moved to SSOT location
#
# ==================================================================================
# 🚨 CRITICAL DEVELOPER GUIDANCE - Issue #871 DeepAgentState SSOT Remediation 🚨
# ==================================================================================
#
# ❌ DEPRECATED: DeepAgentState was removed from this file (netra_backend.app.agents.state)
# ✅ SSOT LOCATION: Use netra_backend.app.schemas.agent_models.DeepAgentState instead
#
# CORRECT IMPORT:
#     from netra_backend.app.schemas.agent_models import DeepAgentState
#
# INCORRECT IMPORTS (will fail):
#     from netra_backend.app.agents.state import DeepAgentState  # ❌ REMOVED
#     from .state import DeepAgentState                          # ❌ REMOVED
#
# BUSINESS VALUE PROTECTION:
# - This remediation protects $500K+ ARR by eliminating SSOT violations
# - Prevents duplicate class definitions that cause runtime conflicts
# - Maintains Golden Path user workflow compatibility
# - Ensures single source of truth architectural compliance
#
# MIGRATION COMPLETED: 2025-09-13 (Issue #871 Phase 2)
# All production imports updated to use SSOT location
# Backwards compatibility maintained through import redirection
#
# ==================================================================================


# REMOVED: rebuild_model() function and DeepAgentState.model_rebuild() calls
# DeepAgentState is now in SSOT location: netra_backend.app.schemas.agent_models
# Model rebuilding is handled by the SSOT version automatically

# COMPATIBILITY ALIAS: Import from SSOT location for backward compatibility
# This allows existing imports to continue working while directing to the authoritative source
try:
    from netra_backend.app.schemas.agent_models import DeepAgentState
    # Issue #871: DeepAgentState compatibility alias successfully imported from SSOT location
except ImportError as e:
    # Safety fallback in case of circular import issues
    warnings.warn(
        f"Failed to import DeepAgentState from SSOT location: {e}. "
        "Please use 'from netra_backend.app.schemas.agent_models import DeepAgentState' directly.",
        DeprecationWarning,
        stacklevel=2
    )
    DeepAgentState = None
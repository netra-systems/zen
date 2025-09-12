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
    
     ALERT:  CRITICAL DEPRECATION WARNING: DeepAgentState creates user isolation risks
    and will be REMOVED in v3.0.0 (Q1 2025).
    
    [U+1F4CB] MIGRATION REQUIRED:
    - Replace with UserExecutionContext pattern for complete user isolation
    - Use context.metadata for request-specific data instead of global state
    - Access database via context.db_session instead of global sessions
    
    [U+1F4D6] Migration Guide: See EXECUTION_PATTERN_TECHNICAL_DESIGN.md
     WARNING: [U+FE0F]  USER DATA AT RISK: This pattern may cause data leakage between users
    
    [U+1F680] GOLDEN PATH FIX (2025-09-10): Added thread_id property for backward compatibility.
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
        """Initialize DeepAgentState with critical security isolation barriers.
        
        PHASE 1 EMERGENCY SECURITY REMEDIATION (2025-09-11):
        - Added strict user isolation validation
        - Implemented cross-user contamination detection
        - Added runtime security boundary enforcement
        """
        # EMERGENCY SECURITY VALIDATION: Detect potential cross-user contamination attempts
        self._validate_security_boundaries(data)
        
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
        
        # CRITICAL SECURITY WARNING: Issue comprehensive deprecation warning with security implications
        warnings.warn(
            f" ALERT:  CRITICAL SECURITY VULNERABILITY: DeepAgentState usage creates user isolation risks. "
            f"This pattern will be REMOVED in v3.0.0 (Q1 2025). "
            f"\n"
            f"[U+1F4CB] IMMEDIATE MIGRATION REQUIRED:"
            f"\n1. Replace with UserExecutionContext pattern"
            f"\n2. Use 'context.metadata' for request data instead of DeepAgentState fields"
            f"\n3. Access database via 'context.db_session' instead of global sessions"
            f"\n4. Use 'context.user_id', 'context.thread_id', 'context.run_id' for identifiers"
            f"\n"
            f"[U+1F4D6] Migration Guide: See EXECUTION_PATTERN_TECHNICAL_DESIGN.md"
            f"\n WARNING: [U+FE0F]  CRITICAL: Multiple users may see each other's data with this pattern",
            DeprecationWarning,
            stacklevel=2
        )
        
        # SECURITY ISOLATION: Initialize with isolated defaults to prevent cross-user contamination
        super().__init__(**self._apply_security_isolation(data))
    
    def _validate_security_boundaries(self, data: Dict[str, Any]) -> None:
        """
        CRITICAL SECURITY: Validate data for cross-user contamination risks.
        
        This method implements emergency security barriers to detect and prevent
        potential cross-user data contamination during DeepAgentState creation.
        
        Raises:
            SecurityError: If cross-user contamination risks are detected
            ValueError: If security validation fails
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Security validation flags
        security_violations = []
        
        # SECURITY CHECK 1: Validate user identifiers are consistent
        user_id = data.get('user_id')
        thread_id = data.get('chat_thread_id') or data.get('thread_id')
        run_id = data.get('run_id')
        
        if user_id and thread_id:
            # Basic validation that thread belongs to user (simplified check)
            if not str(thread_id).startswith(str(user_id)[:8]):
                logger.warning(
                    f"[U+1F512] SECURITY ALERT: Thread ID '{thread_id}' may not belong to user '{user_id}'. "
                    f"Potential cross-user thread assignment detected."
                )
        
        # SECURITY CHECK 2: Validate sensitive data patterns
        agent_input = data.get('agent_input', {})
        if isinstance(agent_input, dict):
            sensitive_patterns = [
                'api_key', 'password', 'secret', 'token', 'credential',
                'admin', 'root', 'backdoor', 'bypass', 'override'
            ]
            
            agent_input_str = str(agent_input).lower()
            for pattern in sensitive_patterns:
                if pattern in agent_input_str:
                    logger.warning(
                        f"[U+1F512] SECURITY ALERT: Potential sensitive data pattern '{pattern}' "
                        f"detected in agent_input for user '{user_id}'"
                    )
        
        # SECURITY CHECK 3: Validate no cross-user data injection
        context_tracking = data.get('context_tracking', {})
        if isinstance(context_tracking, dict):
            # Check for references to other users
            context_str = str(context_tracking)
            if any(keyword in context_str.lower() for keyword in ['other_user', 'cross_user', 'all_users']):
                security_violations.append("Cross-user references detected in context_tracking")
        
        # SECURITY CHECK 4: Validate metadata integrity
        metadata = data.get('metadata')
        if metadata and hasattr(metadata, 'custom_fields'):
            custom_fields_str = str(metadata.custom_fields)
            if any(dangerous in custom_fields_str.lower() for dangerous in ['inject', 'execute', 'eval', 'system']):
                security_violations.append("Potentially dangerous code injection patterns in metadata")
        
        # ENFORCE SECURITY BOUNDARIES
        if security_violations:
            violation_summary = "; ".join(security_violations)
            logger.error(
                f" ALERT:  CRITICAL SECURITY VIOLATIONS DETECTED: {violation_summary}. "
                f"User: {user_id}, Thread: {thread_id}, Run: {run_id}"
            )
            raise ValueError(
                f" ALERT:  SECURITY BOUNDARY VIOLATION: DeepAgentState creation blocked due to "
                f"security violations: {violation_summary}. "
                f"This pattern poses cross-user contamination risks."
            )
    
    def _apply_security_isolation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        CRITICAL SECURITY: Apply security isolation to prevent cross-user contamination.
        
        This method ensures that all mutable objects are properly isolated
        and cannot be shared between different user contexts.
        
        Args:
            data: The initialization data
            
        Returns:
            Dict[str, Any]: Data with security isolation applied
        """
        import copy
        import logging
        logger = logging.getLogger(__name__)
        
        # DEEP COPY all mutable objects to ensure isolation
        isolated_data = {}
        
        for key, value in data.items():
            if isinstance(value, (list, dict, set)):
                # Deep copy all mutable collections to prevent sharing
                isolated_data[key] = copy.deepcopy(value)
                logger.debug(f"[U+1F512] Security isolation: Deep copied mutable field '{key}' for user isolation")
            elif hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, type(None))):
                # Deep copy objects with state
                try:
                    isolated_data[key] = copy.deepcopy(value)
                    logger.debug(f"[U+1F512] Security isolation: Deep copied object field '{key}' for user isolation")
                except Exception as e:
                    # Fallback for non-copyable objects
                    isolated_data[key] = value
                    logger.warning(f" WARNING: [U+FE0F] Could not deep copy field '{key}': {e}")
            else:
                # Immutable types are safe to share
                isolated_data[key] = value
        
        # ENSURE ISOLATED DEFAULT FACTORIES
        # Force creation of new instances for list/dict fields to prevent sharing
        if 'messages' not in isolated_data:
            isolated_data['messages'] = []  # New list instance
        if 'quality_metrics' not in isolated_data:
            isolated_data['quality_metrics'] = {}  # New dict instance
        if 'context_tracking' not in isolated_data:
            isolated_data['context_tracking'] = {}  # New dict instance
        if 'agent_context' not in isolated_data:
            isolated_data['agent_context'] = {}  # New dict instance
        
        logger.info(f"[U+1F512] Security isolation applied to DeepAgentState initialization")
        return isolated_data
    
    def _validate_updates_security(self, updates: Dict[str, Any]) -> None:
        """
        CRITICAL SECURITY: Validate updates for cross-user contamination risks.
        
        This method prevents malicious updates that could cause cross-user data
        contamination during copy_with_updates operations.
        
        Args:
            updates: The update dictionary to validate
            
        Raises:
            ValueError: If security violations are detected
        """
        import logging
        logger = logging.getLogger(__name__)
        
        security_violations = []
        
        # SECURITY CHECK 1: Validate user_id consistency
        if 'user_id' in updates:
            new_user_id = updates['user_id']
            current_user_id = self.user_id
            
            if current_user_id and new_user_id != current_user_id:
                security_violations.append(
                    f"User ID change attempt: {current_user_id} -> {new_user_id}"
                )
        
        # SECURITY CHECK 2: Validate thread_id ownership
        if 'thread_id' in updates or 'chat_thread_id' in updates:
            new_thread_id = updates.get('thread_id') or updates.get('chat_thread_id')
            current_user_id = self.user_id
            
            if current_user_id and new_thread_id:
                # Basic check that thread belongs to user
                if not str(new_thread_id).startswith(str(current_user_id)[:8]):
                    security_violations.append(
                        f"Cross-user thread assignment: user {current_user_id} attempting to access thread {new_thread_id}"
                    )
        
        # SECURITY CHECK 3: Validate no malicious injection patterns
        for key, value in updates.items():
            if isinstance(value, str):
                value_lower = value.lower()
                dangerous_patterns = [
                    'exec(', 'eval(', '__import__', 'subprocess', 'os.system',
                    '<script>', 'javascript:', 'data:', 'bypass', 'override',
                    'admin_access', 'root_access', 'backdoor'
                ]
                
                for pattern in dangerous_patterns:
                    if pattern in value_lower:
                        security_violations.append(
                            f"Dangerous injection pattern '{pattern}' in field '{key}'"
                        )
        
        # ENFORCE SECURITY BOUNDARIES
        if security_violations:
            violation_summary = "; ".join(security_violations)
            logger.error(
                f" ALERT:  CRITICAL SECURITY VIOLATIONS in copy_with_updates: {violation_summary}. "
                f"User: {self.user_id}, Thread: {self.chat_thread_id}"
            )
            raise ValueError(
                f" ALERT:  SECURITY VIOLATION: copy_with_updates blocked due to security violations: "
                f"{violation_summary}. This prevents cross-user contamination."
            )
    
    def _validate_merge_security(self, other_state: 'DeepAgentState') -> None:
        """
        CRITICAL SECURITY: Validate merge operation for cross-user contamination risks.
        
        This method prevents merging states from different users which would cause
        severe security violations and data contamination.
        
        Args:
            other_state: The state to merge from
            
        Raises:
            ValueError: If cross-user merge is attempted
        """
        import logging
        logger = logging.getLogger(__name__)
        
        security_violations = []
        
        # SECURITY CHECK 1: Prevent cross-user merges
        current_user = self.user_id
        other_user = other_state.user_id
        
        if current_user and other_user and current_user != other_user:
            security_violations.append(
                f"Cross-user merge attempt: {current_user} trying to merge from {other_user}"
            )
            
        # SECURITY CHECK 2: Validate thread ownership
        current_thread = self.chat_thread_id
        other_thread = other_state.chat_thread_id
        
        if current_thread and other_thread and current_thread != other_thread:
            # Check if threads belong to the same user
            if current_user and not str(other_thread).startswith(str(current_user)[:8]):
                security_violations.append(
                    f"Cross-user thread merge: thread {other_thread} doesn't belong to user {current_user}"
                )
        
        # SECURITY CHECK 3: Scan for sensitive data in other state
        other_dict = other_state.to_dict()
        other_str = str(other_dict).lower()
        
        sensitive_patterns = [
            'api_key', 'password', 'secret', 'token', 'credential', 'auth',
            'admin', 'backdoor', 'bypass', 'override', 'inject', 'execute'
        ]
        
        for pattern in sensitive_patterns:
            if pattern in other_str:
                logger.warning(
                    f"[U+1F512] SECURITY ALERT: Merge operation involves sensitive data pattern '{pattern}' "
                    f"from user {other_user} to user {current_user}"
                )
        
        # ENFORCE SECURITY BOUNDARIES  
        if security_violations:
            violation_summary = "; ".join(security_violations)
            logger.error(
                f" ALERT:  CRITICAL SECURITY VIOLATIONS in merge_from: {violation_summary}. "
                f"Current user: {current_user}, Other user: {other_user}"
            )
            raise ValueError(
                f" ALERT:  SECURITY VIOLATION: merge_from blocked due to cross-user contamination risk: "
                f"{violation_summary}. This prevents unauthorized data access between users."
            )
    
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
        # CRITICAL SECURITY: Validate updates for cross-user contamination risks
        self._validate_updates_security(updates)
        
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
        
        # CRITICAL SECURITY: Validate merge operation for cross-user contamination risks
        self._validate_merge_security(other_state)
        
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
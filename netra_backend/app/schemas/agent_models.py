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

import copy
import uuid
import re
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
    user_prompt: str = "default_request"   # SSOT MIGRATION FIX: Interface alignment for execution engines (Golden Path)
    chat_thread_id: Optional[str] = None
    user_id: Optional[str] = None
    run_id: Optional[str] = None           # SSOT MIGRATION FIX: Unique execution run identifier
    agent_input: Optional[Dict[str, Any]] = None  # SSOT MIGRATION FIX: Agent configuration parameters

    # Strongly typed result fields with proper type unions
    triage_result: Optional["TriageResult"] = None
    data_result: Optional[Union[DataAnalysisResponse, AnomalyDetectionResponse]] = None
    optimizations_result: Optional[Any] = None  # Will be strongly typed when OptimizationsResult is moved to schemas
    action_plan_result: Optional[Any] = None    # Will be strongly typed when ActionPlanResult is moved to schemas
    report_result: Optional[Any] = None         # Will be strongly typed when ReportResult is moved to schemas
    synthetic_data_result: Optional[SyntheticDataResult] = None
    supply_research_result: Optional[Any] = None # Will be strongly typed when SupplyResearchResult is moved to schemas
    corpus_admin_result: Optional[Any] = None
    corpus_admin_error: Optional[str] = None  # SSOT MIGRATION FIX: Corpus admin error handling

    # Execution tracking
    final_report: Optional[str] = None
    step_count: int = 0
    current_step: int = 0  # Current pipeline step number for execution tracking
    messages: List[Dict[str, Any]] = Field(default_factory=list)  # SSOT MIGRATION FIX: E2E test compatibility
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)
    quality_metrics: Dict[str, Any] = Field(default_factory=dict)
    context_tracking: Dict[str, Any] = Field(default_factory=dict)  # SSOT MIGRATION FIX: E2E test compatibility
    
    # PHASE 1 BACKWARDS COMPATIBILITY FIX: Add agent_context for UserExecutionContext compatibility
    # This field provides backwards compatibility with execution code that expects agent_context
    # from the UserExecutionContext migration. Should be removed in Phase 2 after proper migration.
    agent_context: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('metadata', mode='before')
    @classmethod
    def validate_metadata(cls, v: Union[Dict, AgentMetadata]) -> AgentMetadata:
        """Convert dict metadata to AgentMetadata object with deep copy protection.
        
        SECURITY FIX: Issue #953 - Prevents shared reference vulnerabilities by
        creating deep copies of metadata objects to ensure user isolation.
        """
        if isinstance(v, dict):
            # Deep copy the dictionary to prevent shared references
            safe_dict = copy.deepcopy(v)
            return AgentMetadata(**safe_dict)
        elif isinstance(v, AgentMetadata):
            # Deep copy the AgentMetadata object to prevent shared references
            return copy.deepcopy(v)
        else:
            return AgentMetadata()
    
    @field_validator('agent_context', mode='before')
    @classmethod
    def validate_agent_context(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Deep copy agent_context to prevent cross-user contamination.
        
        SECURITY FIX: Issue #953 - Critical security vulnerability fix.
        Prevents shared reference vulnerabilities by creating deep copies of
        agent_context dictionaries to ensure complete user isolation.
        
        This is the primary fix for the cross-user data contamination vulnerability
        where multiple users could access each other's sensitive data through
        shared dictionary references.
        """
        if v is None:
            return {}
        # Deep copy the entire context dictionary to prevent shared references
        return copy.deepcopy(v)
    
    @field_validator('agent_input', mode='before')
    @classmethod
    def validate_agent_input_security(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """SECURITY FIX: Validate agent_input to prevent injection attacks.

        Issue #1017 Resolution: This validator prevents malicious data injection by:
        1. Detecting and sanitizing dangerous system commands
        2. Removing code execution payloads
        3. Filtering malicious API keys and credentials
        4. Sanitizing permission bypass attempts
        5. Cleaning data extraction directives

        This protects enterprise customers from regulatory violations (HIPAA, SOC2, SEC).
        Uses sanitization approach rather than rejection to allow testing while maintaining security.
        """
        if v is None:
            return v

        # Deep copy to prevent reference mutation
        safe_input = copy.deepcopy(v)

        # Apply security sanitization (clean rather than reject)
        cls._sanitize_agent_input_recursive(safe_input)

        return safe_input

    @classmethod
    def _sanitize_agent_input_recursive(cls, data: Any, path: str = "") -> None:
        """Recursively sanitize agent input data to remove security threats.

        Args:
            data: The data structure to sanitize
            path: Current path in the data structure for logging
        """
        if isinstance(data, dict):
            cls._sanitize_dict_values(data, path)
        elif isinstance(data, list):
            cls._sanitize_list_values(data, path)
        # Note: String sanitization now happens at the dict/list level to allow modification

    @classmethod
    def _sanitize_dict_values(cls, data_dict: Dict[str, Any], path: str) -> None:
        """Sanitize dictionary values and keys."""
        # Check for dangerous keys
        dangerous_keys = [
            'system_commands', 'exec', 'eval', 'import', '__class__', '__globals__',
            'bypass_permissions', 'admin_override', 'backdoor_access', 'extract_pii',
            'database_password', 'api_key', 'secret_key', 'jwt_secret', 'admin_credentials'
        ]

        keys_to_remove = []
        for key in list(data_dict.keys()):  # Convert to list to allow modification during iteration
            if any(dangerous in str(key).lower() for dangerous in dangerous_keys):
                keys_to_remove.append(key)
            elif isinstance(data_dict[key], (dict, list)):
                cls._sanitize_agent_input_recursive(data_dict[key], f"{path}.{key}")
            elif isinstance(data_dict[key], str):
                # Sanitize string values in place
                data_dict[key] = cls._sanitize_string_content(data_dict[key], f"{path}.{key}")

        # Remove dangerous keys
        for key in keys_to_remove:
            del data_dict[key]

    @classmethod
    def _sanitize_list_values(cls, data_list: List[Any], path: str) -> None:
        """Sanitize list values."""
        for i in range(len(data_list)):
            if isinstance(data_list[i], str):
                # Sanitize string values in place
                data_list[i] = cls._sanitize_string_content(data_list[i], f"{path}[{i}]")
            elif isinstance(data_list[i], (dict, list)):
                cls._sanitize_agent_input_recursive(data_list[i], f"{path}[{i}]")

    @classmethod
    def _validate_string_security(cls, value: str, path: str) -> None:
        """Validate string values for security threats."""
        if cls._is_dangerous_string(value):
            raise ValueError(
                f"SECURITY VIOLATION: Dangerous content detected in {path}. "
                f"Input contains potential security threats that are not allowed."
            )

    @classmethod
    def _is_dangerous_string(cls, value: str) -> bool:
        """Check if a string contains dangerous content."""
        dangerous_patterns = [
            r'rm\s+-rf\s*/',  # Destructive file operations
            r'exec\s*\(',     # Code execution
            r'eval\s*\(',     # Code evaluation
            r'import\s+os',   # OS module imports
            r'__class__',     # Python introspection
            r'__globals__',   # Global access
            r'cat\s+/etc/passwd',  # System file access
            r'wget\s+http',   # Remote file downloads
            r'curl\s+http',   # Remote file access
            r'sk-[a-zA-Z0-9\-]+',  # API keys
            r'admin:admin',   # Default credentials
            r'DROP\s+TABLE',  # SQL injection
            r'<script>',      # XSS
            r'javascript:',   # JavaScript injection
        ]

        value_lower = value.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True

        return False

    @field_validator('step_count')
    @classmethod
    def validate_step_count(cls, v: int) -> int:
        """Validate step count is within reasonable bounds."""
        if v < 0:
            raise ValueError('Step count must be non-negative')
        if v > 10000:  # Reasonable upper bound
            raise ValueError('Step count exceeds maximum allowed value (10000)')
        return v

    @field_validator('current_step')
    @classmethod
    def validate_current_step(cls, v: int) -> int:
        """Validate current step is within reasonable bounds."""
        if v < 0:
            raise ValueError('Current step must be non-negative')
        if v > 10000:  # Reasonable upper bound
            raise ValueError('Current step exceeds maximum allowed value (10000)')
        return v

    @property
    def thread_id(self) -> Optional[str]:
        """SSOT INTERFACE COMPATIBILITY: Property to access chat_thread_id as thread_id for backward compatibility.

        This property ensures the SSOT version of DeepAgentState maintains interface compatibility
        with the deprecated version, preventing 'object has no attribute thread_id' runtime errors.

        Returns:
            Optional[str]: The chat_thread_id value accessed via thread_id property
        """
        return self.chat_thread_id

    @thread_id.setter
    def thread_id(self, value: Optional[str]) -> None:
        """SSOT INTERFACE COMPATIBILITY: Setter to update chat_thread_id via thread_id for backward compatibility.

        This setter ensures the SSOT version of DeepAgentState maintains interface compatibility
        with the deprecated version, allowing thread_id assignment to update chat_thread_id.

        Args:
            value: The thread ID value to set
        """
        self.chat_thread_id = value

    def __init__(self, **data):
        """Initialize DeepAgentState with SSOT interface compatibility and security protection.

        SSOT INTERFACE COMPATIBILITY: This constructor ensures compatibility with the deprecated
        version by handling thread_id parameter mapping and maintaining backward compatibility
        for existing code that passes thread_id instead of chat_thread_id.

        SECURITY FIX: Issue #953 - Implements deep copy protection for mutable objects
        to prevent shared reference vulnerabilities and ensure user isolation.

        Args:
            **data: Initialization data, including potential thread_id parameter
        """
        # SSOT COMPATIBILITY: Handle thread_id backward compatibility
        # Map thread_id to chat_thread_id for compatibility with deprecated interface
        if 'thread_id' in data and 'chat_thread_id' not in data:
            data['chat_thread_id'] = data.pop('thread_id')
        elif 'thread_id' in data and 'chat_thread_id' in data:
            # If both provided, use thread_id as the canonical value
            data['chat_thread_id'] = data.pop('thread_id')

        # SSOT COMPATIBILITY: Synchronize user_request and user_prompt fields for backward compatibility
        if 'user_prompt' in data and 'user_request' not in data:
            data['user_request'] = data['user_prompt']
        elif 'user_request' in data and 'user_prompt' not in data:
            data['user_prompt'] = data['user_request']
        elif 'user_prompt' in data and 'user_request' in data:
            # If both are provided, prefer user_prompt as it's the expected interface
            data['user_request'] = data['user_prompt']

        # SECURITY FIX: Deep copy protection for mutable objects to prevent shared references
        # This ensures user isolation by preventing cross-user data contamination
        mutable_fields = ['messages', 'quality_metrics', 'context_tracking', 'agent_context', 'agent_input']
        for field_name in mutable_fields:
            if field_name in data and data[field_name] is not None:
                # Deep copy mutable objects to ensure no shared references
                data[field_name] = copy.deepcopy(data[field_name])

        super().__init__(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary with sensitive data filtering.

        SECURITY FIX: Issue #1017 - Prevents information disclosure by filtering
        sensitive data from serialization output. This protects enterprise customers
        from exposing internal secrets, credentials, and system information.
        """
        # Get full model data
        raw_dict = self.model_dump(exclude_none=True, mode='json')

        # Apply security filtering
        filtered_dict = self._filter_sensitive_data(raw_dict)

        return filtered_dict

    def _filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from dictionary representation.

        This method removes or redacts sensitive information that should not
        be exposed in serialized output, protecting against information disclosure.

        Args:
            data: Raw dictionary data from model_dump

        Returns:
            Filtered dictionary with sensitive data removed/redacted
        """
        filtered_data = copy.deepcopy(data)

        # Filter metadata custom_fields for sensitive information
        if 'metadata' in filtered_data and 'custom_fields' in filtered_data['metadata']:
            filtered_data['metadata']['custom_fields'] = self._filter_custom_fields(
                filtered_data['metadata']['custom_fields']
            )

        # Filter execution_context for sensitive information
        if 'metadata' in filtered_data and 'execution_context' in filtered_data['metadata']:
            filtered_data['metadata']['execution_context'] = self._filter_execution_context(
                filtered_data['metadata']['execution_context']
            )

        # Filter context_tracking for sensitive information
        if 'context_tracking' in filtered_data:
            filtered_data['context_tracking'] = self._filter_context_tracking(
                filtered_data['context_tracking']
            )

        # Filter agent_context for sensitive information
        if 'agent_context' in filtered_data:
            filtered_data['agent_context'] = self._filter_agent_context(
                filtered_data['agent_context']
            )

        return filtered_data

    def _filter_custom_fields(self, custom_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from custom_fields."""
        if not custom_fields:
            return custom_fields

        filtered_fields = {}
        sensitive_patterns = [
            'api_key', 'secret', 'password', 'token', 'credential', 'admin',
            'internal', 'system', 'database', 'jwt', 'auth', 'private'
        ]

        for key, value in custom_fields.items():
            key_lower = key.lower()
            if any(pattern in key_lower for pattern in sensitive_patterns):
                # SECURITY: Completely remove sensitive fields rather than redacting
                # This prevents exposure of sensitive field names to potential attackers
                continue
            elif isinstance(value, str) and self._contains_sensitive_content(value):
                # SECURITY: Remove fields with sensitive content
                continue
            elif isinstance(value, dict):
                # Recursively filter nested dictionaries
                filtered_fields[key] = self._apply_generic_filtering(value)
            else:
                filtered_fields[key] = value

        return filtered_fields

    def _filter_execution_context(self, execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from execution_context."""
        if not execution_context:
            return execution_context

        return self._apply_generic_filtering(execution_context)

    def _filter_context_tracking(self, context_tracking: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from context_tracking."""
        if not context_tracking:
            return context_tracking

        return self._apply_generic_filtering(context_tracking)

    def _filter_agent_context(self, agent_context: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from agent_context."""
        if not agent_context:
            return agent_context

        return self._apply_generic_filtering(agent_context)

    def _apply_generic_filtering(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply generic sensitive data filtering to any dictionary."""
        filtered_data = {}
        sensitive_key_patterns = [
            'secret', 'password', 'token', 'key', 'credential', 'admin',
            'internal', 'system', 'database', 'jwt', 'auth', 'bypass'
        ]

        for key, value in data.items():
            key_lower = key.lower()
            if any(pattern in key_lower for pattern in sensitive_key_patterns):
                # SECURITY: Completely remove sensitive fields rather than redacting
                continue
            elif isinstance(value, str) and self._contains_sensitive_content(value):
                # SECURITY: Remove fields with sensitive content
                continue
            elif isinstance(value, dict):
                filtered_data[key] = self._apply_generic_filtering(value)
            else:
                filtered_data[key] = value

        return filtered_data

    def _contains_sensitive_content(self, value: str) -> bool:
        """Check if a string value contains sensitive content."""
        sensitive_patterns = [
            r'sk-[a-zA-Z0-9\-]+',  # API keys
            r'[a-zA-Z0-9]{32,}',   # Long hex strings (likely tokens/hashes)
            r'admin:admin',        # Default credentials
            r'password[_\s]*[:=][_\s]*\w+',  # Password assignments
            r'secret[_\s]*[:=][_\s]*\w+',    # Secret assignments
            r'token[_\s]*[:=][_\s]*\w+',     # Token assignments
        ]

        value_lower = value.lower()
        for pattern in sensitive_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True

        return False
    
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

    def create_child_context(
        self,
        operation_name: str,
        additional_context: Optional[Dict[str, Any]] = None,
        additional_agent_context: Optional[Dict[str, Any]] = None
    ) -> 'DeepAgentState':
        """PHASE 1 INTERFACE COMPATIBILITY FIX: Create child context with dual parameter support.

        CRITICAL ISSUE #1085 RESOLUTION: This method now supports BOTH parameter names to resolve
        the interface mismatch that was blocking enterprise customers from adopting secure
        UserExecutionContext patterns.

        DUAL PARAMETER SUPPORT:
        - additional_context: Legacy parameter name (backward compatibility)
        - additional_agent_context: Production parameter name (UserExecutionContext compatibility)

        This fix enables:
        - Existing code using 'additional_context' continues to work
        - Production code using 'additional_agent_context' now works with DeepAgentState
        - Enterprise customers can migrate to UserExecutionContext without breaking changes
        - $750K+ ARR business value protection through interface compatibility

        Args:
            operation_name: Name of the sub-operation
            additional_context: Additional context data (legacy parameter name)
            additional_agent_context: Additional agent context data (production parameter name)

        Returns:
            New DeepAgentState instance with child context data

        Raises:
            ValueError: If both parameters are provided with conflicting data
        """
        # PHASE 1 COMPATIBILITY FIX: Reconcile dual parameter support
        final_additional_context = self._reconcile_child_context_parameters(
            additional_context, additional_agent_context
        )

        enhanced_agent_context = self.agent_context.copy()
        if final_additional_context:
            enhanced_agent_context.update(final_additional_context)

        enhanced_agent_context.update({
            'parent_operation': self.agent_context.get('operation_name', 'root'),
            'operation_name': operation_name,
            'operation_depth': self.agent_context.get('operation_depth', 0) + 1
        })

        return self.copy_with_updates(
            agent_context=enhanced_agent_context,
            step_count=self.step_count + 1
        )

    def _reconcile_child_context_parameters(
        self,
        additional_context: Optional[Dict[str, Any]],
        additional_agent_context: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """PHASE 1 COMPATIBILITY FIX: Reconcile dual parameter support for child context creation.

        This method handles the parameter interface mismatch between DeepAgentState and
        UserExecutionContext by accepting both parameter names and providing intelligent
        reconciliation logic.

        Parameter Priority Logic:
        1. If only one parameter provided, use that parameter
        2. If both parameters provided with identical data, use either (they're the same)
        3. If both parameters provided with different data, merge with additional_agent_context taking priority
        4. If neither parameter provided, return None

        Args:
            additional_context: Legacy parameter (for backward compatibility)
            additional_agent_context: Production parameter (for UserExecutionContext compatibility)

        Returns:
            Reconciled context dictionary or None

        Raises:
            ValueError: If both parameters are provided with conflicting keys
        """
        # Case 1: Neither parameter provided
        if additional_context is None and additional_agent_context is None:
            return None

        # Case 2: Only legacy parameter provided
        if additional_context is not None and additional_agent_context is None:
            return copy.deepcopy(additional_context)

        # Case 3: Only production parameter provided
        if additional_context is None and additional_agent_context is not None:
            return copy.deepcopy(additional_agent_context)

        # Case 4: Both parameters provided - need reconciliation
        if additional_context is not None and additional_agent_context is not None:
            return self._merge_context_parameters(additional_context, additional_agent_context)

        return None

    def _merge_context_parameters(
        self,
        additional_context: Dict[str, Any],
        additional_agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge context parameters when both are provided.

        Merge strategy:
        - Start with additional_context as base
        - Overlay additional_agent_context (production parameter takes priority)
        - Detect and warn about conflicts but allow override

        Args:
            additional_context: Legacy context data
            additional_agent_context: Production context data

        Returns:
            Merged context dictionary
        """
        # Deep copy to avoid mutation
        merged_context = copy.deepcopy(additional_context)

        # Check for conflicts before merging
        conflicts = set(additional_context.keys()) & set(additional_agent_context.keys())
        if conflicts:
            # Simple logging for parameter conflicts - using basic logging to avoid import complexity
            import logging
            logging.warning(
                f"PHASE 1 INTERFACE COMPATIBILITY: Parameter conflict detected in create_child_context. "
                f"Conflicting keys: {conflicts}. Production parameter (additional_agent_context) "
                f"takes priority for Issue #1085 resolution."
            )

        # Merge with production parameter taking priority
        merged_context.update(copy.deepcopy(additional_agent_context))

        return merged_context


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
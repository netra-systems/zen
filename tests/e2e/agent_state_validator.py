# REMOVED_SYNTAX_ERROR: '''Agent State Validator - Unified System Testing Phase 5
# REMOVED_SYNTAX_ERROR: Validates agent initialization, transitions, and resource usage.
# REMOVED_SYNTAX_ERROR: BVJ: Enterprise/Growth segment - $50K+ revenue protection from session failures.
# REMOVED_SYNTAX_ERROR: Architecture: ≤300 lines, ≤8 lines per function, modular validators.
# REMOVED_SYNTAX_ERROR: '''

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import psutil
import pytest

from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import AgentMetadata, DeepAgentState
from netra_backend.app.schemas.agent_models import AgentMetadata
from netra_backend.app.schemas.core_enums import ExecutionStatus
# REMOVED_SYNTAX_ERROR: from tests.e2e.config import ( )
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
CustomerTier,
UnifiedTestConfig,
get_test_user,



# REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class AgentStateMetrics:
    # REMOVED_SYNTAX_ERROR: """Agent state performance and resource metrics"""
    # REMOVED_SYNTAX_ERROR: memory_usage_mb: float = 0.0
    # REMOVED_SYNTAX_ERROR: initialization_time_ms: float = 0.0
    # REMOVED_SYNTAX_ERROR: state_transition_time_ms: float = 0.0
    # REMOVED_SYNTAX_ERROR: token_consumption: int = 0
    # REMOVED_SYNTAX_ERROR: context_preservation_score: float = 1.0
    # REMOVED_SYNTAX_ERROR: error_count: int = 0
    # REMOVED_SYNTAX_ERROR: validation_errors: List[str] = field(default_factory=list)


    # REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class StateValidationResult:
    # REMOVED_SYNTAX_ERROR: """Agent state validation result with detailed metrics"""
    # REMOVED_SYNTAX_ERROR: agent_name: str
    # REMOVED_SYNTAX_ERROR: validation_passed: bool
    # REMOVED_SYNTAX_ERROR: state_metrics: AgentStateMetrics
    # REMOVED_SYNTAX_ERROR: validation_details: Dict[str, Any] = field(default_factory=dict)
    # REMOVED_SYNTAX_ERROR: timestamp: datetime = field(default_factory=lambda x: None datetime.now(timezone.utc))


# REMOVED_SYNTAX_ERROR: class AgentStateValidator:
    # REMOVED_SYNTAX_ERROR: """Main agent state validation engine"""

# REMOVED_SYNTAX_ERROR: def __init__(self, test_config: Optional[UnifiedTestConfig] = None):
    # REMOVED_SYNTAX_ERROR: """Initialize validator with test configuration"""
    # REMOVED_SYNTAX_ERROR: self.config = test_config or UnifiedTestConfig()
    # REMOVED_SYNTAX_ERROR: self.validation_results: List[StateValidationResult] = []
    # REMOVED_SYNTAX_ERROR: self.resource_tracker = ResourceTracker()
    # REMOVED_SYNTAX_ERROR: self.context_validator = ContextValidator()

# REMOVED_SYNTAX_ERROR: async def validate_agent_startup(self, agent_name: str,
# REMOVED_SYNTAX_ERROR: state: DeepAgentState) -> StateValidationResult:
    # REMOVED_SYNTAX_ERROR: """Validate agent startup initialization state"""
    # REMOVED_SYNTAX_ERROR: metrics = AgentStateMetrics()
    # REMOVED_SYNTAX_ERROR: start_time = time.perf_counter()

    # REMOVED_SYNTAX_ERROR: startup_valid = self._validate_startup_fields(state, metrics)
    # REMOVED_SYNTAX_ERROR: memory_valid = await self._validate_memory_usage(agent_name, metrics)

    # REMOVED_SYNTAX_ERROR: metrics.initialization_time_ms = (time.perf_counter() - start_time) * 1000
    # REMOVED_SYNTAX_ERROR: validation_passed = startup_valid and memory_valid

    # REMOVED_SYNTAX_ERROR: return StateValidationResult(agent_name, validation_passed, metrics)

# REMOVED_SYNTAX_ERROR: def _validate_startup_fields(self, state: DeepAgentState,
# REMOVED_SYNTAX_ERROR: metrics: AgentStateMetrics) -> bool:
    # REMOVED_SYNTAX_ERROR: """Validate required startup state fields"""
    # REMOVED_SYNTAX_ERROR: required_fields = ['user_request', 'metadata']
    # REMOVED_SYNTAX_ERROR: validation_passed = True
    # REMOVED_SYNTAX_ERROR: for field_name in required_fields:
        # REMOVED_SYNTAX_ERROR: validation_passed = _validate_single_field(state, field_name, metrics, validation_passed)
        # REMOVED_SYNTAX_ERROR: return validation_passed


# REMOVED_SYNTAX_ERROR: async def _validate_memory_usage(self, agent_name: str,
# REMOVED_SYNTAX_ERROR: metrics: AgentStateMetrics) -> bool:
    # REMOVED_SYNTAX_ERROR: """Validate agent memory usage within limits"""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: memory_mb = self.resource_tracker.get_memory_usage_mb()
        # REMOVED_SYNTAX_ERROR: metrics.memory_usage_mb = memory_mb
        # REMOVED_SYNTAX_ERROR: return memory_mb < self._get_memory_limit(agent_name)
        # REMOVED_SYNTAX_ERROR: except Exception as e:
            # REMOVED_SYNTAX_ERROR: metrics.validation_errors.append("formatted_string")
            # REMOVED_SYNTAX_ERROR: return False


# REMOVED_SYNTAX_ERROR: class ContextValidator:
    # REMOVED_SYNTAX_ERROR: """Validator for agent context preservation and injection"""

# REMOVED_SYNTAX_ERROR: def validate_context_injection(self, state: DeepAgentState,
# REMOVED_SYNTAX_ERROR: user_context: Dict[str, Any]) -> bool:
    # REMOVED_SYNTAX_ERROR: """Validate user context injection into agent state"""
    # REMOVED_SYNTAX_ERROR: if not user_context:
        # REMOVED_SYNTAX_ERROR: return True

        # REMOVED_SYNTAX_ERROR: injected_context = self._extract_injected_context(state)
        # REMOVED_SYNTAX_ERROR: return self._verify_context_preservation(user_context, injected_context)

# REMOVED_SYNTAX_ERROR: def _extract_injected_context(self, state: DeepAgentState) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Extract injected context from agent state"""
    # REMOVED_SYNTAX_ERROR: if not state.metadata or not state.metadata.execution_context:
        # REMOVED_SYNTAX_ERROR: return {}
        # REMOVED_SYNTAX_ERROR: return state.metadata.execution_context

# REMOVED_SYNTAX_ERROR: def _verify_context_preservation(self, original: Dict[str, Any],
# REMOVED_SYNTAX_ERROR: injected: Dict[str, Any]) -> bool:
    # REMOVED_SYNTAX_ERROR: """Verify context data preservation during injection"""
    # REMOVED_SYNTAX_ERROR: for key, value in original.items():
        # REMOVED_SYNTAX_ERROR: if injected.get(key) != value:
            # REMOVED_SYNTAX_ERROR: return False
            # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: def validate_session_context(self, state: DeepAgentState,
# REMOVED_SYNTAX_ERROR: session_id: str) -> bool:
    # REMOVED_SYNTAX_ERROR: """Validate session context consistency"""
    # REMOVED_SYNTAX_ERROR: if not state.chat_thread_id:
        # REMOVED_SYNTAX_ERROR: return False
        # REMOVED_SYNTAX_ERROR: return state.chat_thread_id == session_id


# REMOVED_SYNTAX_ERROR: class ResourceTracker:
    # REMOVED_SYNTAX_ERROR: """Tracks agent resource consumption and limits"""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: """Initialize resource tracking"""
    # REMOVED_SYNTAX_ERROR: self.process = psutil.Process()

# REMOVED_SYNTAX_ERROR: def get_memory_usage_mb(self) -> float:
    # REMOVED_SYNTAX_ERROR: """Get current memory usage in MB"""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: return self.process.memory_info().rss / 1024 / 1024
        # REMOVED_SYNTAX_ERROR: except Exception:
            # REMOVED_SYNTAX_ERROR: return 0.0

# REMOVED_SYNTAX_ERROR: def get_token_consumption(self, agent_state: DeepAgentState) -> int:
    # REMOVED_SYNTAX_ERROR: """Calculate estimated token consumption"""
    # REMOVED_SYNTAX_ERROR: base_tokens = len(agent_state.user_request.split()) * 1.3
    # REMOVED_SYNTAX_ERROR: context_tokens = self._get_context_size(agent_state) * 0.25
    # REMOVED_SYNTAX_ERROR: return int(base_tokens + context_tokens)

# REMOVED_SYNTAX_ERROR: def _get_context_size(self, state: DeepAgentState) -> float:
    # REMOVED_SYNTAX_ERROR: """Get context size for token calculation"""
    # REMOVED_SYNTAX_ERROR: if not (state.metadata and state.metadata.execution_context):
        # REMOVED_SYNTAX_ERROR: return 0
        # REMOVED_SYNTAX_ERROR: return sum(len(str(v)) for v in state.metadata.execution_context.values())


# REMOVED_SYNTAX_ERROR: class StateTransitionValidator:
    # REMOVED_SYNTAX_ERROR: """Validates agent state transitions and routing decisions"""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: """Initialize transition validator"""
    # REMOVED_SYNTAX_ERROR: self.valid_transitions = self._define_valid_transitions()

# REMOVED_SYNTAX_ERROR: def _define_valid_transitions(self) -> Dict[ExecutionStatus, List[ExecutionStatus]]:
    # REMOVED_SYNTAX_ERROR: """Define valid state transitions"""
    # REMOVED_SYNTAX_ERROR: base_transitions = _get_base_transitions()
    # REMOVED_SYNTAX_ERROR: execution_transitions = _get_execution_transitions()
    # REMOVED_SYNTAX_ERROR: return {**base_transitions, **execution_transitions}

# REMOVED_SYNTAX_ERROR: def validate_transition(self, from_status: ExecutionStatus,
# REMOVED_SYNTAX_ERROR: to_status: ExecutionStatus) -> bool:
    # REMOVED_SYNTAX_ERROR: """Validate state transition is allowed"""
    # REMOVED_SYNTAX_ERROR: if from_status not in self.valid_transitions:
        # REMOVED_SYNTAX_ERROR: return False
        # REMOVED_SYNTAX_ERROR: return to_status in self.valid_transitions[from_status]

# REMOVED_SYNTAX_ERROR: def validate_message_routing(self, state: DeepAgentState,
# REMOVED_SYNTAX_ERROR: routing_decision: str) -> bool:
    # REMOVED_SYNTAX_ERROR: """Validate message routing decision based on state"""
    # REMOVED_SYNTAX_ERROR: request_type = self._classify_request_type(state.user_request)
    # REMOVED_SYNTAX_ERROR: expected_routing = self._get_expected_routing(request_type)
    # REMOVED_SYNTAX_ERROR: return routing_decision == expected_routing

# REMOVED_SYNTAX_ERROR: def _classify_request_type(self, user_request: str) -> str:
    # REMOVED_SYNTAX_ERROR: """Classify user request type for routing"""
    # REMOVED_SYNTAX_ERROR: keywords = _get_classification_keywords()

    # REMOVED_SYNTAX_ERROR: for request_type, words in keywords.items():
        # REMOVED_SYNTAX_ERROR: if _matches_keywords(user_request, words):
            # REMOVED_SYNTAX_ERROR: return request_type
            # REMOVED_SYNTAX_ERROR: return 'general'

# REMOVED_SYNTAX_ERROR: def _get_expected_routing(self, request_type: str) -> str:
    # REMOVED_SYNTAX_ERROR: """Get expected routing for request type"""
    # REMOVED_SYNTAX_ERROR: routing_map = _build_routing_map()
    # REMOVED_SYNTAX_ERROR: return routing_map.get(request_type, 'triage_sub_agent')


# REMOVED_SYNTAX_ERROR: class AgentStateValidatorTestSuite:
    # REMOVED_SYNTAX_ERROR: """Test suite for agent state validation"""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.validator = AgentStateValidator()
    # REMOVED_SYNTAX_ERROR: self.state_transition_validator = StateTransitionValidator()

# REMOVED_SYNTAX_ERROR: async def validate_full_agent_lifecycle(self, agent_name: str,
# REMOVED_SYNTAX_ERROR: initial_state: DeepAgentState) -> StateValidationResult:
    # REMOVED_SYNTAX_ERROR: """Validate complete agent lifecycle"""
    # REMOVED_SYNTAX_ERROR: result = await self.validator.validate_agent_startup(agent_name, initial_state)
    # REMOVED_SYNTAX_ERROR: if result.validation_passed:
        # REMOVED_SYNTAX_ERROR: self._validate_processing_state(initial_state, result)
        # REMOVED_SYNTAX_ERROR: return result

# REMOVED_SYNTAX_ERROR: def _validate_processing_state(self, state: DeepAgentState, result: StateValidationResult) -> None:
    # REMOVED_SYNTAX_ERROR: """Validate agent processing state"""
    # REMOVED_SYNTAX_ERROR: session_id = state.chat_thread_id or 'test-session'
    # REMOVED_SYNTAX_ERROR: context_valid = self.validator.context_validator.validate_session_context(state, session_id)
    # REMOVED_SYNTAX_ERROR: if not context_valid:
        # REMOVED_SYNTAX_ERROR: _handle_context_validation_failure(result)


        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def agent_state_validator():
    # REMOVED_SYNTAX_ERROR: return AgentStateValidator()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_agent_states():
    # REMOVED_SYNTAX_ERROR: base_metadata = _create_test_metadata()
    # REMOVED_SYNTAX_ERROR: return {'valid_state': _create_valid_test_state(base_metadata), 'invalid_state': _create_invalid_test_state()}

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def execution_contexts():
    # REMOVED_SYNTAX_ERROR: test_state = DeepAgentState(user_request="Test request")
    # REMOVED_SYNTAX_ERROR: return {'valid_context': _create_test_execution_context(test_state)}


    # Consolidated helper functions
# REMOVED_SYNTAX_ERROR: def _validate_single_field(state, field_name, metrics, validation_passed):
    # REMOVED_SYNTAX_ERROR: """Validate individual field presence"""
    # REMOVED_SYNTAX_ERROR: value = getattr(state, field_name, None)
    # REMOVED_SYNTAX_ERROR: valid = bool(value and value.strip()) if field_name == 'user_request' else value is not None
    # REMOVED_SYNTAX_ERROR: if not valid:
        # REMOVED_SYNTAX_ERROR: metrics.validation_errors.append("formatted_string")
        # REMOVED_SYNTAX_ERROR: return False
        # REMOVED_SYNTAX_ERROR: return validation_passed

# REMOVED_SYNTAX_ERROR: def _get_base_transitions():
    # REMOVED_SYNTAX_ERROR: """Get base state transitions"""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: ExecutionStatus.PENDING: [ExecutionStatus.INITIALIZING, ExecutionStatus.FAILED],
    # REMOVED_SYNTAX_ERROR: ExecutionStatus.INITIALIZING: [ExecutionStatus.EXECUTING, ExecutionStatus.FAILED],
    # REMOVED_SYNTAX_ERROR: ExecutionStatus.EXECUTING: [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.RETRYING],
    # REMOVED_SYNTAX_ERROR: ExecutionStatus.RETRYING: [ExecutionStatus.EXECUTING, ExecutionStatus.FAILED, ExecutionStatus.FALLBACK],
    # REMOVED_SYNTAX_ERROR: ExecutionStatus.FALLBACK: [ExecutionStatus.COMPLETED, ExecutionStatus.DEGRADED]}

# REMOVED_SYNTAX_ERROR: def _get_classification_keywords():
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: 'data': ['analyze', 'data', 'query', 'report'],
    # REMOVED_SYNTAX_ERROR: 'optimization': ['optimize', 'improve', 'reduce', 'costs'],
    # REMOVED_SYNTAX_ERROR: 'action': ['implement', 'execute', 'deploy', 'action']
    

# REMOVED_SYNTAX_ERROR: def _matches_keywords(user_request, words):
    # REMOVED_SYNTAX_ERROR: return any(word in user_request.lower() for word in words)

# REMOVED_SYNTAX_ERROR: def _build_routing_map():
    # REMOVED_SYNTAX_ERROR: return {'data': 'data_sub_agent', 'optimization': 'optimizations_sub_agent',
    # REMOVED_SYNTAX_ERROR: 'action': 'actions_sub_agent', 'general': 'triage_sub_agent'}

# REMOVED_SYNTAX_ERROR: def _define_agent_memory_limits():
    # REMOVED_SYNTAX_ERROR: return {'supervisor': 512.0, 'data_sub_agent': 256.0, 'optimizations_sub_agent': 256.0, 'default': 128.0}

# REMOVED_SYNTAX_ERROR: def _handle_context_validation_failure(result):
    # REMOVED_SYNTAX_ERROR: result.state_metrics.validation_errors.append("Session context validation failed")
    # REMOVED_SYNTAX_ERROR: result.validation_passed = False

# REMOVED_SYNTAX_ERROR: def _create_valid_test_state(base_metadata):
    # REMOVED_SYNTAX_ERROR: return DeepAgentState(user_request="Optimize AI costs", user_id="test-user",
    # REMOVED_SYNTAX_ERROR: chat_thread_id="test-thread", metadata=base_metadata)

# REMOVED_SYNTAX_ERROR: def _create_invalid_test_state():
    # REMOVED_SYNTAX_ERROR: return DeepAgentState(user_request="", metadata=None)

# REMOVED_SYNTAX_ERROR: def _create_test_metadata():
    # REMOVED_SYNTAX_ERROR: return AgentMetadata(execution_context={'test_mode': True},
    # REMOVED_SYNTAX_ERROR: custom_fields={'tier': CustomerTier.ENTERPRISE.value})

# REMOVED_SYNTAX_ERROR: def _get_context_params(test_state):
    # REMOVED_SYNTAX_ERROR: return {'run_id': "test-run", 'agent_name': "test_agent", 'state': test_state,
    # REMOVED_SYNTAX_ERROR: 'stream_updates': True, 'user_id': "test-user"}

# REMOVED_SYNTAX_ERROR: def _create_test_execution_context(test_state):
    # REMOVED_SYNTAX_ERROR: return ExecutionContext(**_get_context_params(test_state))


    # Test collection for pytest discovery
    # REMOVED_SYNTAX_ERROR: __all__ = [ )
    # REMOVED_SYNTAX_ERROR: 'AgentStateValidator',
    # REMOVED_SYNTAX_ERROR: 'ContextValidator',
    # REMOVED_SYNTAX_ERROR: 'ResourceTracker',
    # REMOVED_SYNTAX_ERROR: 'StateTransitionValidator',
    # REMOVED_SYNTAX_ERROR: 'AgentStateValidatorTestSuite',
    # REMOVED_SYNTAX_ERROR: 'agent_state_validator',
    # REMOVED_SYNTAX_ERROR: 'sample_agent_states',
    # REMOVED_SYNTAX_ERROR: 'execution_contexts'
    
'''Agent State Validator - Unified System Testing Phase 5
Validates agent initialization, transitions, and resource usage.
BVJ: Enterprise/Growth segment - $50K+ revenue protection from session failures.
Architecture:  <= 300 lines,  <= 8 lines per function, modular validators.
'''

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
from tests.e2e.config import ( )
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
CustomerTier,
UnifiedTestConfig,
get_test_user,



@dataclass
class AgentStateMetrics:
    """Agent state performance and resource metrics"""
    memory_usage_mb: float = 0.0
    initialization_time_ms: float = 0.0
    state_transition_time_ms: float = 0.0
    token_consumption: int = 0
    context_preservation_score: float = 1.0
    error_count: int = 0
    validation_errors: List[str] = field(default_factory=list)


    @dataclass
class StateValidationResult:
    """Agent state validation result with detailed metrics"""
    agent_name: str
    validation_passed: bool
    state_metrics: AgentStateMetrics
    validation_details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda x: None datetime.now(timezone.utc))


class AgentStateValidator:
    """Main agent state validation engine"""

    def __init__(self, test_config: Optional[UnifiedTestConfig] = None):
        """Initialize validator with test configuration"""
        self.config = test_config or UnifiedTestConfig()
        self.validation_results: List[StateValidationResult] = []
        self.resource_tracker = ResourceTracker()
        self.context_validator = ContextValidator()

        async def validate_agent_startup(self, agent_name: str,
        state: DeepAgentState) -> StateValidationResult:
        """Validate agent startup initialization state"""
        metrics = AgentStateMetrics()
        start_time = time.perf_counter()

        startup_valid = self._validate_startup_fields(state, metrics)
        memory_valid = await self._validate_memory_usage(agent_name, metrics)

        metrics.initialization_time_ms = (time.perf_counter() - start_time) * 1000
        validation_passed = startup_valid and memory_valid

        return StateValidationResult(agent_name, validation_passed, metrics)

        def _validate_startup_fields(self, state: DeepAgentState,
        metrics: AgentStateMetrics) -> bool:
        """Validate required startup state fields"""
        required_fields = ['user_request', 'metadata']
        validation_passed = True
        for field_name in required_fields:
        validation_passed = _validate_single_field(state, field_name, metrics, validation_passed)
        return validation_passed


        async def _validate_memory_usage(self, agent_name: str,
        metrics: AgentStateMetrics) -> bool:
        """Validate agent memory usage within limits"""
        try:
        memory_mb = self.resource_tracker.get_memory_usage_mb()
        metrics.memory_usage_mb = memory_mb
        return memory_mb < self._get_memory_limit(agent_name)
        except Exception as e:
        metrics.validation_errors.append("formatted_string")
        return False


class ContextValidator:
        """Validator for agent context preservation and injection"""

        def validate_context_injection(self, state: DeepAgentState,
        user_context: Dict[str, Any]) -> bool:
        """Validate user context injection into agent state"""
        if not user_context:
        return True

        injected_context = self._extract_injected_context(state)
        return self._verify_context_preservation(user_context, injected_context)

    def _extract_injected_context(self, state: DeepAgentState) -> Dict[str, Any]:
        """Extract injected context from agent state"""
        if not state.metadata or not state.metadata.execution_context:
        return {}
        return state.metadata.execution_context

        def _verify_context_preservation(self, original: Dict[str, Any],
        injected: Dict[str, Any]) -> bool:
        """Verify context data preservation during injection"""
        for key, value in original.items():
        if injected.get(key) != value:
        return False
        return True

        def validate_session_context(self, state: DeepAgentState,
        session_id: str) -> bool:
        """Validate session context consistency"""
        if not state.chat_thread_id:
        return False
        return state.chat_thread_id == session_id


class ResourceTracker:
        """Tracks agent resource consumption and limits"""

    def __init__(self):
        """Initialize resource tracking"""
        self.process = psutil.Process()

    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
        return self.process.memory_info().rss / 1024 / 1024
        except Exception:
        return 0.0

    def get_token_consumption(self, agent_state: DeepAgentState) -> int:
        """Calculate estimated token consumption"""
        base_tokens = len(agent_state.user_request.split()) * 1.3
        context_tokens = self._get_context_size(agent_state) * 0.25
        return int(base_tokens + context_tokens)

    def _get_context_size(self, state: DeepAgentState) -> float:
        """Get context size for token calculation"""
        if not (state.metadata and state.metadata.execution_context):
        return 0
        return sum(len(str(v)) for v in state.metadata.execution_context.values())


class StateTransitionValidator:
        """Validates agent state transitions and routing decisions"""

    def __init__(self):
        """Initialize transition validator"""
        self.valid_transitions = self._define_valid_transitions()

    def _define_valid_transitions(self) -> Dict[ExecutionStatus, List[ExecutionStatus]]:
        """Define valid state transitions"""
        base_transitions = _get_base_transitions()
        execution_transitions = _get_execution_transitions()
        return {**base_transitions, **execution_transitions}

        def validate_transition(self, from_status: ExecutionStatus,
        to_status: ExecutionStatus) -> bool:
        """Validate state transition is allowed"""
        if from_status not in self.valid_transitions:
        return False
        return to_status in self.valid_transitions[from_status]

        def validate_message_routing(self, state: DeepAgentState,
        routing_decision: str) -> bool:
        """Validate message routing decision based on state"""
        request_type = self._classify_request_type(state.user_request)
        expected_routing = self._get_expected_routing(request_type)
        return routing_decision == expected_routing

    def _classify_request_type(self, user_request: str) -> str:
        """Classify user request type for routing"""
        keywords = _get_classification_keywords()

        for request_type, words in keywords.items():
        if _matches_keywords(user_request, words):
        return request_type
        return 'general'

    def _get_expected_routing(self, request_type: str) -> str:
        """Get expected routing for request type"""
        routing_map = _build_routing_map()
        return routing_map.get(request_type, 'triage_sub_agent')


class AgentStateValidatorTestSuite:
        """Test suite for agent state validation"""

    def __init__(self):
        self.validator = AgentStateValidator()
        self.state_transition_validator = StateTransitionValidator()

        async def validate_full_agent_lifecycle(self, agent_name: str,
        initial_state: DeepAgentState) -> StateValidationResult:
        """Validate complete agent lifecycle"""
        result = await self.validator.validate_agent_startup(agent_name, initial_state)
        if result.validation_passed:
        self._validate_processing_state(initial_state, result)
        return result

    def _validate_processing_state(self, state: DeepAgentState, result: StateValidationResult) -> None:
        """Validate agent processing state"""
        session_id = state.chat_thread_id or 'test-session'
        context_valid = self.validator.context_validator.validate_session_context(state, session_id)
        if not context_valid:
        _handle_context_validation_failure(result)


        @pytest.fixture
    def agent_state_validator():
        return AgentStateValidator()

        @pytest.fixture
    def sample_agent_states():
        base_metadata = _create_test_metadata()
        return {'valid_state': _create_valid_test_state(base_metadata), 'invalid_state': _create_invalid_test_state()}

        @pytest.fixture
    def execution_contexts():
        test_state = DeepAgentState(user_request="Test request")
        return {'valid_context': _create_test_execution_context(test_state)}


    # Consolidated helper functions
    def _validate_single_field(state, field_name, metrics, validation_passed):
        """Validate individual field presence"""
        value = getattr(state, field_name, None)
        valid = bool(value and value.strip()) if field_name == 'user_request' else value is not None
        if not valid:
        metrics.validation_errors.append("formatted_string")
        return False
        return validation_passed

    def _get_base_transitions():
        """Get base state transitions"""
        return { )
        ExecutionStatus.PENDING: [ExecutionStatus.INITIALIZING, ExecutionStatus.FAILED],
        ExecutionStatus.INITIALIZING: [ExecutionStatus.EXECUTING, ExecutionStatus.FAILED],
        ExecutionStatus.EXECUTING: [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.RETRYING],
        ExecutionStatus.RETRYING: [ExecutionStatus.EXECUTING, ExecutionStatus.FAILED, ExecutionStatus.FALLBACK],
        ExecutionStatus.FALLBACK: [ExecutionStatus.COMPLETED, ExecutionStatus.DEGRADED]}

    def _get_classification_keywords():
        return { )
        'data': ['analyze', 'data', 'query', 'report'],
        'optimization': ['optimize', 'improve', 'reduce', 'costs'],
        'action': ['implement', 'execute', 'deploy', 'action']
    

    def _matches_keywords(user_request, words):
        return any(word in user_request.lower() for word in words)

    def _build_routing_map():
        return {'data': 'data_sub_agent', 'optimization': 'optimizations_sub_agent',
        'action': 'actions_sub_agent', 'general': 'triage_sub_agent'}

    def _define_agent_memory_limits():
        return {'supervisor': 512.0, 'data_sub_agent': 256.0, 'optimizations_sub_agent': 256.0, 'default': 128.0}

    def _handle_context_validation_failure(result):
        result.state_metrics.validation_errors.append("Session context validation failed")
        result.validation_passed = False

    def _create_valid_test_state(base_metadata):
        return DeepAgentState(user_request="Optimize AI costs", user_id="test-user",
        chat_thread_id="test-thread", metadata=base_metadata)

    def _create_invalid_test_state():
        return DeepAgentState(user_request="", metadata=None)

    def _create_test_metadata():
        return AgentMetadata(execution_context={'test_mode': True},
        custom_fields={'tier': CustomerTier.ENTERPRISE.value})

    def _get_context_params(test_state):
        return {'run_id': "test-run", 'agent_name': "test_agent", 'state': test_state,
        'stream_updates': True, 'user_id': "test-user"}

    def _create_test_execution_context(test_state):
        return ExecutionContext(**_get_context_params(test_state))


    # Test collection for pytest discovery
        __all__ = [ )
        'AgentStateValidator',
        'ContextValidator',
        'ResourceTracker',
        'StateTransitionValidator',
        'AgentStateValidatorTestSuite',
        'agent_state_validator',
        'sample_agent_states',
        'execution_contexts'
    

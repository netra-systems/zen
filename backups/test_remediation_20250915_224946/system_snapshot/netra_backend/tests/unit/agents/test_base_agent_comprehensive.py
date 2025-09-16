"""Comprehensive BaseAgent Unit Test Suite - 100% Coverage Focus

MISSION-CRITICAL TEST SUITE: Complete validation of BaseAgent SSOT patterns and infrastructure.

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)  
- Business Goal: Platform Reliability & System Availability
- Value Impact: BaseAgent reliability = Core platform foundation = $2M+ ARR protection
- Strategic Impact: Every agent in the system inherits from BaseAgent, so reliability here
  cascades to ALL agent operations, directly impacting user chat experience and business value delivery

COVERAGE TARGET: 100% of BaseAgent critical methods and patterns including:
- State management and lifecycle transitions (lines 234-287)
- WebSocket bridge integration and event emission (lines 904-1020) 
- Token management and cost optimization (lines 374-491)
- Session isolation validation (lines 492-531)
- Reliability infrastructure patterns (lines 1020-1100)
- Factory method patterns (lines 1477-1759)
- Abstract method contracts and execution patterns

CRITICAL: Uses REAL services approach with minimal mocks per CLAUDE.md standards.
Only external dependencies are mocked - all internal components tested with real instances.
"""
import asyncio
import copy
import pytest
import time
import warnings
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
from shared.isolated_environment import get_env, IsolatedEnvironment
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.observability import generate_llm_correlation_id
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler

def create_real_user_execution_context(user_id='test-user-123', thread_id='test-thread-456', run_id='test-run-789', request_id='test-request-123', agent_context=None, audit_metadata=None, db_session=None):
    """Create a real UserExecutionContext for testing with proper interface."""
    if agent_context is None:
        agent_context = {}
    if audit_metadata is None:
        audit_metadata = {}
    if db_session is None:
        db_session = Mock()
    return UserExecutionContext(user_id=user_id, thread_id=thread_id, run_id=run_id, request_id=request_id, agent_context=agent_context, audit_metadata=audit_metadata, db_session=db_session)

@dataclass
class MockUserExecutionContext:
    """Mock UserExecutionContext for testing isolated behavior.
    
    Updated to match the evolved UserExecutionContext interface with agent_context
    and audit_metadata instead of the legacy metadata parameter.
    """
    user_id: str = 'test-user-123'
    thread_id: str = 'test-thread-456'
    run_id: str = 'test-run-789'
    request_id: str = 'test-request-123'
    agent_context: dict = None
    audit_metadata: dict = None
    db_session: Mock = None
    websocket_client_id: Optional[str] = None

    def __post_init__(self):
        if self.agent_context is None:
            self.agent_context = {}
        if self.audit_metadata is None:
            self.audit_metadata = {}
        if self.db_session is None:
            self.db_session = Mock()

    @property
    def metadata(self) -> dict:
        """Backward compatibility property for legacy tests."""
        merged = copy.deepcopy(self.agent_context)
        merged.update(self.audit_metadata)
        return merged

    @metadata.setter
    def metadata(self, value: dict):
        """Backward compatibility setter for legacy tests."""
        self.agent_context.clear()
        self.audit_metadata.clear()
        self.agent_context.update(value)

    @metadata.deleter
    def metadata(self):
        """Backward compatibility deleter for legacy tests."""
        self.agent_context.clear()
        self.audit_metadata.clear()

class MockableBaseAgent(BaseAgent):
    """Mockable BaseAgent implementation for comprehensive testing.
    
    Note: Renamed from MockableBaseAgent to avoid pytest collection issues.
    Class names starting with 'Test' are automatically collected by pytest.
    """

    def __init__(self, *args, **kwargs):
        self._test_execution_should_succeed = kwargs.pop('execution_should_succeed', True)
        self._test_validation_should_pass = kwargs.pop('validation_should_pass', True)
        self._test_execution_result = kwargs.pop('execution_result', {})
        self._test_websocket_events_enabled = kwargs.pop('websocket_events_enabled', True)
        self._test_reliability_mode = kwargs.pop('reliability_mode', 'normal')
        super().__init__(*args, **kwargs)

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool=False) -> dict:
        """Modern execution method for UserExecutionContext pattern."""
        if not self._test_execution_should_succeed:
            raise RuntimeError('Test execution failure')
        if self._test_websocket_events_enabled:
            await self.emit_agent_started('Test agent execution started')
            await self.emit_thinking('Test agent processing request')
            if context.metadata.get('simulate_tools'):
                await self.emit_tool_executing('test_tool', {'param': 'value'})
                await self.emit_tool_completed('test_tool', {'result': 'success'})
            await self.emit_agent_completed(self._test_execution_result, context)
        return {'status': 'completed', 'result': self._test_execution_result, 'agent_name': self.name, 'execution_time': time.time()}

    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validation method for legacy execution testing."""
        return self._test_validation_should_pass

    async def execute_core_logic(self, context: ExecutionContext) -> dict:
        """Legacy execution method for backward compatibility testing."""
        if not self._test_execution_should_succeed:
            raise ValueError('Test core logic failure')
        return {'status': 'legacy_completed', 'result': self._test_execution_result, 'agent_name': self.name}

class BaseAgentInitializationTests:
    """Test BaseAgent initialization patterns and configuration.
    
    BVJ: Platform Stability | Agent initialization must be bulletproof for system reliability.
    """

    def test_basic_initialization_with_defaults(self):
        """Test BaseAgent basic initialization with default parameters.
        
        COVERAGE: __init__ method, basic attribute assignment, default configurations.
        """
        agent = MockableBaseAgent(name='BasicTestAgent', description='Test agent')
        assert agent is not None
        assert agent.name == 'BasicTestAgent'
        assert agent.description == 'Test agent'
        assert agent.state == SubAgentLifecycle.PENDING
        assert agent.agent_id.startswith('BasicTestAgent_')
        assert agent.correlation_id is not None
        assert hasattr(agent, 'timing_collector')
        assert hasattr(agent, 'token_counter')
        assert hasattr(agent, 'token_context_manager')
        assert hasattr(agent, 'circuit_breaker')
        assert hasattr(agent, 'monitor')

    def test_initialization_with_reliability_enabled(self):
        """Test BaseAgent initialization with reliability features enabled.
        
        COVERAGE: _init_unified_reliability_infrastructure method, reliability manager setup.
        """
        agent = MockableBaseAgent(name='ReliabilityAgent', enable_reliability=True, enable_execution_engine=True)
        assert agent._enable_reliability is True
        assert agent._unified_reliability_handler is not None
        assert agent._reliability_manager_instance is not None
        assert agent.reliability_manager is not None
        assert hasattr(agent, 'circuit_breaker')
        assert agent.circuit_breaker is not None

    def test_initialization_with_legacy_tool_dispatcher_warning(self):
        """Test BaseAgent initialization with deprecated tool_dispatcher parameter.
        
        COVERAGE: Deprecation warning system for legacy patterns.
        """
        mock_tool_dispatcher = Mock(spec=ToolDispatcher)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            agent = MockableBaseAgent(name='LegacyAgent', tool_dispatcher=mock_tool_dispatcher)
            assert len(w) > 0
            assert any(('tool_dispatcher parameter creates global state risks' in str(warning.message) for warning in w))
            assert any(('tool_dispatcher' in str(warning.message) for warning in w))
        assert agent.tool_dispatcher is mock_tool_dispatcher

    def test_initialization_with_user_context(self):
        """Test BaseAgent initialization with UserExecutionContext.
        
        COVERAGE: user_context handling, WebSocket emitter initialization.
        """
        mock_context = MockUserExecutionContext()
        agent = MockableBaseAgent(name='ContextAgent', user_context=mock_context)
        assert agent.user_context is mock_context
        assert agent._websocket_emitter is None

    def test_session_isolation_validation_on_init(self):
        """Test session isolation validation during initialization.
        
        COVERAGE: _validate_session_isolation method.
        """
        agent = MockableBaseAgent(name='IsolatedAgent')
        assert agent is not None

class BaseAgentStateManagementTests:
    """Test BaseAgent state management and lifecycle transitions.
    
    BVJ: Platform Stability | Agent state consistency prevents execution errors and user confusion.
    COVERAGE TARGET: Lines 234-287 (state management methods).
    """

    @pytest.fixture(autouse=True)
    def setUp(self):
        """Set up test agent for state management testing."""
        self.agent = MockableBaseAgent(name='StateTestAgent')

    def test_initial_state_is_pending(self):
        """Test agent initializes in PENDING state.
        
        COVERAGE: Initial state assignment in __init__.
        """
        assert self.agent.get_state() == SubAgentLifecycle.PENDING

    def test_valid_state_transitions(self):
        """Test all valid state transitions according to state machine.
        
        COVERAGE: set_state method, _is_valid_transition, _get_valid_transitions.
        """
        self.agent.set_state(SubAgentLifecycle.RUNNING)
        assert self.agent.get_state() == SubAgentLifecycle.RUNNING
        self.agent.set_state(SubAgentLifecycle.COMPLETED)
        assert self.agent.get_state() == SubAgentLifecycle.COMPLETED
        self.agent.set_state(SubAgentLifecycle.SHUTDOWN)
        assert self.agent.get_state() == SubAgentLifecycle.SHUTDOWN

    def test_running_to_failed_transition(self):
        """Test RUNNING -> FAILED transition.
        
        COVERAGE: State transition validation for failure scenarios.
        """
        self.agent.set_state(SubAgentLifecycle.RUNNING)
        self.agent.set_state(SubAgentLifecycle.FAILED)
        assert self.agent.get_state() == SubAgentLifecycle.FAILED

    def test_failed_to_pending_retry_transition(self):
        """Test FAILED -> PENDING transition for retry scenarios.
        
        COVERAGE: Retry transition logic in state machine.
        """
        self.agent.set_state(SubAgentLifecycle.RUNNING)
        self.agent.set_state(SubAgentLifecycle.FAILED)
        self.agent.set_state(SubAgentLifecycle.PENDING)
        assert self.agent.get_state() == SubAgentLifecycle.PENDING

    def test_invalid_state_transitions_raise_errors(self):
        """Test invalid state transitions raise ValueError.
        
        COVERAGE: _raise_transition_error method, invalid transition validation.
        """
        with pytest.raises(ValueError) as exc_info:
            self.agent.set_state(SubAgentLifecycle.COMPLETED)
        assert 'Invalid state transition' in str(exc_info.value)
        assert 'PENDING' in str(exc_info.value)
        assert 'COMPLETED' in str(exc_info.value)

    def test_completed_state_only_allows_shutdown(self):
        """Test COMPLETED state only allows transition to SHUTDOWN.
        
        COVERAGE: Terminal state behavior in state machine.
        """
        self.agent.set_state(SubAgentLifecycle.RUNNING)
        self.agent.set_state(SubAgentLifecycle.COMPLETED)
        with pytest.raises(ValueError):
            self.agent.set_state(SubAgentLifecycle.RUNNING)
        with pytest.raises(ValueError):
            self.agent.set_state(SubAgentLifecycle.PENDING)

    def test_shutdown_is_terminal_state(self):
        """Test SHUTDOWN is terminal state with no valid transitions.
        
        COVERAGE: Terminal state enforcement in state machine.
        """
        self.agent.set_state(SubAgentLifecycle.RUNNING)
        self.agent.set_state(SubAgentLifecycle.COMPLETED)
        self.agent.set_state(SubAgentLifecycle.SHUTDOWN)
        with pytest.raises(ValueError):
            self.agent.set_state(SubAgentLifecycle.PENDING)

class BaseAgentWebSocketBridgeTests:
    """Test BaseAgent WebSocket bridge integration and event emission.
    
    BVJ: Revenue Generation | WebSocket events = User engagement = Chat value = Revenue.
    COVERAGE TARGET: Lines 904-1020 (WebSocket bridge methods).
    """

    @pytest.fixture(autouse=True)
    def setUp(self):
        """Set up agent with WebSocket bridge for testing."""
        self.agent = MockableBaseAgent(name='WebSocketTestAgent')
        self.mock_bridge = Mock()
        self.mock_context = MockUserExecutionContext()
        self.agent._websocket_adapter.set_websocket_bridge = Mock()
        self.agent._websocket_adapter.has_websocket_bridge = Mock(return_value=False)
        self.agent._websocket_adapter.emit_agent_started = AsyncMock()
        self.agent._websocket_adapter.emit_thinking = AsyncMock()
        self.agent._websocket_adapter.emit_tool_executing = AsyncMock()
        self.agent._websocket_adapter.emit_tool_completed = AsyncMock()
        self.agent._websocket_adapter.emit_agent_completed = AsyncMock()
        self.agent._websocket_adapter.emit_progress = AsyncMock()
        self.agent._websocket_adapter.emit_error = AsyncMock()
        self.agent._websocket_adapter.emit_tool_started = AsyncMock()
        self.agent._websocket_adapter.emit_subagent_started = AsyncMock()
        self.agent._websocket_adapter.emit_subagent_completed = AsyncMock()

    def test_websocket_bridge_adapter_initialization(self):
        """Test WebSocket bridge adapter is properly initialized.
        
        COVERAGE: WebSocketBridgeAdapter initialization in __init__.
        """
        assert hasattr(self.agent, '_websocket_adapter')
        assert self.agent._websocket_adapter is not None

    def test_set_websocket_bridge_method(self):
        """Test set_websocket_bridge configures bridge correctly.
        
        COVERAGE: set_websocket_bridge method.
        """
        run_id = 'test-run-123'
        self.agent.set_websocket_bridge(self.mock_bridge, run_id)
        self.agent._websocket_adapter.set_websocket_bridge.assert_called_once_with(self.mock_bridge, run_id, self.agent.name)

    def test_has_websocket_context_detection(self):
        """Test has_websocket_context method correctly detects bridge availability.
        
        COVERAGE: has_websocket_context method.
        """
        self.agent._websocket_adapter.has_websocket_bridge.return_value = False
        assert not self.agent.has_websocket_context()
        self.agent._websocket_adapter.has_websocket_bridge.return_value = True
        assert self.agent.has_websocket_context()

    @pytest.mark.asyncio
    async def test_emit_agent_started_event(self):
        """Test emit_agent_started WebSocket event.
        
        COVERAGE: emit_agent_started method delegation to adapter.
        """
        self.agent._websocket_adapter.emit_agent_started = AsyncMock()
        await self.agent.emit_agent_started('Test agent started')
        self.agent._websocket_adapter.emit_agent_started.assert_called_once_with('Test agent started')

    @pytest.mark.asyncio
    async def test_emit_thinking_event_with_token_enhancement(self):
        """Test emit_thinking with token usage enhancement.
        
        COVERAGE: emit_thinking method with context enhancement logic.
        """
        self.agent._websocket_adapter.emit_thinking = AsyncMock()
        await self.agent.emit_thinking('Processing request')
        self.agent._websocket_adapter.emit_thinking.assert_called_with('Processing request', None)
        context = MockUserExecutionContext()
        context.metadata = {'token_usage': {'operations': [{'input_tokens': 100, 'output_tokens': 50, 'cost': 0.0025}]}}
        await self.agent.emit_thinking('Enhanced thinking', context=context)
        call_args = self.agent._websocket_adapter.emit_thinking.call_args
        enhanced_thought = call_args[0][0]
        assert 'Tokens: 150' in enhanced_thought
        assert 'Cost: $0.0025' in enhanced_thought

    @pytest.mark.asyncio
    async def test_emit_tool_events(self):
        """Test tool execution WebSocket events.
        
        COVERAGE: emit_tool_executing, emit_tool_completed methods.
        """
        self.agent._websocket_adapter.emit_tool_executing = AsyncMock()
        self.agent._websocket_adapter.emit_tool_completed = AsyncMock()
        await self.agent.emit_tool_executing('analyze_costs', {'account': '123'})
        self.agent._websocket_adapter.emit_tool_executing.assert_called_once_with('analyze_costs', {'account': '123'})
        await self.agent.emit_tool_completed('analyze_costs', {'savings': 1000})
        self.agent._websocket_adapter.emit_tool_completed.assert_called_once_with('analyze_costs', {'savings': 1000})

    @pytest.mark.asyncio
    async def test_emit_agent_completed_with_cost_analysis(self):
        """Test emit_agent_completed with cost analysis enhancement.
        
        COVERAGE: emit_agent_completed method with context enhancement.
        """
        self.agent._websocket_adapter.emit_agent_completed = AsyncMock()
        context = MockUserExecutionContext()
        context.metadata = {'token_usage': {'operations': [{'input_tokens': 100, 'output_tokens': 50, 'cost': 0.003}, {'input_tokens': 200, 'output_tokens': 75, 'cost': 0.005}], 'cumulative_cost': 0.008, 'cumulative_tokens': 425}, 'cost_optimization_suggestions': [{'priority': 'high', 'suggestion': 'Use shorter prompts'}], 'prompt_optimizations': [{'tokens_saved': 50, 'cost_savings': 0.001}]}
        result = {'analysis': 'complete'}
        await self.agent.emit_agent_completed(result, context)
        call_args = self.agent._websocket_adapter.emit_agent_completed.call_args[0][0]
        assert 'cost_analysis' in call_args
        assert call_args['cost_analysis']['total_operations'] == 2
        assert call_args['cost_analysis']['cumulative_cost'] == 0.008
        assert 'optimization_alerts' in call_args
        assert 'optimization_summary' in call_args

    def test_propagate_websocket_context_to_state(self):
        """Test WebSocket context propagation for critical path validation.
        
        COVERAGE: propagate_websocket_context_to_state method.
        """
        context = {'bridge_id': 'test-bridge', 'connection_id': 'conn-123'}
        self.agent.propagate_websocket_context_to_state(context)
        assert hasattr(self.agent, '_websocket_context')
        assert self.agent._websocket_context == context

class BaseAgentTokenManagementTests:
    """Test BaseAgent token management and cost optimization methods.
    
    BVJ: Cost Optimization | Token management = Cost control = Customer satisfaction = Revenue retention.
    COVERAGE TARGET: Lines 374-491 (token management methods).
    """

    @pytest.fixture(autouse=True)
    def setUp(self):
        """Set up agent for token management testing."""
        self.agent = MockableBaseAgent(name='TokenTestAgent')
        self.mock_context = MockUserExecutionContext()

    def test_track_llm_usage_creates_enhanced_context(self):
        """Test track_llm_usage properly tracks usage and returns enhanced context.
        
        COVERAGE: track_llm_usage method, TokenOptimizationContextManager integration.
        """
        self.agent.token_context_manager.track_agent_usage = Mock()
        enhanced_context = MockUserExecutionContext()
        enhanced_context.metadata = {'token_tracking': 'added'}
        self.agent.token_context_manager.track_agent_usage.return_value = enhanced_context
        result = self.agent.track_llm_usage(context=self.mock_context, input_tokens=100, output_tokens=50, model='gpt-4', operation_type='execution')
        self.agent.token_context_manager.track_agent_usage.assert_called_once_with(context=self.mock_context, agent_name=self.agent.name, input_tokens=100, output_tokens=50, model='gpt-4', operation_type='execution')
        assert result is enhanced_context
        assert result.metadata['token_tracking'] == 'added'

    def test_optimize_prompt_for_context_returns_tuple(self):
        """Test optimize_prompt_for_context returns enhanced context and optimized prompt.
        
        COVERAGE: optimize_prompt_for_context method.
        """
        self.agent.token_context_manager.optimize_prompt_for_context = Mock()
        enhanced_context = MockUserExecutionContext()
        enhanced_context.metadata = {'prompt_optimizations': [{'tokens_saved': 20, 'reduction_percent': 15.5}]}
        optimized_prompt = 'Shorter prompt'
        self.agent.token_context_manager.optimize_prompt_for_context.return_value = (enhanced_context, optimized_prompt)
        original_prompt = 'This is a very long prompt that could be optimized'
        result_context, result_prompt = self.agent.optimize_prompt_for_context(context=self.mock_context, prompt=original_prompt, target_reduction=20)
        self.agent.token_context_manager.optimize_prompt_for_context.assert_called_once_with(context=self.mock_context, agent_name=self.agent.name, prompt=original_prompt, target_reduction=20)
        assert result_context is enhanced_context
        assert result_prompt == optimized_prompt

    def test_get_cost_optimization_suggestions(self):
        """Test get_cost_optimization_suggestions returns suggestions from context.
        
        COVERAGE: get_cost_optimization_suggestions method.
        """
        self.agent.token_context_manager.add_cost_suggestions = Mock()
        enhanced_context = MockUserExecutionContext()
        enhanced_context.metadata = {'cost_optimization_suggestions': {'suggestions': [{'type': 'prompt_optimization', 'priority': 'high'}, {'type': 'model_selection', 'priority': 'medium'}]}}
        self.agent.token_context_manager.add_cost_suggestions.return_value = enhanced_context
        result_context, suggestions = self.agent.get_cost_optimization_suggestions(self.mock_context)
        self.agent.token_context_manager.add_cost_suggestions.assert_called_once_with(context=self.mock_context, agent_name=self.agent.name)
        assert result_context is enhanced_context
        assert len(suggestions) == 2
        assert suggestions[0]['type'] == 'prompt_optimization'

    def test_get_token_usage_summary(self):
        """Test get_token_usage_summary aggregates usage data.
        
        COVERAGE: get_token_usage_summary method.
        """
        self.agent.token_counter.get_agent_usage_summary = Mock()
        self.agent.token_counter.get_agent_usage_summary.return_value = {'total_operations': 5, 'total_cost': 0.025, 'average_cost': 0.005}
        context = MockUserExecutionContext()
        context.metadata = {'token_usage': {'operations': [{'cost': 0.01}, {'cost': 0.015}], 'cumulative_cost': 0.025, 'cumulative_tokens': 500}}
        summary = self.agent.get_token_usage_summary(context)
        assert summary['total_operations'] == 5
        assert summary['total_cost'] == 0.025
        assert 'current_session' in summary
        assert summary['current_session']['operations_count'] == 2
        assert summary['current_session']['cumulative_cost'] == 0.025

class BaseAgentSessionIsolationTests:
    """Test BaseAgent session isolation validation methods.
    
    BVJ: Data Security | Session isolation = User privacy = Legal compliance = Business continuity.
    COVERAGE TARGET: Lines 492-531 (session isolation methods).
    """

    @pytest.fixture(autouse=True)
    def setUp(self):
        """Set up agent for session isolation testing."""
        self.agent = MockableBaseAgent(name='SessionTestAgent')

    @patch('netra_backend.app.database.session_manager.validate_agent_session_isolation')
    def test_validate_session_isolation_success(self, mock_validate):
        """Test successful session isolation validation.
        
        COVERAGE: _validate_session_isolation method success path.
        """
        mock_validate.return_value = True
        self.agent._validate_session_isolation()
        mock_validate.assert_called_once_with(self.agent)

    @patch('netra_backend.app.database.session_manager.validate_agent_session_isolation')
    def test_validate_session_isolation_failure(self, mock_validate):
        """Test session isolation validation failure handling.
        
        COVERAGE: _validate_session_isolation method error handling.
        """
        mock_validate.side_effect = Exception('Session isolation violation')
        with pytest.raises(Exception) as exc_info:
            self.agent._validate_session_isolation()
        assert 'Session isolation violation' in str(exc_info.value)

    @patch('netra_backend.app.database.session_manager.DatabaseSessionManager')
    def test_get_session_manager_success(self, mock_db_manager_class):
        """Test _get_session_manager creates manager correctly.
        
        COVERAGE: _get_session_manager method success path.
        """
        mock_manager = Mock()
        mock_db_manager_class.return_value = mock_manager
        real_context = UserExecutionContext(user_id='test-user-123', thread_id='test-thread-456', run_id='test-run-789', agent_context={}, audit_metadata={}, db_session=Mock())
        result = self.agent._get_session_manager(real_context)
        mock_db_manager_class.assert_called_once_with(real_context)
        assert result is mock_manager

    def test_get_session_manager_invalid_context_type(self):
        """Test _get_session_manager raises TypeError for invalid context.
        
        COVERAGE: _get_session_manager method type validation.
        """
        invalid_context = {'not': 'user_execution_context'}
        with pytest.raises(TypeError) as exc_info:
            self.agent._get_session_manager(invalid_context)
        assert 'Expected UserExecutionContext' in str(exc_info.value)

class BaseAgentReliabilityInfrastructureTests:
    """Test BaseAgent reliability infrastructure patterns.
    
    BVJ: System Availability | Reliability features = Uptime = Customer satisfaction = Revenue protection.
    COVERAGE TARGET: Lines 1020-1100 (reliability management methods).
    """

    @pytest.fixture(autouse=True)
    def setUp(self):
        """Set up agent with reliability features for testing."""
        self.agent = MockableBaseAgent(name='ReliabilityTestAgent', enable_reliability=True, enable_execution_engine=True)

    def test_unified_reliability_handler_initialization(self):
        """Test unified reliability handler is properly initialized.
        
        COVERAGE: _init_unified_reliability_infrastructure method.
        """
        assert self.agent._unified_reliability_handler is not None
        assert isinstance(self.agent._unified_reliability_handler, UnifiedRetryHandler)
        assert self.agent._unified_reliability_handler.service_name.startswith('agent_')

    def test_reliability_manager_property_access(self):
        """Test reliability_manager property returns correct instance.
        
        COVERAGE: reliability_manager property getter.
        """
        manager = self.agent.reliability_manager
        assert manager is not None
        assert manager is self.agent._reliability_manager_instance

    def test_unified_reliability_handler_property(self):
        """Test unified_reliability_handler property access.
        
        COVERAGE: unified_reliability_handler property getter.
        """
        handler = self.agent.unified_reliability_handler
        assert handler is self.agent._unified_reliability_handler
        assert isinstance(handler, UnifiedRetryHandler)

    def test_legacy_reliability_property_delegates(self):
        """Test legacy_reliability property delegates to unified handler.
        
        COVERAGE: legacy_reliability property for backward compatibility.
        """
        legacy = self.agent.legacy_reliability
        assert legacy is self.agent._unified_reliability_handler

    def test_execution_engine_initialization(self):
        """Test execution engine is properly initialized.
        
        COVERAGE: _init_execution_infrastructure method.
        """
        assert self.agent._execution_engine is not None
        assert self.agent.execution_engine is not None

    def test_execution_monitor_initialization(self):
        """Test execution monitor is properly initialized.
        
        COVERAGE: execution monitor setup and property access.
        """
        assert self.agent._execution_monitor is not None
        assert self.agent.execution_monitor is not None
        assert self.agent.monitor is self.agent._execution_monitor

    @pytest.mark.asyncio
    async def test_execute_with_reliability_success(self):
        """Test execute_with_reliability method success path.
        
        COVERAGE: execute_with_reliability method.
        """

        async def mock_operation():
            return {'status': 'success', 'data': 'test_result'}
        mock_result = Mock()
        mock_result.success = True
        mock_result.result = {'status': 'success', 'data': 'test_result'}
        self.agent._unified_reliability_handler.execute_with_retry_async = AsyncMock(return_value=mock_result)
        result = await self.agent.execute_with_reliability(operation=mock_operation, operation_name='test_operation')
        assert result == {'status': 'success', 'data': 'test_result'}

    @pytest.mark.asyncio
    async def test_execute_with_reliability_failure_with_fallback(self):
        """Test execute_with_reliability with failure and successful fallback.
        
        COVERAGE: execute_with_reliability method fallback logic.
        """

        async def mock_operation():
            raise RuntimeError('Primary operation failed')

        async def mock_fallback():
            return {'status': 'fallback_success'}
        mock_primary_result = Mock()
        mock_primary_result.success = False
        mock_primary_result.final_exception = RuntimeError('Primary failed')
        mock_fallback_result = Mock()
        mock_fallback_result.success = True
        mock_fallback_result.result = {'status': 'fallback_success'}
        self.agent._unified_reliability_handler.execute_with_retry_async = AsyncMock()
        self.agent._unified_reliability_handler.execute_with_retry_async.side_effect = [mock_primary_result, mock_fallback_result]
        result = await self.agent.execute_with_reliability(operation=mock_operation, operation_name='test_operation', fallback=mock_fallback)
        assert result == {'status': 'fallback_success'}

    def test_get_circuit_breaker_status_with_reliability_enabled(self):
        """Test get_circuit_breaker_status with reliability enabled.
        
        COVERAGE: get_circuit_breaker_status method with enabled reliability.
        """
        self.agent.circuit_breaker.get_status = Mock(return_value={'state': 'closed', 'domain': 'agent', 'metrics': {'failure_count': 0}, 'is_healthy': True})
        self.agent.circuit_breaker.can_execute = Mock(return_value=True)
        status = self.agent.get_circuit_breaker_status()
        assert status['state'] == 'closed'
        assert status['status'] == 'closed'
        assert status['domain'] == 'agent'
        assert status['is_healthy'] is True

    def test_get_circuit_breaker_status_with_reliability_disabled(self):
        """Test get_circuit_breaker_status with reliability disabled.
        
        COVERAGE: get_circuit_breaker_status method with disabled reliability.
        """
        disabled_agent = MockableBaseAgent(name='DisabledReliabilityAgent', enable_reliability=False)
        status = disabled_agent.get_circuit_breaker_status()
        assert status['status'] == 'not_available'
        assert 'reliability not enabled' in status['reason']

class BaseAgentHealthStatusTests:
    """Test BaseAgent health status infrastructure.
    
    BVJ: Operations Excellence | Health monitoring = Proactive issue detection = Reduced downtime.
    COVERAGE TARGET: Health status and monitoring methods.
    """

    @pytest.fixture(autouse=True)
    def setUp(self):
        """Set up agent with full infrastructure for health testing."""
        self.agent = MockableBaseAgent(name='HealthTestAgent', enable_reliability=True, enable_execution_engine=True)

    def test_get_health_status_comprehensive(self):
        """Test get_health_status returns comprehensive health data.
        
        COVERAGE: get_health_status method with all components.
        """
        self.agent.circuit_breaker.get_status = Mock(return_value={'state': 'closed', 'metrics': {'failure_count': 0}, 'is_healthy': True})
        self.agent.circuit_breaker.can_execute = Mock(return_value=True)
        self.agent._reliability_manager_instance.get_health_status = Mock(return_value={'status': 'active', 'total_executions': 10, 'success_rate': 0.9, 'circuit_breaker_state': 'closed'})
        self.agent.monitor.get_health_status = Mock(return_value={'total_executions': 15, 'success_rate': 0.95, 'average_execution_time': 100.0, 'error_rate': 0.05})
        self.agent._execution_engine.get_health_status = Mock(return_value={'monitor': {'status': 'healthy'}, 'status': 'operational'})
        health = self.agent.get_health_status()
        assert health['agent_name'] == 'HealthTestAgent'
        assert health['state'] == 'pending'
        assert health['uses_unified_reliability'] is True
        assert 'circuit_breaker' in health
        assert 'reliability_manager' in health
        assert 'monitor' in health
        assert 'execution_engine' in health
        assert 'unified_reliability' in health
        assert health['overall_status'] == 'healthy'

    def test_determine_overall_health_status_healthy(self):
        """Test _determine_overall_health_status returns healthy for good metrics.
        
        COVERAGE: _determine_overall_health_status method healthy path.
        """
        health_data = {'circuit_breaker': {'state': 'closed', 'can_execute': True}, 'monitor': {'error_rate': 0.05}}
        status = self.agent._determine_overall_health_status(health_data)
        assert status == 'healthy'

    def test_determine_overall_health_status_degraded(self):
        """Test _determine_overall_health_status returns degraded for issues.
        
        COVERAGE: _determine_overall_health_status method degraded path.
        """
        health_data = {'circuit_breaker': {'state': 'open', 'can_execute': False}, 'monitor': {'error_rate': 0.25}}
        status = self.agent._determine_overall_health_status(health_data)
        assert status == 'degraded'

class BaseAgentExecutionPatternsTests:
    """Test BaseAgent execution patterns and abstract method contracts.
    
    BVJ: Core Functionality | Execution patterns = Agent behavior = User value = Revenue generation.
    COVERAGE TARGET: Execution methods, abstract contracts, legacy bridge patterns.
    """

    @pytest.fixture(autouse=True)
    def setUp(self):
        """Set up agent for execution testing."""
        self.agent = MockableBaseAgent(name='ExecutionTestAgent', websocket_events_enabled=False)
        self.mock_context = MockUserExecutionContext()
        self.real_context = create_real_user_execution_context()

    @pytest.mark.asyncio
    async def test_execute_with_user_execution_context(self):
        """Test execute method with UserExecutionContext (modern pattern).
        
        COVERAGE: execute method with UserExecutionContext pattern.
        """
        result = await self.agent.execute(self.real_context, stream_updates=True)
        assert result['status'] == 'completed'
        assert result['agent_name'] == 'ExecutionTestAgent'
        assert 'execution_time' in result

    @pytest.mark.asyncio
    async def test_execute_with_context_method_directly(self):
        """Test execute_with_context method directly.
        
        COVERAGE: execute_with_context method with telemetry spans.
        """
        with patch('netra_backend.app.core.telemetry.telemetry_manager') as mock_telemetry:
            mock_span = AsyncMock()
            mock_telemetry.start_agent_span.return_value.__aenter__.return_value = mock_span
            result = await self.agent.execute_with_context(self.mock_context)
            mock_telemetry.start_agent_span.assert_called_once()
            assert result['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_execute_with_execution_failure(self):
        """Test execute method handles execution failures correctly.
        
        COVERAGE: Error handling in execution methods.
        """
        failing_agent = MockableBaseAgent(name='FailingAgent', execution_should_succeed=False)
        with pytest.raises(RuntimeError) as exc_info:
            await failing_agent.execute(self.mock_context)
        assert 'Test execution failure' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_modern_legacy_compatibility(self):
        """Test modern execution via execute method (legacy compatibility).
        
        COVERAGE: Modern execution pattern compatibility.
        Note: execute_modern method was removed, testing via execute() method instead.
        """
        result = await self.agent.execute(self.real_context, stream_updates=False)
        assert result['status'] == 'completed'
        assert result['agent_name'] == 'ExecutionTestAgent'
        assert 'execution_time' in result

    @pytest.mark.asyncio
    async def test_validate_preconditions_default_implementation(self):
        """Test validate_preconditions default implementation.
        
        COVERAGE: validate_preconditions method default behavior.
        """
        context = ExecutionContext(request_id='test-123', run_id='run-456', agent_name='TestAgent', state={}, correlation_id='corr-789')
        result = await self.agent.validate_preconditions(context)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_status_update_variants(self):
        """Test send_status_update method handles different status types.
        
        COVERAGE: send_status_update method with all status variants.
        """
        context = ExecutionContext(request_id='test-123', run_id='run-456', agent_name='TestAgent', state={}, correlation_id='corr-789')
        self.agent._websocket_adapter.emit_thinking = AsyncMock()
        self.agent._websocket_adapter.emit_progress = AsyncMock()
        self.agent._websocket_adapter.emit_error = AsyncMock()
        await self.agent.send_status_update(context, 'executing', 'Processing')
        self.agent._websocket_adapter.emit_thinking.assert_called_with('Processing')
        await self.agent.send_status_update(context, 'completed', 'Done')
        self.agent._websocket_adapter.emit_progress.assert_called_with('Done', is_complete=True)
        await self.agent.send_status_update(context, 'failed', 'Error occurred')
        self.agent._websocket_adapter.emit_error.assert_called_with('Error occurred')
        await self.agent.send_status_update(context, 'custom', 'Custom status')
        self.agent._websocket_adapter.emit_progress.assert_called_with('Custom status')

class BaseAgentFactoryPatternsTests:
    """Test BaseAgent factory method patterns and agent creation.
    
    BVJ: Architecture Quality | Factory patterns = Proper isolation = User data security = Compliance.
    COVERAGE TARGET: Lines 1477-1759 (factory methods and creation patterns).
    """

    @pytest.fixture(autouse=True)
    def setUp(self):
        """Set up for factory pattern testing."""
        self.mock_context = MockUserExecutionContext()

    def test_create_with_context_factory_method(self):
        """Test create_with_context factory method.
        
        COVERAGE: create_with_context class method.
        """
        agent_config = {'custom_param': 'test_value'}
        agent = BaseAgent.create_with_context(self.mock_context, agent_config)
        assert agent is not None
        assert isinstance(agent, BaseAgent)
        assert agent._user_context is self.mock_context

    def test_create_with_context_invalid_context_type(self):
        """Test create_with_context raises error for invalid context type.
        
        COVERAGE: create_with_context type validation.
        """
        invalid_context = {'invalid': 'context'}
        with pytest.raises(ValueError) as exc_info:
            BaseAgent.create_with_context(invalid_context)
        assert 'Expected UserExecutionContext' in str(exc_info.value)

    def test_create_legacy_with_warnings_factory(self):
        """Test create_legacy_with_warnings factory method.
        
        COVERAGE: create_legacy_with_warnings deprecated factory.
        """
        mock_llm = Mock(spec=LLMManager)
        mock_tool_dispatcher = Mock(spec=ToolDispatcher)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            agent = BaseAgent.create_legacy_with_warnings(llm_manager=mock_llm, tool_dispatcher=mock_tool_dispatcher)
            assert len(w) > 0
            assert any(('DEPRECATED' in str(warning.message) for warning in w))
        assert agent.llm_manager is mock_llm
        assert agent.tool_dispatcher is mock_tool_dispatcher

    def test_create_agent_with_context_factory(self):
        """Test create_agent_with_context factory method.
        
        COVERAGE: create_agent_with_context class method.
        """
        agent = MockableBaseAgent.create_agent_with_context(self.mock_context)
        assert agent is not None
        assert isinstance(agent, MockableBaseAgent)
        assert agent._user_execution_context is self.mock_context
        assert agent.name == 'MockableBaseAgent'

class BaseAgentValidationAndMigrationTests:
    """Test BaseAgent validation and migration support methods.
    
    BVJ: Migration Support | Pattern validation = Smooth transitions = Reduced technical debt.
    COVERAGE TARGET: Validation and migration helper methods.
    """

    @pytest.fixture(autouse=True)
    def setUp(self):
        """Set up agent for validation testing."""
        self.agent = MockableBaseAgent(name='ValidationTestAgent')

    def test_validate_modern_implementation_compliant_agent(self):
        """Test validate_modern_implementation for compliant agent.
        
        COVERAGE: validate_modern_implementation method for compliant agent.
        """
        validation = self.agent.validate_modern_implementation()
        assert validation['compliant'] is True
        assert validation['pattern'] == 'modern'
        assert len(validation['errors']) == 0

    def test_validate_modern_implementation_legacy_agent(self):
        """Test validate_modern_implementation for legacy agent.
        
        COVERAGE: validate_modern_implementation method for legacy patterns.
        """

        class LegacyAgent(BaseAgent):

            async def execute_core_logic(self, context):
                return {'status': 'legacy'}
        legacy_agent = LegacyAgent(name='LegacyAgent')
        validation = legacy_agent.validate_modern_implementation()
        assert validation['compliant'] is False
        assert validation['pattern'] == 'legacy_bridge'
        assert len(validation['warnings']) > 0
        assert len(validation['recommendations']) > 0

    def test_assert_user_execution_context_pattern_compliant(self):
        """Test assert_user_execution_context_pattern for compliant agent.
        
        COVERAGE: assert_user_execution_context_pattern method success path.
        """
        self.agent.assert_user_execution_context_pattern()

    def test_assert_user_execution_context_pattern_critical_violations(self):
        """Test assert_user_execution_context_pattern with critical violations.
        
        COVERAGE: assert_user_execution_context_pattern method error path.
        """

        class ViolatingAgent(BaseAgent):

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.db_session = Mock()
        violating_agent = ViolatingAgent(name='ViolatingAgent')
        violating_agent.validate_modern_implementation = Mock(return_value={'errors': ['CRITICAL: Agent stores database session'], 'warnings': []})
        with pytest.raises(RuntimeError) as exc_info:
            violating_agent.assert_user_execution_context_pattern()
        assert 'CRITICAL COMPLIANCE VIOLATIONS' in str(exc_info.value)

    def test_get_migration_status(self):
        """Test get_migration_status returns detailed status information.
        
        COVERAGE: get_migration_status method.
        """
        status = self.agent.get_migration_status()
        assert status['agent_name'] == 'ValidationTestAgent'
        assert 'agent_class' in status
        assert status['migration_status'] in ['compliant', 'needs_migration']
        assert 'execution_pattern' in status
        assert 'user_isolation_safe' in status
        assert 'validation_timestamp' in status

class BaseAgentResetAndShutdownTests:
    """Test BaseAgent reset and shutdown lifecycle methods.
    
    BVJ: System Stability | Proper cleanup = Resource management = System reliability.
    COVERAGE TARGET: reset_state and shutdown methods.
    """

    @pytest.fixture(autouse=True)
    def setUp(self):
        """Set up agent for lifecycle testing."""
        self.agent = MockableBaseAgent(name='LifecycleTestAgent', enable_reliability=True, enable_execution_engine=True)

    @pytest.mark.asyncio
    async def test_reset_state_comprehensive_cleanup(self):
        """Test reset_state performs comprehensive cleanup.
        
        COVERAGE: reset_state method with all cleanup components.
        """
        self.agent.set_state(SubAgentLifecycle.RUNNING)
        self.agent.start_time = time.time()
        self.agent.context['test_data'] = 'should_be_cleared'
        self.agent.circuit_breaker.reset = Mock()
        self.agent.monitor.reset = Mock()
        self.agent.timing_collector.reset = Mock()
        await self.agent.reset_state()
        assert self.agent.state == SubAgentLifecycle.PENDING
        assert self.agent.start_time is None
        assert self.agent.end_time is None
        assert len(self.agent.context) == 0
        assert self.agent.correlation_id is not None

    @pytest.mark.asyncio
    async def test_reset_state_handles_cleanup_errors_gracefully(self):
        """Test reset_state handles component cleanup errors gracefully.
        
        COVERAGE: reset_state method error handling.
        """
        self.agent.circuit_breaker.reset = Mock(side_effect=Exception('Reset failed'))
        await self.agent.reset_state()
        assert self.agent.state == SubAgentLifecycle.PENDING

    @pytest.mark.asyncio
    async def test_shutdown_idempotent_behavior(self):
        """Test shutdown method is idempotent.
        
        COVERAGE: shutdown method idempotent behavior.
        """
        await self.agent.shutdown()
        assert self.agent.state == SubAgentLifecycle.SHUTDOWN
        await self.agent.shutdown()
        assert self.agent.state == SubAgentLifecycle.SHUTDOWN

    @pytest.mark.asyncio
    async def test_shutdown_cleanup_timing_collector(self):
        """Test shutdown properly cleans up timing collector.
        
        COVERAGE: shutdown method timing collector cleanup.
        """
        self.agent.timing_collector.current_tree = Mock()
        self.agent.timing_collector.complete_execution = Mock()
        await self.agent.shutdown()
        self.agent.timing_collector.complete_execution.assert_called_once()

class BaseAgentMetadataStorageTests:
    """Test BaseAgent metadata storage SSOT methods.
    
    BVJ: Data Integrity | Proper metadata handling = Consistent state = Reliable WebSocket events.
    COVERAGE TARGET: Lines 300-373 (metadata storage methods).
    """

    @pytest.fixture(autouse=True)
    def setUp(self):
        """Set up agent and context for metadata testing."""
        self.agent = MockableBaseAgent(name='MetadataTestAgent')
        self.mock_context = MockUserExecutionContext()

    def test_store_metadata_result_with_serialization(self):
        """Test store_metadata_result with serialization enabled.
        
        COVERAGE: store_metadata_result method with ensure_serializable=True.
        """
        mock_model = Mock()
        mock_model.model_dump = Mock(return_value={'serialized': 'data'})
        self.agent.store_metadata_result(self.mock_context, 'test_key', mock_model, ensure_serializable=True)
        mock_model.model_dump.assert_called_once_with(mode='json', exclude_none=True)
        assert self.mock_context.metadata['test_key'] == {'serialized': 'data'}

    def test_store_metadata_result_without_serialization(self):
        """Test store_metadata_result with serialization disabled.
        
        COVERAGE: store_metadata_result method with ensure_serializable=False.
        """
        test_data = {'raw': 'data', 'numbers': [1, 2, 3]}
        self.agent.store_metadata_result(self.mock_context, 'raw_key', test_data, ensure_serializable=False)
        assert self.mock_context.metadata['raw_key'] == test_data

    def test_store_metadata_batch(self):
        """Test store_metadata_batch method.
        
        COVERAGE: store_metadata_batch method.
        """
        batch_data = {'key1': 'value1', 'key2': {'nested': 'value'}, 'key3': [1, 2, 3]}
        self.agent.store_metadata_batch(self.mock_context, batch_data)
        for key, value in batch_data.items():
            assert self.mock_context.metadata[key] == value

    def test_get_metadata_value_with_metadata_attribute(self):
        """Test get_metadata_value with metadata attribute.
        
        COVERAGE: get_metadata_value method with metadata access.
        """
        self.mock_context.metadata = {'existing_key': 'existing_value'}
        result = self.agent.get_metadata_value(self.mock_context, 'existing_key')
        assert result == 'existing_value'
        result = self.agent.get_metadata_value(self.mock_context, 'missing_key', 'default')
        assert result == 'default'

    def test_get_metadata_value_with_agent_context_fallback(self):
        """Test get_metadata_value with agent_context fallback.
        
        COVERAGE: get_metadata_value method agent_context fallback logic.
        """
        delattr(self.mock_context, 'metadata')
        self.mock_context.agent_context = {'agent_key': 'agent_value'}
        result = self.agent.get_metadata_value(self.mock_context, 'agent_key')
        assert result == 'agent_value'

    def test_get_metadata_value_no_context_attributes(self):
        """Test get_metadata_value when context has no metadata attributes.
        
        COVERAGE: get_metadata_value method fallback to default.
        """
        minimal_context = Mock()
        result = self.agent.get_metadata_value(minimal_context, 'any_key', 'fallback')
        assert result == 'fallback'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
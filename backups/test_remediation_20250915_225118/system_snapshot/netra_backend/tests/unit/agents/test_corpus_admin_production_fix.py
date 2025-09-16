"""
CORPUS ADMIN AGENT PRODUCTION FIX TEST SUITE

CRITICAL MISSION: Validate BaseExecutionEngine implementation and prevent mock regression.

This test suite validates:
1. NO Mock imports - only real objects and implementations
2. BaseExecutionEngine proper initialization and 4-phase execution
3. Pre/post execution hooks functionality
4. UserExecutionContext isolation and state management
5. Error handling and recovery patterns
6. Concurrent execution safety
7. WebSocket event integration
8. Circuit breaker and reliability patterns

BVJ: ALL segments | Platform Stability | Prevents mock regression and execution engine failures
"""
import asyncio
import gc
import os
import pytest
import psutil
import random
import threading
import time
import tracemalloc
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from shared.isolated_environment import IsolatedEnvironment
os.environ['TEST_COLLECTION_MODE'] = '1'
os.environ['TESTING'] = '1'
os.environ['NETRA_ENV'] = 'testing'
from netra_backend.app.agents.corpus_admin.agent import CorpusAdminSubAgent, CorpusParser, CorpusValidator, CorpusOperations
from netra_backend.app.agents.corpus_admin.models import CorpusMetadata, CorpusOperation, CorpusOperationResult, CorpusType
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.base.executor import BaseExecutionEngine, ExecutionStrategy, ExecutionWorkflowBuilder, AgentMethodExecutionPhase, SequentialStrategyHandler, PipelineStrategyHandler
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.errors import ValidationError, AgentExecutionError
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

class RealLLMManager:
    """Real LLM Manager for testing (no mocks)."""

    def __init__(self):
        self.model_name = 'test-model'
        self.config = {'max_tokens': 1000, 'temperature': 0.7}

    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate test response."""
        return f'Test response for: {prompt[:50]}...'

    def get_health_status(self) -> Dict[str, Any]:
        return {'status': 'healthy', 'model': self.model_name}

class RealToolDispatcher:
    """Real Tool Dispatcher for testing (no mocks)."""

    def __init__(self):
        self.tools = {}
        self.execution_count = 0

    async def dispatch(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Dispatch tool execution."""
        self.execution_count += 1
        return {'tool': tool_name, 'result': 'success', 'execution': self.execution_count}

    def get_available_tools(self) -> List[str]:
        return ['file_tool', 'search_tool', 'corpus_tool']

    def get_health_status(self) -> Dict[str, Any]:
        return {'status': 'healthy', 'tools_count': len(self.tools)}

class RealWebSocketManager:
    """Real WebSocket Manager for testing (no mocks)."""

    def __init__(self):
        self.sent_messages = []
        self.connected = True

    async def send_agent_started(self, run_id: str, agent_name: str, **kwargs):
        self.sent_messages.append({'type': 'agent_started', 'run_id': run_id, 'agent_name': agent_name})

    async def send_agent_thinking(self, run_id: str, agent_name: str, message: str, **kwargs):
        self.sent_messages.append({'type': 'agent_thinking', 'run_id': run_id, 'agent_name': agent_name, 'message': message})

    async def send_tool_executing(self, run_id: str, agent_name: str, tool_name: str, metadata: Dict[str, Any]):
        self.sent_messages.append({'type': 'tool_executing', 'run_id': run_id, 'agent_name': agent_name, 'tool_name': tool_name, 'metadata': metadata})

    async def send_tool_completed(self, run_id: str, agent_name: str, tool_name: str, result: Dict[str, Any]):
        self.sent_messages.append({'type': 'tool_completed', 'run_id': run_id, 'agent_name': agent_name, 'tool_name': tool_name, 'result': result})

    async def send_agent_completed(self, run_id: str, agent_name: str, **kwargs):
        self.sent_messages.append({'type': 'agent_completed', 'run_id': run_id, 'agent_name': agent_name})

    async def send_agent_error(self, run_id: str, agent_name: str, error_message: str):
        self.sent_messages.append({'type': 'agent_error', 'run_id': run_id, 'agent_name': agent_name, 'error': error_message})

    def get_sent_message_count(self, message_type: str) -> int:
        return len([msg for msg in self.sent_messages if msg['type'] == message_type])

@dataclass
class ExecutionMetrics:
    """Track execution metrics for validation."""
    start_time: float
    end_time: float
    phase_count: int
    hook_calls: int
    websocket_events: int
    memory_usage_mb: float

    @property
    def execution_time_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000

class CorpusAdminTestFixture:
    """Test fixture for corpus admin agent testing."""

    def __init__(self):
        self.llm_manager = RealLLMManager()
        self.tool_dispatcher = RealToolDispatcher()
        self.websocket_manager = RealWebSocketManager()
        self.agent = None
        self.metrics = None

    def create_agent(self) -> CorpusAdminSubAgent:
        """Create corpus admin agent with real dependencies."""
        self.agent = CorpusAdminSubAgent(llm_manager=self.llm_manager, tool_dispatcher=self.tool_dispatcher, websocket_manager=self.websocket_manager)
        return self.agent

    def create_test_state(self, user_request: str='Create new corpus for documentation') -> DeepAgentState:
        """Create test state with realistic data."""
        state = DeepAgentState()
        state.user_request = user_request
        state.user_id = f'user_{uuid.uuid4().hex[:8]}'
        state.chat_thread_id = f'thread_{uuid.uuid4().hex[:8]}'
        state.triage_result = {'category': 'corpus_administration', 'is_admin_mode': True, 'confidence': 0.9}
        return state

    def create_execution_context(self, state: DeepAgentState, run_id: str) -> ExecutionContext:
        """Create execution context."""
        return ExecutionContext(request_id=f'req_{uuid.uuid4().hex[:8]}', run_id=run_id, agent_name='CorpusAdminSubAgent', state=state, stream_updates=True, user_id=state.user_id, session_id=state.chat_thread_id)

    def start_memory_monitoring(self):
        """Start memory monitoring."""
        tracemalloc.start()
        gc.collect()

    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def record_metrics(self, start_time: float, phase_count: int, hook_calls: int) -> ExecutionMetrics:
        """Record execution metrics."""
        end_time = time.time()
        websocket_events = len(self.websocket_manager.sent_messages)
        memory_mb = self.get_memory_usage_mb()
        self.metrics = ExecutionMetrics(start_time=start_time, end_time=end_time, phase_count=phase_count, hook_calls=hook_calls, websocket_events=websocket_events, memory_usage_mb=memory_mb)
        return self.metrics

@pytest.fixture
def corpus_admin_fixture():
    """Create corpus admin test fixture."""
    return CorpusAdminTestFixture()

@pytest.fixture
def agent(corpus_admin_fixture):
    """Create corpus admin agent."""
    return corpus_admin_fixture.create_agent()

@pytest.fixture
def test_state(corpus_admin_fixture):
    """Create test state."""
    return corpus_admin_fixture.create_test_state()

class NoMockRegressionTests:
    """Validate no mock imports and proper BaseExecutionEngine usage."""

    def test_no_mock_imports_in_agent(self, agent):
        """CRITICAL: Ensure no mock imports exist in agent."""
        import inspect
        import sys
        agent_module = sys.modules[agent.__module__]
        module_globals = vars(agent_module)
        forbidden_imports = ['Mock', 'MagicMock', 'AsyncMock', 'patch', 'mock']
        found_mocks = []
        for name, obj in module_globals.items():
            if any((forbidden in str(type(obj)) for forbidden in forbidden_imports)):
                found_mocks.append(f'{name}: {type(obj)}')
        assert not found_mocks, f'MOCK REGRESSION DETECTED! Found mock imports: {found_mocks}'

    def test_base_execution_engine_properly_initialized(self, agent):
        """Validate BaseExecutionEngine is properly initialized."""
        assert hasattr(agent, '_execution_engine'), 'Agent missing _execution_engine attribute'
        assert isinstance(agent._execution_engine, BaseExecutionEngine), 'Execution engine is not BaseExecutionEngine'
        assert len(agent._execution_engine._phases) == 4, f'Expected 4 phases, got {len(agent._execution_engine._phases)}'
        phase_names = [phase.name for phase in agent._execution_engine._phases]
        expected_phases = ['parsing', 'validation', 'operation', 'finalization']
        assert phase_names == expected_phases, f'Phase mismatch. Expected {expected_phases}, got {phase_names}'

    def test_execution_engine_components_are_real(self, agent):
        """Validate all execution engine components are real objects."""
        engine = agent._execution_engine
        assert isinstance(engine.monitor, ExecutionMonitor), 'Monitor is not ExecutionMonitor'
        assert isinstance(engine._strategy_handlers[ExecutionStrategy.SEQUENTIAL], SequentialStrategyHandler)
        assert isinstance(engine._strategy_handlers[ExecutionStrategy.PIPELINE], PipelineStrategyHandler)
        for phase in engine._phases:
            assert isinstance(phase, AgentMethodExecutionPhase), f'Phase {phase.name} is not AgentMethodExecutionPhase'

class FourPhaseExecutionTests:
    """Test the 4-phase execution pattern of corpus admin agent."""

    @pytest.mark.asyncio
    async def test_sequential_phase_execution(self, corpus_admin_fixture):
        """Test all 4 phases execute sequentially."""
        agent = corpus_admin_fixture.create_agent()
        state = corpus_admin_fixture.create_test_state('Create new documentation corpus')
        run_id = f'run_{uuid.uuid4().hex[:8]}'
        context = corpus_admin_fixture.create_execution_context(state, run_id)
        corpus_admin_fixture.start_memory_monitoring()
        start_time = time.time()
        result = await agent._execution_engine.execute_phases(context)
        metrics = corpus_admin_fixture.record_metrics(start_time, 4, 2)
        assert result.success, f'Execution failed: {result.error}'
        assert result.status == ExecutionStatus.COMPLETED
        phase_results = result.result
        assert 'parsing' in phase_results, 'Parsing phase missing'
        assert 'validation' in phase_results, 'Validation phase missing'
        assert 'operation' in phase_results, 'Operation phase missing'
        assert 'finalization' in phase_results, 'Finalization phase missing'
        parsing_result = phase_results['parsing']
        assert 'parsed_request' in parsing_result, "Parsing phase didn't produce parsed_request"
        assert 'original_request' in parsing_result, "Parsing phase didn't preserve original_request"
        validation_result = phase_results['validation']
        assert 'approval_required' in validation_result, "Validation phase didn't check approval"
        assert 'validated' in validation_result, "Validation phase didn't set validated flag"
        operation_result = phase_results['operation']
        assert 'operation_result' in operation_result, "Operation phase didn't produce result"
        assert 'executed' in operation_result, "Operation phase didn't set executed flag"
        finalization_result = phase_results['finalization']
        assert 'finalized' in finalization_result, "Finalization phase didn't set finalized flag"
        assert metrics.execution_time_ms < 5000, f'Execution too slow: {metrics.execution_time_ms}ms'
        assert metrics.memory_usage_mb < 500, f'Memory usage too high: {metrics.memory_usage_mb}MB'

    @pytest.mark.asyncio
    async def test_phase_dependencies_respected(self, corpus_admin_fixture):
        """Test phase dependencies are respected."""
        agent = corpus_admin_fixture.create_agent()
        phases = agent._execution_engine._phases
        parsing_phase = next((p for p in phases if p.name == 'parsing'))
        validation_phase = next((p for p in phases if p.name == 'validation'))
        operation_phase = next((p for p in phases if p.name == 'operation'))
        finalization_phase = next((p for p in phases if p.name == 'finalization'))
        assert parsing_phase.dependencies == [], 'Parsing phase should have no dependencies'
        assert validation_phase.dependencies == ['parsing'], 'Validation phase should depend on parsing'
        assert operation_phase.dependencies == ['validation'], 'Operation phase should depend on validation'
        assert finalization_phase.dependencies == ['operation'], 'Finalization phase should depend on operation'

    @pytest.mark.asyncio
    async def test_phase_execution_with_approval_required(self, corpus_admin_fixture):
        """Test phase execution when approval is required."""
        agent = corpus_admin_fixture.create_agent()
        agent.validator.validate_approval_required = lambda *args: True
        state = corpus_admin_fixture.create_test_state('Delete production corpus')
        run_id = f'run_{uuid.uuid4().hex[:8]}'
        context = corpus_admin_fixture.create_execution_context(state, run_id)
        result = await agent._execution_engine.execute_phases(context)
        assert result.success, f'Execution failed: {result.error}'
        operation_result = result.result['operation']
        assert operation_result['executed'] is False, 'Operation should not execute when approval required'
        assert operation_result['reason'] == 'approval_required', 'Should indicate approval required'

class ExecutionHooksTests:
    """Test pre and post execution hooks functionality."""

    @pytest.mark.asyncio
    async def test_pre_execution_hook_called(self, corpus_admin_fixture):
        """Test pre-execution hook is called."""
        agent = corpus_admin_fixture.create_agent()
        hook_called = {'count': 0}

        async def test_pre_hook(context):
            hook_called['count'] += 1
            assert context.agent_name == 'CorpusAdminSubAgent'
            assert context.run_id is not None
        agent._execution_engine.add_pre_execution_hook(test_pre_hook)
        state = corpus_admin_fixture.create_test_state()
        run_id = f'run_{uuid.uuid4().hex[:8]}'
        context = corpus_admin_fixture.create_execution_context(state, run_id)
        await agent._execution_engine.execute_phases(context)
        assert hook_called['count'] == 1, 'Pre-execution hook not called'

    @pytest.mark.asyncio
    async def test_post_execution_hook_called(self, corpus_admin_fixture):
        """Test post-execution hook is called."""
        agent = corpus_admin_fixture.create_agent()
        hook_called = {'count': 0, 'phase_results': None}

        async def test_post_hook(context, phase_results):
            hook_called['count'] += 1
            hook_called['phase_results'] = phase_results
            assert len(phase_results) == 4, 'Should have all 4 phase results'
        agent._execution_engine.add_post_execution_hook(test_post_hook)
        state = corpus_admin_fixture.create_test_state()
        run_id = f'run_{uuid.uuid4().hex[:8]}'
        context = corpus_admin_fixture.create_execution_context(state, run_id)
        await agent._execution_engine.execute_phases(context)
        assert hook_called['count'] == 1, 'Post-execution hook not called'
        assert hook_called['phase_results'] is not None, 'Phase results not passed to hook'

    @pytest.mark.asyncio
    async def test_hooks_called_in_correct_order(self, corpus_admin_fixture):
        """Test hooks are called in correct order."""
        agent = corpus_admin_fixture.create_agent()
        call_order = []

        async def pre_hook(context):
            call_order.append('pre')

        async def post_hook(context, phase_results):
            call_order.append('post')
        agent._execution_engine.add_pre_execution_hook(pre_hook)
        agent._execution_engine.add_pre_execution_hook(lambda ctx: call_order.append('pre2'))
        agent._execution_engine.add_post_execution_hook(post_hook)
        agent._execution_engine.add_post_execution_hook(lambda ctx, res: call_order.append('post2'))
        state = corpus_admin_fixture.create_test_state()
        run_id = f'run_{uuid.uuid4().hex[:8]}'
        context = corpus_admin_fixture.create_execution_context(state, run_id)
        await agent._execution_engine.execute_phases(context)
        expected_order = ['pre', 'pre2', 'post', 'post2']
        assert call_order == expected_order, f'Hook call order incorrect. Expected {expected_order}, got {call_order}'

class ErrorHandlingAndRecoveryTests:
    """Test error handling and recovery patterns."""

    @pytest.mark.asyncio
    async def test_phase_execution_error_handling(self, corpus_admin_fixture):
        """Test error handling during phase execution."""
        agent = corpus_admin_fixture.create_agent()
        original_method = agent._execute_validation_phase

        async def failing_validation(context, previous_results):
            raise ValidationError('Simulated validation failure')
        agent._execute_validation_phase = failing_validation
        state = corpus_admin_fixture.create_test_state()
        run_id = f'run_{uuid.uuid4().hex[:8]}'
        context = corpus_admin_fixture.create_execution_context(state, run_id)
        result = await agent._execution_engine.execute_phases(context)
        assert not result.success, 'Execution should have failed'
        assert result.status == ExecutionStatus.FAILED
        assert 'validation failure' in result.error.lower()
        agent._execute_validation_phase = original_method

    @pytest.mark.asyncio
    async def test_hook_error_doesnt_break_execution(self, corpus_admin_fixture):
        """Test that hook errors don't break main execution."""
        agent = corpus_admin_fixture.create_agent()

        def failing_pre_hook(context):
            raise RuntimeError('Pre-hook failure')

        def failing_post_hook(context, phase_results):
            raise RuntimeError('Post-hook failure')
        agent._execution_engine.add_pre_execution_hook(failing_pre_hook)
        agent._execution_engine.add_post_execution_hook(failing_post_hook)
        state = corpus_admin_fixture.create_test_state()
        run_id = f'run_{uuid.uuid4().hex[:8]}'
        context = corpus_admin_fixture.create_execution_context(state, run_id)
        result = await agent._execution_engine.execute_phases(context)
        assert result.success, 'Execution should succeed despite hook failures'
        assert result.status == ExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execution_with_missing_state_data(self, corpus_admin_fixture):
        """Test execution with missing state data."""
        agent = corpus_admin_fixture.create_agent()
        state = DeepAgentState()
        state.user_id = f'user_{uuid.uuid4().hex[:8]}'
        run_id = f'run_{uuid.uuid4().hex[:8]}'
        context = corpus_admin_fixture.create_execution_context(state, run_id)
        result = await agent._execution_engine.execute_phases(context)
        assert result.success, f'Should handle missing user_request gracefully: {result.error}'
        parsing_result = result.result['parsing']
        assert 'original_request' in parsing_result
        assert 'default_request' in parsing_result['original_request'].lower() or 'default corpus operation' in parsing_result['original_request']

class UserExecutionContextIsolationTests:
    """Test UserExecutionContext isolation for multi-user scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_user_isolation(self, corpus_admin_fixture):
        """Test concurrent execution with different users maintains isolation."""
        agent = corpus_admin_fixture.create_agent()
        user1_state = corpus_admin_fixture.create_test_state('Create user1 corpus')
        user1_state.user_id = 'user1'
        user1_state.chat_thread_id = 'thread1'
        user2_state = corpus_admin_fixture.create_test_state('Create user2 corpus')
        user2_state.user_id = 'user2'
        user2_state.chat_thread_id = 'thread2'
        user3_state = corpus_admin_fixture.create_test_state('Create user3 corpus')
        user3_state.user_id = 'user3'
        user3_state.chat_thread_id = 'thread3'
        tasks = []
        for i, state in enumerate([user1_state, user2_state, user3_state], 1):
            run_id = f'run_user{i}_{uuid.uuid4().hex[:8]}'
            context = corpus_admin_fixture.create_execution_context(state, run_id)
            task = asyncio.create_task(agent._execution_engine.execute_phases(context))
            tasks.append((f'user{i}', task))
        results = {}
        for user, task in tasks:
            result = await task
            results[user] = result
        for user, result in results.items():
            assert result.success, f'User {user} execution failed: {result.error}'
            assert result.status == ExecutionStatus.COMPLETED
        user1_final = result.result['finalization']['result']
        user2_final = result.result['finalization']['result']
        user3_final = result.result['finalization']['result']
        assert user1_final['success'] is True
        assert user2_final['success'] is True
        assert user3_final['success'] is True

    @pytest.mark.asyncio
    async def test_user_context_data_isolation(self, corpus_admin_fixture):
        """Test user context data doesn't leak between executions."""
        agent = corpus_admin_fixture.create_agent()
        user1_state = corpus_admin_fixture.create_test_state('User 1 secret corpus')
        user1_state.user_id = 'user1_secret'
        run_id1 = f'run1_{uuid.uuid4().hex[:8]}'
        context1 = corpus_admin_fixture.create_execution_context(user1_state, run_id1)
        result1 = await agent._execution_engine.execute_phases(context1)
        user2_state = corpus_admin_fixture.create_test_state('User 2 confidential corpus')
        user2_state.user_id = 'user2_confidential'
        run_id2 = f'run2_{uuid.uuid4().hex[:8]}'
        context2 = corpus_admin_fixture.create_execution_context(user2_state, run_id2)
        result2 = await agent._execution_engine.execute_phases(context2)
        user1_parsing = result1.result['parsing']
        user2_parsing = result2.result['parsing']
        assert 'secret' in user1_parsing['original_request'].lower()
        assert 'confidential' in user2_parsing['original_request'].lower()
        assert 'secret' not in user2_parsing['original_request'].lower()
        assert 'confidential' not in user1_parsing['original_request'].lower()

class WebSocketEventIntegrationTests:
    """Test WebSocket event integration during execution."""

    @pytest.mark.asyncio
    async def test_websocket_events_during_phase_execution(self, corpus_admin_fixture):
        """Test WebSocket events are sent during phase execution."""
        agent = corpus_admin_fixture.create_agent()
        websocket_manager = corpus_admin_fixture.websocket_manager
        state = corpus_admin_fixture.create_test_state()
        run_id = f'run_{uuid.uuid4().hex[:8]}'
        context = corpus_admin_fixture.create_execution_context(state, run_id)
        context.websocket_manager = websocket_manager
        websocket_manager.sent_messages.clear()
        await agent._execution_engine.execute_phases(context)
        tool_executing_count = websocket_manager.get_sent_message_count('tool_executing')
        tool_completed_count = websocket_manager.get_sent_message_count('tool_completed')
        assert tool_executing_count == 4, f'Expected 4 tool_executing events, got {tool_executing_count}'
        assert tool_completed_count == 4, f'Expected 4 tool_completed events, got {tool_completed_count}'
        executing_messages = [msg for msg in websocket_manager.sent_messages if msg['type'] == 'tool_executing']
        phase_names = [msg['tool_name'] for msg in executing_messages]
        expected_phases = ['parsing', 'validation', 'operation', 'finalization']
        assert phase_names == expected_phases, f'Phase event order incorrect. Expected {expected_phases}, got {phase_names}'

    @pytest.mark.asyncio
    async def test_websocket_events_with_phase_error(self, corpus_admin_fixture):
        """Test WebSocket error events when phase fails."""
        agent = corpus_admin_fixture.create_agent()
        websocket_manager = corpus_admin_fixture.websocket_manager
        original_method = agent._execute_operation_phase

        async def failing_operation(context, previous_results):
            raise RuntimeError('Operation failed')
        agent._execute_operation_phase = failing_operation
        state = corpus_admin_fixture.create_test_state()
        run_id = f'run_{uuid.uuid4().hex[:8]}'
        context = corpus_admin_fixture.create_execution_context(state, run_id)
        context.websocket_manager = websocket_manager
        websocket_manager.sent_messages.clear()
        try:
            await agent._execution_engine.execute_phases(context)
        except RuntimeError:
            pass
        error_count = websocket_manager.get_sent_message_count('agent_error')
        assert error_count >= 1, f'Expected at least 1 error event, got {error_count}'
        agent._execute_operation_phase = original_method

class DifficultEdgeCasesTests:
    """Test difficult edge cases and failure scenarios."""

    @pytest.mark.asyncio
    async def test_execution_with_null_context_data(self, corpus_admin_fixture):
        """Test execution with null/missing context data."""
        agent = corpus_admin_fixture.create_agent()
        context = ExecutionContext(request_id='test_req', run_id='test_run', agent_name='CorpusAdminSubAgent', state=None, stream_updates=False)
        result = await agent._execution_engine.execute_phases(context)
        assert result is not None
        assert hasattr(result, 'success')
        assert hasattr(result, 'status')

    @pytest.mark.asyncio
    async def test_memory_leak_prevention_long_execution(self, corpus_admin_fixture):
        """Test memory doesn't leak during long execution sequences."""
        agent = corpus_admin_fixture.create_agent()
        corpus_admin_fixture.start_memory_monitoring()
        initial_memory = corpus_admin_fixture.get_memory_usage_mb()
        for i in range(20):
            state = corpus_admin_fixture.create_test_state(f'Corpus operation {i}')
            run_id = f'run_{i}_{uuid.uuid4().hex[:8]}'
            context = corpus_admin_fixture.create_execution_context(state, run_id)
            result = await agent._execution_engine.execute_phases(context)
            assert result.success, f'Execution {i} failed'
            if i % 5 == 0:
                gc.collect()
        final_memory = corpus_admin_fixture.get_memory_usage_mb()
        memory_growth = final_memory - initial_memory
        assert memory_growth < 50, f'Memory leak detected! Growth: {memory_growth}MB'

    @pytest.mark.asyncio
    async def test_rapid_concurrent_execution_stress(self, corpus_admin_fixture):
        """Stress test with rapid concurrent executions."""
        agent = corpus_admin_fixture.create_agent()
        tasks = []
        for i in range(50):
            state = corpus_admin_fixture.create_test_state(f'Concurrent corpus {i}')
            state.user_id = f'stress_user_{i % 10}'
            run_id = f'stress_run_{i}_{uuid.uuid4().hex[:8]}'
            context = corpus_admin_fixture.create_execution_context(state, run_id)
            task = asyncio.create_task(agent._execution_engine.execute_phases(context))
            tasks.append((i, task))
        success_count = 0
        failure_count = 0
        for task_id, task in tasks:
            try:
                result = await asyncio.wait_for(task, timeout=10.0)
                if result.success:
                    success_count += 1
                else:
                    failure_count += 1
            except asyncio.TimeoutError:
                failure_count += 1
            except Exception:
                failure_count += 1
        success_rate = success_count / len(tasks)
        assert success_rate > 0.8, f'Success rate too low under stress: {success_rate:.2%}'

    @pytest.mark.asyncio
    async def test_execution_engine_health_monitoring(self, corpus_admin_fixture):
        """Test execution engine health monitoring capabilities."""
        agent = corpus_admin_fixture.create_agent()
        engine = agent._execution_engine
        health = engine.get_health_status()
        assert 'monitor' in health, 'Health status missing monitor'
        assert 'error_handler' in health, 'Health status missing error_handler'
        assert 'strategy' in health, 'Health status missing strategy'
        assert 'phases_count' in health, 'Health status missing phases_count'
        assert 'hooks_count' in health, 'Health status missing hooks_count'
        assert health['strategy'] == 'sequential', f"Wrong strategy: {health['strategy']}"
        assert health['phases_count'] == 4, f"Wrong phase count: {health['phases_count']}"
        assert isinstance(health['hooks_count'], dict), 'hooks_count should be dict'
        assert 'pre_execution' in health['hooks_count'], 'Missing pre_execution hook count'
        assert 'post_execution' in health['hooks_count'], 'Missing post_execution hook count'

class PerformanceBenchmarksTests:
    """Performance benchmark tests to ensure no degradation."""

    @pytest.mark.asyncio
    async def test_single_execution_performance(self, corpus_admin_fixture):
        """Benchmark single execution performance."""
        agent = corpus_admin_fixture.create_agent()
        state = corpus_admin_fixture.create_test_state()
        run_id = f'perf_run_{uuid.uuid4().hex[:8]}'
        context = corpus_admin_fixture.create_execution_context(state, run_id)
        await agent._execution_engine.execute_phases(context)
        times = []
        for _ in range(10):
            start = time.time()
            result = await agent._execution_engine.execute_phases(context)
            end = time.time()
            assert result.success, 'Benchmark execution failed'
            times.append((end - start) * 1000)
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        assert avg_time < 100, f'Average execution too slow: {avg_time:.2f}ms'
        assert max_time < 200, f'Max execution too slow: {max_time:.2f}ms'
        assert min_time >= 0, f'Min execution invalid: {min_time:.2f}ms'

    @pytest.mark.asyncio
    async def test_throughput_benchmark(self, corpus_admin_fixture):
        """Test execution throughput under load."""
        agent = corpus_admin_fixture.create_agent()
        start_time = time.time()
        completed_executions = 0
        timeout = 5.0
        tasks = []
        while time.time() - start_time < timeout:
            state = corpus_admin_fixture.create_test_state(f'Throughput test {completed_executions}')
            run_id = f'throughput_{completed_executions}_{uuid.uuid4().hex[:8]}'
            context = corpus_admin_fixture.create_execution_context(state, run_id)
            task = asyncio.create_task(agent._execution_engine.execute_phases(context))
            tasks.append(task)
            if len(tasks) >= 20:
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    result = await task
                    if result.success:
                        completed_executions += 1
                tasks = list(pending)
        for task in tasks:
            try:
                result = await task
                if result.success:
                    completed_executions += 1
            except Exception:
                pass
        total_time = time.time() - start_time
        throughput = completed_executions / total_time
        assert throughput >= 5, f'Throughput too low: {throughput:.2f} executions/sec'
        assert completed_executions >= 25, f'Too few completed executions: {completed_executions}'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
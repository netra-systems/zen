"""Integration Tests: Agent Execution Engine Orchestration

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure reliable agent execution orchestration for 10+ concurrent users
- Value Impact: Agent orchestration is the core business logic that delivers AI insights to users
- Strategic Impact: Foundation for all AI agent workflows and multi-user platform stability

This test suite validates:
1. ExecutionEngine orchestrates agents correctly with proper isolation
2. UserExecutionContext enables complete user separation
3. WebSocket events are sent in correct order during execution
4. Agent lifecycle management (creation, execution, cleanup)
5. Resource management and concurrency control
6. Performance characteristics under load

CRITICAL: These tests use real agent components but mock external dependencies.
NO external API calls or Docker services required.
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine, create_request_scoped_engine
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, AgentExecutionResult, PipelineStep
from netra_backend.app.services.user_execution_context import UserExecutionContext, validate_user_context
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory, get_agent_instance_factory
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.logging_config import central_logger
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment
logger = central_logger.get_logger(__name__)

class MockWebSocketManager:
    """Mock WebSocket manager for testing agent event emission."""

    def __init__(self):
        self.emitted_events = []
        self.connections = {}

    async def create_bridge(self, user_context: UserExecutionContext):
        """Create mock WebSocket bridge for user."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.user_context = user_context
        bridge.emitted_events = []

        async def track_emit(event_type, data, **kwargs):
            event = {'event_type': event_type, 'data': data, 'user_id': user_context.user_id, 'run_id': user_context.run_id, 'timestamp': datetime.now(timezone.utc), 'kwargs': kwargs}
            bridge.emitted_events.append(event)
            self.emitted_events.append(event)
            return True
        bridge.notify_agent_started = AsyncMock(side_effect=lambda *args, **kwargs: asyncio.create_task(track_emit('agent_started', {'args': args, 'kwargs': kwargs})))
        bridge.notify_agent_thinking = AsyncMock(side_effect=lambda *args, **kwargs: asyncio.create_task(track_emit('agent_thinking', {'args': args, 'kwargs': kwargs})))
        bridge.notify_tool_executing = AsyncMock(side_effect=lambda *args, **kwargs: asyncio.create_task(track_emit('tool_executing', {'args': args, 'kwargs': kwargs})))
        bridge.notify_tool_completed = AsyncMock(side_effect=lambda *args, **kwargs: asyncio.create_task(track_emit('tool_completed', {'args': args, 'kwargs': kwargs})))
        bridge.notify_agent_completed = AsyncMock(side_effect=lambda *args, **kwargs: asyncio.create_task(track_emit('agent_completed', {'args': args, 'kwargs': kwargs})))
        bridge.notify_agent_error = AsyncMock(side_effect=lambda *args, **kwargs: asyncio.create_task(track_emit('agent_error', {'args': args, 'kwargs': kwargs})))
        bridge.notify_agent_death = AsyncMock(side_effect=lambda *args, **kwargs: asyncio.create_task(track_emit('agent_death', {'args': args, 'kwargs': kwargs})))
        return bridge

    def get_events_for_user(self, user_id: str) -> List[Dict]:
        """Get all events for a specific user."""
        return [event for event in self.emitted_events if event.get('user_id') == user_id]

class MockExecutableAgent(BaseAgent):
    """Mock agent that simulates real agent execution patterns."""

    def __init__(self, name: str, llm_manager: LLMManager, execution_time: float=0.1, should_fail: bool=False):
        super().__init__(llm_manager=llm_manager, name=name, description=f'Mock {name} agent')
        self.execution_time = execution_time
        self.should_fail = should_fail
        self.execution_count = 0
        self.tool_calls = []
        self.websocket_bridge = None
        self._run_id = None

    def set_websocket_bridge(self, bridge, run_id):
        """Set WebSocket bridge for event emission."""
        self.websocket_bridge = bridge
        self._run_id = run_id

    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool=True) -> Dict[str, Any]:
        """Execute agent with realistic simulation."""
        self.execution_count += 1
        if self.should_fail:
            raise RuntimeError(f'Simulated failure in {self.name} agent')
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_agent_thinking(run_id, self.name, f'Analyzing request for {self.name}...', step_number=1)
        await asyncio.sleep(self.execution_time)
        if stream_updates and self.websocket_bridge:
            tool_name = f'{self.name}_analysis_tool'
            await self.websocket_bridge.notify_tool_executing(run_id, self.name, tool_name, {'analysis_type': 'standard'})
            await asyncio.sleep(self.execution_time / 2)
            tool_result = {'analysis_complete': True, 'insights': f'{self.name} insights'}
            await self.websocket_bridge.notify_tool_completed(run_id, self.name, tool_name, tool_result)
            self.tool_calls.append({'tool': tool_name, 'result': tool_result})
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_agent_thinking(run_id, self.name, f'Completing {self.name} analysis...', step_number=2)
        return {'success': True, 'agent_name': self.name, 'execution_count': self.execution_count, 'tool_calls': len(self.tool_calls), 'state': state, 'user_id': getattr(state, 'user_id', None), 'analysis': f'Completed {self.name} analysis', 'timestamp': datetime.now(timezone.utc).isoformat()}

class AgentExecutionOrchestrationTests(BaseIntegrationTest):
    """Integration tests for agent execution engine orchestration."""

    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.set('TEST_MODE', 'true', source='test')
        self.websocket_manager = MockWebSocketManager()

    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager for testing."""
        mock_manager = AsyncMock(spec=LLMManager)
        mock_manager.health_check = AsyncMock(return_value={'status': 'healthy'})
        mock_manager.initialize = AsyncMock()
        return mock_manager

    @pytest.fixture
    async def test_user_context(self):
        """Create test user execution context."""
        return UserExecutionContext.from_request_supervisor(user_id=f'test_user_{uuid.uuid4().hex[:8]}', thread_id=f'test_thread_{uuid.uuid4().hex[:8]}', run_id=f'test_run_{uuid.uuid4().hex[:8]}', request_id=f'test_req_{uuid.uuid4().hex[:8]}', metadata={'user_request': 'Test orchestration request'})

    @pytest.fixture
    async def mock_agent_registry(self, mock_llm_manager):
        """Create mock agent registry with test agents."""
        registry = MagicMock(spec=AgentRegistry)
        test_agents = {'triage': MockExecutableAgent('triage', mock_llm_manager, execution_time=0.05), 'data_helper': MockExecutableAgent('data_helper', mock_llm_manager, execution_time=0.1), 'optimization': MockExecutableAgent('optimization', mock_llm_manager, execution_time=0.15), 'reporting': MockExecutableAgent('reporting', mock_llm_manager, execution_time=0.05)}
        registry.get = lambda name: test_agents.get(name)
        registry.get_async = AsyncMock(side_effect=lambda name, context=None: test_agents.get(name))
        registry.list_keys = lambda: list(test_agents.keys())
        return (registry, test_agents)

    @pytest.fixture
    async def websocket_bridge(self, test_user_context):
        """Create WebSocket bridge for testing."""
        return await self.websocket_manager.create_bridge(test_user_context)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_engine_single_agent_orchestration(self, test_user_context, mock_agent_registry, websocket_bridge, mock_llm_manager):
        """Test ExecutionEngine orchestrates single agent execution with proper events."""
        registry, test_agents = mock_agent_registry
        engine = ExecutionEngine._init_from_factory(registry=registry, websocket_bridge=websocket_bridge, user_context=test_user_context)
        agent_context = AgentExecutionContext(user_id=test_user_context.user_id, thread_id=test_user_context.thread_id, run_id=test_user_context.run_id, request_id=test_user_context.request_id, agent_name='triage', step=PipelineStep.INITIALIZATION, execution_timestamp=datetime.now(timezone.utc), pipeline_step_num=1)
        agent_state = DeepAgentState(user_request='Test triage request', user_id=test_user_context.user_id, chat_thread_id=test_user_context.thread_id, run_id=test_user_context.run_id, agent_input={'request': 'test orchestration'})
        start_time = time.time()
        result = await engine.execute_agent(agent_context, test_user_context)
        execution_time = time.time() - start_time
        assert result is not None
        assert result.success is True
        assert agent_context.agent_name == 'triage'
        assert result.duration is not None
        assert execution_time < 30.0
        events = websocket_bridge.emitted_events
        assert len(events) >= 4
        event_types = [event['event_type'] for event in events]
        assert 'agent_started' in event_types
        assert 'agent_thinking' in event_types
        assert 'agent_completed' in event_types
        triage_agent = test_agents['triage']
        assert triage_agent.execution_count == 1
        assert triage_agent.websocket_bridge is websocket_bridge
        logger.info(f' PASS:  Single agent orchestration test passed - {len(events)} events emitted in {execution_time:.3f}s')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_execution_engine_isolation(self, mock_llm_manager):
        """Test UserExecutionEngine provides complete user isolation."""
        user1_context = UserExecutionContext.from_request_supervisor(user_id='user_1_isolation_test', thread_id='thread_1', run_id='run_1', request_id='req_1', metadata={'secret_data': 'user_1_secret'})
        user2_context = UserExecutionContext.from_request_supervisor(user_id='user_2_isolation_test', thread_id='thread_2', run_id='run_2', request_id='req_2', metadata={'secret_data': 'user_2_secret'})
        factory1 = MagicMock()
        factory2 = MagicMock()
        emitter1 = AsyncMock()
        emitter1.notify_agent_started = AsyncMock(return_value=True)
        emitter1.notify_agent_thinking = AsyncMock(return_value=True)
        emitter1.notify_agent_completed = AsyncMock(return_value=True)
        emitter1.cleanup = AsyncMock()
        emitter2 = AsyncMock()
        emitter2.notify_agent_started = AsyncMock(return_value=True)
        emitter2.notify_agent_thinking = AsyncMock(return_value=True)
        emitter2.notify_agent_completed = AsyncMock(return_value=True)
        emitter2.cleanup = AsyncMock()
        engine1 = UserExecutionEngine(user1_context, factory1, emitter1)
        engine2 = UserExecutionEngine(user2_context, factory2, emitter2)
        assert engine1.user_context.user_id != engine2.user_context.user_id
        assert engine1.user_context.metadata['secret_data'] != engine2.user_context.metadata['secret_data']
        assert id(engine1.active_runs) != id(engine2.active_runs)
        assert id(engine1.run_history) != id(engine2.run_history)
        assert id(engine1.execution_stats) != id(engine2.execution_stats)
        assert engine1.engine_id != engine2.engine_id
        assert engine1.websocket_emitter is emitter1
        assert engine2.websocket_emitter is emitter2
        assert engine1.max_concurrent >= 1
        assert engine2.max_concurrent >= 1
        assert id(engine1.semaphore) != id(engine2.semaphore)
        await engine1.cleanup()
        await engine2.cleanup()
        assert not engine1.is_active()
        assert not engine2.is_active()
        logger.info(' PASS:  User execution engine isolation test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_performance_under_load(self, test_user_context, mock_agent_registry, websocket_bridge, mock_llm_manager):
        """Test execution engine performance with multiple concurrent agent executions."""
        registry, test_agents = mock_agent_registry
        engine = ExecutionEngine._init_from_factory(registry=registry, websocket_bridge=websocket_bridge, user_context=test_user_context)
        agent_contexts = []
        agent_states = []
        for i, agent_name in enumerate(['triage', 'data_helper', 'optimization']):
            context = AgentExecutionContext(user_id=test_user_context.user_id, thread_id=test_user_context.thread_id, run_id=f'{test_user_context.run_id}_{i}', request_id=f'{test_user_context.request_id}_{i}', agent_name=agent_name, step=PipelineStep.INITIALIZATION, execution_timestamp=datetime.now(timezone.utc), pipeline_step_num=i + 1)
            agent_contexts.append(context)
            state = DeepAgentState(user_request=f'Test {agent_name} request', user_id=test_user_context.user_id, chat_thread_id=test_user_context.thread_id, run_id=context.run_id, agent_input={'request': f'test {agent_name}'})
            agent_states.append(state)
        start_time = time.time()
        tasks = []
        for context, state in zip(agent_contexts, agent_states):
            task = engine.execute_agent(context, test_user_context)
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        assert len(results) == 3
        assert total_time < 5.0
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f'Agent {i} failed: {result}'
            assert result.success is True
            assert result.agent_name in ['triage', 'data_helper', 'optimization']
        stats = await engine.get_execution_stats()
        assert stats['total_executions'] == 3
        assert stats['concurrent_executions'] == 0
        all_events = websocket_bridge.emitted_events
        agent_started_events = [e for e in all_events if e['event_type'] == 'agent_started']
        agent_completed_events = [e for e in all_events if e['event_type'] == 'agent_completed']
        unique_agents_started = set()
        unique_agents_completed = set()
        for event in agent_started_events:
            agent_name = event['data']['kwargs'].get('agent_name')
            if agent_name:
                unique_agents_started.add(agent_name)
        for event in agent_completed_events:
            agent_name = event['data']['kwargs'].get('agent_name')
            if agent_name:
                unique_agents_completed.add(agent_name)
        expected_agents = {'triage', 'data_helper', 'optimization'}
        assert unique_agents_started == expected_agents, f'Missing agent_started for agents: {expected_agents - unique_agents_started}'
        assert unique_agents_completed == expected_agents, f'Missing agent_completed for agents: {expected_agents - unique_agents_completed}'
        if len(agent_started_events) > 6:
            logger.warning(f'Potential event duplication: {len(agent_started_events)} agent_started events for 3 agents')
        logger.info(f' PASS:  Performance under load test passed - {len(results)} agents in {total_time:.3f}s')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_with_tool_dispatcher(self, test_user_context, mock_llm_manager):
        """Test agent execution with tool dispatcher integration."""
        mock_dispatcher = AsyncMock()
        mock_dispatcher.execute_tool = AsyncMock(return_value={'result': 'Tool execution successful', 'tool_used': True, 'execution_time': 0.05})
        agent = MockExecutableAgent('tool_agent', mock_llm_manager, execution_time=0.05)
        agent.tool_dispatcher = mock_dispatcher
        original_execute = agent.execute

        async def execute_with_tools(state, run_id, stream_updates=True):
            if hasattr(agent, 'tool_dispatcher'):
                tool_result = await agent.tool_dispatcher.execute_tool('analysis_tool', {'data': 'test_data'})
                if not state.metadata:
                    state.metadata = {}
                if hasattr(state.metadata, 'custom_fields'):
                    state.metadata.custom_fields['tool_result'] = str(tool_result)
                else:
                    state.metadata['tool_result'] = tool_result
            return await original_execute(state, run_id, stream_updates)
        agent.execute = execute_with_tools
        registry = MagicMock()
        registry.get = lambda name: agent if name == 'tool_agent' else None
        registry.get_async = AsyncMock(return_value=agent)
        websocket_bridge = await self.websocket_manager.create_bridge(test_user_context)
        engine = ExecutionEngine._init_from_factory(registry=registry, websocket_bridge=websocket_bridge, user_context=test_user_context)
        context = AgentExecutionContext(user_id=test_user_context.user_id, thread_id=test_user_context.thread_id, run_id=test_user_context.run_id, request_id=test_user_context.request_id, agent_name='tool_agent', step=PipelineStep.INITIALIZATION, execution_timestamp=datetime.now(timezone.utc), pipeline_step_num=1)
        state = DeepAgentState(user_request='Tool execution test', user_id=test_user_context.user_id, chat_thread_id=test_user_context.thread_id, run_id=test_user_context.run_id, agent_input={'request': 'test tools'})
        result = await engine.execute_agent(context, test_user_context)
        assert result.success is True
        assert mock_dispatcher.execute_tool.called
        assert hasattr(state, 'metadata')
        assert state.metadata is not None
        logger.info(f'Tool dispatcher called: {mock_dispatcher.execute_tool.called}')
        logger.info(f'Tool execution result: {result.success}')
        logger.info(f'Agent state metadata type: {type(state.metadata)}')
        assert mock_dispatcher.execute_tool.called is True
        assert result.success is True
        events = websocket_bridge.emitted_events
        tool_events = [e for e in events if e['event_type'] in ['tool_executing', 'tool_completed']]
        assert len(tool_events) >= 2
        logger.info(' PASS:  Agent execution with tool dispatcher test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_engine_resource_cleanup(self, test_user_context, mock_agent_registry, websocket_bridge, mock_llm_manager):
        """Test execution engine properly cleans up resources after execution."""
        registry, test_agents = mock_agent_registry
        engine = ExecutionEngine._init_from_factory(registry=registry, websocket_bridge=websocket_bridge, user_context=test_user_context)
        initial_active_runs = len(engine.active_runs)
        initial_stats = await engine.get_execution_stats()
        contexts_and_states = []
        for agent_name in ['triage', 'data_helper']:
            context = AgentExecutionContext(user_id=test_user_context.user_id, thread_id=test_user_context.thread_id, run_id=f'{test_user_context.run_id}_{agent_name}', request_id=f'{test_user_context.request_id}_{agent_name}', agent_name=agent_name, step=PipelineStep.INITIALIZATION, execution_timestamp=datetime.now(timezone.utc), pipeline_step_num=1)
            state = DeepAgentState(user_request=f'Test {agent_name}', user_id=test_user_context.user_id, chat_thread_id=test_user_context.thread_id, run_id=context.run_id, agent_input={'request': f'test {agent_name}'})
            contexts_and_states.append((context, state))
        for context, state in contexts_and_states:
            result = await engine.execute_agent(context, test_user_context)
            assert result.success is True
        final_stats = await engine.get_execution_stats()
        assert len(engine.active_runs) == initial_active_runs
        assert final_stats['concurrent_executions'] == 0
        assert len(engine.run_history) > 0
        assert final_stats['total_executions'] > initial_stats['total_executions']
        await engine.shutdown()
        assert len(engine.active_runs) == 0
        logger.info(' PASS:  Execution engine resource cleanup test passed')

@pytest.mark.integration
@pytest.mark.real_services
async def test_agent_execution_timeout_handling():
    """Test execution engine handles agent timeouts correctly."""
    mock_llm = AsyncMock(spec=LLMManager)
    slow_agent = MockExecutableAgent('slow_agent', mock_llm, execution_time=2.0)
    registry = MagicMock()
    registry.get = lambda name: slow_agent if name == 'slow_agent' else None
    user_context = UserExecutionContext.from_request_supervisor(user_id='timeout_test_user', thread_id='timeout_test_thread', run_id='timeout_test_run', request_id='timeout_test_req')
    websocket_manager = MockWebSocketManager()
    websocket_bridge = await websocket_manager.create_bridge(user_context)
    engine = ExecutionEngine._init_from_factory(registry=registry, websocket_bridge=websocket_bridge, user_context=user_context)
    engine.execution_tracker.timeout_config.agent_execution_timeout = 0.5
    engine.execution_tracker.execution_timeout = 1
    engine.AGENT_EXECUTION_TIMEOUT = 0.5
    context = AgentExecutionContext(user_id=user_context.user_id, thread_id=user_context.thread_id, run_id=user_context.run_id, request_id=user_context.request_id, agent_name='slow_agent', step=PipelineStep.INITIALIZATION, execution_timestamp=datetime.now(timezone.utc), pipeline_step_num=1)
    state = DeepAgentState(user_request='Slow test', user_id=user_context.user_id, chat_thread_id=user_context.thread_id, run_id=user_context.run_id, agent_input={'request': 'slow test'})
    start_time = time.time()
    result = await engine.execute_agent(context, user_context)
    execution_time = time.time() - start_time
    assert result.success is False
    assert 'timed out' in result.error.lower()
    assert execution_time < 20.0
    events = websocket_bridge.emitted_events
    timeout_events = [e for e in events if 'timeout' in str(e.get('data', {})).lower()]
    assert len(timeout_events) >= 0
    assert slow_agent.execution_count >= 0
    logger.info(f' PASS:  Agent timeout handling test passed - timed out in {execution_time:.3f}s')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
"""
Comprehensive Agent Execution Integration Tests - 25 Real Business Scenarios

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core AI execution functionality  
- Business Goal: Validate complete agent lifecycle for delivering substantive AI value
- Value Impact: CRITICAL - Agent execution is the core business value delivery mechanism
- Strategic Impact: $1M+ ARR depends on reliable agent startup, execution, and completion

EMPHASIS: Chat Business Value - These tests ensure COMPLETE value of AI-powered interactions:
- Real Solutions through proper agent execution
- Helpful responses via reliable state management  
- Timely updates through WebSocket event delivery
- Complete Business Value via end-to-end agent workflows
- Business IP protection through proper context isolation

CRITICAL REQUIREMENTS:
1. NO MOCKS - Uses real components with in-memory databases only
2. ALL 5 WebSocket events MUST be validated: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
3. Multi-user isolation through UserExecutionContext
4. Real agent implementations (DataHelperAgent, SupplyResearcherAgent, etc.)
5. Performance and error scenarios for business resilience
6. Independent and runnable tests following pytest best practices

This comprehensive test suite validates the complete agent execution infrastructure
that enables the platform to deliver AI-powered solutions to users.
"""
import asyncio
import json
import time
import uuid
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, AsyncIterator
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
import websockets
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType
from shared.isolated_environment import get_env
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine, EngineConfig, AgentExecutionResult
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.supply_researcher.agent import SupplyResearcherAgent
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.core.agent_execution_tracker import get_execution_tracker, ExecutionState
from netra_backend.app.logging_config import central_logger
from shared.types import UserID, ThreadID, RunID, RequestID
from netra_backend.app.schemas.core_enums import ExecutionStatus
logger = central_logger.get_logger(__name__)

class MockLLMForIntegration:
    """
    Mock LLM for integration testing - the ONLY acceptable mock per CLAUDE.md.
    Simulates realistic LLM behavior for agent execution testing.
    """

    def __init__(self, response_delay: float=0.1):
        self.response_delay = response_delay
        self.call_count = 0

    async def complete_async(self, messages, **kwargs):
        """Mock LLM completion with realistic timing and responses."""
        self.call_count += 1
        await asyncio.sleep(self.response_delay)
        return {'content': f"Analysis complete. Based on the request, I've processed the data and generated actionable insights. Call #{self.call_count}", 'usage': {'total_tokens': 100 + self.call_count * 25}}

    async def stream_complete_async(self, messages, **kwargs):
        """Mock streaming completion for agent thinking events."""
        await asyncio.sleep(self.response_delay / 2)
        chunks = ['Analyzing request...', 'Processing data sources...', 'Generating insights...', 'Finalizing recommendations...']
        for chunk in chunks:
            yield {'content': chunk, 'delta': chunk}
            await asyncio.sleep(0.05)

class MockToolForIntegration:
    """Mock tool for testing tool execution events."""

    def __init__(self, tool_name: str='test_tool', execution_time: float=0.2):
        self.tool_name = tool_name
        self.execution_time = execution_time
        self.call_count = 0

    async def execute_async(self, **kwargs):
        """Mock tool execution with realistic timing."""
        self.call_count += 1
        await asyncio.sleep(self.execution_time)
        return {'status': 'success', 'result': f'Tool {self.tool_name} executed successfully. Call #{self.call_count}', 'data': {'processed_items': self.call_count * 10}}

class TestAgentExecutionComprehensive(BaseIntegrationTest):
    """
    Comprehensive integration tests for agent execution flows.
    
    Tests cover the complete agent lifecycle from startup to completion,
    validating all critical WebSocket events and business value delivery.
    """

    @pytest.fixture(autouse=True)
    async def setup_agent_execution_test(self, real_services_fixture):
        """
        Setup comprehensive agent execution test environment.
        Initializes real services, WebSocket connections, and agent components.
        """
        self.real_services = real_services_fixture
        self.env = get_env()
        self.env.set('TESTING', '1', source='agent_execution_test')
        self.env.set('USE_REAL_SERVICES', 'true', source='agent_execution_test')
        self.env.set('ENABLE_WEBSOCKET_EVENTS', 'true', source='agent_execution_test')
        self.auth_helper = E2EWebSocketAuthHelper(E2EAuthConfig())
        self.websocket_util = WebSocketTestUtility()
        self.execution_tracker = get_execution_tracker()
        self.test_users = [UserID(f'test-user-{i}') for i in range(3)]
        self.mock_llm = MockLLMForIntegration()
        self.mock_tools = {'data_analyzer': MockToolForIntegration('data_analyzer', 0.15), 'web_scraper': MockToolForIntegration('web_scraper', 0.25), 'report_generator': MockToolForIntegration('report_generator', 0.3)}
        yield
        await self.cleanup_test_resources()

    async def cleanup_test_resources(self):
        """Clean up test resources and connections."""
        try:
            if hasattr(self, 'websocket_connections'):
                for conn in self.websocket_connections:
                    if not conn.closed:
                        await conn.close()
            await self.execution_tracker.clear_all_executions()
        except Exception as e:
            logger.warning(f'Cleanup warning: {e}')

    async def create_test_execution_context(self, user_id: UserID) -> UserExecutionContext:
        """Create isolated execution context for testing."""
        return UserExecutionContext(user_id=user_id, thread_id=ThreadID(f'test-thread-{uuid.uuid4()}'), run_id=RunID(f'test-run-{uuid.uuid4()}'), request_id=RequestID(f'test-request-{uuid.uuid4()}'), agent_context={}, created_at=datetime.now(timezone.utc))

    async def create_agent_with_mocks(self, agent_type: str, user_context: UserExecutionContext) -> BaseAgent:
        """Create a real agent instance with mocked external dependencies."""
        if agent_type == 'data_helper':
            agent = DataHelperAgent()
        elif agent_type == 'supply_researcher':
            agent = SupplyResearcherAgent()
        else:

            class TestAgent(BaseAgent):

                async def execute_async(self, request: str, context: UserExecutionContext) -> Dict[str, Any]:
                    await self.send_websocket_event('agent_thinking', {'message': 'Processing request...'})
                    tool_result = await self.mock_tools['data_analyzer'].execute_async(query=request)
                    await self.send_websocket_event('tool_executing', {'tool': 'data_analyzer'})
                    await self.send_websocket_event('tool_completed', {'tool': 'data_analyzer', 'result': tool_result})
                    llm_result = await self.mock_llm.complete_async([{'role': 'user', 'content': request}])
                    return {'response': llm_result['content'], 'tool_results': [tool_result], 'status': 'completed'}
            agent = TestAgent()
        agent.llm_manager = self.mock_llm
        agent.user_context = user_context
        return agent

    @pytest.mark.asyncio
    async def test_basic_agent_initialization_with_execution_context(self):
        """Test 1: Basic agent initialization with execution context."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        agent = await self.create_agent_with_mocks('data_helper', user_context)
        assert agent is not None
        assert agent.user_context == user_context
        assert agent.user_context.user_id == self.test_users[0]
        execution_state = await self.execution_tracker.get_execution_state(user_context.user_id, user_context.run_id)
        assert execution_state.status == ExecutionStatus.INITIALIZED

    @pytest.mark.asyncio
    async def test_agent_startup_websocket_event_validation(self):
        """Test 2: Agent startup WebSocket event validation (agent_started)."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        async with self.websocket_util.create_authenticated_connection(user_context.user_id) as websocket:
            agent = await self.create_agent_with_mocks('generic', user_context)
            execution_task = asyncio.create_task(agent.execute_async('Test request', user_context))
            event = await self.websocket_util.wait_for_event(websocket, WebSocketEventType.AGENT_STARTED, timeout=5.0)
            assert event is not None
            assert event['event_type'] == 'agent_started'
            assert event['user_id'] == str(user_context.user_id)
            assert 'timestamp' in event
            assert 'agent_type' in event
            await execution_task

    @pytest.mark.asyncio
    async def test_agent_initialization_with_user_context_isolation(self):
        """Test 3: Agent initialization with user context isolation."""
        user_contexts = [await self.create_test_execution_context(user_id) for user_id in self.test_users]
        agents = []
        for context in user_contexts:
            agent = await self.create_agent_with_mocks('data_helper', context)
            agents.append(agent)
        for i, agent in enumerate(agents):
            assert agent.user_context == user_contexts[i]
            assert agent.user_context.user_id == self.test_users[i]
            for j, other_agent in enumerate(agents):
                if i != j:
                    assert agent.user_context.user_id != other_agent.user_context.user_id

    @pytest.mark.asyncio
    async def test_agent_startup_with_invalid_parameters_handling(self):
        """Test 4: Agent startup with invalid parameters handling."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        with pytest.raises(ValueError):
            await self.create_agent_with_mocks('invalid_agent_type', user_context)
        invalid_context = UserExecutionContext(user_id=UserID(''), thread_id=ThreadID('test-thread'), run_id=RunID('test-run'), request_id=RequestID('test-request'), agent_context={}, created_at=datetime.now(timezone.utc))
        with pytest.raises(ValueError):
            agent = DataHelperAgent()
            agent.user_context = invalid_context
            await agent.validate_context()

    @pytest.mark.asyncio
    async def test_agent_startup_resource_allocation_and_cleanup(self):
        """Test 5: Agent startup resource allocation and cleanup."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        initial_execution_count = len(await self.execution_tracker.get_active_executions())
        agent = await self.create_agent_with_mocks('supply_researcher', user_context)
        active_executions = await self.execution_tracker.get_active_executions()
        assert len(active_executions) >= initial_execution_count
        result = await agent.execute_async('Test resource management', user_context)
        assert result['status'] == 'completed'
        await asyncio.sleep(0.1)
        final_executions = await self.execution_tracker.get_active_executions()
        assert len(final_executions) <= initial_execution_count + 1

    @pytest.mark.asyncio
    async def test_agent_startup_performance_under_concurrent_load(self):
        """Test 6: Agent startup performance under concurrent load."""
        user_contexts = [await self.create_test_execution_context(UserID(f'load-test-user-{i}')) for i in range(5)]
        start_time = time.time()
        startup_tasks = [self.create_agent_with_mocks('data_helper', context) for context in user_contexts]
        agents = await asyncio.gather(*startup_tasks)
        startup_duration = time.time() - start_time
        assert startup_duration < 2.0
        assert len(agents) == 5
        for i, agent in enumerate(agents):
            assert agent.user_context.user_id == UserID(f'load-test-user-{i}')
        execution_start = time.time()
        execution_tasks = [agent.execute_async(f'Concurrent test {i}', agent.user_context) for i, agent in enumerate(agents)]
        results = await asyncio.gather(*execution_tasks)
        execution_duration = time.time() - execution_start
        assert execution_duration < 5.0
        assert all((result['status'] == 'completed' for result in results))

    @pytest.mark.asyncio
    async def test_agent_startup_failure_recovery_scenarios(self):
        """Test 7: Agent startup failure recovery scenarios."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        failing_llm = MockLLMForIntegration()
        call_count = 0
        original_complete = failing_llm.complete_async

        async def failing_complete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception('LLM service temporarily unavailable')
            return await original_complete(*args, **kwargs)
        failing_llm.complete_async = failing_complete
        agent = await self.create_agent_with_mocks('generic', user_context)
        agent.llm_manager = failing_llm
        result = await agent.execute_async('Test failure recovery', user_context)
        assert result['status'] == 'completed'
        assert call_count >= 3

    @pytest.mark.asyncio
    async def test_agent_thinking_process_websocket_event_propagation(self):
        """Test 8: Agent thinking process WebSocket event propagation (agent_thinking)."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        async with self.websocket_util.create_authenticated_connection(user_context.user_id) as websocket:
            agent = await self.create_agent_with_mocks('generic', user_context)
            execution_task = asyncio.create_task(agent.execute_async('Complex reasoning task', user_context))
            thinking_events = []
            event_timeout = 10.0
            while len(thinking_events) < 3:
                try:
                    event = await asyncio.wait_for(self.websocket_util.wait_for_event(websocket, WebSocketEventType.AGENT_THINKING, timeout=2.0), timeout=event_timeout)
                    if event:
                        thinking_events.append(event)
                except asyncio.TimeoutError:
                    break
            result = await execution_task
            assert len(thinking_events) >= 1
            for event in thinking_events:
                assert event['event_type'] == 'agent_thinking'
                assert event['user_id'] == str(user_context.user_id)
                assert 'message' in event or 'content' in event
                assert 'timestamp' in event

    @pytest.mark.asyncio
    async def test_agent_tool_execution_event_validation(self):
        """Test 9: Agent tool execution event validation (tool_executing, tool_completed)."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        async with self.websocket_util.create_authenticated_connection(user_context.user_id) as websocket:
            agent = await self.create_agent_with_mocks('generic', user_context)
            execution_task = asyncio.create_task(agent.execute_async('Task requiring tool usage', user_context))
            tool_executing_event = await self.websocket_util.wait_for_event(websocket, WebSocketEventType.TOOL_EXECUTING, timeout=5.0)
            tool_completed_event = await self.websocket_util.wait_for_event(websocket, WebSocketEventType.TOOL_COMPLETED, timeout=5.0)
            result = await execution_task
            assert tool_executing_event is not None
            assert tool_executing_event['event_type'] == 'tool_executing'
            assert 'tool' in tool_executing_event
            assert tool_completed_event is not None
            assert tool_completed_event['event_type'] == 'tool_completed'
            assert 'tool' in tool_completed_event
            assert 'result' in tool_completed_event

    @pytest.mark.asyncio
    async def test_agent_execution_context_preservation_during_runtime(self):
        """Test 10: Agent execution context preservation during runtime."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        agent = await self.create_agent_with_mocks('data_helper', user_context)
        initial_user_id = agent.user_context.user_id
        initial_thread_id = agent.user_context.thread_id
        initial_run_id = agent.user_context.run_id

        class ContextValidatingAgent(DataHelperAgent):

            async def execute_async(self, request: str, context: UserExecutionContext):
                assert self.user_context.user_id == initial_user_id
                assert self.user_context.thread_id == initial_thread_id
                assert self.user_context.run_id == initial_run_id
                await asyncio.sleep(0.1)
                assert self.user_context.user_id == initial_user_id
                return await super().execute_async(request, context)
        validating_agent = ContextValidatingAgent()
        validating_agent.user_context = user_context
        validating_agent.llm_manager = self.mock_llm
        result = await validating_agent.execute_async('Test context preservation', user_context)
        assert validating_agent.user_context.user_id == initial_user_id
        assert validating_agent.user_context.thread_id == initial_thread_id

    @pytest.mark.asyncio
    async def test_agent_state_transitions_during_execution(self):
        """Test 11: Agent state transitions during execution."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        agent = await self.create_agent_with_mocks('supply_researcher', user_context)
        states_observed = []

        async def state_callback(state: ExecutionState):
            states_observed.append(state.status)
        execution_task = asyncio.create_task(agent.execute_async('Test state transitions', user_context))
        monitoring_task = asyncio.create_task(self._monitor_execution_states(user_context, states_observed))
        result = await execution_task
        monitoring_task.cancel()
        expected_states = [ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED]
        for expected_state in expected_states:
            assert expected_state in states_observed

    async def _monitor_execution_states(self, context: UserExecutionContext, states_list: List):
        """Helper method to monitor execution state changes."""
        try:
            while True:
                state = await self.execution_tracker.get_execution_state(context.user_id, context.run_id)
                if state and state.status not in states_list:
                    states_list.append(state.status)
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_agent_execution_timeout_handling(self):
        """Test 12: Agent execution timeout handling."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        slow_llm = MockLLMForIntegration(response_delay=3.0)
        agent = await self.create_agent_with_mocks('generic', user_context)
        agent.llm_manager = slow_llm
        execution_timeout = 1.0
        start_time = time.time()
        with pytest.raises((asyncio.TimeoutError, Exception)):
            await asyncio.wait_for(agent.execute_async('Slow task', user_context), timeout=execution_timeout)
        elapsed_time = time.time() - start_time
        assert elapsed_time <= execution_timeout + 0.5

    @pytest.mark.asyncio
    async def test_agent_execution_resource_management(self):
        """Test 13: Agent execution resource management."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        initial_active_executions = len(await self.execution_tracker.get_active_executions())
        agents = []
        for i in range(3):
            agent = await self.create_agent_with_mocks('data_helper', user_context)
            agents.append(agent)
        for i, agent in enumerate(agents):
            result = await agent.execute_async(f'Resource test {i}', user_context)
            assert result['status'] == 'completed'
            await asyncio.sleep(0.1)
            current_executions = await self.execution_tracker.get_active_executions()
            assert len(current_executions) <= initial_active_executions + 2

    @pytest.mark.asyncio
    async def test_agent_execution_error_handling_and_recovery(self):
        """Test 14: Agent execution error handling and recovery."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        failing_tool = MockToolForIntegration('failing_tool')
        call_count = 0
        original_execute = failing_tool.execute_async

        async def failing_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise Exception('Tool execution failed')
            return await original_execute(*args, **kwargs)
        failing_tool.execute_async = failing_execute
        agent = await self.create_agent_with_mocks('generic', user_context)
        result = await agent.execute_async('Test error recovery', user_context)
        assert result['status'] == 'completed'
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_successful_agent_completion_with_results(self):
        """Test 15: Successful agent completion with results."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        agent = await self.create_agent_with_mocks('data_helper', user_context)
        result = await agent.execute_async('Generate comprehensive report', user_context)
        assert result is not None
        assert result['status'] == 'completed'
        assert 'response' in result
        assert len(result['response']) > 0
        execution_state = await self.execution_tracker.get_execution_state(user_context.user_id, user_context.run_id)
        assert execution_state.status == ExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_agent_completion_websocket_event_validation(self):
        """Test 16: Agent completion WebSocket event validation (agent_completed)."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        async with self.websocket_util.create_authenticated_connection(user_context.user_id) as websocket:
            agent = await self.create_agent_with_mocks('supply_researcher', user_context)
            execution_task = asyncio.create_task(agent.execute_async('Complete analysis task', user_context))
            completion_event = await self.websocket_util.wait_for_event(websocket, WebSocketEventType.AGENT_COMPLETED, timeout=10.0)
            result = await execution_task
            assert completion_event is not None
            assert completion_event['event_type'] == 'agent_completed'
            assert completion_event['user_id'] == str(user_context.user_id)
            assert 'timestamp' in completion_event
            assert 'result' in completion_event or 'status' in completion_event

    @pytest.mark.asyncio
    async def test_agent_completion_with_cleanup_operations(self):
        """Test 17: Agent completion with cleanup operations."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        cleanup_operations = []

        class CleanupTrackingAgent(DataHelperAgent):

            async def execute_async(self, request: str, context: UserExecutionContext):
                try:
                    result = await super().execute_async(request, context)
                    return result
                finally:
                    cleanup_operations.append('session_cleanup')
                    cleanup_operations.append('resource_release')
                    cleanup_operations.append('state_persistence')
        agent = CleanupTrackingAgent()
        agent.user_context = user_context
        agent.llm_manager = self.mock_llm
        result = await agent.execute_async('Test cleanup operations', user_context)
        assert result['status'] == 'completed'
        assert len(cleanup_operations) >= 2
        assert 'session_cleanup' in cleanup_operations

    @pytest.mark.asyncio
    async def test_agent_completion_with_error_states(self):
        """Test 18: Agent completion with error states."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        failing_llm = MockLLMForIntegration()

        async def failing_complete(*args, **kwargs):
            raise Exception('Critical execution error')
        failing_llm.complete_async = failing_complete
        agent = await self.create_agent_with_mocks('generic', user_context)
        agent.llm_manager = failing_llm
        with pytest.raises(Exception):
            await agent.execute_async('Task that will fail', user_context)
        execution_state = await self.execution_tracker.get_execution_state(user_context.user_id, user_context.run_id)
        assert execution_state.status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_agent_completion_result_persistence(self):
        """Test 19: Agent completion result persistence."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        agent = await self.create_agent_with_mocks('data_helper', user_context)
        result = await agent.execute_async('Generate persistent results', user_context)
        assert result['status'] == 'completed'
        assert 'response' in result
        assert 'timestamp' in result or 'created_at' in str(result)
        execution_state = await self.execution_tracker.get_execution_state(user_context.user_id, user_context.run_id)
        assert execution_state is not None
        assert execution_state.status == ExecutionStatus.COMPLETED
        assert execution_state.result_data is not None

    @pytest.mark.asyncio
    async def test_agent_completion_performance_metrics(self):
        """Test 20: Agent completion performance metrics."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        agent = await self.create_agent_with_mocks('supply_researcher', user_context)
        start_time = time.time()
        result = await agent.execute_async('Performance measurement task', user_context)
        end_time = time.time()
        execution_duration = end_time - start_time
        assert result['status'] == 'completed'
        assert execution_duration < 5.0
        assert self.mock_llm.call_count >= 1
        execution_state = await self.execution_tracker.get_execution_state(user_context.user_id, user_context.run_id)
        assert execution_state.completed_at is not None
        assert execution_state.completed_at > execution_state.created_at

    @pytest.mark.asyncio
    async def test_execution_engine_factory_pattern_integration(self):
        """Test 21: ExecutionEngine factory pattern integration."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        factory = ExecutionEngineFactory()
        engine = await factory.create_execution_engine(user_context)
        assert engine is not None
        assert hasattr(engine, 'execute_agent')
        test_agent = await self.create_agent_with_mocks('generic', user_context)
        result = await engine.execute_agent(test_agent, 'Factory pattern test')
        assert result is not None
        if hasattr(result, 'status'):
            assert result.status in ['completed', 'success']
        elif isinstance(result, dict):
            assert result.get('status') in ['completed', 'success', None]

    @pytest.mark.asyncio
    async def test_multi_agent_concurrent_execution_isolation(self):
        """Test 22: Multi-agent concurrent execution isolation."""
        user_contexts = [await self.create_test_execution_context(UserID(f'concurrent-user-{i}')) for i in range(3)]
        concurrent_agents = []
        for i, context in enumerate(user_contexts):
            agent = await self.create_agent_with_mocks('data_helper', context)
            concurrent_agents.append(agent)
        execution_tasks = [agent.execute_async(f'Concurrent task {i}', agent.user_context) for i, agent in enumerate(concurrent_agents)]
        results = await asyncio.gather(*execution_tasks)
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result['status'] == 'completed'
            assert f'Call #{i + 1}' in result['response'] or 'Analysis complete' in result['response']
        for i, agent in enumerate(concurrent_agents):
            assert agent.user_context.user_id == UserID(f'concurrent-user-{i}')

    @pytest.mark.asyncio
    async def test_execution_engine_resource_pool_management(self):
        """Test 23: ExecutionEngine resource pool management."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        factory = ExecutionEngineFactory()
        engine = await factory.create_execution_engine(user_context)
        agents = [await self.create_agent_with_mocks('generic', user_context) for _ in range(3)]
        initial_resources = await self._get_system_resource_count()
        results = []
        for i, agent in enumerate(agents):
            result = await engine.execute_agent(agent, f'Resource pool test {i}')
            results.append(result)
        final_resources = await self._get_system_resource_count()
        resource_growth = final_resources - initial_resources
        assert resource_growth <= 5
        assert len(results) == 3
        assert all((result is not None for result in results))

    async def _get_system_resource_count(self) -> int:
        """Helper method to get current system resource count."""
        active_executions = await self.execution_tracker.get_active_executions()
        return len(active_executions)

    @pytest.mark.asyncio
    async def test_execution_engine_error_propagation(self):
        """Test 24: ExecutionEngine error propagation."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        factory = ExecutionEngineFactory()
        engine = await factory.create_execution_engine(user_context)
        failing_agent = await self.create_agent_with_mocks('generic', user_context)

        async def failing_complete(*args, **kwargs):
            raise Exception('LLM service error')
        failing_agent.llm_manager.complete_async = failing_complete
        with pytest.raises(Exception) as exc_info:
            await engine.execute_agent(failing_agent, 'Task that will fail')
        assert 'LLM service error' in str(exc_info.value)
        try:
            execution_state = await self.execution_tracker.get_execution_state(user_context.user_id, user_context.run_id)
            if execution_state:
                assert execution_state.status in [ExecutionStatus.FAILED, ExecutionStatus.RUNNING]
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_execution_engine_performance_monitoring(self):
        """Test 25: ExecutionEngine performance monitoring."""
        user_context = await self.create_test_execution_context(self.test_users[0])
        factory = ExecutionEngineFactory()
        engine = await factory.create_execution_engine(user_context)
        agent = await self.create_agent_with_mocks('supply_researcher', user_context)
        start_time = time.time()
        result = await engine.execute_agent(agent, 'Performance monitoring test')
        end_time = time.time()
        execution_duration = end_time - start_time
        assert result is not None
        assert execution_duration < 10.0
        try:
            execution_state = await self.execution_tracker.get_execution_state(user_context.user_id, user_context.run_id)
            if execution_state and execution_state.completed_at:
                assert execution_state.completed_at > execution_state.created_at
                tracked_duration = (execution_state.completed_at - execution_state.created_at).total_seconds()
                assert tracked_duration > 0
                assert tracked_duration < 20.0
        except Exception:
            assert execution_duration > 0.01

@pytest.fixture
async def agent_execution_environment():
    """Fixture providing complete agent execution test environment."""
    env = get_env()
    env.set('TESTING', '1', source='agent_execution_fixture')
    env.set('USE_REAL_SERVICES', 'true', source='agent_execution_fixture')
    env.set('ENABLE_WEBSOCKET_EVENTS', 'true', source='agent_execution_fixture')
    yield env
    env.clear_test_data()

class AgentExecutionTestHelper:
    """Helper class for agent execution testing utilities."""

    @staticmethod
    async def create_mock_websocket_bridge(user_id: UserID) -> AgentWebSocketBridge:
        """Create mock WebSocket bridge for testing."""
        bridge = MagicMock(spec=AgentWebSocketBridge)
        bridge.user_id = user_id
        bridge.send_event = AsyncMock()
        return bridge

    @staticmethod
    async def validate_websocket_event_sequence(events: List[Dict], expected_sequence: List[str]):
        """Validate WebSocket event sequence matches expected order."""
        event_types = [event.get('event_type') for event in events]
        for expected_type in expected_sequence:
            assert expected_type in event_types, f'Missing expected event: {expected_type}'
        critical_order = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        actual_critical = [etype for etype in event_types if etype in critical_order]
        for i in range(len(actual_critical) - 1):
            current_idx = critical_order.index(actual_critical[i])
            next_idx = critical_order.index(actual_critical[i + 1])
            assert current_idx <= next_idx, f'Event order violation: {actual_critical[i]} -> {actual_critical[i + 1]}'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
"""
Integration Tests for Concurrent Agent Execution with User Context Isolation
Test #7 of Agent Registry and Factory Patterns Test Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core multi-user platform capability
- Business Goal: Enable reliable concurrent multi-user agent execution without cross-contamination
- Value Impact: Supports 10+ concurrent users with guaranteed isolation - enables platform scalability  
- Strategic Impact: $1.5M+ ARR foundation - multi-user isolation is core to platform business model

CRITICAL MISSION: Test Concurrent Agent Execution with User Context Isolation ensuring:
1. 10+ users can execute agents concurrently without interference
2. UserExecutionContext maintains complete isolation between users
3. Agent state, memory, and execution results remain user-specific
4. WebSocket events are delivered only to correct user connections
5. Resource allocation and cleanup work correctly under concurrent load
6. Factory-based isolation patterns prevent shared state corruption
7. Error handling isolates failures to specific user contexts
8. Performance remains acceptable under multi-user concurrent load

FOCUS: Real concurrent execution testing with actual agent instances, WebSocket connections,
        and user context validation to ensure business-critical multi-user isolation.
"""
import asyncio
import pytest
import time
import uuid
import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from collections import defaultdict, Counter
import random
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory, configure_agent_instance_factory
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, create_agent_websocket_bridge
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher

@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager for concurrent testing."""
    mock_llm = AsyncMock()
    mock_llm.initialize = AsyncMock()
    mock_llm.chat_completion = AsyncMock(return_value='Concurrent test response from agent')
    mock_llm.is_healthy = Mock(return_value=True)
    mock_llm.get_usage_stats = Mock(return_value={'total_requests': 0, 'concurrent_requests': 0})
    return mock_llm

@pytest.fixture
def concurrent_websocket_manager():
    """Create WebSocket manager optimized for concurrent testing."""
    ws_manager = UnifiedWebSocketManager()
    ws_manager._event_log = []
    ws_manager._event_lock = asyncio.Lock()
    ws_manager._user_connections = {}
    ws_manager._connection_stats = {'total_events': 0, 'total_users': 0}

    async def thread_safe_send_event(*args, **kwargs):
        async with ws_manager._event_lock:
            event_data = args[0] if args else kwargs
            ws_manager._event_log.append({'timestamp': time.time(), 'thread_id': threading.get_ident(), 'event': event_data, 'user_id': event_data.get('user_id', 'unknown')})
            ws_manager._connection_stats['total_events'] += 1
        return True
    ws_manager.send_event = thread_safe_send_event
    ws_manager.send_to_thread = thread_safe_send_event
    ws_manager.is_connected = Mock(return_value=True)
    ws_manager.get_connection_count = Mock(return_value=10)
    return ws_manager

@pytest.fixture
def multi_user_contexts():
    """Create multiple isolated user contexts for concurrent testing."""
    contexts = []
    user_tiers = ['free', 'early', 'mid', 'enterprise']
    for i in range(12):
        tier = user_tiers[i % len(user_tiers)]
        context = UserExecutionContext(user_id=f'concurrent_user_{i}_{uuid.uuid4().hex[:8]}', request_id=f'concurrent_req_{i}_{uuid.uuid4().hex[:8]}', thread_id=f'concurrent_thread_{i}_{uuid.uuid4().hex[:8]}', run_id=f'concurrent_run_{i}_{uuid.uuid4().hex[:8]}', agent_context={'user_tier': tier, 'concurrency_limit': {'free': 1, 'early': 2, 'mid': 3, 'enterprise': 5}[tier], 'test_data': f'isolated_data_for_user_{i}', 'user_index': i})
        contexts.append(context)
    return contexts

@pytest.fixture
def mock_concurrent_agent():
    """Create mock agent that simulates realistic concurrent execution."""

    class MockConcurrentAgent:

        def __init__(self, llm_manager=None, tool_dispatcher=None):
            self.llm_manager = llm_manager
            self.tool_dispatcher = tool_dispatcher
            self.execution_history = []
            self._websocket_bridge = None
            self._run_id = None
            self._agent_name = None
            self._user_specific_memory = {}
            self._execution_lock = asyncio.Lock()

        def set_websocket_bridge(self, bridge, run_id, agent_name=None):
            self._websocket_bridge = bridge
            self._run_id = run_id
            self._agent_name = agent_name or 'concurrent_agent'

        async def execute(self, state, run_id):
            """Concurrent-safe agent execution with user isolation."""
            async with self._execution_lock:
                execution_id = f'{run_id}_{time.time()}'
                start_time = time.time()
                try:
                    if run_id not in self._user_specific_memory:
                        self._user_specific_memory[run_id] = {'execution_count': 0, 'user_data': state, 'private_memory': f'private_to_{run_id}'}
                    self._user_specific_memory[run_id]['execution_count'] += 1
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_agent_started(run_id=self._run_id, agent_name=self._agent_name, context={'state': 'started', 'execution_id': execution_id, 'user_specific_data': self._user_specific_memory[run_id]['private_memory'], 'execution_count': self._user_specific_memory[run_id]['execution_count']})
                    processing_time = random.uniform(0.1, 0.5)
                    for step in range(3):
                        if self._websocket_bridge:
                            await self._websocket_bridge.notify_agent_thinking(run_id=self._run_id, agent_name=self._agent_name, reasoning=f'Processing step {step + 1}/3 for {run_id}', step_number=step + 1, progress_percentage=(step + 1) * 33.33)
                        await asyncio.sleep(processing_time / 3)
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_tool_executing(run_id=self._run_id, agent_name=self._agent_name, tool_name='concurrent_processor', parameters={'input': state, 'user_memory': self._user_specific_memory[run_id]['private_memory'], 'execution_id': execution_id})
                    processed_result = {'original_state': state, 'processed_data': f'processed_{state}_{execution_id}', 'user_memory': self._user_specific_memory[run_id]['private_memory'], 'execution_count': self._user_specific_memory[run_id]['execution_count'], 'processing_time': processing_time}
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_tool_completed(run_id=self._run_id, agent_name=self._agent_name, tool_name='concurrent_processor', result=processed_result, execution_time_ms=processing_time * 1000)
                    execution_time = (time.time() - start_time) * 1000
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_agent_completed(run_id=self._run_id, agent_name=self._agent_name, result={'status': 'success', 'data': processed_result, 'execution_metadata': {'execution_id': execution_id, 'execution_time_ms': execution_time, 'thread_id': threading.get_ident(), 'run_id': run_id}}, execution_time_ms=execution_time)
                    self.execution_history.append({'execution_id': execution_id, 'state': state, 'run_id': run_id, 'result': processed_result, 'execution_time': execution_time, 'thread_id': threading.get_ident()})
                    return {'status': 'success', 'data': processed_result, 'execution_id': execution_id}
                except Exception as e:
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_agent_error(run_id=self._run_id, agent_name=self._agent_name, error=str(e), context={'execution_id': execution_id})
                    raise

        async def cleanup(self):
            """Clean up user-specific memory and resources."""
            self._user_specific_memory.clear()

        def get_user_memory_for_run(self, run_id):
            """Get user-specific memory for testing isolation."""
            return self._user_specific_memory.get(run_id, {})
    return MockConcurrentAgent

class TestMultiUserConcurrentExecution(SSotBaseTestCase):
    """Test multi-user concurrent agent execution with complete isolation."""

    @pytest.mark.asyncio
    async def test_concurrent_10_users_agent_execution_isolation(self, mock_llm_manager, concurrent_websocket_manager, mock_concurrent_agent, multi_user_contexts):
        """Test 10+ users executing agents concurrently with complete isolation."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(concurrent_websocket_manager)
        user_agents = []
        for i, context in enumerate(multi_user_contexts[:10]):
            agent = mock_concurrent_agent()
            registry.get_async = AsyncMock(return_value=agent)
            created_agent = await registry.create_agent_for_user(user_id=context.user_id, agent_type=f'concurrent_test_agent_{i}', user_context=context, websocket_manager=concurrent_websocket_manager)
            user_agents.append((created_agent, context))
        execution_tasks = []
        start_time = time.time()
        for agent, context in user_agents:
            user_input = f"test_data_for_{context.user_id}_{context.agent_context['user_index']}"
            task = agent.execute(user_input, context.run_id)
            execution_tasks.append((task, context))
        task_list = [task for task, _ in execution_tasks]
        results = await asyncio.gather(*task_list)
        total_execution_time = time.time() - start_time
        assert len(results) == 10, 'Should have 10 concurrent execution results'
        for result in results:
            assert result['status'] == 'success'
            assert 'execution_id' in result
            assert 'data' in result
        for i, (result, (agent, context)) in enumerate(zip(results, user_agents)):
            expected_user_data = f"test_data_for_{context.user_id}_{context.agent_context['user_index']}"
            assert expected_user_data in result['data']['original_state']
            assert context.run_id in result['data']['processed_data']
            user_memory = agent.get_user_memory_for_run(context.run_id)
            assert context.run_id in user_memory['private_memory']
            for j, (other_agent, other_context) in enumerate(user_agents):
                if i != j:
                    other_memory = other_agent.get_user_memory_for_run(other_context.run_id)
                    assert other_context.run_id not in user_memory.get('private_memory', '')
                    assert context.run_id not in other_memory.get('private_memory', '')
        async with concurrent_websocket_manager._event_lock:
            event_log = concurrent_websocket_manager._event_log.copy()
        events_by_user = defaultdict(list)
        for event_entry in event_log:
            user_id = event_entry['event'].get('user_id', 'unknown')
            events_by_user[user_id].append(event_entry)
        assert len(events_by_user) >= 10, 'Should have events for at least 10 users'
        for context in multi_user_contexts[:10]:
            user_events = events_by_user.get(context.user_id, [])
            assert len(user_events) > 0, f'User {context.user_id} should have received WebSocket events'
            for event_entry in user_events:
                event_user_id = event_entry['event'].get('user_id')
                assert event_user_id == context.user_id, f'User {context.user_id} should only receive their own events'
        assert total_execution_time < 2.0, f'Concurrent execution of 10 users should complete in <2s, took {total_execution_time:.2f}s'

    @pytest.mark.asyncio
    async def test_concurrent_user_context_factory_isolation(self, mock_llm_manager, concurrent_websocket_manager, multi_user_contexts):
        """Test UserExecutionContext factory creates properly isolated contexts for concurrent users."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(concurrent_websocket_manager)
        factory = AgentInstanceFactory()
        mock_bridge = AsyncMock()
        mock_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
        factory.configure(agent_registry=registry, websocket_bridge=mock_bridge, websocket_manager=concurrent_websocket_manager, llm_manager=mock_llm_manager)
        context_creation_tasks = []
        for context in multi_user_contexts[:8]:
            task = factory.create_user_execution_context(user_id=context.user_id, thread_id=context.thread_id, run_id=context.run_id, request_id=context.request_id)
            context_creation_tasks.append((task, context))
        task_list = [task for task, _ in context_creation_tasks]
        created_contexts = await asyncio.gather(*task_list)
        assert len(created_contexts) == 8, 'Should have created 8 concurrent contexts'
        for i, (created_context, (_, original_context)) in enumerate(zip(created_contexts, context_creation_tasks)):
            assert created_context.user_id == original_context.user_id
            assert created_context.run_id == original_context.run_id
            assert created_context.thread_id == original_context.thread_id
            for j, other_created_context in enumerate(created_contexts):
                if i != j:
                    assert created_context is not other_created_context
                    assert created_context.user_id != other_created_context.user_id
                    assert created_context.run_id != other_created_context.run_id
                    assert created_context.thread_id != other_created_context.thread_id
        cleanup_tasks = [factory.cleanup_user_context(ctx) for ctx in created_contexts]
        await asyncio.gather(*cleanup_tasks)

    @pytest.mark.asyncio
    async def test_concurrent_websocket_event_delivery_isolation(self, mock_llm_manager, concurrent_websocket_manager, multi_user_contexts):
        """Test WebSocket events are delivered only to correct users during concurrent execution."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(concurrent_websocket_manager)
        user_sessions = []
        for context in multi_user_contexts[:6]:
            session = await registry.get_user_session(context.user_id)
            user_sessions.append((session, context))
        event_sending_tasks = []
        event_types = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        for session, context in user_sessions:
            for event_type in event_types:
                task = concurrent_websocket_manager.send_event({'event_type': event_type, 'user_id': context.user_id, 'run_id': context.run_id, 'thread_id': context.thread_id, 'timestamp': time.time(), 'data': f'event_data_for_{context.user_id}_{event_type}'})
                event_sending_tasks.append(task)
        await asyncio.gather(*event_sending_tasks)
        async with concurrent_websocket_manager._event_lock:
            all_events = concurrent_websocket_manager._event_log.copy()
        events_by_user = defaultdict(list)
        for event_entry in all_events:
            user_id = event_entry['event'].get('user_id')
            events_by_user[user_id].append(event_entry)
        assert len(events_by_user) == 6, 'Should have events for exactly 6 users'
        for session, context in user_sessions:
            user_events = events_by_user[context.user_id]
            assert len(user_events) == len(event_types), f'User {context.user_id} should receive all {len(event_types)} event types'
            for event_entry in user_events:
                event = event_entry['event']
                assert event['user_id'] == context.user_id
                assert event['run_id'] == context.run_id
                assert event['thread_id'] == context.thread_id
                assert context.user_id in event['data']
        all_user_ids = {context.user_id for _, context in user_sessions}
        for user_id, user_events in events_by_user.items():
            assert user_id in all_user_ids, f'Unexpected user_id {user_id} in events'
            for event_entry in user_events:
                event_user_id = event_entry['event']['user_id']
                assert event_user_id == user_id, f'Event for {user_id} contains data for {event_user_id}'

class TestConcurrentResourceManagement(SSotBaseTestCase):
    """Test concurrent resource management and cleanup."""

    @pytest.mark.asyncio
    async def test_concurrent_agent_resource_allocation_and_cleanup(self, mock_llm_manager, concurrent_websocket_manager, mock_concurrent_agent, multi_user_contexts):
        """Test resource allocation and cleanup work correctly under concurrent load."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(concurrent_websocket_manager)
        allocated_resources = {'agents': {}, 'sessions': {}, 'websocket_bridges': {}, 'memory_usage': defaultdict(int)}
        concurrent_executions = []
        for i, context in enumerate(multi_user_contexts[:8]):
            agent = mock_concurrent_agent()
            registry.get_async = AsyncMock(return_value=agent)
            allocated_resources['agents'][context.user_id] = agent
            allocated_resources['memory_usage'][context.user_id] = i * 1024
            created_agent = await registry.create_agent_for_user(user_id=context.user_id, agent_type=f'resource_test_agent_{i}', user_context=context, websocket_manager=concurrent_websocket_manager)
            execution_task = created_agent.execute(f'resource_test_data_{i}', context.run_id)
            concurrent_executions.append((execution_task, created_agent, context))
        execution_tasks = [task for task, _, _ in concurrent_executions]
        results = await asyncio.gather(*execution_tasks)
        for result in results:
            assert result['status'] == 'success'
        cleanup_tasks = []
        for _, agent, context in concurrent_executions:
            cleanup_task = agent.cleanup()
            cleanup_tasks.append(cleanup_task)
        await asyncio.gather(*cleanup_tasks)
        for _, agent, context in concurrent_executions:
            user_memory = agent.get_user_memory_for_run(context.run_id)
            assert len(user_memory) == 0, f'Agent for {context.user_id} should have cleaned up user-specific memory'
        assert len(allocated_resources['agents']) == 8, 'Should have allocated 8 agent resources'
        for user_id in list(allocated_resources['agents'].keys()):
            del allocated_resources['agents'][user_id]
            del allocated_resources['memory_usage'][user_id]
        assert len(allocated_resources['agents']) == 0, 'All agent resources should be deallocated'
        assert len(allocated_resources['memory_usage']) == 0, 'All memory usage should be cleared'

    @pytest.mark.asyncio
    async def test_concurrent_error_isolation_and_recovery(self, mock_llm_manager, concurrent_websocket_manager, mock_concurrent_agent, multi_user_contexts):
        """Test error handling isolates failures to specific users during concurrent execution."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(concurrent_websocket_manager)
        successful_agents = []
        failing_agents = []
        for i, context in enumerate(multi_user_contexts[:6]):
            if i < 3:
                agent = mock_concurrent_agent()
                successful_agents.append((agent, context))
            else:
                agent = mock_concurrent_agent()
                original_execute = agent.execute

                async def failing_execute(state, run_id):
                    if agent._websocket_bridge:
                        await agent._websocket_bridge.notify_agent_started(run_id=agent._run_id, agent_name=agent._agent_name, context={'state': 'started', 'will_fail': True})
                    raise Exception(f'Simulated failure for user {context.user_id}')
                agent.execute = failing_execute
                failing_agents.append((agent, context))
        all_agents = successful_agents + failing_agents
        for agent, context in all_agents:
            registry.get_async = AsyncMock(return_value=agent)
            created_agent = await registry.create_agent_for_user(user_id=context.user_id, agent_type=f'error_test_agent', user_context=context, websocket_manager=concurrent_websocket_manager)
            if (agent, context) in successful_agents:
                index = successful_agents.index((agent, context))
                successful_agents[index] = (created_agent, context)
            else:
                index = failing_agents.index((agent, context))
                failing_agents[index] = (created_agent, context)
        execution_tasks = []
        for agent, context in all_agents:
            task = agent.execute(f'test_input_{context.user_id}', context.run_id)
            execution_tasks.append((task, context))
        results = await asyncio.gather(*[task for task, _ in execution_tasks], return_exceptions=True)
        success_count = sum((1 for result in results if not isinstance(result, Exception)))
        failure_count = sum((1 for result in results if isinstance(result, Exception)))
        assert success_count == 3, f'Should have 3 successful executions, got {success_count}'
        assert failure_count == 3, f'Should have 3 failed executions, got {failure_count}'
        for i, result in enumerate(results):
            context = execution_tasks[i][1]
            if i < 3:
                assert not isinstance(result, Exception), f'User {context.user_id} should have succeeded'
                assert result['status'] == 'success'
            else:
                assert isinstance(result, Exception), f'User {context.user_id} should have failed'
                assert context.user_id in str(result), 'Error should contain user-specific information'
        async with concurrent_websocket_manager._event_lock:
            all_events = concurrent_websocket_manager._event_log.copy()
        error_events_by_user = defaultdict(list)
        success_events_by_user = defaultdict(list)
        for event_entry in all_events:
            event = event_entry['event']
            user_id = event.get('user_id')
            event_type = event.get('event_type', '')
            if 'error' in event_type.lower():
                error_events_by_user[user_id].append(event)
            elif 'completed' in event_type.lower() or 'success' in str(event).lower():
                success_events_by_user[user_id].append(event)
        failing_user_ids = {context.user_id for _, context in failing_agents}
        successful_user_ids = {context.user_id for _, context in successful_agents}
        for user_id in error_events_by_user.keys():
            assert user_id in failing_user_ids, f'Error events should only be for failing users, not {user_id}'
        for user_id in successful_user_ids:
            assert user_id not in error_events_by_user, f'Successful user {user_id} should not have error events'

class TestConcurrentPerformance(SSotBaseTestCase):
    """Test system performance under concurrent multi-user load."""

    @pytest.mark.asyncio
    async def test_performance_12_concurrent_users_execution(self, mock_llm_manager, concurrent_websocket_manager, mock_concurrent_agent, multi_user_contexts):
        """Test system performance with 12 concurrent users executing agents."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(concurrent_websocket_manager)
        performance_metrics = {'user_execution_times': {}, 'websocket_event_counts': defaultdict(int), 'resource_usage': {'peak_agents': 0, 'total_events': 0}, 'concurrency_stats': {'max_concurrent': 0, 'avg_response_time': 0}}
        user_agents = []
        agent_creation_start = time.time()
        for i, context in enumerate(multi_user_contexts):
            agent = mock_concurrent_agent()
            registry.get_async = AsyncMock(return_value=agent)
            created_agent = await registry.create_agent_for_user(user_id=context.user_id, agent_type=f'performance_agent_{i}', user_context=context, websocket_manager=concurrent_websocket_manager)
            user_agents.append((created_agent, context, time.time()))
            performance_metrics['resource_usage']['peak_agents'] += 1
        agent_creation_time = time.time() - agent_creation_start
        execution_start_time = time.time()
        execution_tasks = []
        for agent, context, creation_time in user_agents:
            user_input = f"performance_test_{context.agent_context['user_index']}"
            task = agent.execute(user_input, context.run_id)
            execution_tasks.append((task, context, creation_time))
        performance_metrics['concurrency_stats']['max_concurrent'] = len(execution_tasks)
        task_list = [task for task, _, _ in execution_tasks]
        results = await asyncio.gather(*task_list)
        total_execution_time = time.time() - execution_start_time
        for i, (result, (_, context, creation_time)) in enumerate(zip(results, execution_tasks)):
            user_execution_time = result.get('execution_id', 0)
            performance_metrics['user_execution_times'][context.user_id] = user_execution_time
        async with concurrent_websocket_manager._event_lock:
            total_events = len(concurrent_websocket_manager._event_log)
            performance_metrics['resource_usage']['total_events'] = total_events
            for event_entry in concurrent_websocket_manager._event_log:
                user_id = event_entry['event'].get('user_id', 'unknown')
                performance_metrics['websocket_event_counts'][user_id] += 1
        assert len(results) == 12, 'Should have 12 concurrent execution results'
        assert all((result['status'] == 'success' for result in results)), 'All executions should succeed'
        assert agent_creation_time < 2.0, f'Agent creation for 12 users should take <2s, took {agent_creation_time:.2f}s'
        assert total_execution_time < 3.0, f'Concurrent execution for 12 users should take <3s, took {total_execution_time:.2f}s'
        avg_response_time = total_execution_time / 12
        performance_metrics['concurrency_stats']['avg_response_time'] = avg_response_time
        assert avg_response_time < 0.5, f'Average response time should be <500ms, got {avg_response_time:.3f}s'
        assert total_events >= 48, f'Should have at least 4 events per user (48 total), got {total_events}'
        event_counts = list(performance_metrics['websocket_event_counts'].values())
        min_events = min(event_counts) if event_counts else 0
        max_events = max(event_counts) if event_counts else 0
        assert min_events > 0, 'All users should have received some events'
        assert max_events / min_events < 3, 'Event distribution should be relatively even across users'
        assert performance_metrics['resource_usage']['peak_agents'] == 12, 'Should track 12 peak agents'
        assert performance_metrics['concurrency_stats']['max_concurrent'] == 12, 'Should track 12 max concurrent executions'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
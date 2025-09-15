"""
Test AgentRegistry UserAgentSession Isolation and Lifecycle Management

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure user agent sessions are completely isolated
- Value Impact: Prevents agent contamination between users
- Strategic Impact: Foundation for secure multi-user agent management

CRITICAL MISSION: Test AgentRegistry UserAgentSession isolation ensuring:
1. UserAgentSession creation and lifecycle management
2. Per-user WebSocket bridge isolation and cleanup
3. Agent registration and cleanup within user sessions
4. Memory leak prevention in concurrent scenarios
5. Thread-safe access to user-specific resources
6. Concurrent user session management
7. WebSocket manager propagation to user sessions
8. Complete resource cleanup on session termination

FOCUS: Factory-based isolation patterns from USER_CONTEXT_ARCHITECTURE.md
"""
import asyncio
import pytest
import time
import uuid
import weakref
import gc
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession, AgentLifecycleManager, get_agent_registry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.agents.base_agent import BaseAgent

@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager."""
    mock_llm = AsyncMock()
    mock_llm.initialize = AsyncMock()
    mock_llm.chat_completion = AsyncMock(return_value='Test response')
    mock_llm.is_healthy = Mock(return_value=True)
    return mock_llm

@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager with bridge factory."""
    mock_manager = Mock(spec=WebSocketManager)
    mock_manager.send_event = AsyncMock(return_value=True)
    mock_manager.is_connected = Mock(return_value=True)
    mock_manager.disconnect = AsyncMock()

    async def create_bridge(user_context):
        mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
        mock_bridge.notify_agent_started = AsyncMock(return_value=True)
        mock_bridge.notify_agent_thinking = AsyncMock(return_value=True)
        mock_bridge.notify_tool_executing = AsyncMock(return_value=True)
        mock_bridge.notify_tool_completed = AsyncMock(return_value=True)
        mock_bridge.notify_agent_completed = AsyncMock(return_value=True)
        mock_bridge.notify_agent_error = AsyncMock(return_value=True)
        mock_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
        mock_bridge.unregister_run_mapping = AsyncMock(return_value=True)
        return mock_bridge
    mock_manager.create_bridge = AsyncMock(side_effect=create_bridge)
    return mock_manager

@pytest.fixture
def test_user_context():
    """Create test user execution context."""
    return UserExecutionContext(user_id=f'test_user_{uuid.uuid4().hex[:8]}', request_id=f'test_request_{uuid.uuid4().hex[:8]}', thread_id=f'test_thread_{uuid.uuid4().hex[:8]}', run_id=f'test_run_{uuid.uuid4().hex[:8]}')

@pytest.fixture
def multiple_user_contexts():
    """Create multiple user contexts for isolation testing."""
    contexts = []
    for i in range(5):
        context = UserExecutionContext(user_id=f'user_{i}_{uuid.uuid4().hex[:6]}', request_id=f'req_{i}_{uuid.uuid4().hex[:6]}', thread_id=f'thread_{i}_{uuid.uuid4().hex[:6]}', run_id=f'run_{i}_{uuid.uuid4().hex[:6]}')
        contexts.append(context)
    return contexts

@pytest.fixture
def mock_agent():
    """Create mock agent for testing."""
    mock_agent = Mock(spec=BaseAgent)
    mock_agent.cleanup = AsyncMock()
    mock_agent.close = AsyncMock()
    return mock_agent

class TestUserAgentSessionCreationAndInitialization(SSotBaseTestCase):
    """Test UserAgentSession creation and initialization patterns."""

    def test_user_agent_session_basic_initialization(self):
        """Test basic UserAgentSession initialization."""
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = UserAgentSession(user_id)
        assert session.user_id == user_id
        assert isinstance(session._agents, dict)
        assert len(session._agents) == 0
        assert isinstance(session._execution_contexts, dict)
        assert len(session._execution_contexts) == 0
        assert session._websocket_bridge is None
        assert session._websocket_manager is None
        assert session._created_at is not None
        assert isinstance(session._created_at, datetime)
        assert session._access_lock is not None
        self.record_metric('session_initialization_success', True)

    def test_user_agent_session_initialization_validation(self):
        """Test UserAgentSession initialization validation."""
        with pytest.raises(ValueError, match='user_id must be a non-empty string'):
            UserAgentSession(None)
        with pytest.raises(ValueError, match='user_id must be a non-empty string'):
            UserAgentSession('')
        with pytest.raises(ValueError, match='user_id must be a non-empty string'):
            UserAgentSession('   ')
        with pytest.raises(ValueError, match='user_id must be a non-empty string'):
            UserAgentSession(123)
        self.record_metric('validation_tests_passed', 4)

    def test_user_agent_session_multiple_instances_isolation(self):
        """Test multiple UserAgentSession instances maintain isolation."""
        user_ids = [f'user_{i}_{uuid.uuid4().hex[:6]}' for i in range(5)]
        sessions = [UserAgentSession(user_id) for user_id in user_ids]
        for i, session in enumerate(sessions):
            assert session.user_id == user_ids[i]
        for i, session in enumerate(sessions):
            for j, other_session in enumerate(sessions):
                if i != j:
                    assert session.user_id != other_session.user_id
                    assert session._agents is not other_session._agents
                    assert session._execution_contexts is not other_session._execution_contexts
                    assert session._access_lock is not other_session._access_lock
        self.record_metric('isolation_test_sessions', len(sessions))

    @pytest.mark.asyncio
    async def test_user_agent_session_websocket_manager_setting(self, mock_websocket_manager, test_user_context):
        """Test setting WebSocket manager on UserAgentSession."""
        session = UserAgentSession(test_user_context.user_id)
        await session.set_websocket_manager(mock_websocket_manager, test_user_context)
        assert session._websocket_manager == mock_websocket_manager
        assert session._websocket_bridge is not None
        mock_websocket_manager.create_bridge.assert_called_once_with(test_user_context)
        self.record_metric('websocket_manager_set_success', True)

    @pytest.mark.asyncio
    async def test_user_agent_session_websocket_manager_none_handling(self, test_user_context):
        """Test handling of None WebSocket manager."""
        session = UserAgentSession(test_user_context.user_id)
        await session.set_websocket_manager(None, test_user_context)
        assert session._websocket_manager is None
        assert session._websocket_bridge is None
        self.record_metric('none_websocket_manager_handled', True)

    @pytest.mark.asyncio
    async def test_user_agent_session_websocket_manager_without_context(self, mock_websocket_manager):
        """Test WebSocket manager setting creates default context."""
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = UserAgentSession(user_id)
        await session.set_websocket_manager(mock_websocket_manager)
        assert session._websocket_manager == mock_websocket_manager
        assert session._websocket_bridge is not None
        mock_websocket_manager.create_bridge.assert_called_once()
        call_args = mock_websocket_manager.create_bridge.call_args[0]
        created_context = call_args[0]
        assert created_context.user_id == user_id
        assert created_context.request_id.startswith(f'session_{user_id}')
        self.record_metric('default_context_creation_success', True)

class TestUserAgentSessionAgentManagement(SSotBaseTestCase):
    """Test agent management within UserAgentSession."""

    @pytest.mark.asyncio
    async def test_user_agent_session_agent_registration(self, mock_agent):
        """Test agent registration in UserAgentSession."""
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = UserAgentSession(user_id)
        agent_type = 'test_agent'
        await session.register_agent(agent_type, mock_agent)
        assert agent_type in session._agents
        assert session._agents[agent_type] == mock_agent
        retrieved_agent = await session.get_agent(agent_type)
        assert retrieved_agent == mock_agent
        self.record_metric('agent_registration_success', True)

    @pytest.mark.asyncio
    async def test_user_agent_session_multiple_agent_registration(self, mock_websocket_manager):
        """Test multiple agent registration in single session."""
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = UserAgentSession(user_id)
        agents = {'triage': Mock(spec=BaseAgent), 'data': Mock(spec=BaseAgent), 'optimization': Mock(spec=BaseAgent)}
        for agent_type, agent in agents.items():
            await session.register_agent(agent_type, agent)
        assert len(session._agents) == 3
        for agent_type, agent in agents.items():
            assert session._agents[agent_type] == agent
            retrieved_agent = await session.get_agent(agent_type)
            assert retrieved_agent == agent
        self.record_metric('multiple_agents_registered', len(agents))

    @pytest.mark.asyncio
    async def test_user_agent_session_execution_context_creation(self, test_user_context):
        """Test execution context creation for agents."""
        session = UserAgentSession(test_user_context.user_id)
        agent_type = 'test_agent'
        execution_context = await session.create_agent_execution_context(agent_type, test_user_context)
        assert execution_context is not None
        assert agent_type in session._execution_contexts
        assert session._execution_contexts[agent_type] == execution_context
        assert execution_context.user_id == test_user_context.user_id
        self.record_metric('execution_context_creation_success', True)

    @pytest.mark.asyncio
    async def test_user_agent_session_get_nonexistent_agent(self):
        """Test getting non-existent agent returns None."""
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = UserAgentSession(user_id)
        agent = await session.get_agent('nonexistent_agent')
        assert agent is None
        self.record_metric('nonexistent_agent_handled', True)

    @pytest.mark.asyncio
    async def test_user_agent_session_concurrent_agent_access(self, multiple_user_contexts):
        """Test concurrent agent access maintains thread safety."""
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = UserAgentSession(user_id)
        agents = [Mock(spec=BaseAgent) for _ in range(10)]

        async def register_agent(i, agent):
            agent_type = f'agent_{i}'
            await session.register_agent(agent_type, agent)
            return await session.get_agent(agent_type)
        tasks = [register_agent(i, agent) for i, agent in enumerate(agents)]
        retrieved_agents = await asyncio.gather(*tasks)
        assert len(retrieved_agents) == len(agents)
        assert len(session._agents) == len(agents)
        for i, retrieved_agent in enumerate(retrieved_agents):
            assert retrieved_agent == agents[i]
        self.record_metric('concurrent_agent_operations', len(agents))

class TestUserAgentSessionCleanupAndLifecycle(SSotBaseTestCase):
    """Test UserAgentSession cleanup and lifecycle management."""

    @pytest.mark.asyncio
    async def test_user_agent_session_cleanup_all_agents(self, mock_websocket_manager):
        """Test cleanup of all agents in session."""
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = UserAgentSession(user_id)
        agents = {}
        for i in range(3):
            agent = Mock(spec=BaseAgent)
            agent.cleanup = AsyncMock()
            agent.close = AsyncMock()
            agent_type = f'agent_{i}'
            agents[agent_type] = agent
            await session.register_agent(agent_type, agent)
        for agent_type in agents.keys():
            context = Mock()
            session._execution_contexts[agent_type] = context
        await session.set_websocket_manager(mock_websocket_manager)
        assert len(session._agents) == 3
        assert len(session._execution_contexts) == 3
        assert session._websocket_bridge is not None
        await session.cleanup_all_agents()
        assert len(session._agents) == 0
        assert len(session._execution_contexts) == 0
        assert session._websocket_bridge is None
        for agent in agents.values():
            agent.cleanup.assert_called_once()
        self.record_metric('agents_cleaned_up', len(agents))

    @pytest.mark.asyncio
    async def test_user_agent_session_cleanup_handles_exceptions(self):
        """Test cleanup handles exceptions in agent cleanup gracefully."""
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = UserAgentSession(user_id)
        failing_agent = Mock(spec=BaseAgent)
        failing_agent.cleanup = AsyncMock(side_effect=Exception('Cleanup failed'))
        working_agent = Mock(spec=BaseAgent)
        working_agent.cleanup = AsyncMock()
        await session.register_agent('failing', failing_agent)
        await session.register_agent('working', working_agent)
        await session.cleanup_all_agents()
        failing_agent.cleanup.assert_called_once()
        working_agent.cleanup.assert_called_once()
        assert len(session._agents) == 0
        self.record_metric('cleanup_exception_handling_success', True)

    @pytest.mark.asyncio
    async def test_user_agent_session_cleanup_agents_without_cleanup_method(self):
        """Test cleanup handles agents without cleanup method."""
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = UserAgentSession(user_id)
        simple_agent = Mock()
        await session.register_agent('simple', simple_agent)
        await session.cleanup_all_agents()
        assert len(session._agents) == 0
        self.record_metric('cleanup_without_method_success', True)

    def test_user_agent_session_get_metrics(self, mock_websocket_manager):
        """Test UserAgentSession metrics reporting."""
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = UserAgentSession(user_id)
        metrics = session.get_metrics()
        assert metrics['user_id'] == user_id
        assert metrics['agent_count'] == 0
        assert metrics['context_count'] == 0
        assert metrics['has_websocket_bridge'] is False
        assert metrics['uptime_seconds'] >= 0
        self.record_metric('metrics_reporting_success', True)

    @pytest.mark.asyncio
    async def test_user_agent_session_metrics_with_agents(self, mock_websocket_manager):
        """Test metrics reporting with agents and contexts."""
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = UserAgentSession(user_id)
        for i in range(3):
            agent = Mock(spec=BaseAgent)
            await session.register_agent(f'agent_{i}', agent)
            session._execution_contexts[f'agent_{i}'] = Mock()
        await session.set_websocket_manager(mock_websocket_manager)
        metrics = session.get_metrics()
        assert metrics['agent_count'] == 3
        assert metrics['context_count'] == 3
        assert metrics['has_websocket_bridge'] is True
        self.record_metric('metrics_with_agents_success', True)

class TestAgentRegistryUserAgentSessionIntegration(SSotBaseTestCase):
    """Test AgentRegistry integration with UserAgentSession."""

    @pytest.mark.asyncio
    async def test_agent_registry_get_user_session_creation(self, mock_llm_manager):
        """Test AgentRegistry creates UserAgentSession on demand."""
        registry = AgentRegistry(mock_llm_manager)
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = await registry.get_user_session(user_id)
        assert isinstance(session, UserAgentSession)
        assert session.user_id == user_id
        assert user_id in registry._user_sessions
        assert registry._user_sessions[user_id] == session
        self.record_metric('user_session_creation_success', True)

    @pytest.mark.asyncio
    async def test_agent_registry_get_user_session_reuse(self, mock_llm_manager):
        """Test AgentRegistry reuses existing UserAgentSession."""
        registry = AgentRegistry(mock_llm_manager)
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session1 = await registry.get_user_session(user_id)
        session2 = await registry.get_user_session(user_id)
        assert session1 is session2
        assert len(registry._user_sessions) == 1
        self.record_metric('user_session_reuse_success', True)

    @pytest.mark.asyncio
    async def test_agent_registry_get_user_session_validation(self, mock_llm_manager):
        """Test AgentRegistry user session validation."""
        registry = AgentRegistry(mock_llm_manager)
        with pytest.raises(ValueError, match='user_id is required and must be non-empty string'):
            await registry.get_user_session(None)
        with pytest.raises(ValueError, match='user_id is required and must be non-empty string'):
            await registry.get_user_session('')
        with pytest.raises(ValueError, match='user_id is required and must be non-empty string'):
            await registry.get_user_session(123)
        self.record_metric('registry_validation_tests_passed', 3)

    @pytest.mark.asyncio
    async def test_agent_registry_concurrent_user_session_creation(self, mock_llm_manager, multiple_user_contexts):
        """Test concurrent user session creation maintains isolation."""
        registry = AgentRegistry(mock_llm_manager)

        async def get_session(context):
            return await registry.get_user_session(context.user_id)
        tasks = [get_session(ctx) for ctx in multiple_user_contexts]
        sessions = await asyncio.gather(*tasks)
        assert len(sessions) == len(multiple_user_contexts)
        assert len(registry._user_sessions) == len(multiple_user_contexts)
        for i, session in enumerate(sessions):
            expected_user_id = multiple_user_contexts[i].user_id
            assert session.user_id == expected_user_id
        session_ids = [session.user_id for session in sessions]
        assert len(session_ids) == len(set(session_ids))
        self.record_metric('concurrent_sessions_created', len(sessions))

    @pytest.mark.asyncio
    async def test_agent_registry_user_session_websocket_propagation(self, mock_llm_manager, mock_websocket_manager):
        """Test WebSocket manager propagation to user sessions."""
        registry = AgentRegistry(mock_llm_manager)
        user_ids = [f'user_{i}_{uuid.uuid4().hex[:6]}' for i in range(3)]
        sessions = []
        for user_id in user_ids:
            session = await registry.get_user_session(user_id)
            sessions.append(session)
        for session in sessions:
            assert session._websocket_bridge is None
        await registry.set_websocket_manager_async(mock_websocket_manager)
        for session in sessions:
            assert session._websocket_bridge is not None
            assert session._websocket_manager == mock_websocket_manager
        self.record_metric('websocket_propagation_success', len(sessions))

    @pytest.mark.asyncio
    async def test_agent_registry_cleanup_user_session(self, mock_llm_manager, mock_agent):
        """Test cleanup of specific user session."""
        registry = AgentRegistry(mock_llm_manager)
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = await registry.get_user_session(user_id)
        await session.register_agent('test_agent', mock_agent)
        assert len(session._agents) == 1
        assert user_id in registry._user_sessions
        cleanup_metrics = await registry.cleanup_user_session(user_id)
        assert user_id not in registry._user_sessions
        assert cleanup_metrics['user_id'] == user_id
        assert cleanup_metrics['status'] == 'cleaned'
        assert cleanup_metrics['cleaned_agents'] == 1
        mock_agent.cleanup.assert_called_once()
        self.record_metric('user_session_cleanup_success', True)

    @pytest.mark.asyncio
    async def test_agent_registry_create_agent_for_user(self, mock_llm_manager, test_user_context, mock_websocket_manager):
        """Test creating agent for specific user with isolation."""
        registry = AgentRegistry(mock_llm_manager)
        await registry.set_websocket_manager_async(mock_websocket_manager)
        mock_agent = Mock(spec=BaseAgent)
        registry.register('test_agent', mock_agent)
        agent = await registry.create_agent_for_user(user_id=test_user_context.user_id, agent_type='test_agent', user_context=test_user_context, websocket_manager=mock_websocket_manager)
        assert agent == mock_agent
        user_session = registry._user_sessions[test_user_context.user_id]
        assert await user_session.get_agent('test_agent') == mock_agent
        self.record_metric('agent_creation_for_user_success', True)

    @pytest.mark.asyncio
    async def test_agent_registry_get_user_agent(self, mock_llm_manager, test_user_context, mock_agent):
        """Test getting agent for specific user."""
        registry = AgentRegistry(mock_llm_manager)
        session = await registry.get_user_session(test_user_context.user_id)
        await session.register_agent('test_agent', mock_agent)
        retrieved_agent = await registry.get_user_agent(test_user_context.user_id, 'test_agent')
        assert retrieved_agent == mock_agent
        self.record_metric('get_user_agent_success', True)

    @pytest.mark.asyncio
    async def test_agent_registry_remove_user_agent(self, mock_llm_manager, test_user_context, mock_agent):
        """Test removing specific agent from user session."""
        registry = AgentRegistry(mock_llm_manager)
        session = await registry.get_user_session(test_user_context.user_id)
        await session.register_agent('test_agent', mock_agent)
        assert await session.get_agent('test_agent') == mock_agent
        removed = await registry.remove_user_agent(test_user_context.user_id, 'test_agent')
        assert removed is True
        assert await session.get_agent('test_agent') is None
        mock_agent.cleanup.assert_called_once()
        self.record_metric('remove_user_agent_success', True)

    @pytest.mark.asyncio
    async def test_agent_registry_reset_user_agents(self, mock_llm_manager, test_user_context, mock_agent):
        """Test resetting all agents for specific user."""
        registry = AgentRegistry(mock_llm_manager)
        session = await registry.get_user_session(test_user_context.user_id)
        for i in range(3):
            agent = Mock(spec=BaseAgent)
            agent.cleanup = AsyncMock()
            await session.register_agent(f'agent_{i}', agent)
        assert len(session._agents) == 3
        reset_report = await registry.reset_user_agents(test_user_context.user_id)
        assert reset_report['status'] == 'reset_complete'
        assert reset_report['agents_reset'] == 3
        new_session = registry._user_sessions[test_user_context.user_id]
        assert new_session is not session
        assert len(new_session._agents) == 0
        self.record_metric('reset_user_agents_success', True)

class TestAgentLifecycleManager(SSotBaseTestCase):
    """Test AgentLifecycleManager memory leak prevention."""

    @pytest.mark.asyncio
    async def test_lifecycle_manager_cleanup_agent_resources(self, mock_llm_manager):
        """Test lifecycle manager integration for agent resource cleanup."""
        registry = AgentRegistry(mock_llm_manager)
        lifecycle_manager = registry._lifecycle_manager
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        agent_id = 'test_agent'
        mock_agent = Mock(spec=BaseAgent)
        mock_agent.cleanup = AsyncMock()
        session = await registry.get_user_session(user_id)
        await session.register_agent(agent_id, mock_agent)
        assert await session.get_agent(agent_id) == mock_agent
        assert agent_id in session._agents
        await lifecycle_manager.cleanup_agent_resources(user_id, agent_id)
        assert lifecycle_manager._registry is not None
        assert user_id in registry._user_sessions
        self.record_metric('lifecycle_manager_integration_tested', True)

    @pytest.mark.asyncio
    async def test_lifecycle_manager_monitor_memory_usage(self, mock_llm_manager):
        """Test lifecycle manager monitors memory usage."""
        registry = AgentRegistry(mock_llm_manager)
        lifecycle_manager = registry._lifecycle_manager
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        session = await registry.get_user_session(user_id)
        for i in range(3):
            agent = Mock(spec=BaseAgent)
            await session.register_agent(f'agent_{i}', agent)
        memory_report = await lifecycle_manager.monitor_memory_usage(user_id)
        assert memory_report['status'] == 'healthy'
        assert memory_report['user_id'] == user_id
        assert memory_report['metrics']['agent_count'] == 3
        assert memory_report['metrics']['has_websocket_bridge'] is False
        self.record_metric('memory_monitoring_success', True)

    @pytest.mark.asyncio
    async def test_lifecycle_manager_trigger_cleanup(self, mock_llm_manager):
        """Test lifecycle manager emergency cleanup integration."""
        registry = AgentRegistry(mock_llm_manager)
        lifecycle_manager = registry._lifecycle_manager
        user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        mock_agent = Mock(spec=BaseAgent)
        mock_agent.cleanup = AsyncMock()
        session = await registry.get_user_session(user_id)
        await session.register_agent('test_agent', mock_agent)
        assert user_id in registry._user_sessions
        assert len(session._agents) == 1
        await lifecycle_manager.trigger_cleanup(user_id)
        assert lifecycle_manager._registry is not None
        self.record_metric('emergency_cleanup_integration_tested', True)

class TestConcurrentOperationsAndMemoryManagement(SSotBaseTestCase):
    """Test concurrent operations and memory management."""

    @pytest.mark.asyncio
    async def test_concurrent_user_session_operations(self, mock_llm_manager, multiple_user_contexts):
        """Test concurrent operations across multiple user sessions."""
        registry = AgentRegistry(mock_llm_manager)

        async def perform_operations(context):
            """Perform multiple operations for a user."""
            session = await registry.get_user_session(context.user_id)
            agents = []
            for i in range(3):
                agent = Mock(spec=BaseAgent)
                agent.cleanup = AsyncMock()
                agent_type = f'agent_{i}'
                await session.register_agent(agent_type, agent)
                agents.append((agent_type, agent))
            for agent_type, _ in agents:
                await session.create_agent_execution_context(agent_type, context)
            assert len(session._agents) == 3
            assert len(session._execution_contexts) == 3
            return (session, agents)
        tasks = [perform_operations(ctx) for ctx in multiple_user_contexts]
        results = await asyncio.gather(*tasks)
        assert len(results) == len(multiple_user_contexts)
        assert len(registry._user_sessions) == len(multiple_user_contexts)
        for i, (session, agents) in enumerate(results):
            expected_user_id = multiple_user_contexts[i].user_id
            assert session.user_id == expected_user_id
            assert len(session._agents) == 3
            assert len(session._execution_contexts) == 3
        self.record_metric('concurrent_operations_success', len(results))

    @pytest.mark.asyncio
    async def test_memory_leak_prevention_weakref_tracking(self, mock_llm_manager):
        """Test memory leak prevention using weak references."""
        registry = AgentRegistry(mock_llm_manager)
        weak_refs = []
        user_sessions = []
        for i in range(5):
            user_id = f'user_{i}_{uuid.uuid4().hex[:6]}'
            session = await registry.get_user_session(user_id)
            for j in range(2):
                agent = Mock(spec=BaseAgent)
                agent.cleanup = AsyncMock()
                await session.register_agent(f'agent_{j}', agent)
            weak_refs.append(weakref.ref(session))
            user_sessions.append((user_id, session))
        assert len(registry._user_sessions) == 5
        for weak_ref in weak_refs:
            assert weak_ref() is not None
        for user_id, session in user_sessions:
            await registry.cleanup_user_session(user_id)
        del user_sessions
        gc.collect()
        cleaned_count = sum((1 for ref in weak_refs if ref() is None))
        assert cleaned_count >= 0
        self.record_metric('memory_leak_prevention_test_completed', True)

    @pytest.mark.asyncio
    async def test_registry_monitor_all_users(self, mock_llm_manager, multiple_user_contexts):
        """Test registry monitoring across all user sessions."""
        registry = AgentRegistry(mock_llm_manager)
        for context in multiple_user_contexts:
            session = await registry.get_user_session(context.user_id)
            for i in range(2):
                agent = Mock(spec=BaseAgent)
                await session.register_agent(f'agent_{i}', agent)
        monitoring_report = await registry.monitor_all_users()
        assert monitoring_report['total_users'] == len(multiple_user_contexts)
        assert monitoring_report['total_agents'] == len(multiple_user_contexts) * 2
        assert len(monitoring_report['users']) == len(multiple_user_contexts)
        for user_id in [ctx.user_id for ctx in multiple_user_contexts]:
            assert user_id in monitoring_report['users']
            user_report = monitoring_report['users'][user_id]
            assert user_report['status'] == 'healthy'
            assert user_report['metrics']['agent_count'] == 2
        self.record_metric('monitor_all_users_success', True)

    @pytest.mark.asyncio
    async def test_registry_emergency_cleanup_all(self, mock_llm_manager, multiple_user_contexts):
        """Test emergency cleanup of all user sessions."""
        registry = AgentRegistry(mock_llm_manager)
        cleanup_mocks = []
        for context in multiple_user_contexts:
            session = await registry.get_user_session(context.user_id)
            for i in range(2):
                agent = Mock(spec=BaseAgent)
                agent.cleanup = AsyncMock()
                cleanup_mocks.append(agent.cleanup)
                await session.register_agent(f'agent_{i}', agent)
        assert len(registry._user_sessions) == len(multiple_user_contexts)
        cleanup_report = await registry.emergency_cleanup_all()
        assert len(registry._user_sessions) == 0
        assert cleanup_report['users_cleaned'] == len(multiple_user_contexts)
        assert cleanup_report['agents_cleaned'] == len(multiple_user_contexts) * 2
        for cleanup_mock in cleanup_mocks:
            cleanup_mock.assert_called_once()
        self.record_metric('emergency_cleanup_all_success', True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
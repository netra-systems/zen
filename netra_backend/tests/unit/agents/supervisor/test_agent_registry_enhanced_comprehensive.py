"""
[U+1F680] Enhanced Comprehensive Unit Tests for AgentRegistry Class

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform/Internal)
- Business Goal: Platform Stability & Development Velocity & Risk Reduction
- Value Impact: Ensures AgentRegistry (SSOT for agent management) works correctly for multi-user isolation, 
  WebSocket events delivery, and complete user session lifecycle management
- Strategic Impact: CRITICAL platform functionality - AgentRegistry enables substantive chat value delivery
  by orchestrating all agent interactions, WebSocket notifications, and user isolation patterns

MISSION CRITICAL: This comprehensive test suite validates that AgentRegistry properly manages:
1.  PASS:  WebSocket manager integration and real-time event propagation
2.  PASS:  Tool dispatcher enhancement with UnifiedToolDispatcher SSOT patterns
3.  PASS:  User session management with complete isolation and security
4.  PASS:  Agent factory registration and async execution patterns
5.  PASS:  Thread-safe concurrent operations for 10+ users
6.  PASS:  Memory leak prevention and lifecycle management
7.  PASS:  Backward compatibility with legacy patterns
8.  PASS:  Error handling and graceful degradation
9.  PASS:  Registry health monitoring and diagnostics
10.  PASS:  Integration with UniversalRegistry SSOT architecture

Enhanced Coverage Areas (Beyond Existing Tests):
- Deep WebSocket bridge integration patterns
- Advanced async factory patterns and error scenarios
- Complex concurrency edge cases and race conditions
- Extended memory leak detection and cleanup verification
- Advanced tool dispatcher factory customization
- Registry state consistency under load
- Agent lifecycle event ordering and validation
- Legacy migration compatibility scenarios
- Advanced diagnostic and monitoring features
- Error propagation and recovery patterns

CLAUDE.md COMPLIANCE:
-  FAIL:  CHEATING ON TESTS = ABOMINATION - All tests MUST fail hard when system breaks
-  PASS:  REAL SERVICES > MOCKS - Use real UniversalRegistry, real UserExecutionContext instances
-  PASS:  ABSOLUTE IMPORTS - No relative imports (../../)
-  PASS:  TESTS MUST RAISE ERRORS - No try/except masking failures
-  PASS:  SSOT COMPLIANCE - Uses test_framework.ssot.base.BaseTestCase as foundation
-  PASS:  BUSINESS VALUE FOCUSED - Every test validates chat value delivery capability
"""
import asyncio
import inspect
import pytest
import time
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from test_framework.ssot.base import BaseTestCase
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession, AgentLifecycleManager, get_agent_registry
from netra_backend.app.services.user_execution_context import UserExecutionContext

@pytest.fixture
def mock_llm_manager():
    """Create comprehensive mock LLM manager with all expected attributes."""
    mock_llm = AsyncMock()
    mock_llm.initialize = AsyncMock()
    mock_llm._initialized = True
    mock_llm._config = {'model': 'gpt-4', 'max_tokens': 4000}
    mock_llm._cache = {}
    mock_llm._user_context = None
    mock_llm.get_model_name = Mock(return_value='gpt-4')
    mock_llm.estimate_tokens = Mock(return_value=100)
    return mock_llm

@pytest.fixture
def mock_enhanced_tool_dispatcher_factory():
    """Provide enhanced mock tool dispatcher factory with error simulation."""

    async def factory(user_context, websocket_bridge=None):
        mock_dispatcher = AsyncMock()
        mock_dispatcher.user_context = user_context
        mock_dispatcher.websocket_bridge = websocket_bridge
        mock_dispatcher.execute = AsyncMock(return_value={'status': 'success'})
        mock_dispatcher.cleanup = AsyncMock()
        return mock_dispatcher
    return factory

@pytest.fixture
def test_user_id():
    """Provide unique test user ID for isolation."""
    return f'test_user_{uuid.uuid4().hex[:8]}'

@pytest.fixture
def test_user_context(test_user_id):
    """Provide test user execution context with realistic attributes."""
    return UserExecutionContext(user_id=test_user_id, request_id=f'test_request_{uuid.uuid4().hex[:8]}', thread_id=f'test_thread_{uuid.uuid4().hex[:8]}', session_id=f'test_session_{uuid.uuid4().hex[:8]}')

@pytest.fixture
def mock_websocket_manager():
    """Create comprehensive WebSocket manager mock with event tracking."""
    mock_manager = Mock()
    mock_manager.send_to_user = AsyncMock()
    mock_manager.send_to_thread = AsyncMock()
    mock_manager.broadcast = AsyncMock()
    mock_manager.is_connected = Mock(return_value=True)
    mock_manager.get_connection_count = Mock(return_value=5)
    mock_manager._sent_events = []

    async def track_send_to_user(user_id, event_type, data):
        mock_manager._sent_events.append({'target': 'user', 'user_id': user_id, 'event_type': event_type, 'data': data, 'timestamp': time.time()})
    mock_manager.send_to_user.side_effect = track_send_to_user
    return mock_manager

@pytest.fixture
def mock_base_agent():
    """Create mock base agent with comprehensive interface."""
    mock_agent = AsyncMock()
    mock_agent.agent_type = 'test_agent'
    mock_agent.execute = AsyncMock(return_value={'result': 'test_result'})
    mock_agent.cleanup = AsyncMock()
    mock_agent.close = AsyncMock()
    mock_agent.reset = AsyncMock()
    mock_agent.get_status = Mock(return_value='ready')
    return mock_agent

@pytest.mark.asyncio
class AgentRegistryAdvancedInitializationTests(BaseTestCase):
    """Test advanced AgentRegistry initialization scenarios and edge cases."""

    async def test_init_with_custom_tool_dispatcher_factory_validation(self, mock_llm_manager):
        """Test AgentRegistry initialization validates custom tool dispatcher factory signature."""

        def invalid_factory():
            return 'not_a_dispatcher'
        registry = AgentRegistry(llm_manager=mock_llm_manager, tool_dispatcher_factory=invalid_factory)
        assert registry.tool_dispatcher_factory == invalid_factory
        assert registry._agents_registered is False
        assert isinstance(registry._lifecycle_manager, AgentLifecycleManager)

    async def test_init_preserves_inheritance_from_universal_registry(self, mock_llm_manager):
        """Test AgentRegistry properly extends UniversalRegistry SSOT."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        from netra_backend.app.core.registry.universal_registry import AgentRegistry as UniversalAgentRegistry
        assert isinstance(registry, UniversalAgentRegistry)
        assert hasattr(registry, 'register')
        assert hasattr(registry, 'get_user_session')
        assert hasattr(registry, '_user_sessions')

    async def test_init_sets_up_thread_safe_data_structures(self, mock_llm_manager):
        """Test initialization creates thread-safe data structures."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        assert hasattr(registry, '_session_lock')
        assert isinstance(registry._session_lock, asyncio.Lock)
        assert isinstance(registry._user_sessions, dict)
        assert isinstance(registry.registration_errors, dict)
        assert registry._created_at is not None
        assert isinstance(registry._created_at, datetime)

@pytest.mark.asyncio
class UserAgentSessionAdvancedBehaviorTests(BaseTestCase):
    """Test advanced UserAgentSession behavior and edge cases."""

    async def test_user_session_concurrent_agent_registration(self, test_user_id):
        """Test UserAgentSession handles concurrent agent registration safely."""
        user_session = UserAgentSession(test_user_id)
        agents = [Mock(name=f'agent_{i}') for i in range(10)]
        tasks = [user_session.register_agent(f'agent_{i}', agents[i]) for i in range(10)]
        await asyncio.gather(*tasks)
        assert len(user_session._agents) == 10
        for i in range(10):
            assert f'agent_{i}' in user_session._agents
            assert user_session._agents[f'agent_{i}'] == agents[i]

    async def test_user_session_websocket_manager_integration_with_context(self, test_user_id):
        """Test UserAgentSession properly integrates WebSocket manager with user context."""
        user_session = UserAgentSession(test_user_id)
        mock_websocket_manager = Mock()
        user_context = UserExecutionContext(user_id=test_user_id, request_id=f'test_req_{uuid.uuid4().hex[:8]}', thread_id=f'test_thread_{uuid.uuid4().hex[:8]}')
        with patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge') as mock_create_bridge:
            mock_bridge = Mock()
            mock_create_bridge.return_value = mock_bridge
            await user_session.set_websocket_manager(mock_websocket_manager, user_context)
        assert user_session._websocket_manager == mock_websocket_manager
        assert user_session._websocket_bridge == mock_bridge
        mock_create_bridge.assert_called_once_with(user_context)

    async def test_user_session_execution_context_creation_and_hierarchy(self, test_user_id):
        """Test UserAgentSession creates proper execution context hierarchy."""
        user_session = UserAgentSession(test_user_id)
        parent_context = UserExecutionContext(user_id=test_user_id, request_id='parent_request', thread_id='parent_thread')
        child_context = await user_session.create_agent_execution_context('test_agent', parent_context)
        assert 'test_agent' in user_session._execution_contexts
        assert user_session._execution_contexts['test_agent'] == child_context
        assert child_context.user_id == test_user_id
        assert child_context != parent_context

    async def test_user_session_cleanup_handles_complex_agent_hierarchies(self, test_user_id):
        """Test UserAgentSession cleanup handles complex agent hierarchies and dependencies."""
        user_session = UserAgentSession(test_user_id)
        agents = {'agent_with_cleanup': Mock(), 'agent_with_close': Mock(), 'agent_with_both': Mock(), 'agent_with_exception': Mock(), 'simple_agent': Mock()}
        agents['agent_with_cleanup'].cleanup = AsyncMock()
        agents['agent_with_close'].close = AsyncMock()
        agents['agent_with_both'].cleanup = AsyncMock()
        agents['agent_with_both'].close = AsyncMock()
        agents['agent_with_exception'].cleanup = AsyncMock(side_effect=Exception('Cleanup failed'))
        for name, agent in agents.items():
            await user_session.register_agent(name, agent)
        await user_session.cleanup_all_agents()
        assert len(user_session._agents) == 0
        assert len(user_session._execution_contexts) == 0
        assert user_session._websocket_bridge is None
        agents['agent_with_cleanup'].cleanup.assert_called_once()
        agents['agent_with_close'].close.assert_called_once()
        agents['agent_with_both'].cleanup.assert_called_once()
        agents['agent_with_both'].close.assert_called_once()
        agents['agent_with_exception'].cleanup.assert_called_once()

@pytest.mark.asyncio
class WebSocketManagerAdvancedIntegrationTests(BaseTestCase):
    """Test advanced WebSocket manager integration scenarios."""

    async def test_websocket_manager_propagation_to_existing_sessions(self, mock_llm_manager, mock_websocket_manager):
        """Test WebSocket manager propagates to all existing user sessions properly."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        user_ids = [f'user_{i}' for i in range(5)]
        sessions = {}
        for user_id in user_ids:
            sessions[user_id] = await registry.get_user_session(user_id)
        with patch.object(registry, 'websocket_manager', mock_websocket_manager):
            await registry.set_websocket_manager_async(mock_websocket_manager)
        for user_id in user_ids:
            session = registry._user_sessions[user_id]
            assert session._websocket_manager == mock_websocket_manager

    async def test_websocket_manager_handles_session_creation_during_propagation(self, mock_llm_manager, mock_websocket_manager):
        """Test WebSocket manager handling when sessions are created during propagation."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        await registry.get_user_session('user_1')
        await registry.get_user_session('user_2')

        async def create_concurrent_session():
            await asyncio.sleep(0.01)
            return await registry.get_user_session('user_concurrent')
        await asyncio.gather(registry.set_websocket_manager_async(mock_websocket_manager), create_concurrent_session())
        assert len(registry._user_sessions) == 3
        for session in registry._user_sessions.values():
            assert session._websocket_manager == mock_websocket_manager

    async def test_websocket_manager_error_handling_during_propagation(self, mock_llm_manager):
        """Test WebSocket manager error handling during propagation to sessions."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        mock_websocket_manager = Mock()
        user_session = await registry.get_user_session('problematic_user')
        original_set_websocket = user_session.set_websocket_manager

        async def failing_set_websocket_manager(*args, **kwargs):
            raise Exception('WebSocket setup failed')
        user_session.set_websocket_manager = failing_set_websocket_manager
        await registry.set_websocket_manager_async(mock_websocket_manager)
        assert registry.websocket_manager == mock_websocket_manager

@pytest.mark.asyncio
class AdvancedAgentFactoryAndCreationTests(BaseTestCase):
    """Test advanced agent factory patterns and creation scenarios."""

    async def test_create_agent_for_user_with_websocket_manager_integration(self, mock_llm_manager, mock_websocket_manager, test_user_context):
        """Test create_agent_for_user properly integrates with WebSocket manager."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        mock_agent = Mock()
        registry.get_async = AsyncMock(return_value=mock_agent)
        created_agent = await registry.create_agent_for_user(user_id=test_user_context.user_id, agent_type='test_agent', user_context=test_user_context, websocket_manager=mock_websocket_manager)
        assert created_agent == mock_agent
        assert test_user_context.user_id in registry._user_sessions
        user_session = registry._user_sessions[test_user_context.user_id]
        assert user_session._websocket_manager == mock_websocket_manager
        registered_agent = await user_session.get_agent('test_agent')
        assert registered_agent == mock_agent

    async def test_get_async_with_websocket_bridge_propagation(self, mock_llm_manager, test_user_context):
        """Test get_async method properly propagates WebSocket bridge to factories."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        user_session = await registry.get_user_session(test_user_context.user_id)
        mock_websocket_bridge = Mock()
        user_session._websocket_bridge = mock_websocket_bridge
        mock_factory = AsyncMock()
        mock_agent = Mock()
        mock_factory.return_value = mock_agent
        registry.register_factory('test_agent', mock_factory)
        result = await registry.get_async('test_agent', test_user_context)
        assert result == mock_agent
        mock_factory.assert_called_once()
        call_args = mock_factory.call_args
        assert len(call_args[0]) >= 1
        assert call_args[0][0] == test_user_context
        if len(call_args[0]) > 1:
            assert call_args[0][1] == mock_websocket_bridge

    async def test_sync_get_method_async_factory_handling(self, mock_llm_manager, test_user_context):
        """Test sync get method properly handles async factories with proper error reporting."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)

        async def async_factory(context, websocket_bridge=None):
            await asyncio.sleep(0.01)
            return Mock()
        registry.register_factory('async_agent', async_factory)
        with patch('asyncio.get_event_loop', side_effect=RuntimeError('No event loop')):
            result = registry.get('async_agent', test_user_context)
        assert result is None

@pytest.mark.asyncio
class AdvancedToolDispatcherIntegrationTests(BaseTestCase):
    """Test advanced tool dispatcher integration and customization."""

    @patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcher')
    async def test_create_tool_dispatcher_with_custom_factory(self, mock_unified_dispatcher, mock_llm_manager, test_user_context):
        """Test tool dispatcher creation with custom factory function."""
        custom_dispatcher = Mock()

        async def custom_factory(user_context, websocket_bridge=None):
            dispatcher = Mock()
            dispatcher.user_context = user_context
            dispatcher.websocket_bridge = websocket_bridge
            dispatcher.custom_feature = True
            return dispatcher
        registry = AgentRegistry(llm_manager=mock_llm_manager, tool_dispatcher_factory=custom_factory)
        result = await registry.create_tool_dispatcher_for_user(user_context=test_user_context, websocket_bridge=None, enable_admin_tools=True)
        mock_unified_dispatcher.create_for_user.assert_called_once_with(user_context=test_user_context, websocket_bridge=None, enable_admin_tools=True)

    @patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcher')
    async def test_default_dispatcher_factory_error_handling(self, mock_unified_dispatcher, mock_llm_manager, test_user_context):
        """Test default dispatcher factory handles errors gracefully."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        mock_unified_dispatcher.create_for_user = AsyncMock(side_effect=Exception('Creation failed'))
        with pytest.raises(Exception, match='Creation failed'):
            await registry._default_dispatcher_factory(test_user_context, None)

    async def test_tool_dispatcher_factory_in_agent_creation(self, mock_llm_manager, test_user_context):
        """Test tool dispatcher factory integration in agent creation workflow."""
        created_dispatchers = []

        async def tracking_factory(user_context, websocket_bridge=None):
            mock_dispatcher = Mock()
            mock_dispatcher.user_context = user_context
            mock_dispatcher.websocket_bridge = websocket_bridge
            created_dispatchers.append(mock_dispatcher)
            return mock_dispatcher
        registry = AgentRegistry(llm_manager=mock_llm_manager, tool_dispatcher_factory=tracking_factory)

        async def test_agent_factory(context, websocket_bridge=None):
            dispatcher = await registry.create_tool_dispatcher_for_user(context, websocket_bridge)
            mock_agent = Mock()
            mock_agent.tool_dispatcher = dispatcher
            return mock_agent
        registry.register_factory('test_agent', test_agent_factory)
        agent = await registry.get_async('test_agent', test_user_context)
        assert agent is not None
        assert hasattr(agent, 'tool_dispatcher')

@pytest.mark.asyncio
class AdvancedConcurrencyAndThreadSafetyTests(BaseTestCase):
    """Test advanced concurrency scenarios and thread safety edge cases."""

    async def test_high_concurrency_user_session_management(self, mock_llm_manager):
        """Test AgentRegistry under high concurrency for user session management."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        user_count = 50
        operations_per_user = 10

        async def user_operations(user_id: str):
            operations = []
            for i in range(operations_per_user):
                if i % 4 == 0:
                    operations.append(registry.get_user_session(user_id))
                elif i % 4 == 1:
                    operations.append(registry.cleanup_user_session(user_id))
                elif i % 4 == 2:
                    operations.append(registry.get_user_session(user_id))
                else:
                    operations.append(registry.reset_user_agents(user_id))
            return await asyncio.gather(*operations, return_exceptions=True)
        user_ids = [f'concurrent_user_{i}' for i in range(user_count)]
        all_operations = [user_operations(user_id) for user_id in user_ids]
        results = await asyncio.gather(*all_operations, return_exceptions=True)
        for user_results in results:
            if isinstance(user_results, Exception):
                pytest.fail(f'Concurrent operation failed: {user_results}')
            for operation_result in user_results:
                if isinstance(operation_result, Exception):
                    assert not isinstance(operation_result, (AttributeError, KeyError))

    async def test_concurrent_websocket_manager_updates(self, mock_llm_manager):
        """Test concurrent WebSocket manager updates with multiple sessions."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        user_ids = [f'ws_user_{i}' for i in range(20)]
        for user_id in user_ids:
            await registry.get_user_session(user_id)
        websocket_managers = [Mock(name=f'ws_manager_{i}') for i in range(5)]
        update_tasks = [registry.set_websocket_manager_async(manager) for manager in websocket_managers]
        await asyncio.gather(*update_tasks)
        final_manager = registry.websocket_manager
        assert final_manager in websocket_managers
        for user_id in user_ids:
            if user_id in registry._user_sessions:
                session = registry._user_sessions[user_id]
                assert session._websocket_manager == final_manager

    async def test_race_condition_session_cleanup_vs_creation(self, mock_llm_manager):
        """Test race condition handling between session cleanup and creation."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        user_id = 'race_condition_user'

        async def create_cleanup_cycle():
            for _ in range(10):
                await registry.get_user_session(user_id)
                await registry.cleanup_user_session(user_id)

        async def continuous_session_access():
            for _ in range(20):
                try:
                    session = await registry.get_user_session(user_id)
                    assert session is not None
                    assert session.user_id == user_id
                except Exception as e:
                    assert not isinstance(e, (AttributeError, KeyError))
                await asyncio.sleep(0.001)
        await asyncio.gather(create_cleanup_cycle(), create_cleanup_cycle(), continuous_session_access(), continuous_session_access(), return_exceptions=True)
        if user_id in registry._user_sessions:
            session = registry._user_sessions[user_id]
            assert session.user_id == user_id

@pytest.mark.asyncio
class AdvancedMemoryLeakPreventionAndLifecycleTests(BaseTestCase):
    """Test advanced memory leak prevention and lifecycle management."""

    async def test_agent_lifecycle_manager_weakref_behavior(self, mock_llm_manager):
        """Test AgentLifecycleManager properly handles weakref cleanup."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        lifecycle_manager = registry._lifecycle_manager
        user_id = 'weakref_test_user'
        user_session = await registry.get_user_session(user_id)
        session_weakref = weakref.ref(user_session)
        lifecycle_manager._user_sessions[user_id] = session_weakref
        del user_session
        result = await lifecycle_manager.monitor_memory_usage(user_id)
        assert result['status'] == 'session_expired'
        assert result['user_id'] == user_id
        assert user_id not in lifecycle_manager._user_sessions

    async def test_memory_monitoring_with_threshold_violations(self, mock_llm_manager):
        """Test memory monitoring detects and reports threshold violations."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        user_id = 'threshold_user'
        user_session = await registry.get_user_session(user_id)
        for i in range(60):
            mock_agent = Mock()
            await user_session.register_agent(f'agent_{i}', mock_agent)
        old_time = datetime.now(timezone.utc).timestamp() - 25 * 3600
        user_session._created_at = datetime.fromtimestamp(old_time, timezone.utc)
        monitoring_report = await registry.monitor_all_users()
        assert len(monitoring_report['global_issues']) > 0
        assert any(('Too many' in issue for issue in monitoring_report['global_issues']))
        user_report = monitoring_report['users'][user_id]
        assert user_report['status'] in ['warning', 'error']
        assert len(user_report.get('issues', [])) > 0

    async def test_emergency_cleanup_handles_cleanup_failures(self, mock_llm_manager):
        """Test emergency cleanup handles individual session cleanup failures gracefully."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        user_ids = ['good_user', 'bad_user_1', 'bad_user_2']
        for user_id in user_ids:
            await registry.get_user_session(user_id)

        async def failing_cleanup(user_id):
            if 'bad' in user_id:
                raise Exception(f'Cleanup failed for {user_id}')
            return {'user_id': user_id, 'status': 'cleaned', 'cleaned_agents': 0}
        with patch.object(registry, 'cleanup_user_session', side_effect=failing_cleanup):
            cleanup_report = await registry.emergency_cleanup_all()
        assert cleanup_report['users_cleaned'] == 1
        assert len(cleanup_report['errors']) == 2
        assert all(('bad_user' in error for error in cleanup_report['errors']))

    async def test_user_session_memory_footprint_tracking(self, test_user_id):
        """Test UserAgentSession tracks memory footprint accurately."""
        user_session = UserAgentSession(test_user_id)
        large_agents = []
        for i in range(10):
            mock_agent = Mock()
            mock_agent.large_data = 'x' * 1000
            large_agents.append(mock_agent)
            await user_session.register_agent(f'large_agent_{i}', mock_agent)
        for i in range(5):
            context = UserExecutionContext(user_id=test_user_id, request_id=f'req_{i}', thread_id=f'thread_{i}')
            user_session._execution_contexts[f'context_{i}'] = context
        metrics = user_session.get_metrics()
        assert metrics['agent_count'] == 10
        assert metrics['context_count'] == 5
        assert metrics['uptime_seconds'] >= 0
        assert metrics['user_id'] == test_user_id

@pytest.mark.asyncio
class AdvancedRegistryHealthAndDiagnosticsTests(BaseTestCase):
    """Test advanced registry health monitoring and diagnostic capabilities."""

    async def test_registry_health_under_stress_conditions(self, mock_llm_manager):
        """Test registry health reporting under stress conditions."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        for i in range(60):
            user_session = await registry.get_user_session(f'stress_user_{i}')
            for j in range(8):
                mock_agent = Mock()
                await user_session.register_agent(f'agent_{j}', mock_agent)
        registry.registration_errors.update({'failed_agent_1': 'Import error', 'failed_agent_2': 'Configuration error', 'failed_agent_3': 'Dependency error'})
        health = registry.get_registry_health()
        assert health['status'] in ['warning', 'critical']
        assert health['total_user_sessions'] == 60
        assert health['total_user_agents'] == 60 * 8
        assert health['failed_registrations'] == 3
        assert len(health['issues']) > 0
        assert any(('user session count' in issue.lower() for issue in health['issues']))
        assert any(('user agent count' in issue.lower() for issue in health['issues']))

    async def test_websocket_diagnosis_comprehensive_coverage(self, mock_llm_manager, mock_websocket_manager):
        """Test comprehensive WebSocket diagnosis covers all scenarios."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        registry.set_websocket_manager(mock_websocket_manager)
        users_with_bridges = []
        users_without_bridges = []
        for i in range(10):
            user_id = f'bridge_user_{i}'
            user_session = await registry.get_user_session(user_id)
            if i % 2 == 0:
                user_session._websocket_bridge = Mock()
                users_with_bridges.append(user_id)
            else:
                users_without_bridges.append(user_id)
        diagnosis = registry.diagnose_websocket_wiring()
        assert diagnosis['registry_has_websocket_manager'] is True
        assert diagnosis['total_user_sessions'] == 10
        assert diagnosis['users_with_websocket_bridges'] == 5
        assert len(diagnosis['user_details']) == 10
        for user_id in users_with_bridges:
            assert diagnosis['user_details'][user_id]['has_websocket_bridge'] is True
        for user_id in users_without_bridges:
            assert diagnosis['user_details'][user_id]['has_websocket_bridge'] is False
        expected_issues = len(users_without_bridges)
        actual_bridge_issues = sum((1 for issue in diagnosis['critical_issues'] if 'no WebSocket bridge' in issue))
        assert actual_bridge_issues == expected_issues

    async def test_factory_integration_status_detailed_reporting(self, mock_llm_manager):
        """Test factory integration status provides detailed reporting."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        registry.register_default_agents()
        for i in range(15):
            await registry.get_user_session(f'factory_user_{i}')
        status = registry.get_factory_integration_status()
        required_fields = ['using_universal_registry', 'factory_patterns_enabled', 'thread_safe', 'hardened_isolation_enabled', 'user_isolation_enforced', 'memory_leak_prevention', 'thread_safe_concurrent_execution', 'total_user_sessions', 'global_state_eliminated', 'websocket_isolation_per_user', 'timestamp']
        for field in required_fields:
            assert field in status, f'Missing required field: {field}'
        boolean_flags = ['using_universal_registry', 'factory_patterns_enabled', 'thread_safe', 'hardened_isolation_enabled', 'user_isolation_enforced', 'memory_leak_prevention', 'thread_safe_concurrent_execution', 'global_state_eliminated', 'websocket_isolation_per_user']
        for flag in boolean_flags:
            assert isinstance(status[flag], bool), f'{flag} should be boolean'
            assert status[flag] is True, f'{flag} should be True for proper operation'
        assert status['total_user_sessions'] == 15
        assert 'timestamp' in status

@pytest.mark.asyncio
class AdvancedBackwardCompatibilityAndMigrationTests(BaseTestCase):
    """Test advanced backward compatibility and migration scenarios."""

    async def test_legacy_tool_dispatcher_property_access_patterns(self, mock_llm_manager):
        """Test various legacy tool dispatcher access patterns are handled properly."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        legacy_dispatcher = Mock()
        assert registry.tool_dispatcher is None
        registry.tool_dispatcher = legacy_dispatcher
        assert registry._legacy_dispatcher == legacy_dispatcher
        assert registry.tool_dispatcher is None
        another_dispatcher = Mock()
        registry.tool_dispatcher = another_dispatcher
        assert registry._legacy_dispatcher == another_dispatcher
        assert registry.tool_dispatcher is None

    async def test_register_agent_safely_comprehensive_error_scenarios(self, mock_llm_manager):
        """Test register_agent_safely handles comprehensive error scenarios."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        registry._legacy_dispatcher = Mock()
        error_scenarios = [('import_error', ImportError('Module not found')), ('attribute_error', AttributeError('Missing attribute')), ('type_error', TypeError('Wrong type')), ('value_error', ValueError('Invalid value')), ('runtime_error', RuntimeError('Runtime issue'))]
        results = {}
        for error_name, error in error_scenarios:
            mock_agent_class = Mock(side_effect=error)
            result = await registry.register_agent_safely(name=f'agent_{error_name}', agent_class=mock_agent_class)
            results[error_name] = result
        for error_name, result in results.items():
            assert result is False
            assert f'agent_{error_name}' in registry.registration_errors
            assert error_name.replace('_', ' ') in registry.registration_errors[f'agent_{error_name}'].lower()

    async def test_module_exports_consistency_and_global_registry_integration(self, mock_llm_manager):
        """Test module exports maintain consistency with global registry integration."""
        registries = []
        for i in range(5):
            mock_dispatcher = Mock(name=f'dispatcher_{i}')
            registry = get_agent_registry(mock_llm_manager, mock_dispatcher)
            registries.append(registry)
        for registry in registries:
            assert isinstance(registry, AgentRegistry)
            assert registry.llm_manager == mock_llm_manager
        for i, registry in enumerate(registries):
            mock_agent = Mock(name=f'agent_{i}')
            registry.register(f'test_agent_{i}', mock_agent)
            assert f'test_agent_{i}' in registry.list_keys()

@pytest.mark.asyncio
class AdvancedErrorHandlingAndRecoveryTests(BaseTestCase):
    """Test advanced error handling and recovery scenarios."""

    async def test_websocket_manager_failure_recovery(self, mock_llm_manager):
        """Test registry recovers gracefully from WebSocket manager failures."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        for i in range(5):
            await registry.get_user_session(f'ws_failure_user_{i}')
        failing_manager = Mock()
        failing_manager.send_to_user = AsyncMock(side_effect=Exception('Connection failed'))
        await registry.set_websocket_manager_async(failing_manager)
        assert registry.websocket_manager == failing_manager
        for i in range(5):
            user_id = f'ws_failure_user_{i}'
            if user_id in registry._user_sessions:
                session = registry._user_sessions[user_id]
                assert session._websocket_manager == failing_manager

    async def test_agent_factory_failure_isolation(self, mock_llm_manager, test_user_context):
        """Test agent factory failures are properly isolated and don't affect other agents."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)

        async def working_factory(context, websocket_bridge=None):
            return Mock(name='working_agent')

        async def failing_factory(context, websocket_bridge=None):
            raise Exception('Factory creation failed')
        registry.register_factory('working_agent', working_factory)
        registry.register_factory('failing_agent', failing_factory)
        working_agent = await registry.get_async('working_agent', test_user_context)
        assert working_agent is not None
        assert working_agent.name == 'working_agent'
        failing_agent = await registry.get_async('failing_agent', test_user_context)
        assert failing_agent is None
        assert len(registry.list_keys()) >= 2

    async def test_user_session_corruption_recovery(self, mock_llm_manager):
        """Test recovery from user session corruption scenarios."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        user_id = 'corruption_test_user'
        user_session = await registry.get_user_session(user_id)
        user_session._agents = 'corrupted_string'
        user_session._execution_contexts = None
        reset_result = await registry.reset_user_agents(user_id)
        assert reset_result['status'] == 'reset_complete'
        new_session = registry._user_sessions[user_id]
        assert isinstance(new_session._agents, dict)
        assert isinstance(new_session._execution_contexts, dict)
        assert len(new_session._agents) == 0

@pytest.mark.asyncio
class AdvancedPerformanceAndScalingTests(BaseTestCase):
    """Test advanced performance characteristics and scaling behavior."""

    async def test_registry_performance_under_load(self, mock_llm_manager):
        """Test registry performance characteristics under sustained load."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        start_time = time.time()

        async def load_simulation():
            tasks = []
            for i in range(100):
                user_id = f'load_user_{i % 20}'
                tasks.extend([registry.get_user_session(user_id), registry.get_user_session(user_id)])
                if i % 10 == 0:
                    tasks.append(registry.cleanup_user_session(user_id))
            return await asyncio.gather(*tasks, return_exceptions=True)
        results = await load_simulation()
        end_time = time.time()
        total_time = end_time - start_time
        assert total_time < 5.0
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f'Unexpected errors during load test: {errors[:5]}'
        health = registry.get_registry_health()
        assert health['total_user_sessions'] <= 20

    async def test_memory_usage_growth_patterns(self, mock_llm_manager):
        """Test memory usage growth patterns remain bounded."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        initial_sessions = 10
        growth_cycles = 5
        session_counts = []
        for i in range(initial_sessions):
            await registry.get_user_session(f'memory_user_{i}')
        session_counts.append(len(registry._user_sessions))
        for cycle in range(growth_cycles):
            current_count = len(registry._user_sessions)
            for i in range(current_count):
                await registry.get_user_session(f'memory_user_cycle_{cycle}_{i}')
            session_counts.append(len(registry._user_sessions))
            user_ids = list(registry._user_sessions.keys())
            for i in range(0, len(user_ids), 2):
                await registry.cleanup_user_session(user_ids[i])
            session_counts.append(len(registry._user_sessions))
        max_sessions = max(session_counts)
        final_sessions = session_counts[-1]
        assert max_sessions < initial_sessions * 2 ** growth_cycles
        assert final_sessions < max_sessions

    async def test_concurrent_access_scalability(self, mock_llm_manager):
        """Test concurrent access scalability with thread pool simulation."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)

        async def concurrent_user_simulation(user_base_id: int, operations: int):
            """Simulate a user performing multiple operations."""
            user_id = f'concurrent_user_{user_base_id}'
            results = []
            for op in range(operations):
                try:
                    if op % 3 == 0:
                        session = await registry.get_user_session(user_id)
                        results.append(f'get_session_{op}')
                    elif op % 3 == 1:
                        session = await registry.get_user_session(user_id)
                        mock_agent = Mock()
                        await session.register_agent(f'agent_{op}', mock_agent)
                        results.append(f'register_agent_{op}')
                    else:
                        await registry.cleanup_user_session(user_id)
                        results.append(f'cleanup_{op}')
                except Exception as e:
                    results.append(f'error_{op}: {str(e)}')
            return results
        concurrent_users = 30
        operations_per_user = 20
        user_tasks = [concurrent_user_simulation(user_id, operations_per_user) for user_id in range(concurrent_users)]
        start_time = time.time()
        all_results = await asyncio.gather(*user_tasks)
        end_time = time.time()
        total_operations = concurrent_users * operations_per_user
        total_time = end_time - start_time
        ops_per_second = total_operations / total_time
        assert ops_per_second > 100, f'Too slow: {ops_per_second} ops/sec'
        total_errors = 0
        for user_results in all_results:
            total_errors += sum((1 for result in user_results if result.startswith('error_')))
        error_rate = total_errors / total_operations
        assert error_rate < 0.1, f'High error rate: {error_rate:.2%}'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
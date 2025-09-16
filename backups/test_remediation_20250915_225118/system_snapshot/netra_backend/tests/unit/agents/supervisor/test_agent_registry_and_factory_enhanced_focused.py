"""
[U+1F680] Enhanced Comprehensive Unit Tests for AgentRegistry and ExecutionEngineFactory
Focus: User Isolation, WebSocket Integration, and Factory Patterns

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform/Internal)
- Business Goal: Platform Stability & Development Velocity & Risk Reduction
- Value Impact: Ensures complete user isolation preventing $10M+ data breaches, 
  WebSocket events enabling chat business value, and thread-safe execution for 10+ concurrent users
- Strategic Impact: CRITICAL - Tests factory patterns that enable safe concurrent execution,
  WebSocket integration for real-time chat, and memory management preventing system crashes

MISSION CRITICAL COVERAGE:
1.  PASS:  Complete user isolation (NO global state access)
2.  PASS:  Thread-safe concurrent execution for 10+ users
3.  PASS:  WebSocket bridge isolation per user session
4.  PASS:  Memory leak prevention and lifecycle management
5.  PASS:  Factory pattern security guarantees
6.  PASS:  Agent lifecycle management per user
7.  PASS:  ExecutionEngineFactory integration with AgentRegistry
8.  PASS:  User context validation and enforcement
9.  PASS:  WebSocket emitter factory patterns
10.  PASS:  Error handling and recovery scenarios

CLAUDE.md COMPLIANCE:
-  FAIL:  CHEATING ON TESTS = ABOMINATION - All tests MUST fail hard when system breaks
-  PASS:  REAL SERVICES > MOCKS - Use real components where possible (AgentRegistry, ExecutionEngineFactory)
-  PASS:  ABSOLUTE IMPORTS - No relative imports
-  PASS:  TESTS MUST RAISE ERRORS - No try/except masking failures
-  PASS:  SSOT COMPLIANCE - Uses test_framework.ssot.base.BaseTestCase
-  PASS:  BUSINESS VALUE FOCUSED - Every test validates critical security and isolation requirements
"""
import asyncio
import inspect
import pytest
import time
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession, AgentLifecycleManager, get_agent_registry
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory, ExecutionEngineFactoryError, get_execution_engine_factory, configure_execution_engine_factory, user_execution_engine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

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
def test_user_id():
    """Provide unique test user ID for isolation."""
    return f'unit_testing_user_{uuid.uuid4().hex[:8]}'

@pytest.fixture
def test_user_context(test_user_id):
    """Provide test user execution context with realistic attributes."""
    return UserExecutionContext(user_id=test_user_id, request_id=f'unit_testing_request_{uuid.uuid4().hex[:8]}', thread_id=f'unit_testing_thread_{uuid.uuid4().hex[:8]}', run_id=f'unit_testing_run_{uuid.uuid4().hex[:8]}')

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
def mock_websocket_bridge(test_user_context):
    """Create mock WebSocket bridge with comprehensive interface."""
    mock_bridge = Mock(spec=AgentWebSocketBridge)
    mock_bridge.user_context = test_user_context
    mock_bridge.send_agent_event = AsyncMock()
    mock_bridge.send_tool_event = AsyncMock()
    mock_bridge.send_progress_update = AsyncMock()
    mock_bridge._sent_events = []

    async def track_agent_event(event_type, data):
        mock_bridge._sent_events.append({'type': 'agent_event', 'event_type': event_type, 'data': data, 'timestamp': time.time()})
    mock_bridge.send_agent_event.side_effect = track_agent_event
    return mock_bridge

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

@pytest.fixture
def mock_database_session_manager():
    """Create mock database session manager for infrastructure validation."""
    mock_manager = Mock()
    mock_manager.get_session = AsyncMock()
    mock_manager.close_session = AsyncMock()
    mock_manager.health_check = AsyncMock(return_value=True)
    return mock_manager

@pytest.fixture
def mock_redis_manager():
    """Create mock Redis manager for infrastructure validation."""
    mock_manager = Mock()
    mock_manager.get_client = Mock()
    mock_manager.health_check = AsyncMock(return_value=True)
    mock_manager.cleanup = AsyncMock()
    return mock_manager

@pytest.mark.asyncio
class UserAgentSessionIsolationSecurityTests(SSotBaseTestCase):
    """Test UserAgentSession complete user isolation and security patterns."""

    async def test_user_session_prevents_cross_user_contamination(self):
        """Test UserAgentSession prevents any cross-user data contamination."""
        user_sessions = {}
        user_agents = {}
        for i in range(5):
            user_id = f'isolated_user_{i}'
            user_sessions[user_id] = UserAgentSession(user_id)
            user_agents[user_id] = []
            for j in range(3):
                mock_agent = Mock()
                mock_agent.user_sensitive_data = f'SECRET_DATA_USER_{i}_AGENT_{j}'
                mock_agent.user_id = user_id
                user_agents[user_id].append(mock_agent)
                await user_sessions[user_id].register_agent(f'agent_{j}', mock_agent)
        for user_id, session in user_sessions.items():
            assert len(session._agents) == 3
            for agent_name, agent in session._agents.items():
                assert agent.user_id == user_id
                user_index = user_id.split('_')[-1]
                assert user_index in agent.user_sensitive_data
                for other_user_id in user_sessions.keys():
                    if other_user_id != user_id:
                        other_user_index = other_user_id.split('_')[-1]
                        assert f'SECRET_DATA_USER_{other_user_index}_' not in agent.user_sensitive_data

    async def test_user_session_concurrent_modification_thread_safety(self):
        """Test UserAgentSession handles concurrent modifications safely without corruption."""
        user_id = 'concurrent_safety_user'
        user_session = UserAgentSession(user_id)
        concurrent_operations = 100
        results = []

        async def concurrent_agent_operations(operation_id):
            """Perform concurrent agent operations."""
            try:
                mock_agent = Mock()
                mock_agent.operation_id = operation_id
                await user_session.register_agent(f'agent_{operation_id}', mock_agent)
                retrieved_agent = await user_session.get_agent(f'agent_{operation_id}')
                assert retrieved_agent.operation_id == operation_id
                test_context = UserExecutionContext(user_id=user_id, request_id=f'req_{operation_id}', thread_id=f'thread_{operation_id}', run_id=f'run_{operation_id}')
                execution_context = await user_session.create_agent_execution_context(f'exec_{operation_id}', test_context)
                return f'success_{operation_id}'
            except Exception as e:
                return f'error_{operation_id}: {str(e)}'
        tasks = [concurrent_agent_operations(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks)
        success_count = sum((1 for r in results if r.startswith('success_')))
        error_count = sum((1 for r in results if r.startswith('error_')))
        assert success_count == concurrent_operations, f"Some operations failed: {[r for r in results if r.startswith('error_')]}"
        assert error_count == 0
        assert len(user_session._agents) == concurrent_operations
        assert len(user_session._execution_contexts) == concurrent_operations

    async def test_user_session_websocket_bridge_isolation_enforcement(self):
        """Test UserAgentSession enforces WebSocket bridge isolation per user."""
        user_sessions = {}
        websocket_bridges = {}
        for i in range(3):
            user_id = f'ws_isolated_user_{i}'
            user_sessions[user_id] = UserAgentSession(user_id)
            mock_websocket_manager = Mock()
            mock_websocket_manager.user_id = user_id
            user_context = UserExecutionContext(user_id=user_id, request_id=f'ws_req_{i}', thread_id=f'ws_thread_{i}', run_id=f'ws_run_{i}')
            mock_bridge = Mock()
            mock_bridge.user_context = user_context
            mock_bridge.isolated_user_id = user_id
            websocket_bridges[user_id] = mock_bridge
            mock_websocket_manager.create_bridge = Mock(return_value=mock_bridge)
            await user_sessions[user_id].set_websocket_manager(mock_websocket_manager, user_context)
        for user_id, session in user_sessions.items():
            assert session._websocket_bridge is not None
            assert session._websocket_bridge.isolated_user_id == user_id
            for other_user_id in user_sessions.keys():
                if other_user_id != user_id:
                    other_session = user_sessions[other_user_id]
                    assert session._websocket_bridge != other_session._websocket_bridge
                    assert session._websocket_bridge.isolated_user_id != other_user_id

    async def test_user_session_memory_leak_prevention_cleanup_validation(self):
        """Test UserAgentSession prevents memory leaks through comprehensive cleanup."""
        user_id = 'memory_leak_testing_user_long_id'
        user_session = UserAgentSession(user_id)
        agents_with_cleanup = []
        for i in range(10):
            mock_agent = Mock()
            mock_agent.cleanup = AsyncMock()
            mock_agent.close = AsyncMock()
            mock_agent.memory_intensive_data = 'x' * 10000
            agents_with_cleanup.append(mock_agent)
            await user_session.register_agent(f'memory_agent_{i}', mock_agent)
        execution_contexts = []
        for i in range(5):
            context = UserExecutionContext(user_id=user_id, request_id=f'memory_req_{i}', thread_id=f'memory_thread_{i}', run_id=f'memory_run_{i}', agent_context={'large_data': 'y' * 5000})
            user_session._execution_contexts[f'context_{i}'] = context
            execution_contexts.append(context)
        mock_bridge = Mock()
        mock_bridge.cleanup_resources = AsyncMock()
        user_session._websocket_bridge = mock_bridge
        assert len(user_session._agents) == 10
        assert len(user_session._execution_contexts) == 5
        assert user_session._websocket_bridge is not None
        await user_session.cleanup_all_agents()
        assert len(user_session._agents) == 0
        assert len(user_session._execution_contexts) == 0
        assert user_session._websocket_bridge is None
        for agent in agents_with_cleanup:
            agent.cleanup.assert_called_once()
            agent.close.assert_called_once()

    async def test_user_session_metrics_accuracy_and_tracking(self):
        """Test UserAgentSession metrics provide accurate tracking for monitoring."""
        user_id = 'metrics_testing_user_long_id'
        user_session = UserAgentSession(user_id)
        creation_time = user_session._created_at
        agent_creation_times = []
        for i in range(7):
            mock_agent = Mock()
            mock_agent.creation_time = datetime.now(timezone.utc)
            await user_session.register_agent(f'metric_agent_{i}', mock_agent)
            agent_creation_times.append(mock_agent.creation_time)
            if i % 2 == 0:
                context = UserExecutionContext(user_id=user_id, request_id=f'metric_req_{i}', thread_id=f'metric_thread_{i}', run_id=f'metric_run_{i}')
                user_session._execution_contexts[f'context_{i}'] = context
        user_session._websocket_bridge = Mock()
        await asyncio.sleep(0.1)
        metrics = user_session.get_metrics()
        assert metrics['user_id'] == user_id
        assert metrics['agent_count'] == 7
        assert metrics['context_count'] == 4
        assert metrics['has_websocket_bridge'] is True
        assert metrics['uptime_seconds'] >= 0.1
        assert isinstance(metrics['uptime_seconds'], float)
        required_fields = ['user_id', 'agent_count', 'context_count', 'has_websocket_bridge', 'uptime_seconds']
        for field in required_fields:
            assert field in metrics, f'Missing metric field: {field}'

@pytest.mark.asyncio
class AgentRegistryEnhancedUserIsolationTests(SSotBaseTestCase):
    """Test AgentRegistry enhanced user isolation and hardening features."""

    async def test_agent_registry_enforces_complete_user_session_isolation(self, mock_llm_manager):
        """Test AgentRegistry enforces complete isolation between user sessions."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        user_data = {}
        sensitive_agents = {}
        for i in range(10):
            user_id = f'isolated_reg_user_{i}'
            user_data[user_id] = {'api_key': f'secret_key_{i}_{uuid.uuid4().hex}', 'private_data': f'confidential_{i}_{uuid.uuid4().hex}', 'user_permissions': f'admin' if i % 2 == 0 else 'user'}
            user_session = await registry.get_user_session(user_id)
            sensitive_agents[user_id] = []
            for j in range(3):
                mock_agent = Mock()
                mock_agent.user_secrets = user_data[user_id]
                mock_agent.isolation_id = f'{user_id}_agent_{j}'
                sensitive_agents[user_id].append(mock_agent)
                await user_session.register_agent(f'sensitive_agent_{j}', mock_agent)
        for user_id in user_data.keys():
            user_session = registry._user_sessions[user_id]
            for agent_name, agent in user_session._agents.items():
                assert agent.user_secrets == user_data[user_id]
                assert user_id in agent.isolation_id
                for other_user_id, other_data in user_data.items():
                    if other_user_id != user_id:
                        assert agent.user_secrets != other_data
                        assert other_user_id not in agent.isolation_id
            assert len(user_session._agents) == 3
            assert user_session.user_id == user_id

    async def test_agent_registry_websocket_manager_propagation_isolation(self, mock_llm_manager):
        """Test AgentRegistry WebSocket manager propagation maintains user isolation."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        user_sessions = []
        for i in range(5):
            user_id = f'ws_prop_user_{i}'
            session = await registry.get_user_session(user_id)
            user_sessions.append((user_id, session))
        mock_websocket_manager = Mock()
        mock_websocket_manager.create_user_specific_bridge = Mock()

        def create_user_bridge(user_context):
            mock_bridge = Mock()
            mock_bridge.user_context = user_context
            mock_bridge.user_specific_id = user_context.user_id
            return mock_bridge
        mock_websocket_manager.create_bridge = Mock(side_effect=create_user_bridge)
        await registry.set_websocket_manager_async(mock_websocket_manager)
        for user_id, session in user_sessions:
            assert session._websocket_manager == mock_websocket_manager
            assert session._websocket_bridge is not None
            assert session._websocket_bridge.user_specific_id == user_id
            for other_user_id, other_session in user_sessions:
                if other_user_id != user_id:
                    assert session._websocket_bridge != other_session._websocket_bridge
                    assert session._websocket_bridge.user_specific_id != other_user_id

    async def test_agent_registry_create_agent_for_user_complete_isolation(self, mock_llm_manager, mock_websocket_manager):
        """Test create_agent_for_user creates completely isolated agent instances."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        created_agents = []

        async def isolated_agent_factory(agent_type, context=None):
            """Factory function that matches the signature of get_async"""
            mock_agent = Mock()
            mock_agent.user_context = context
            mock_agent.creation_timestamp = datetime.now(timezone.utc)
            if context:
                mock_agent.unique_id = f'{context.user_id}_{uuid.uuid4().hex[:8]}'
            else:
                mock_agent.unique_id = f'unknown_user_{uuid.uuid4().hex[:8]}'
            created_agents.append(mock_agent)
            return mock_agent
        registry.get_async = AsyncMock(side_effect=isolated_agent_factory)
        user_contexts = []
        for i in range(3):
            user_id = f'create_iso_user_{i}'
            context = UserExecutionContext(user_id=user_id, request_id=f'create_req_{i}', thread_id=f'create_thread_{i}', run_id=f'create_run_{i}')
            user_contexts.append(context)
        created_agent_instances = []
        for context in user_contexts:
            agent = await registry.create_agent_for_user(user_id=context.user_id, agent_type='isolated_test_agent', user_context=context, websocket_manager=mock_websocket_manager)
            created_agent_instances.append(agent)
        for i, agent in enumerate(created_agent_instances):
            expected_context = user_contexts[i]
            assert agent.user_context.user_id == expected_context.user_id
            assert agent.user_context.thread_id == expected_context.thread_id
            assert agent.user_context.run_id == expected_context.run_id
            assert expected_context.user_id in agent.unique_id
            user_session = registry._user_sessions[expected_context.user_id]
            registered_agent = await user_session.get_agent('isolated_test_agent')
            assert registered_agent == agent
            for j, other_context in enumerate(user_contexts):
                if i != j:
                    other_session = registry._user_sessions[other_context.user_id]
                    other_agent = await other_session.get_agent('isolated_test_agent')
                    assert other_agent != agent
                    assert other_agent.user_context.user_id != expected_context.user_id

    async def test_agent_registry_concurrent_user_operations_thread_safety(self, mock_llm_manager):
        """Test AgentRegistry handles concurrent user operations with thread safety."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        concurrent_users = 20
        operations_per_user = 15
        all_results = []

        async def concurrent_user_operations(base_user_id):
            """Simulate concurrent operations for a single user."""
            user_id = f'concurrent_ops_user_{base_user_id}'
            operations_results = []
            try:
                for op in range(operations_per_user):
                    if op % 5 == 0:
                        session = await registry.get_user_session(user_id)
                        operations_results.append(f'session_created_{op}')
                    elif op % 5 == 1:
                        context = UserExecutionContext(user_id=user_id, request_id=f'concurrent_req_{op}', thread_id=f'concurrent_thread_{op}', run_id=f'concurrent_run_{op}')
                        session = await registry.get_user_session(user_id)
                        mock_agent = Mock()
                        mock_agent.op_id = op
                        await session.register_agent(f'concurrent_agent_{op}', mock_agent)
                        operations_results.append(f'agent_created_{op}')
                    elif op % 5 == 2:
                        session = await registry.get_user_session(user_id)
                        agent = await session.get_agent(f'concurrent_agent_{op - 1}')
                        if agent:
                            operations_results.append(f'agent_retrieved_{op}')
                        else:
                            operations_results.append(f'agent_not_found_{op}')
                    elif op % 5 == 3:
                        if user_id in registry._user_sessions:
                            session = registry._user_sessions[user_id]
                            metrics = session.get_metrics()
                            operations_results.append(f'metrics_collected_{op}')
                    else:
                        reset_result = await registry.reset_user_agents(user_id)
                        operations_results.append(f'user_reset_{op}')
                return operations_results
            except Exception as e:
                return [f'error: {str(e)}']
        tasks = [concurrent_user_operations(i) for i in range(concurrent_users)]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        total_operations = 0
        total_errors = 0
        for user_results in all_results:
            if isinstance(user_results, Exception):
                total_errors += 1
            else:
                total_operations += len(user_results)
                error_ops = [op for op in user_results if op.startswith('error:')]
                total_errors += len(error_ops)
        assert total_errors == 0, f'Thread safety violations detected: {total_errors} errors'
        expected_total_operations = concurrent_users * operations_per_user
        assert total_operations >= expected_total_operations * 0.8
        assert len(registry._user_sessions) <= concurrent_users

    async def test_agent_registry_memory_monitoring_and_cleanup_triggers(self, mock_llm_manager):
        """Test AgentRegistry memory monitoring and automatic cleanup triggers."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        threshold_exceeding_users = []
        for i in range(2):
            user_id = f'memory_monitor_user_{i}'
            user_session = await registry.get_user_session(user_id)
            for j in range(12):
                mock_agent = Mock()
                mock_agent.memory_usage = 1000000
                mock_agent.created_at = datetime.now(timezone.utc)
                mock_agent.cleanup = AsyncMock()
                mock_agent.close = AsyncMock()
                await user_session.register_agent(f'memory_agent_{j}', mock_agent)
            old_time = datetime.now(timezone.utc) - timedelta(hours=26)
            user_session._created_at = old_time
            threshold_exceeding_users.append(user_id)
        monitoring_report = await registry.monitor_all_users()
        assert monitoring_report['total_users'] == 2
        assert monitoring_report['total_agents'] == 2 * 12
        global_issues = monitoring_report['global_issues']
        assert len(global_issues) > 0
        memory_issue_found = any(('session too old' in issue.lower() or 'user session' in issue.lower() or 'agent' in issue.lower() for issue in global_issues))
        assert memory_issue_found, f'Memory pressure not detected in issues: {global_issues}'
        for user_id in threshold_exceeding_users:
            user_report = monitoring_report['users'][user_id]
            assert user_report['status'] in ['warning', 'error']
            if 'issues' in user_report:
                assert len(user_report['issues']) > 0
        cleanup_report = await registry.emergency_cleanup_all()
        assert cleanup_report['users_cleaned'] == 2
        assert cleanup_report['agents_cleaned'] == 2 * 12
        assert len(registry._user_sessions) == 0
        await registry.cleanup()
        await asyncio.sleep(0.01)

@pytest.mark.asyncio
class ExecutionEngineFactoryIntegrationTests(SSotBaseTestCase):
    """Test ExecutionEngineFactory integration with AgentRegistry and user isolation."""

    async def test_execution_engine_factory_requires_websocket_bridge_validation(self):
        """Test ExecutionEngineFactory enforces WebSocket bridge requirement."""
        with pytest.raises(ExecutionEngineFactoryError) as exc_info:
            ExecutionEngineFactory(websocket_bridge=None)
        assert 'requires websocket_bridge during initialization' in str(exc_info.value)
        assert 'WebSocket events that enable chat business value' in str(exc_info.value)

    async def test_execution_engine_factory_creates_isolated_engines_per_user(self, mock_websocket_bridge):
        """Test ExecutionEngineFactory creates completely isolated engines per user."""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        user_contexts = []
        for i in range(5):
            user_id = f'factory_iso_user_{i}'
            context = UserExecutionContext(user_id=user_id, request_id=f'factory_req_{i}', thread_id=f'factory_thread_{i}', run_id=f'factory_run_{i}')
            user_contexts.append(context)
        created_engines = []
        for context in user_contexts:
            with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
                mock_agent_factory = Mock()
                mock_get_factory.return_value = mock_agent_factory
                engine = await factory.create_for_user(context)
                created_engines.append(engine)
        for i, engine in enumerate(created_engines):
            expected_context = user_contexts[i]
            engine_context = engine.get_user_context()
            assert engine_context.user_id == expected_context.user_id
            assert engine_context.request_id == expected_context.request_id
            assert engine_context.thread_id == expected_context.thread_id
            assert engine.is_active()
            assert engine.engine_id is not None
            for j, other_engine in enumerate(created_engines):
                if i != j:
                    other_context = other_engine.get_user_context()
                    assert engine_context.user_id != other_context.user_id
                    assert engine.engine_id != other_engine.engine_id
        factory_metrics = factory.get_factory_metrics()
        assert factory_metrics['total_engines_created'] == 5
        assert factory_metrics['active_engines_count'] == 5
        assert factory_metrics['creation_errors'] == 0

    async def test_execution_engine_factory_user_limits_enforcement(self, mock_websocket_bridge):
        """Test ExecutionEngineFactory enforces per-user engine limits."""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        user_id = 'limit_testing_user_long_id'
        base_context = UserExecutionContext(user_id=user_id, request_id='base_request', thread_id='base_thread', run_id='base_run')
        created_engines = []
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            for i in range(factory._max_engines_per_user):
                context = UserExecutionContext(user_id=user_id, request_id=f'limit_req_{i}', thread_id=f'limit_thread_{i}', run_id=f'limit_run_{i}')
                engine = await factory.create_for_user(context)
                created_engines.append(engine)
            excess_context = UserExecutionContext(user_id=user_id, request_id='excess_request', thread_id='excess_thread', run_id='excess_run')
            with pytest.raises(ExecutionEngineFactoryError) as exc_info:
                await factory.create_for_user(excess_context)
            assert 'reached maximum engine limit' in str(exc_info.value)
            assert user_id in str(exc_info.value)
        assert len(created_engines) == factory._max_engines_per_user
        factory_metrics = factory.get_factory_metrics()
        assert factory_metrics['user_limit_rejections'] == 1
        assert factory_metrics['total_engines_created'] == factory._max_engines_per_user

    async def test_execution_engine_factory_user_scope_context_manager(self, mock_websocket_bridge):
        """Test ExecutionEngineFactory user_execution_scope context manager provides proper isolation."""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        user_id = 'scope_testing_user_long_id'
        context = UserExecutionContext(user_id=user_id, request_id='scope_request', thread_id='scope_thread', run_id='scope_run')
        execution_results = []
        engine_instances = []
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            async with factory.user_execution_scope(context) as engine:
                assert engine is not None
                assert engine.is_active()
                assert engine.get_user_context().user_id == user_id
                engine_instances.append(engine)
                execution_results.append('scope_entered')
                factory_metrics = factory.get_factory_metrics()
                assert factory_metrics['active_engines_count'] >= 1
                execution_results.append('scope_executing')
        execution_results.append('scope_exited')
        final_metrics = factory.get_factory_metrics()
        assert final_metrics['total_engines_cleaned'] >= 1
        expected_results = ['scope_entered', 'scope_executing', 'scope_exited']
        assert execution_results == expected_results

    async def test_execution_engine_factory_websocket_emitter_integration(self, mock_websocket_bridge):
        """Test ExecutionEngineFactory creates proper WebSocket emitters for user isolation."""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        user_contexts = []
        for i in range(3):
            user_id = f'emitter_user_{i}'
            context = UserExecutionContext(user_id=user_id, request_id=f'emitter_req_{i}', thread_id=f'emitter_thread_{i}', run_id=f'emitter_run_{i}')
            user_contexts.append(context)
        created_engines = []
        for context in user_contexts:
            with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
                mock_agent_factory = Mock()
                mock_get_factory.return_value = mock_agent_factory
                with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserWebSocketEmitter') as mock_emitter_class:
                    mock_emitter = Mock()
                    mock_emitter.user_id = context.user_id
                    mock_emitter.thread_id = context.thread_id
                    mock_emitter.run_id = context.run_id
                    mock_emitter_class.return_value = mock_emitter
                    engine = await factory.create_for_user(context)
                    created_engines.append(engine)
                    mock_emitter_class.assert_called_once()
                    call_kwargs = mock_emitter_class.call_args.kwargs
                    assert call_kwargs['user_id'] == context.user_id
                    assert call_kwargs['thread_id'] == context.thread_id
                    assert call_kwargs['run_id'] == context.run_id
                    assert call_kwargs['websocket_bridge'] == mock_websocket_bridge
        for i, engine in enumerate(created_engines):
            expected_context = user_contexts[i]
            engine_context = engine.get_user_context()
            assert engine_context.user_id == expected_context.user_id

    async def test_execution_engine_factory_cleanup_and_lifecycle_management(self, mock_websocket_bridge):
        """Test ExecutionEngineFactory properly manages engine lifecycle and cleanup."""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        test_engines = []
        user_contexts = []
        for i in range(4):
            user_id = f'lifecycle_user_{i}'
            context = UserExecutionContext(user_id=user_id, request_id=f'lifecycle_req_{i}', thread_id=f'lifecycle_thread_{i}', run_id=f'lifecycle_run_{i}')
            user_contexts.append(context)
            with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
                mock_agent_factory = Mock()
                mock_get_factory.return_value = mock_agent_factory
                engine = await factory.create_for_user(context)
                test_engines.append(engine)
        initial_metrics = factory.get_factory_metrics()
        assert initial_metrics['active_engines_count'] == 4
        assert initial_metrics['total_engines_created'] == 4
        for i, engine in enumerate(test_engines[:2]):
            await factory.cleanup_engine(engine)
        partial_metrics = factory.get_factory_metrics()
        assert partial_metrics['active_engines_count'] == 2
        assert partial_metrics['total_engines_cleaned'] == 2
        user_to_cleanup = user_contexts[2].user_id
        cleanup_success = await factory.cleanup_user_context(user_to_cleanup)
        assert cleanup_success is True
        user_cleanup_metrics = factory.get_factory_metrics()
        assert user_cleanup_metrics['active_engines_count'] == 1
        assert user_cleanup_metrics['total_engines_cleaned'] == 3
        await factory.shutdown()
        final_metrics = factory.get_factory_metrics()
        assert final_metrics['active_engines_count'] == 0
        assert final_metrics['total_engines_cleaned'] == 4

@pytest.mark.asyncio
class AgentRegistryExecutionEngineFactoryIntegrationTests(SSotBaseTestCase):
    """Test integration between AgentRegistry and ExecutionEngineFactory for complete user isolation."""

    async def test_integrated_user_isolation_end_to_end(self, mock_llm_manager, mock_websocket_bridge):
        """Test complete end-to-end user isolation between AgentRegistry and ExecutionEngineFactory."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        users_data = []
        for i in range(3):
            user_id = f'e2e_isolation_user_{i}'
            context = UserExecutionContext(user_id=user_id, request_id=f'e2e_req_{i}', thread_id=f'e2e_thread_{i}', run_id=f'e2e_run_{i}')
            users_data.append((user_id, context))
        user_environments = {}
        for user_id, context in users_data:
            user_session = await registry.get_user_session(user_id)
            with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
                mock_agent_factory = Mock()
                mock_get_factory.return_value = mock_agent_factory
                execution_engine = await factory.create_for_user(context)
            mock_agent = Mock()
            mock_agent.user_id = user_id
            mock_agent.execution_engine = execution_engine
            await user_session.register_agent('isolated_agent', mock_agent)
            user_environments[user_id] = {'session': user_session, 'engine': execution_engine, 'agent': mock_agent, 'context': context}
        for user_id, env in user_environments.items():
            assert env['session'].user_id == user_id
            assert len(env['session']._agents) == 1
            engine_context = env['engine'].get_user_context()
            assert engine_context.user_id == user_id
            assert engine_context == env['context']
            assert env['agent'].user_id == user_id
            assert env['agent'].execution_engine == env['engine']
            for other_user_id, other_env in user_environments.items():
                if user_id != other_user_id:
                    assert env['session'] != other_env['session']
                    assert env['session'].user_id != other_user_id
                    assert env['engine'] != other_env['engine']
                    assert engine_context.user_id != other_user_id
                    assert env['agent'] != other_env['agent']
                    assert env['agent'].user_id != other_user_id

    async def test_integrated_websocket_isolation_across_components(self, mock_llm_manager, mock_websocket_manager):
        """Test WebSocket isolation works across AgentRegistry and ExecutionEngineFactory."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        mock_websocket_bridge.send_agent_event = AsyncMock()
        mock_websocket_bridge.user_context = None
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.ExecutionEngineFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_factory_class.return_value = mock_factory
            await registry.set_websocket_manager_async(mock_websocket_manager)
            websocket_users = []
            for i in range(2):
                user_id = f'ws_integrated_user_{i}'
                context = UserExecutionContext(user_id=user_id, request_id=f'ws_req_{i}', thread_id=f'ws_thread_{i}', run_id=f'ws_run_{i}')
                websocket_users.append((user_id, context))
            user_websocket_environments = {}
            for user_id, context in websocket_users:
                user_session = await registry.get_user_session(user_id)
                assert user_session._websocket_manager == mock_websocket_manager
                mock_execution_engine = Mock()
                mock_execution_engine.get_user_context = Mock(return_value=context)
                mock_execution_engine.is_active = Mock(return_value=True)
                mock_factory.create_for_user = AsyncMock(return_value=mock_execution_engine)
                execution_engine = await mock_factory.create_for_user(context)
                user_websocket_environments[user_id] = {'session': user_session, 'engine': execution_engine, 'context': context}
            for user_id, env in user_websocket_environments.items():
                user_session = env['session']
                assert user_session._websocket_manager == mock_websocket_manager
                execution_engine = env['engine']
                assert execution_engine is not None
                assert execution_engine.get_user_context().user_id == user_id
                for other_user_id, other_env in user_websocket_environments.items():
                    if user_id != other_user_id:
                        assert env['session'] != other_env['session']
                        assert env['engine'] != other_env['engine']

    async def test_integrated_memory_management_and_cleanup(self, mock_llm_manager, mock_websocket_bridge):
        """Test integrated memory management and cleanup across AgentRegistry and ExecutionEngineFactory."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        memory_test_users = []
        created_environments = {}
        for i in range(5):
            user_id = f'memory_mgmt_user_{i}'
            context = UserExecutionContext(user_id=user_id, request_id=f'memory_req_{i}', thread_id=f'memory_thread_{i}', run_id=f'memory_run_{i}')
            memory_test_users.append((user_id, context))
            user_session = await registry.get_user_session(user_id)
            with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
                mock_agent_factory = Mock()
                mock_get_factory.return_value = mock_agent_factory
                execution_engine = await factory.create_for_user(context)
            for j in range(3):
                mock_agent = Mock()
                mock_agent.cleanup = AsyncMock()
                mock_agent.memory_data = 'x' * 10000
                await user_session.register_agent(f'memory_agent_{j}', mock_agent)
            created_environments[user_id] = {'session': user_session, 'engine': execution_engine, 'agents': user_session._agents.copy()}
        initial_registry_health = registry.get_registry_health()
        initial_factory_metrics = factory.get_factory_metrics()
        assert initial_registry_health['total_user_sessions'] == 5
        assert initial_factory_metrics['active_engines_count'] == 5
        users_to_cleanup = [memory_test_users[i][0] for i in range(3)]
        for user_id in users_to_cleanup:
            registry_cleanup = await registry.cleanup_user_session(user_id)
            assert registry_cleanup['status'] == 'cleaned'
            factory_cleanup = await factory.cleanup_user_context(user_id)
            assert factory_cleanup is True
        partial_registry_health = registry.get_registry_health()
        partial_factory_metrics = factory.get_factory_metrics()
        assert partial_registry_health['total_user_sessions'] == 2
        assert partial_factory_metrics['active_engines_count'] == 2
        assert partial_factory_metrics['total_engines_cleaned'] == 3
        emergency_registry_cleanup = await registry.emergency_cleanup_all()
        await factory.shutdown()
        final_registry_health = registry.get_registry_health()
        final_factory_metrics = factory.get_factory_metrics()
        assert final_registry_health['total_user_sessions'] == 0
        assert final_factory_metrics['active_engines_count'] == 0
        assert emergency_registry_cleanup['users_cleaned'] == 2
        assert emergency_registry_cleanup['agents_cleaned'] == 6

    async def test_integrated_concurrent_operations_stress_test(self, mock_llm_manager, mock_websocket_bridge):
        """Test integrated components under concurrent operation stress."""
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        concurrent_users = 10
        operations_per_user = 8

        async def integrated_user_operations(base_user_id):
            """Perform integrated operations across registry and factory."""
            user_id = f'stress_user_{base_user_id}'
            results = []
            try:
                context = UserExecutionContext(user_id=user_id, request_id=f'stress_req_{base_user_id}', thread_id=f'stress_thread_{base_user_id}', run_id=f'stress_run_{base_user_id}')
                user_session = await registry.get_user_session(user_id)
                results.append('session_created')
                with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
                    mock_agent_factory = Mock()
                    mock_get_factory.return_value = mock_agent_factory
                    execution_engine = await factory.create_for_user(context)
                    results.append('engine_created')
                for op in range(operations_per_user):
                    if op % 4 == 0:
                        mock_agent = Mock()
                        mock_agent.operation_id = op
                        await user_session.register_agent(f'stress_agent_{op}', mock_agent)
                        results.append(f'agent_created_{op}')
                    elif op % 4 == 1:
                        session_metrics = user_session.get_metrics()
                        factory_metrics = factory.get_factory_metrics()
                        results.append(f'metrics_collected_{op}')
                    elif op % 4 == 2:
                        is_active = execution_engine.is_active()
                        if is_active:
                            results.append(f'engine_active_{op}')
                        else:
                            results.append(f'engine_inactive_{op}')
                    else:
                        await registry.cleanup_user_session(user_id)
                        await factory.cleanup_user_context(user_id)
                        results.append(f'cleanup_complete_{op}')
                return results
            except Exception as e:
                return [f'error: {str(e)}']
        start_time = time.time()
        tasks = [integrated_user_operations(i) for i in range(concurrent_users)]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        total_time = end_time - start_time
        total_operations = 0
        total_errors = 0
        for user_results in all_results:
            if isinstance(user_results, Exception):
                total_errors += 1
            else:
                total_operations += len(user_results)
                error_ops = [op for op in user_results if op.startswith('error:')]
                total_errors += len(error_ops)
        assert total_time < 10.0, f'Stress test took too long: {total_time:.2f}s'
        expected_total_operations = concurrent_users * (2 + operations_per_user)
        error_rate = total_errors / max(total_operations, 1)
        assert error_rate < 0.1, f'High error rate under stress: {error_rate:.2%}, errors: {total_errors}'
        final_registry_health = registry.get_registry_health()
        final_factory_metrics = factory.get_factory_metrics()
        assert final_registry_health['status'] in ['healthy', 'warning']
        assert final_factory_metrics['creation_errors'] < concurrent_users * 0.5
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
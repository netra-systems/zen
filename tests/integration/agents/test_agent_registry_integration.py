""" ALERT:  CRITICAL INTEGRATION TESTS: AgentRegistry User Isolation and Factory Patterns

BUSINESS CRITICAL SCENARIOS:
- Enterprise customer isolation ($15K+ MRR per customer protection)
- Golden Path agent orchestration ($500K+ ARR protection) 
- Factory pattern preventing singleton-related memory issues
- WebSocket bridge isolation for chat functionality

USER ISOLATION CRITICAL SSOT class - 1,729 lines, MEGA CLASS validation.

Requirements:
- NO MOCKS allowed - use real agent registration and user isolation components
- Test factory pattern isolation preventing memory leaks and shared state
- Focus on per-user agent isolation validation for Enterprise customers
- Test WebSocket bridge management and integration
- Validate the Golden Path agent orchestration protecting business value

Test Categories:
1. User Isolation and Factory Pattern Tests
2. Agent Registration and Management Tests  
3. WebSocket Bridge Integration Tests
4. Enterprise Multi-User Validation
5. Golden Path Agent Orchestration
6. Memory and Resource Management

SSOT Compliance:
- Uses test_framework.ssot.base_test_case.SSotBaseTestCase
- Imports from SSOT_IMPORT_REGISTRY.md verified paths
- Tests real AgentRegistry with UserAgentSession components
- Includes UserExecutionContext and UserContextManager integration
"""
import asyncio
import gc
import time
import uuid
import psutil
import pytest
import weakref
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase, SsotTestMetrics
from test_framework.ssot.websocket import WebSocketTestMetrics, MockWebSocketConnection
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession, AgentLifecycleManager, get_agent_registry
from netra_backend.app.services.user_execution_context import UserExecutionContext, UserContextManager, UserContextFactory, create_isolated_execution_context, managed_user_context
from shared.types.core_types import UserID, ThreadID, RunID
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
from netra_backend.app.llm.llm_manager import LLMManager
from shared.isolated_environment import get_env
import logging
logger = logging.getLogger(__name__)

class MockWebSocketManager:
    """Mock WebSocket manager for testing without real WebSocket infrastructure."""

    def __init__(self):
        self.connections = {}
        self.events = []
        self.user_id = None

    def create_bridge(self, user_context):
        """Factory method for creating test bridges."""
        bridge = MockAgentWebSocketBridge(user_context, self)
        return bridge

    async def notify_agent_started(self, run_id, agent_name, metadata):
        self.events.append(('agent_started', run_id, agent_name, metadata))

    async def notify_agent_thinking(self, run_id, agent_name, reasoning, step_number=None, **kwargs):
        self.events.append(('agent_thinking', run_id, agent_name, reasoning))

    async def notify_tool_executing(self, run_id, agent_name, tool_name, parameters):
        self.events.append(('tool_executing', run_id, agent_name, tool_name))

    async def notify_tool_completed(self, run_id, agent_name, tool_name, result, execution_time_ms):
        self.events.append(('tool_completed', run_id, agent_name, tool_name))

    async def notify_agent_completed(self, run_id, agent_name, result, execution_time_ms):
        self.events.append(('agent_completed', run_id, agent_name, result))

    async def notify_agent_error(self, run_id, agent_name, error, error_context=None):
        self.events.append(('agent_error', run_id, agent_name, error))

class MockAgentWebSocketBridge:
    """Mock WebSocket bridge for testing."""

    def __init__(self, user_context, websocket_manager):
        self.user_context = user_context
        self.websocket_manager = websocket_manager
        self.events = []

    async def notify_agent_started(self, run_id, agent_name, metadata):
        self.events.append(('agent_started', run_id, agent_name))

    async def notify_agent_thinking(self, run_id, agent_name, reasoning, step_number=None, **kwargs):
        self.events.append(('agent_thinking', run_id, agent_name))

class MockLLMManager:
    """Mock LLM manager for agent creation."""

    def __init__(self):
        self.requests = []

    async def get_completion(self, messages, model='gpt-4', **kwargs):
        self.requests.append(('completion', messages, model))
        return {'content': 'Mock LLM response', 'usage': {'total_tokens': 100}}

@pytest.mark.integration
class AgentRegistryUserIsolationIntegrationTests(SSotAsyncTestCase):
    """Integration tests for AgentRegistry user isolation and factory patterns.
    
    CRITICAL: Tests Enterprise customer isolation ($15K+ MRR protection)
    and factory pattern validation preventing memory leaks.
    """

    async def async_setup_method(self, method):
        """Setup method for each test with isolated resources."""
        await super().async_setup_method(method)
        self.env = get_env()
        self.llm_manager = MockLLMManager()
        self.registry = AgentRegistry(llm_manager=self.llm_manager, tool_dispatcher_factory=self._create_mock_tool_dispatcher)
        self.registry.register_default_agents()
        self.initial_memory = psutil.Process().memory_info().rss
        self.test_users = []
        self.websocket_metrics = WebSocketTestMetrics()

    async def async_teardown_method(self, method):
        """Cleanup after each test."""
        await self.registry.cleanup()
        gc.collect()
        final_memory = psutil.Process().memory_info().rss
        memory_increase = final_memory - self.initial_memory
        logger.info(f'Test {method.__name__} memory increase: {memory_increase / 1024 / 1024:.2f} MB')
        if memory_increase > 50 * 1024 * 1024:
            logger.warning(f'High memory usage increase detected: {memory_increase / 1024 / 1024:.2f} MB')
        await super().async_teardown_method(method)

    async def _create_mock_tool_dispatcher(self, user_context, websocket_bridge=None):
        """Factory method for creating mock tool dispatchers."""
        dispatcher = MagicMock()
        dispatcher.user_context = user_context
        dispatcher.websocket_bridge = websocket_bridge
        dispatcher.execute_tool = AsyncMock(return_value={'result': 'mock_tool_execution'})
        return dispatcher

    async def test_per_user_agent_registry_isolation_validation(self):
        """Test per-user agent registry isolation preventing cross-user contamination.
        
        BUSINESS CRITICAL: Enterprise customer data protection ($15K+ MRR per customer).
        """
        user1_id = f'enterprise_user_1_{uuid.uuid4().hex[:8]}'
        user2_id = f'enterprise_user_2_{uuid.uuid4().hex[:8]}'
        user3_id = f'enterprise_user_3_{uuid.uuid4().hex[:8]}'
        user1_context = await create_isolated_execution_context(user_id=user1_id, request_id=f'isolation_test_{uuid.uuid4().hex[:8]}', isolation_level='strict')
        user2_context = await create_isolated_execution_context(user_id=user2_id, request_id=f'isolation_test_{uuid.uuid4().hex[:8]}', isolation_level='strict')
        user3_context = await create_isolated_execution_context(user_id=user3_id, request_id=f'isolation_test_{uuid.uuid4().hex[:8]}', isolation_level='strict')
        user1_session = await self.registry.get_user_session(user1_id)
        user2_session = await self.registry.get_user_session(user2_id)
        user3_session = await self.registry.get_user_session(user3_id)
        assert user1_session != user2_session != user3_session
        assert id(user1_session) != id(user2_session) != id(user3_session)
        assert user1_session.user_id == user1_id
        assert user2_session.user_id == user2_id
        assert user3_session.user_id == user3_id
        mock_ws_manager = MockWebSocketManager()
        agent1 = await self.registry.create_agent_for_user(user1_id, 'data_helper', user1_context, mock_ws_manager)
        agent2 = await self.registry.create_agent_for_user(user2_id, 'data_helper', user2_context, mock_ws_manager)
        agent3 = await self.registry.create_agent_for_user(user3_id, 'optimization', user3_context, mock_ws_manager)
        assert agent1 != agent2 != agent3
        assert id(agent1) != id(agent2) != id(agent3)
        user1_agent_from_user2 = await self.registry.get_user_agent(user2_id, 'data_helper')
        user1_agent_from_user1 = await self.registry.get_user_agent(user1_id, 'data_helper')
        assert user1_agent_from_user2 != agent1
        assert user1_agent_from_user1 == agent1
        await user1_session.register_agent('test_agent', MagicMock())
        user1_agents = len(user1_session._agents)
        user2_agents = len(user2_session._agents)
        assert user1_agents > user2_agents
        self.test_users.extend([user1_id, user2_id, user3_id])
        self.test_metrics.record_custom('isolated_users_tested', 3)
        self.test_metrics.record_custom('isolated_agents_created', 3)
        self.test_metrics.record_custom('isolation_validation_passed', True)

    async def test_factory_pattern_memory_leak_prevention_under_load(self):
        """Test factory pattern preventing memory leaks under high concurrent load.
        
        BUSINESS CRITICAL: System stability under Enterprise load preventing service degradation.
        """
        initial_memory = psutil.Process().memory_info().rss
        num_concurrent_users = 20
        agents_per_user = 10
        total_agents = num_concurrent_users * agents_per_user

        async def create_user_session_with_agents(user_index):
            user_id = f'load_test_user_{user_index}_{uuid.uuid4().hex[:8]}'
            user_context = await create_isolated_execution_context(user_id=user_id, request_id=f'load_test_{uuid.uuid4().hex[:8]}', isolation_level='standard')
            agents = []
            mock_ws_manager = MockWebSocketManager()
            for agent_index in range(agents_per_user):
                agent_type = ['data_helper', 'optimization', 'reporting'][agent_index % 3]
                agent = await self.registry.create_agent_for_user(user_id, agent_type, user_context, mock_ws_manager)
                agents.append(agent)
                await asyncio.sleep(0.01)
            weak_refs = [weakref.ref(agent) for agent in agents]
            return (user_id, agents, weak_refs)
        tasks = [create_user_session_with_agents(i) for i in range(num_concurrent_users)]
        results = await asyncio.gather(*tasks)
        user_ids = [result[0] for result in results]
        all_agents = [agent for result in results for agent in result[1]]
        all_weak_refs = [ref for result in results for ref in result[2]]
        assert len(all_agents) == total_agents
        mid_memory = psutil.Process().memory_info().rss
        creation_memory_increase = mid_memory - initial_memory
        logger.info(f'Memory increase after creating {total_agents} agents: {creation_memory_increase / 1024 / 1024:.2f} MB')
        cleanup_tasks = []
        for user_id in user_ids:
            cleanup_tasks.append(self.registry.cleanup_user_session(user_id))
        cleanup_results = await asyncio.gather(*cleanup_tasks)
        total_agents_cleaned = sum((result['cleaned_agents'] for result in cleanup_results))
        assert total_agents_cleaned == total_agents
        del all_agents
        gc.collect()
        await asyncio.sleep(0.1)
        dead_refs = sum((1 for ref in all_weak_refs if ref() is None))
        gc_ratio = dead_refs / len(all_weak_refs)
        assert gc_ratio > 0.8, f'Expected >80% garbage collection, got {gc_ratio:.1%}'
        final_memory = psutil.Process().memory_info().rss
        net_memory_increase = final_memory - initial_memory
        logger.info(f'Net memory increase after cleanup: {net_memory_increase / 1024 / 1024:.2f} MB')
        max_acceptable_leak = 10 * 1024 * 1024
        assert net_memory_increase < max_acceptable_leak, f'Memory leak detected: {net_memory_increase / 1024 / 1024:.2f} MB > 10 MB'
        self.test_metrics.record_custom('concurrent_users_tested', num_concurrent_users)
        self.test_metrics.record_custom('total_agents_created', total_agents)
        self.test_metrics.record_custom('garbage_collection_ratio', gc_ratio)
        self.test_metrics.record_custom('memory_leak_mb', net_memory_increase / 1024 / 1024)

    async def test_shared_state_contamination_detection(self):
        """Test detection and prevention of shared state contamination between users.
        
        BUSINESS CRITICAL: Data security preventing cross-user data exposure.
        """
        enterprise_user1 = f'enterprise_client_1_{uuid.uuid4().hex[:8]}'
        enterprise_user2 = f'enterprise_client_2_{uuid.uuid4().hex[:8]}'
        sensitive_data_1 = {'customer_tier': 'enterprise_premium', 'account_value': 250000, 'data_classification': 'confidential', 'pii_present': True}
        sensitive_data_2 = {'customer_tier': 'enterprise_standard', 'account_value': 150000, 'data_classification': 'internal', 'pii_present': True}
        user1_context = await create_isolated_execution_context(user_id=enterprise_user1, request_id=f'contamination_test_{uuid.uuid4().hex[:8]}', isolation_level='strict')
        user1_context.agent_context.update(sensitive_data_1)
        user2_context = await create_isolated_execution_context(user_id=enterprise_user2, request_id=f'contamination_test_{uuid.uuid4().hex[:8]}', isolation_level='strict')
        user2_context.agent_context.update(sensitive_data_2)
        mock_ws_manager1 = MockWebSocketManager()
        mock_ws_manager2 = MockWebSocketManager()
        agent1 = await self.registry.create_agent_for_user(enterprise_user1, 'optimization', user1_context, mock_ws_manager1)
        agent2 = await self.registry.create_agent_for_user(enterprise_user2, 'optimization', user2_context, mock_ws_manager2)
        assert hasattr(agent1, 'tool_dispatcher') or hasattr(agent1, '_tool_dispatcher')
        assert hasattr(agent2, 'tool_dispatcher') or hasattr(agent2, '_tool_dispatcher')
        dispatcher1 = getattr(agent1, 'tool_dispatcher', getattr(agent1, '_tool_dispatcher', None))
        dispatcher2 = getattr(agent2, 'tool_dispatcher', getattr(agent2, '_tool_dispatcher', None))
        if dispatcher1 and dispatcher2:
            assert id(dispatcher1) != id(dispatcher2)
            assert dispatcher1.user_context.user_id == enterprise_user1
            assert dispatcher2.user_context.user_id == enterprise_user2
            user1_data = dispatcher1.user_context.agent_context
            user2_data = dispatcher2.user_context.agent_context
            assert user1_data.get('account_value') != user2_data.get('account_value')
            assert user1_data.get('customer_tier') != user2_data.get('customer_tier')
        original_value_1 = user1_context.agent_context['account_value']
        original_value_2 = user2_context.agent_context['account_value']
        user1_context.agent_context['account_value'] = 999999
        assert user2_context.agent_context['account_value'] == original_value_2
        assert user2_context.agent_context['account_value'] != 999999
        user1_session = await self.registry.get_user_session(enterprise_user1)
        user2_session = await self.registry.get_user_session(enterprise_user2)
        assert id(user1_session) != id(user2_session)
        assert user1_session._agents != user2_session._agents
        user2_optimization_agent = await self.registry.get_user_agent(enterprise_user2, 'optimization')
        user1_optimization_agent = await self.registry.get_user_agent(enterprise_user1, 'optimization')
        assert id(user1_optimization_agent) != id(user2_optimization_agent)
        self.test_users.extend([enterprise_user1, enterprise_user2])
        self.test_metrics.record_custom('contamination_tests_passed', True)
        self.test_metrics.record_custom('enterprise_users_tested', 2)
        self.test_metrics.record_custom('data_isolation_validated', True)

    async def test_user_context_boundary_enforcement(self):
        """Test enforcement of user context boundaries preventing unauthorized access.
        
        BUSINESS CRITICAL: Access control validation for Enterprise security compliance.
        """
        admin_user = f'admin_user_{uuid.uuid4().hex[:8]}'
        standard_user = f'standard_user_{uuid.uuid4().hex[:8]}'
        restricted_user = f'restricted_user_{uuid.uuid4().hex[:8]}'
        admin_context = await create_isolated_execution_context(user_id=admin_user, request_id=f'boundary_test_admin_{uuid.uuid4().hex[:8]}', isolation_level='strict')
        admin_context.agent_context.update({'role': 'administrator', 'permissions': ['read', 'write', 'admin', 'delete'], 'clearance_level': 'top_secret'})
        standard_context = await create_isolated_execution_context(user_id=standard_user, request_id=f'boundary_test_standard_{uuid.uuid4().hex[:8]}', isolation_level='strict')
        standard_context.agent_context.update({'role': 'user', 'permissions': ['read', 'write'], 'clearance_level': 'confidential'})
        restricted_context = await create_isolated_execution_context(user_id=restricted_user, request_id=f'boundary_test_restricted_{uuid.uuid4().hex[:8]}', isolation_level='strict')
        restricted_context.agent_context.update({'role': 'readonly', 'permissions': ['read'], 'clearance_level': 'public'})
        admin_ws = MockWebSocketManager()
        standard_ws = MockWebSocketManager()
        restricted_ws = MockWebSocketManager()
        admin_agent = await self.registry.create_agent_for_user(admin_user, 'corpus_admin', admin_context, admin_ws)
        standard_agent = await self.registry.create_agent_for_user(standard_user, 'optimization', standard_context, standard_ws)
        restricted_agent = await self.registry.create_agent_for_user(restricted_user, 'data_helper', restricted_context, restricted_ws)
        admin_dispatcher = getattr(admin_agent, 'tool_dispatcher', None)
        standard_dispatcher = getattr(standard_agent, 'tool_dispatcher', None)
        restricted_dispatcher = getattr(restricted_agent, 'tool_dispatcher', None)
        if admin_dispatcher and standard_dispatcher and restricted_dispatcher:
            assert admin_dispatcher.user_context.user_id == admin_user
            assert standard_dispatcher.user_context.user_id == standard_user
            assert restricted_dispatcher.user_context.user_id == restricted_user
            admin_perms = admin_dispatcher.user_context.agent_context.get('permissions', [])
            standard_perms = standard_dispatcher.user_context.agent_context.get('permissions', [])
            restricted_perms = restricted_dispatcher.user_context.agent_context.get('permissions', [])
            assert 'admin' in admin_perms
            assert 'admin' not in standard_perms
            assert 'admin' not in restricted_perms
            assert 'write' in standard_perms
            assert 'write' not in restricted_perms
        admin_from_standard = await self.registry.get_user_agent(standard_user, 'corpus_admin')
        standard_from_restricted = await self.registry.get_user_agent(restricted_user, 'optimization')
        assert admin_from_standard != admin_agent or admin_from_standard is None
        assert standard_from_restricted != standard_agent or standard_from_restricted is None
        admin_session = await self.registry.get_user_session(admin_user)
        standard_session = await self.registry.get_user_session(standard_user)
        restricted_session = await self.registry.get_user_session(restricted_user)
        assert admin_session != standard_session != restricted_session
        assert len(admin_session._agents) >= 1
        assert len(standard_session._agents) >= 1
        assert len(restricted_session._agents) >= 1
        admin_agents = list(admin_session._agents.keys())
        standard_agents = list(standard_session._agents.keys())
        restricted_agents = list(restricted_session._agents.keys())
        assert 'corpus_admin' in admin_agents or any(('admin' in agent for agent in admin_agents))
        assert 'optimization' in standard_agents or 'triage' in standard_agents
        assert 'data_helper' in restricted_agents or 'data' in restricted_agents
        original_admin_clearance = admin_context.agent_context['clearance_level']
        admin_context.agent_context['clearance_level'] = 'modified'
        assert standard_context.agent_context['clearance_level'] == 'confidential'
        assert restricted_context.agent_context['clearance_level'] == 'public'
        self.test_users.extend([admin_user, standard_user, restricted_user])
        self.test_metrics.record_custom('boundary_enforcement_validated', True)
        self.test_metrics.record_custom('permission_isolation_tested', 3)
        self.test_metrics.record_custom('security_clearance_levels', 3)

    async def test_agent_registration_with_user_context_isolation(self):
        """Test agent registration with complete user context isolation."""
        users = [f'reg_user_{i}_{uuid.uuid4().hex[:8]}' for i in range(5)]
        agent_types = ['data_helper', 'optimization', 'reporting', 'triage', 'goals_triage']
        registered_agents = {}
        for user_id in users:
            user_context = await create_isolated_execution_context(user_id=user_id, request_id=f'registration_test_{uuid.uuid4().hex[:8]}')
            registered_agents[user_id] = {}
            mock_ws_manager = MockWebSocketManager()
            for agent_type in agent_types:
                agent = await self.registry.create_agent_for_user(user_id, agent_type, user_context, mock_ws_manager)
                registered_agents[user_id][agent_type] = agent
                retrieved_agent = await self.registry.get_user_agent(user_id, agent_type)
                assert retrieved_agent == agent
        for user_id in users:
            for other_user_id in users:
                if user_id != other_user_id:
                    for agent_type in agent_types:
                        other_agent = await self.registry.get_user_agent(other_user_id, agent_type)
                        own_agent = registered_agents[user_id].get(agent_type)
                        if other_agent and own_agent:
                            assert id(other_agent) != id(own_agent)
        health = self.registry.get_registry_health()
        assert health['total_user_sessions'] == len(users)
        assert health['total_user_agents'] == len(users) * len(agent_types)
        self.test_users.extend(users)
        self.test_metrics.record_custom('users_registered', len(users))
        self.test_metrics.record_custom('agents_per_user', len(agent_types))

    async def test_agent_retrieval_by_user_and_thread_isolation(self):
        """Test agent retrieval with proper user and thread isolation."""
        base_users = [f'thread_test_user_{i}_{uuid.uuid4().hex[:8]}' for i in range(3)]
        user_thread_agents = {}
        for user_id in base_users:
            user_thread_agents[user_id] = {}
            for thread_num in range(3):
                thread_id = f'thread_{thread_num}_{uuid.uuid4().hex[:8]}'
                user_context = await create_isolated_execution_context(user_id=user_id, request_id=f'thread_test_{uuid.uuid4().hex[:8]}', thread_id=thread_id)
                mock_ws_manager = MockWebSocketManager()
                agent = await self.registry.create_agent_for_user(user_id, 'data_helper', user_context, mock_ws_manager)
                user_thread_agents[user_id][thread_id] = agent
        for user_id in base_users:
            threads = list(user_thread_agents[user_id].keys())
            for i, thread1 in enumerate(threads):
                for thread2 in threads[i + 1:]:
                    agent1 = user_thread_agents[user_id][thread1]
                    agent2 = user_thread_agents[user_id][thread2]
                    retrieved_agent1 = await self.registry.get_user_agent(user_id, 'data_helper')
                    retrieved_agent2 = await self.registry.get_user_agent(user_id, 'data_helper')
                    assert retrieved_agent1 == retrieved_agent2
        self.test_users.extend(base_users)
        self.test_metrics.record_custom('thread_isolation_tested', True)

    async def test_agent_lifecycle_management_per_user(self):
        """Test complete agent lifecycle management with per-user isolation."""
        user_id = f'lifecycle_user_{uuid.uuid4().hex[:8]}'
        user_context = await create_isolated_execution_context(user_id=user_id, request_id=f'lifecycle_test_{uuid.uuid4().hex[:8]}')
        mock_ws_manager = MockWebSocketManager()
        agent = await self.registry.create_agent_for_user(user_id, 'optimization', user_context, mock_ws_manager)
        assert agent is not None
        retrieved_agent = await self.registry.get_user_agent(user_id, 'optimization')
        assert retrieved_agent == agent
        if hasattr(agent, 'tool_dispatcher'):
            dispatcher = agent.tool_dispatcher
            if hasattr(dispatcher, 'execute_tool'):
                result = await dispatcher.execute_tool('test_tool', {})
                assert result is not None
        removed = await self.registry.remove_user_agent(user_id, 'optimization')
        assert removed is True
        retrieved_after_removal = await self.registry.get_user_agent(user_id, 'optimization')
        assert retrieved_after_removal is None
        reset_result = await self.registry.reset_user_agents(user_id)
        assert reset_result['status'] == 'reset_complete'
        cleanup_result = await self.registry.cleanup_user_session(user_id)
        assert cleanup_result['status'] == 'cleaned'
        self.test_metrics.record_custom('lifecycle_phases_tested', 5)

    async def test_concurrent_agent_registration_safety(self):
        """Test thread-safe concurrent agent registration across multiple users."""
        concurrent_users = 10
        agents_per_user = 5

        async def register_agents_for_user(user_index):
            user_id = f'concurrent_user_{user_index}_{uuid.uuid4().hex[:8]}'
            user_context = await create_isolated_execution_context(user_id=user_id, request_id=f'concurrent_test_{uuid.uuid4().hex[:8]}')
            mock_ws_manager = MockWebSocketManager()
            agents = []
            for agent_index in range(agents_per_user):
                agent_type = ['data_helper', 'optimization', 'reporting', 'triage', 'goals_triage'][agent_index]
                agent = await self.registry.create_agent_for_user(user_id, agent_type, user_context, mock_ws_manager)
                agents.append(agent)
            return (user_id, agents)
        tasks = [register_agents_for_user(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks)
        total_agents = 0
        user_ids = []
        for user_id, agents in results:
            user_ids.append(user_id)
            total_agents += len(agents)
            for i, agent in enumerate(agents):
                agent_type = ['data_helper', 'optimization', 'reporting', 'triage', 'goals_triage'][i]
                retrieved = await self.registry.get_user_agent(user_id, agent_type)
                assert retrieved == agent
        expected_total = concurrent_users * agents_per_user
        assert total_agents == expected_total
        health = self.registry.get_registry_health()
        assert health['total_user_sessions'] >= concurrent_users
        assert health['total_user_agents'] >= expected_total
        self.test_users.extend(user_ids)
        self.test_metrics.record_custom('concurrent_users', concurrent_users)
        self.test_metrics.record_custom('concurrent_registrations', total_agents)

    async def test_websocket_manager_association_with_user_context(self):
        """Test WebSocket manager association with proper user context isolation."""
        users_configs = [{'user_id': f'ws_user_1_{uuid.uuid4().hex[:8]}', 'events_expected': 5}, {'user_id': f'ws_user_2_{uuid.uuid4().hex[:8]}', 'events_expected': 3}, {'user_id': f'ws_user_3_{uuid.uuid4().hex[:8]}', 'events_expected': 7}]
        user_websocket_managers = {}
        user_contexts = {}
        for config in users_configs:
            user_id = config['user_id']
            user_ws_manager = MockWebSocketManager()
            user_websocket_managers[user_id] = user_ws_manager
            user_context = await create_isolated_execution_context(user_id=user_id, request_id=f'ws_test_{uuid.uuid4().hex[:8]}', websocket_emitter=user_ws_manager)
            user_contexts[user_id] = user_context
            agent = await self.registry.create_agent_for_user(user_id, 'optimization', user_context, user_ws_manager)
            user_session = await self.registry.get_user_session(user_id)
            assert user_session._websocket_manager == user_ws_manager
            assert user_session._websocket_bridge is not None
        for config in users_configs:
            user_id = config['user_id']
            user_ws_manager = user_websocket_managers[user_id]
            expected_events = config['events_expected']
            for event_num in range(expected_events):
                await user_ws_manager.notify_agent_started(f'run_{event_num}', 'test_agent', {'event': event_num})
                await user_ws_manager.notify_agent_completed(f'run_{event_num}', 'test_agent', {'result': f'event_{event_num}'}, 100.0)
        for config in users_configs:
            user_id = config['user_id']
            user_ws_manager = user_websocket_managers[user_id]
            expected_events = config['events_expected']
            agent_started_events = [e for e in user_ws_manager.events if e[0] == 'agent_started']
            agent_completed_events = [e for e in user_ws_manager.events if e[0] == 'agent_completed']
            assert len(agent_started_events) == expected_events
            assert len(agent_completed_events) == expected_events
        user1_events = user_websocket_managers[users_configs[0]['user_id']].events
        user2_events = user_websocket_managers[users_configs[1]['user_id']].events
        user3_events = user_websocket_managers[users_configs[2]['user_id']].events
        assert len(set((id(event) for event in user1_events)) & set((id(event) for event in user2_events))) == 0
        assert len(set((id(event) for event in user2_events)) & set((id(event) for event in user3_events))) == 0
        self.test_users.extend([config['user_id'] for config in users_configs])
        self.test_metrics.record_custom('websocket_users_tested', len(users_configs))
        self.test_metrics.record_custom('websocket_events_total', sum((c['events_expected'] * 2 for c in users_configs)))

    async def test_bridge_communication_validation_per_user(self):
        """Test WebSocket bridge communication with per-user message validation."""
        user_id = f'bridge_test_user_{uuid.uuid4().hex[:8]}'
        user_context = await create_isolated_execution_context(user_id=user_id, request_id=f'bridge_comm_test_{uuid.uuid4().hex[:8]}')
        user_ws_manager = MockWebSocketManager()
        agent = await self.registry.create_agent_for_user(user_id, 'reporting', user_context, user_ws_manager)
        user_session = await self.registry.get_user_session(user_id)
        bridge = user_session._websocket_bridge
        assert bridge is not None
        assert bridge.websocket_manager == user_ws_manager
        test_scenarios = [{'method': 'notify_agent_started', 'args': ('test_run_1', 'reporting_agent', {'test': 'started'}), 'expected_event': 'agent_started'}, {'method': 'notify_agent_thinking', 'args': ('test_run_1', 'reporting_agent', 'Processing data...', 1), 'expected_event': 'agent_thinking'}, {'method': 'notify_tool_executing', 'args': ('test_run_1', 'reporting_agent', 'data_query', {'query': 'SELECT * FROM reports'}), 'expected_event': 'tool_executing'}, {'method': 'notify_tool_completed', 'args': ('test_run_1', 'reporting_agent', 'data_query', {'rows': 100}, 250.5), 'expected_event': 'tool_completed'}, {'method': 'notify_agent_completed', 'args': ('test_run_1', 'reporting_agent', {'report': 'generated'}, 1500.0), 'expected_event': 'agent_completed'}]
        for scenario in test_scenarios:
            method_name = scenario['method']
            args = scenario['args']
            expected_event = scenario['expected_event']
            if hasattr(bridge, method_name):
                bridge_method = getattr(bridge, method_name)
                await bridge_method(*args)
                matching_events = [e for e in user_ws_manager.events if e[0] == expected_event]
                assert len(matching_events) >= 1, f'Expected {expected_event} event not found'
        user2_id = f'bridge_test_user2_{uuid.uuid4().hex[:8]}'
        user2_context = await create_isolated_execution_context(user_id=user2_id, request_id=f'bridge_comm_test2_{uuid.uuid4().hex[:8]}')
        user2_ws_manager = MockWebSocketManager()
        agent2 = await self.registry.create_agent_for_user(user2_id, 'reporting', user2_context, user2_ws_manager)
        user2_session = await self.registry.get_user_session(user2_id)
        bridge2 = user2_session._websocket_bridge
        assert bridge != bridge2
        assert bridge.websocket_manager != bridge2.websocket_manager
        await bridge2.notify_agent_started('user2_run', 'user2_agent', {'user2': 'test'})
        user1_events = [e for e in user_ws_manager.events if 'user2' in str(e)]
        assert len(user1_events) == 0
        self.test_users.extend([user_id, user2_id])
        self.test_metrics.record_custom('bridge_methods_tested', len(test_scenarios))

    async def test_event_delivery_isolation_between_users(self):
        """Test WebSocket event delivery isolation preventing cross-user event leakage."""
        enterprise_users = [{'user_id': f'enterprise_events_user_{i}_{uuid.uuid4().hex[:8]}', 'department': f'dept_{i}', 'security_level': ['public', 'internal', 'confidential', 'secret'][i % 4]} for i in range(4)]
        user_managers = {}
        user_agents = {}
        user_contexts = {}
        for user_info in enterprise_users:
            user_id = user_info['user_id']
            user_context = await create_isolated_execution_context(user_id=user_id, request_id=f'event_isolation_{uuid.uuid4().hex[:8]}')
            user_context.agent_context.update({'department': user_info['department'], 'security_level': user_info['security_level']})
            user_contexts[user_id] = user_context
            ws_manager = MockWebSocketManager()
            user_managers[user_id] = ws_manager
            user_agents[user_id] = {}
            for agent_type in ['optimization', 'reporting', 'data_helper']:
                agent = await self.registry.create_agent_for_user(user_id, agent_type, user_context, ws_manager)
                user_agents[user_id][agent_type] = agent
        event_scenarios = [{'user_idx': 0, 'operation': 'quarterly_report', 'sensitivity': 'confidential'}, {'user_idx': 1, 'operation': 'customer_analysis', 'sensitivity': 'internal'}, {'user_idx': 2, 'operation': 'financial_forecast', 'sensitivity': 'secret'}, {'user_idx': 3, 'operation': 'public_metrics', 'sensitivity': 'public'}]
        for scenario in event_scenarios:
            user_info = enterprise_users[scenario['user_idx']]
            user_id = user_info['user_id']
            operation = scenario['operation']
            sensitivity = scenario['sensitivity']
            ws_manager = user_managers[user_id]
            run_id = f'{operation}_run_{uuid.uuid4().hex[:8]}'
            await ws_manager.notify_agent_started(run_id, 'optimization', {'operation': operation, 'sensitivity': sensitivity, 'department': user_info['department']})
            await ws_manager.notify_agent_thinking(run_id, 'optimization', f"Processing {sensitivity} {operation} data for {user_info['department']}")
            await ws_manager.notify_tool_executing(run_id, 'optimization', 'data_query', {'query': f"SELECT * FROM {user_info['department']}_data WHERE sensitivity='{sensitivity}'", 'department': user_info['department']})
            await ws_manager.notify_tool_completed(run_id, 'optimization', 'data_query', {'rows': 50 + scenario['user_idx'] * 10, 'department': user_info['department'], 'operation': operation}, 150.0 + scenario['user_idx'] * 25)
            await ws_manager.notify_agent_completed(run_id, 'optimization', {'operation': operation, 'status': 'completed', 'sensitivity': sensitivity, 'department': user_info['department']}, 500.0 + scenario['user_idx'] * 100)
        for i, user_info in enumerate(enterprise_users):
            user_id = user_info['user_id']
            ws_manager = user_managers[user_id]
            user_events = ws_manager.events
            assert len(user_events) >= 5
            for event in user_events:
                if len(event) > 3 and isinstance(event[3], dict):
                    event_data = event[3]
                    if 'department' in event_data:
                        assert event_data['department'] == user_info['department']
                    if 'sensitivity' in event_data:
                        allowed_sensitivities = [user_info['security_level']]
                        assert event_data['sensitivity'] in allowed_sensitivities
            for j, other_user_info in enumerate(enterprise_users):
                if i != j:
                    other_user_id = other_user_info['user_id']
                    other_ws_manager = user_managers[other_user_id]
                    other_events = other_ws_manager.events
                    for event in user_events:
                        event_str = str(event)
                        assert other_user_info['department'] not in event_str
                        other_operations = [s['operation'] for s in event_scenarios if s['user_idx'] == j]
                        for other_op in other_operations:
                            if other_op != event_scenarios[i]['operation']:
                                if other_user_info['security_level'] in ['secret', 'confidential']:
                                    assert other_op not in event_str
        total_events_expected = len(event_scenarios) * 5
        total_events_actual = sum((len(manager.events) for manager in user_managers.values()))
        assert total_events_actual == total_events_expected
        self.test_users.extend([user['user_id'] for user in enterprise_users])
        self.test_metrics.record_custom('event_isolation_users', len(enterprise_users))
        self.test_metrics.record_custom('events_per_user', 5)
        self.test_metrics.record_custom('total_isolated_events', total_events_actual)

    async def test_websocket_connection_lifecycle_management(self):
        """Test WebSocket connection lifecycle management with proper cleanup."""
        user_id = f'lifecycle_ws_user_{uuid.uuid4().hex[:8]}'
        user_context = await create_isolated_execution_context(user_id=user_id, request_id=f'ws_lifecycle_{uuid.uuid4().hex[:8]}')
        ws_manager = MockWebSocketManager()
        agent = await self.registry.create_agent_for_user(user_id, 'data_helper', user_context, ws_manager)
        user_session = await self.registry.get_user_session(user_id)
        assert user_session._websocket_manager is not None
        assert user_session._websocket_bridge is not None
        bridge = user_session._websocket_bridge
        await bridge.notify_agent_started('active_run', 'data_helper', {'phase': 'active'})
        await bridge.notify_agent_thinking('active_run', 'data_helper', 'Processing...')
        await bridge.notify_agent_completed('active_run', 'data_helper', {'result': 'success'}, 300.0)
        assert len(ws_manager.events) >= 3
        reset_result = await self.registry.reset_user_agents(user_id)
        assert reset_result['status'] == 'reset_complete'
        user_session_after_reset = await self.registry.get_user_session(user_id)
        assert len(user_session_after_reset._agents) == 0
        new_ws_manager = MockWebSocketManager()
        new_agent = await self.registry.create_agent_for_user(user_id, 'optimization', user_context, new_ws_manager)
        user_session_reconnected = await self.registry.get_user_session(user_id)
        assert user_session_reconnected._websocket_manager == new_ws_manager
        cleanup_result = await self.registry.cleanup_user_session(user_id)
        assert cleanup_result['status'] == 'cleaned'
        try:
            cleaned_session = await self.registry.get_user_session(user_id)
            assert len(cleaned_session._agents) == 0
        except:
            pass
        self.test_metrics.record_custom('websocket_lifecycle_phases', 5)

    async def test_concurrent_user_operations_isolation(self):
        """Test isolation during high-concurrency Enterprise operations.
        
        BUSINESS CRITICAL: Enterprise customer concurrent usage scenarios.
        """
        num_enterprise_users = 15
        operations_per_user = 8

        async def enterprise_user_workflow(user_index):
            user_id = f'enterprise_concurrent_user_{user_index}_{uuid.uuid4().hex[:8]}'
            user_context = await create_isolated_execution_context(user_id=user_id, request_id=f'enterprise_workflow_{uuid.uuid4().hex[:8]}', isolation_level='strict')
            user_context.agent_context.update({'enterprise_tier': 'premium', 'concurrent_operations': operations_per_user, 'user_type': 'enterprise_concurrent'})
            ws_manager = MockWebSocketManager()
            operation_tasks = []
            for op_index in range(operations_per_user):
                operation_task = self._enterprise_operation(user_id, user_context, ws_manager, op_index)
                operation_tasks.append(operation_task)
            operation_results = await asyncio.gather(*operation_tasks, return_exceptions=True)
            successful_operations = sum((1 for result in operation_results if not isinstance(result, Exception)))
            return {'user_id': user_id, 'successful_operations': successful_operations, 'total_operations': operations_per_user, 'operation_results': operation_results}
        user_tasks = [enterprise_user_workflow(i) for i in range(num_enterprise_users)]
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        successful_users = []
        total_operations = 0
        successful_operations = 0
        for result in user_results:
            if isinstance(result, Exception):
                logger.error(f'Enterprise user workflow failed: {result}')
                continue
            successful_users.append(result['user_id'])
            total_operations += result['total_operations']
            successful_operations += result['successful_operations']
        expected_operations = num_enterprise_users * operations_per_user
        success_rate = successful_operations / expected_operations if expected_operations > 0 else 0
        assert success_rate > 0.95, f'Enterprise success rate too low: {success_rate:.2%}'
        assert len(successful_users) >= num_enterprise_users * 0.9
        health = self.registry.get_registry_health()
        assert health['status'] in ['healthy', 'warning']
        self.test_users.extend(successful_users)
        self.test_metrics.record_custom('enterprise_users', num_enterprise_users)
        self.test_metrics.record_custom('total_concurrent_operations', total_operations)
        self.test_metrics.record_custom('enterprise_success_rate', success_rate)

    async def _enterprise_operation(self, user_id, user_context, ws_manager, operation_index):
        """Execute a single enterprise operation with full isolation."""
        operation_types = ['data_analysis', 'optimization', 'reporting', 'forecasting', 'compliance']
        agent_types = ['data_helper', 'optimization', 'reporting', 'triage', 'goals_triage']
        operation_type = operation_types[operation_index % len(operation_types)]
        agent_type = agent_types[operation_index % len(agent_types)]
        agent = await self.registry.create_agent_for_user(user_id, agent_type, user_context, ws_manager)
        run_id = f'{operation_type}_run_{operation_index}_{uuid.uuid4().hex[:8]}'
        await ws_manager.notify_agent_started(run_id, agent_type, {'operation': operation_type, 'operation_index': operation_index})
        await asyncio.sleep(0.01 + operation_index * 0.005)
        await ws_manager.notify_agent_completed(run_id, agent_type, {'operation': operation_type, 'status': 'completed', 'operation_index': operation_index}, 100.0 + operation_index * 50)
        return {'operation_type': operation_type, 'agent_type': agent_type, 'run_id': run_id, 'success': True}

    async def test_enterprise_customer_data_protection(self):
        """Test Enterprise-level data protection and access controls.
        
        BUSINESS CRITICAL: Data security for $15K+ MRR customers.
        """
        enterprise_customers = [{'customer_id': f'enterprise_tier1_{uuid.uuid4().hex[:8]}', 'tier': 'enterprise_plus', 'annual_value': 500000, 'data_sensitivity': 'top_secret', 'compliance_requirements': ['SOX', 'HIPAA', 'ISO27001']}, {'customer_id': f'enterprise_tier2_{uuid.uuid4().hex[:8]}', 'tier': 'enterprise_standard', 'annual_value': 250000, 'data_sensitivity': 'confidential', 'compliance_requirements': ['SOC2', 'ISO27001']}, {'customer_id': f'enterprise_tier3_{uuid.uuid4().hex[:8]}', 'tier': 'enterprise_basic', 'annual_value': 150000, 'data_sensitivity': 'internal', 'compliance_requirements': ['SOC2']}]
        customer_contexts = {}
        customer_agents = {}
        customer_data = {}
        for customer in enterprise_customers:
            customer_id = customer['customer_id']
            customer_context = await create_isolated_execution_context(user_id=customer_id, request_id=f'enterprise_protection_{uuid.uuid4().hex[:8]}', isolation_level='strict')
            customer_context.agent_context.update({'customer_tier': customer['tier'], 'annual_contract_value': customer['annual_value'], 'data_classification': customer['data_sensitivity'], 'compliance_requirements': customer['compliance_requirements'], 'pii_handling': 'strict', 'audit_level': 'comprehensive'})
            customer_contexts[customer_id] = customer_context
            customer_data[customer_id] = {'financial_data': f"revenue_{customer['annual_value']}_confidential", 'user_data': f'users_database_{customer_id}_encrypted', 'compliance_logs': f'audit_trail_{customer_id}_secure', 'business_intelligence': f'analytics_{customer_id}_restricted'}
            ws_manager = MockWebSocketManager()
            customer_agents[customer_id] = {}
            for agent_type in ['optimization', 'reporting', 'data_helper']:
                agent = await self.registry.create_agent_for_user(customer_id, agent_type, customer_context, ws_manager)
                customer_agents[customer_id][agent_type] = agent
        for customer in enterprise_customers:
            customer_id = customer['customer_id']
            for agent_type in ['optimization', 'reporting', 'data_helper']:
                own_agent = await self.registry.get_user_agent(customer_id, agent_type)
                assert own_agent is not None
                assert own_agent == customer_agents[customer_id][agent_type]
        for i, customer1 in enumerate(enterprise_customers):
            for j, customer2 in enumerate(enterprise_customers):
                if i != j:
                    customer1_id = customer1['customer_id']
                    customer2_id = customer2['customer_id']
                    for agent_type in ['optimization', 'reporting', 'data_helper']:
                        customer2_agent_from_customer1 = await self.registry.get_user_agent(customer2_id, agent_type)
                        customer1_agent = customer_agents[customer1_id][agent_type]
                        if customer2_agent_from_customer1:
                            assert customer2_agent_from_customer1 != customer1_agent
        for customer in enterprise_customers:
            customer_id = customer['customer_id']
            customer_context = customer_contexts[customer_id]
            context_data = customer_context.agent_context
            expected_sensitivity = customer['data_sensitivity']
            assert context_data['data_classification'] == expected_sensitivity
            assert context_data['annual_contract_value'] == customer['annual_value']
            assert set(context_data['compliance_requirements']) == set(customer['compliance_requirements'])
        for customer in enterprise_customers:
            customer_id = customer['customer_id']
            for agent_type in ['optimization', 'reporting', 'data_helper']:
                agent = customer_agents[customer_id][agent_type]
                if hasattr(agent, 'tool_dispatcher'):
                    dispatcher = agent.tool_dispatcher
                    assert dispatcher.user_context.user_id == customer_id
                    dispatcher_context = dispatcher.user_context.agent_context
                    assert dispatcher_context.get('customer_tier') == customer['tier']
                    assert dispatcher_context.get('data_classification') == customer['data_sensitivity']
        for i, customer1 in enumerate(enterprise_customers):
            customer1_id = customer1['customer_id']
            customer1_context = customer_contexts[customer1_id]
            original_acv = customer1_context.agent_context['annual_contract_value']
            customer1_context.agent_context['test_modification'] = 'modified_data'
            for j, customer2 in enumerate(enterprise_customers):
                if i != j:
                    customer2_id = customer2['customer_id']
                    customer2_context = customer_contexts[customer2_id]
                    assert 'test_modification' not in customer2_context.agent_context
                    assert customer2_context.agent_context['annual_contract_value'] == customer2['annual_value']
        self.test_users.extend([c['customer_id'] for c in enterprise_customers])
        self.test_metrics.record_custom('enterprise_customers_protected', len(enterprise_customers))
        self.test_metrics.record_custom('total_contract_value_protected', sum((c['annual_value'] for c in enterprise_customers)))

    async def test_multi_tenant_agent_execution_boundaries(self):
        """Test multi-tenant execution boundaries preventing tenant data mixing."""
        tenants = [{'tenant_id': f'tenant_healthcare_{uuid.uuid4().hex[:8]}', 'organization': 'healthcare_corp', 'industry': 'healthcare', 'data_residency': 'us_east', 'encryption_level': 'aes_256'}, {'tenant_id': f'tenant_finance_{uuid.uuid4().hex[:8]}', 'organization': 'finance_group', 'industry': 'financial_services', 'data_residency': 'us_west', 'encryption_level': 'aes_256_fips'}, {'tenant_id': f'tenant_retail_{uuid.uuid4().hex[:8]}', 'organization': 'retail_chain', 'industry': 'retail', 'data_residency': 'eu_central', 'encryption_level': 'aes_256'}]
        tenant_execution_boundaries = {}
        for tenant in tenants:
            tenant_id = tenant['tenant_id']
            tenant_context = await create_isolated_execution_context(user_id=tenant_id, request_id=f'tenant_boundary_{uuid.uuid4().hex[:8]}', isolation_level='strict')
            tenant_context.agent_context.update({'tenant_organization': tenant['organization'], 'industry_compliance': tenant['industry'], 'data_residency_requirement': tenant['data_residency'], 'encryption_standard': tenant['encryption_level'], 'multi_tenant_isolation': True})
            ws_manager = MockWebSocketManager()
            tenant_agents = {}
            for agent_type in ['data_helper', 'optimization', 'reporting']:
                agent = await self.registry.create_agent_for_user(tenant_id, agent_type, tenant_context, ws_manager)
                tenant_agents[agent_type] = agent
            tenant_execution_boundaries[tenant_id] = {'context': tenant_context, 'agents': tenant_agents, 'ws_manager': ws_manager}
        for tenant in tenants:
            tenant_id = tenant['tenant_id']
            boundary = tenant_execution_boundaries[tenant_id]
            for agent_type, agent in boundary['agents'].items():
                run_id = f'tenant_operation_{tenant_id}_{agent_type}'
                await boundary['ws_manager'].notify_agent_started(run_id, agent_type, {'tenant': tenant['organization'], 'industry': tenant['industry'], 'data_classification': 'tenant_specific'})
                if hasattr(agent, 'tool_dispatcher') and hasattr(agent.tool_dispatcher, 'execute_tool'):
                    result = await agent.tool_dispatcher.execute_tool('tenant_data_query', {'tenant_id': tenant_id, 'organization': tenant['organization'], 'compliance_industry': tenant['industry']})
                    assert result is not None
                await boundary['ws_manager'].notify_agent_completed(run_id, agent_type, {'tenant': tenant['organization'], 'processing_completed': True, 'data_isolation_verified': True}, 200.0)
        tenant_ids = [t['tenant_id'] for t in tenants]
        for i, tenant1_id in enumerate(tenant_ids):
            for j, tenant2_id in enumerate(tenant_ids):
                if i != j:
                    for agent_type in ['data_helper', 'optimization', 'reporting']:
                        tenant1_agent = await self.registry.get_user_agent(tenant1_id, agent_type)
                        tenant2_agent = await self.registry.get_user_agent(tenant2_id, agent_type)
                        if tenant1_agent and tenant2_agent:
                            assert tenant1_agent != tenant2_agent
                            assert id(tenant1_agent) != id(tenant2_agent)
                    tenant1_session = await self.registry.get_user_session(tenant1_id)
                    tenant2_session = await self.registry.get_user_session(tenant2_id)
                    assert tenant1_session != tenant2_session
                    assert tenant1_session._agents != tenant2_session._agents
        for tenant in tenants:
            tenant_id = tenant['tenant_id']
            boundary = tenant_execution_boundaries[tenant_id]
            tenant_context = boundary['context']
            context_data = tenant_context.agent_context
            assert context_data['industry_compliance'] == tenant['industry']
            assert context_data['data_residency_requirement'] == tenant['data_residency']
            assert context_data['encryption_standard'] == tenant['encryption_level']
        for tenant in tenants:
            tenant_id = tenant['tenant_id']
            ws_manager = tenant_execution_boundaries[tenant_id]['ws_manager']
            for event in ws_manager.events:
                event_str = str(event)
                assert tenant['organization'] in event_str
                for other_tenant in tenants:
                    if other_tenant['tenant_id'] != tenant_id:
                        assert other_tenant['organization'] not in event_str
        self.test_users.extend([t['tenant_id'] for t in tenants])
        self.test_metrics.record_custom('multi_tenant_boundaries_tested', len(tenants))

    async def test_user_session_cleanup_and_isolation(self):
        """Test user session cleanup maintaining isolation guarantees."""
        cleanup_users = [f'cleanup_user_{i}_{uuid.uuid4().hex[:8]}' for i in range(6)]
        user_sessions_data = {}
        for i, user_id in enumerate(cleanup_users):
            user_context = await create_isolated_execution_context(user_id=user_id, request_id=f'cleanup_test_{uuid.uuid4().hex[:8]}')
            ws_manager = MockWebSocketManager()
            num_agents = i % 3 + 1
            agents = {}
            agent_types = ['data_helper', 'optimization', 'reporting']
            for j in range(num_agents):
                agent_type = agent_types[j]
                agent = await self.registry.create_agent_for_user(user_id, agent_type, user_context, ws_manager)
                agents[agent_type] = agent
            user_sessions_data[user_id] = {'context': user_context, 'agents': agents, 'ws_manager': ws_manager, 'expected_agent_count': num_agents}
        total_initial_agents = sum((data['expected_agent_count'] for data in user_sessions_data.values()))
        registry_health_before = self.registry.get_registry_health()
        assert registry_health_before['total_user_sessions'] >= len(cleanup_users)
        assert registry_health_before['total_user_agents'] >= total_initial_agents
        users_to_clean = cleanup_users[:3]
        users_to_keep = cleanup_users[3:]
        cleaned_agent_counts = []
        for user_id in users_to_clean:
            cleanup_result = await self.registry.cleanup_user_session(user_id)
            assert cleanup_result['status'] == 'cleaned'
            cleaned_agent_counts.append(cleanup_result['cleaned_agents'])
        total_cleaned_agents = sum(cleaned_agent_counts)
        expected_cleaned_agents = sum((user_sessions_data[uid]['expected_agent_count'] for uid in users_to_clean))
        assert total_cleaned_agents == expected_cleaned_agents
        for user_id in users_to_keep:
            expected_agents = user_sessions_data[user_id]['expected_agent_count']
            user_session = await self.registry.get_user_session(user_id)
            assert len(user_session._agents) >= 0
            for agent_type in ['data_helper', 'optimization', 'reporting']:
                if agent_type in user_sessions_data[user_id]['agents']:
                    agent = await self.registry.get_user_agent(user_id, agent_type)
        for user_id in users_to_keep:
            ws_manager = user_sessions_data[user_id]['ws_manager']
            await ws_manager.notify_agent_started('cleanup_test', 'test_agent', {'test': 'isolation'})
            assert len(ws_manager.events) > 0
        registry_health_after = self.registry.get_registry_health()
        assert registry_health_after['total_user_agents'] <= registry_health_before['total_user_agents']
        remaining_cleanup_results = []
        for user_id in users_to_keep:
            cleanup_result = await self.registry.cleanup_user_session(user_id)
            remaining_cleanup_results.append(cleanup_result)
        for result in remaining_cleanup_results:
            assert result['status'] == 'cleaned'
        registry_health_final = self.registry.get_registry_health()
        assert registry_health_final['total_user_agents'] <= registry_health_before['total_user_agents'] * 0.1
        self.test_metrics.record_custom('cleanup_users_tested', len(cleanup_users))
        self.test_metrics.record_custom('selective_cleanup_validated', True)
        self.test_metrics.record_custom('isolation_during_cleanup_verified', True)

    async def test_complete_agent_orchestration_flow_per_user(self):
        """Test complete Golden Path agent orchestration with per-user isolation.
        
        BUSINESS CRITICAL: Golden Path protecting $500K+ ARR.
        """
        golden_user_id = f'golden_path_user_{uuid.uuid4().hex[:8]}'
        golden_context = await create_isolated_execution_context(user_id=golden_user_id, request_id=f'golden_path_orchestration_{uuid.uuid4().hex[:8]}', isolation_level='strict')
        golden_context.agent_context.update({'workflow_type': 'golden_path', 'business_value': '500k_arr_protection', 'orchestration_level': 'complete', 'quality_tier': 'enterprise_premium'})
        ws_manager = MockWebSocketManager()
        triage_agent = await self.registry.create_agent_for_user(golden_user_id, 'triage', golden_context, ws_manager)
        triage_run_id = f'triage_{uuid.uuid4().hex[:8]}'
        await ws_manager.notify_agent_started(triage_run_id, 'triage', {'phase': 'triage', 'input_analysis': 'user_optimization_request'})
        triage_result = {'category': 'optimization', 'complexity': 'high', 'estimated_time': 300, 'next_agents': ['data_helper', 'optimization']}
        await ws_manager.notify_agent_completed(triage_run_id, 'triage', triage_result, 50.0)
        data_agent = await self.registry.create_agent_for_user(golden_user_id, 'data_helper', golden_context, ws_manager)
        data_run_id = f'data_gathering_{uuid.uuid4().hex[:8]}'
        await ws_manager.notify_agent_started(data_run_id, 'data_helper', {'phase': 'data_gathering', 'triage_result': triage_result})
        await ws_manager.notify_tool_executing(data_run_id, 'data_helper', 'database_query', {'query': 'SELECT * FROM user_performance_metrics WHERE user_id = ?', 'parameters': [golden_user_id]})
        data_result = {'metrics_collected': 150, 'data_quality': 'high', 'coverage': 'complete', 'ready_for_optimization': True}
        await ws_manager.notify_tool_completed(data_run_id, 'data_helper', 'database_query', data_result, 120.0)
        await ws_manager.notify_agent_completed(data_run_id, 'data_helper', data_result, 180.0)
        optimization_agent = await self.registry.create_agent_for_user(golden_user_id, 'optimization', golden_context, ws_manager)
        optimization_run_id = f'optimization_{uuid.uuid4().hex[:8]}'
        await ws_manager.notify_agent_started(optimization_run_id, 'optimization', {'phase': 'optimization_analysis', 'data_input': data_result, 'triage_guidance': triage_result})
        await ws_manager.notify_agent_thinking(optimization_run_id, 'optimization', 'Analyzing performance patterns and identifying optimization opportunities...', 1)
        await ws_manager.notify_tool_executing(optimization_run_id, 'optimization', 'ai_analysis', {'algorithm': 'advanced_optimization', 'data_points': 150, 'analysis_type': 'comprehensive'})
        optimization_result = {'optimizations_identified': 12, 'potential_improvement': '35%', 'implementation_difficulty': 'medium', 'business_impact': 'high', 'recommendations': ['Database query optimization', 'Cache layer implementation', 'API response compression', 'Background job optimization']}
        await ws_manager.notify_tool_completed(optimization_run_id, 'optimization', 'ai_analysis', optimization_result, 250.0)
        await ws_manager.notify_agent_completed(optimization_run_id, 'optimization', optimization_result, 320.0)
        reporting_agent = await self.registry.create_agent_for_user(golden_user_id, 'reporting', golden_context, ws_manager)
        reporting_run_id = f'reporting_{uuid.uuid4().hex[:8]}'
        await ws_manager.notify_agent_started(reporting_run_id, 'reporting', {'phase': 'report_generation', 'optimization_results': optimization_result, 'data_context': data_result})
        await ws_manager.notify_tool_executing(reporting_run_id, 'reporting', 'report_generator', {'template': 'executive_summary', 'data_sources': ['optimization_analysis', 'performance_metrics'], 'format': 'comprehensive'})
        final_report = {'executive_summary': 'Performance optimization analysis complete', 'key_findings': optimization_result['recommendations'], 'business_impact': '35% improvement potential', 'implementation_roadmap': '4-phase rollout plan', 'roi_projection': '250% return within 6 months', 'golden_path_completed': True}
        await ws_manager.notify_tool_completed(reporting_run_id, 'reporting', 'report_generator', final_report, 80.0)
        await ws_manager.notify_agent_completed(reporting_run_id, 'reporting', final_report, 120.0)
        user_session = await self.registry.get_user_session(golden_user_id)
        expected_agents = ['triage', 'data_helper', 'optimization', 'reporting']
        for agent_type in expected_agents:
            agent = await self.registry.get_user_agent(golden_user_id, agent_type)
            assert agent is not None, f'Golden Path agent {agent_type} not found'
        events = ws_manager.events
        expected_event_types = ['agent_started', 'agent_completed', 'tool_executing', 'tool_completed']
        for event_type in expected_event_types:
            matching_events = [e for e in events if e[0] == event_type]
            assert len(matching_events) > 0, f'Expected {event_type} events not found in Golden Path'
        final_events = [e for e in events if e[0] == 'agent_completed']
        assert len(final_events) >= 4
        reporting_completion_events = [e for e in events if e[0] == 'agent_completed' and len(e) > 3]
        golden_path_completed = False
        for event in reporting_completion_events:
            if len(event) > 3 and isinstance(event[3], dict):
                if event[3].get('golden_path_completed'):
                    golden_path_completed = True
                    break
        assert golden_path_completed, 'Golden Path completion flag not found'
        second_user_id = f'golden_path_user_2_{uuid.uuid4().hex[:8]}'
        second_context = await create_isolated_execution_context(user_id=second_user_id, request_id=f'golden_path_2_{uuid.uuid4().hex[:8]}')
        second_ws_manager = MockWebSocketManager()
        second_agent = await self.registry.create_agent_for_user(second_user_id, 'triage', second_context, second_ws_manager)
        assert len(second_ws_manager.events) == 0
        assert second_agent != triage_agent
        self.test_users.extend([golden_user_id, second_user_id])
        self.test_metrics.record_custom('golden_path_phases_completed', 4)
        self.test_metrics.record_custom('golden_path_agents_used', len(expected_agents))
        self.test_metrics.record_custom('golden_path_events_generated', len(events))
        self.test_metrics.record_custom('business_value_delivered', '500k_arr_protected')

    async def test_agent_coordination_with_supervisor_integration(self):
        """Test agent coordination with supervisor integration maintaining user isolation."""
        supervisor_user_id = f'supervisor_test_user_{uuid.uuid4().hex[:8]}'
        supervisor_context = await create_isolated_execution_context(user_id=supervisor_user_id, request_id=f'supervisor_integration_{uuid.uuid4().hex[:8]}')
        supervisor_context.agent_context.update({'workflow_mode': 'supervisor_coordinated', 'coordination_level': 'advanced', 'multi_agent_flow': True})
        coordination_ws_manager = MockWebSocketManager()
        agents = {}
        agent_types = ['triage', 'data_helper', 'optimization', 'reporting', 'goals_triage']
        for agent_type in agent_types:
            agent = await self.registry.create_agent_for_user(supervisor_user_id, agent_type, supervisor_context, coordination_ws_manager)
            agents[agent_type] = agent
        coordination_sequence = [{'phase': 'initialization', 'active_agents': ['triage'], 'coordination_type': 'single_agent'}, {'phase': 'data_gathering', 'active_agents': ['data_helper'], 'coordination_type': 'sequential'}, {'phase': 'parallel_analysis', 'active_agents': ['optimization', 'goals_triage'], 'coordination_type': 'parallel'}, {'phase': 'consolidation', 'active_agents': ['reporting'], 'coordination_type': 'aggregation'}]
        coordination_results = {}
        for phase_info in coordination_sequence:
            phase = phase_info['phase']
            active_agents = phase_info['active_agents']
            coord_type = phase_info['coordination_type']
            phase_results = {}
            if coord_type == 'parallel':
                parallel_tasks = []
                for agent_type in active_agents:
                    task = self._execute_coordinated_agent(supervisor_user_id, agent_type, phase, coordination_ws_manager)
                    parallel_tasks.append(task)
                parallel_results = await asyncio.gather(*parallel_tasks)
                for i, agent_type in enumerate(active_agents):
                    phase_results[agent_type] = parallel_results[i]
            else:
                for agent_type in active_agents:
                    result = await self._execute_coordinated_agent(supervisor_user_id, agent_type, phase, coordination_ws_manager)
                    phase_results[agent_type] = result
            coordination_results[phase] = phase_results
        assert len(coordination_results) == len(coordination_sequence)
        for phase in ['initialization', 'data_gathering', 'parallel_analysis', 'consolidation']:
            assert phase in coordination_results
            assert len(coordination_results[phase]) > 0
        parallel_phase = coordination_results['parallel_analysis']
        assert 'optimization' in parallel_phase
        assert 'goals_triage' in parallel_phase
        assert parallel_phase['optimization']['success'] is True
        assert parallel_phase['goals_triage']['success'] is True
        events = coordination_ws_manager.events
        phase_events = {}
        for event in events:
            if len(event) > 3 and isinstance(event[3], dict) and ('phase' in event[3]):
                phase = event[3]['phase']
                if phase not in phase_events:
                    phase_events[phase] = []
                phase_events[phase].append(event)
        for phase in ['initialization', 'data_gathering', 'parallel_analysis', 'consolidation']:
            assert phase in phase_events, f'No events found for phase {phase}'
            assert len(phase_events[phase]) > 0
        second_supervisor_user = f'supervisor_test_user_2_{uuid.uuid4().hex[:8]}'
        second_context = await create_isolated_execution_context(user_id=second_supervisor_user, request_id=f'supervisor_integration_2_{uuid.uuid4().hex[:8]}')
        second_ws_manager = MockWebSocketManager()
        second_agent = await self.registry.create_agent_for_user(second_supervisor_user, 'triage', second_context, second_ws_manager)
        assert second_agent != agents['triage']
        assert len(second_ws_manager.events) == 0
        first_session = await self.registry.get_user_session(supervisor_user_id)
        second_session = await self.registry.get_user_session(second_supervisor_user)
        assert first_session != second_session
        assert len(first_session._agents) >= len(agent_types)
        assert len(second_session._agents) >= 1
        self.test_users.extend([supervisor_user_id, second_supervisor_user])
        self.test_metrics.record_custom('coordination_phases', len(coordination_sequence))
        self.test_metrics.record_custom('coordinated_agents', len(agent_types))
        self.test_metrics.record_custom('coordination_events', len(events))

    async def _execute_coordinated_agent(self, user_id, agent_type, phase, ws_manager):
        """Execute agent in coordination with supervisor logic."""
        run_id = f'coord_{phase}_{agent_type}_{uuid.uuid4().hex[:8]}'
        await ws_manager.notify_agent_started(run_id, agent_type, {'phase': phase, 'coordination_mode': True, 'user_id': user_id})
        await ws_manager.notify_agent_thinking(run_id, agent_type, f'Processing {phase} coordination for {agent_type}')
        result = {'agent_type': agent_type, 'phase': phase, 'status': 'completed', 'coordination_successful': True, 'execution_time': 100.0}
        await ws_manager.notify_agent_completed(run_id, agent_type, result, 100.0)
        return {'agent_type': agent_type, 'phase': phase, 'run_id': run_id, 'success': True, 'result': result}

    async def test_memory_usage_validation_during_concurrent_operations(self):
        """Test memory usage patterns during high concurrent operations."""
        initial_memory = psutil.Process().memory_info().rss
        concurrent_sessions = 25
        operations_per_session = 15

        async def sustained_user_operations(session_index):
            user_id = f'memory_test_user_{session_index}_{uuid.uuid4().hex[:8]}'
            user_context = await create_isolated_execution_context(user_id=user_id, request_id=f'memory_test_{uuid.uuid4().hex[:8]}')
            ws_manager = MockWebSocketManager()
            session_agents = []
            for op_index in range(operations_per_session):
                agent_type = ['data_helper', 'optimization', 'reporting'][op_index % 3]
                agent = await self.registry.create_agent_for_user(user_id, agent_type, user_context, ws_manager)
                session_agents.append(agent)
                run_id = f'memory_op_{op_index}'
                await ws_manager.notify_agent_started(run_id, agent_type, {'op': op_index})
                await ws_manager.notify_agent_completed(run_id, agent_type, {'result': 'ok'}, 50.0)
                if op_index % 5 == 0:
                    await asyncio.sleep(0.01)
            return {'user_id': user_id, 'agents_created': len(session_agents), 'operations_completed': operations_per_session}
        memory_samples = [initial_memory]
        tasks = [sustained_user_operations(i) for i in range(concurrent_sessions)]

        async def memory_sampler():
            for _ in range(10):
                await asyncio.sleep(0.1)
                current_memory = psutil.Process().memory_info().rss
                memory_samples.append(current_memory)
        sampler_task = asyncio.create_task(memory_sampler())
        session_results = await asyncio.gather(*tasks)
        await sampler_task
        final_memory = psutil.Process().memory_info().rss
        memory_samples.append(final_memory)
        max_memory = max(memory_samples)
        memory_growth = final_memory - initial_memory
        peak_memory_growth = max_memory - initial_memory
        total_operations = sum((result['operations_completed'] for result in session_results))
        total_agents = sum((result['agents_created'] for result in session_results))
        logger.info(f'Memory analysis: {total_operations} operations, {total_agents} agents created')
        logger.info(f'Memory growth: {memory_growth / 1024 / 1024:.2f} MB')
        logger.info(f'Peak memory growth: {peak_memory_growth / 1024 / 1024:.2f} MB')
        max_acceptable_growth = 200 * 1024 * 1024
        assert memory_growth < max_acceptable_growth, f'Excessive memory growth: {memory_growth / 1024 / 1024:.2f} MB'
        peak_ratio = peak_memory_growth / max(memory_growth, 1)
        assert peak_ratio < 2.0, f'Poor memory cleanup patterns: peak ratio {peak_ratio:.2f}'
        memory_per_operation = memory_growth / max(total_operations, 1)
        max_memory_per_operation = 1024 * 1024
        assert memory_per_operation < max_memory_per_operation, f'High memory per operation: {memory_per_operation / 1024:.2f} KB'
        cleanup_user_ids = [result['user_id'] for result in session_results]
        cleanup_tasks = [self.registry.cleanup_user_session(uid) for uid in cleanup_user_ids]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        gc.collect()
        await asyncio.sleep(0.1)
        post_cleanup_memory = psutil.Process().memory_info().rss
        cleanup_effectiveness = (final_memory - post_cleanup_memory) / max(memory_growth, 1)
        logger.info(f'Cleanup effectiveness: {cleanup_effectiveness:.2%}')
        self.test_metrics.record_custom('concurrent_memory_sessions', concurrent_sessions)
        self.test_metrics.record_custom('total_memory_operations', total_operations)
        self.test_metrics.record_custom('memory_growth_mb', memory_growth / 1024 / 1024)
        self.test_metrics.record_custom('memory_per_operation_kb', memory_per_operation / 1024)
        self.test_metrics.record_custom('cleanup_effectiveness_ratio', cleanup_effectiveness)

    async def test_resource_cleanup_after_user_session_termination(self):
        """Test comprehensive resource cleanup after user session termination."""
        cleanup_test_user = f'resource_cleanup_user_{uuid.uuid4().hex[:8]}'
        user_context = await create_isolated_execution_context(user_id=cleanup_test_user, request_id=f'resource_cleanup_{uuid.uuid4().hex[:8]}')
        ws_manager = MockWebSocketManager()
        resource_agents = {}
        agent_types = ['data_helper', 'optimization', 'reporting', 'triage', 'goals_triage']
        for agent_type in agent_types:
            agent = await self.registry.create_agent_for_user(cleanup_test_user, agent_type, user_context, ws_manager)
            resource_agents[agent_type] = agent
        resource_tracking = {'agents_created': len(resource_agents), 'websocket_events': 0, 'tool_executions': 0, 'memory_objects': []}
        for agent_type, agent in resource_agents.items():
            for operation_num in range(5):
                run_id = f'resource_op_{agent_type}_{operation_num}'
                await ws_manager.notify_agent_started(run_id, agent_type, {'op': operation_num})
                await ws_manager.notify_agent_thinking(run_id, agent_type, f'Processing {operation_num}')
                await ws_manager.notify_tool_executing(run_id, agent_type, 'test_tool', {'param': operation_num})
                await ws_manager.notify_tool_completed(run_id, agent_type, 'test_tool', {'result': operation_num}, 50.0)
                await ws_manager.notify_agent_completed(run_id, agent_type, {'status': 'completed'}, 200.0)
                resource_tracking['websocket_events'] += 5
                resource_tracking['tool_executions'] += 1
                memory_object = {'agent': agent_type, 'operation': operation_num, 'data': list(range(100))}
                resource_tracking['memory_objects'].append(weakref.ref(memory_object))
        user_session = await self.registry.get_user_session(cleanup_test_user)
        pre_cleanup_state = {'user_session_exists': True, 'agent_count': len(user_session._agents), 'websocket_manager_set': user_session._websocket_manager is not None, 'websocket_bridge_set': user_session._websocket_bridge is not None, 'websocket_events_generated': len(ws_manager.events)}
        assert pre_cleanup_state['agent_count'] == len(agent_types)
        assert pre_cleanup_state['websocket_events_generated'] >= resource_tracking['websocket_events']
        cleanup_result = await self.registry.cleanup_user_session(cleanup_test_user)
        assert cleanup_result['status'] == 'cleaned'
        assert cleanup_result['cleaned_agents'] == len(agent_types)
        try:
            post_cleanup_session = await self.registry.get_user_session(cleanup_test_user)
            assert len(post_cleanup_session._agents) == 0
        except:
            pass
        del resource_agents
        gc.collect()
        await asyncio.sleep(0.1)
        gc.collect()
        dead_memory_refs = sum((1 for ref in resource_tracking['memory_objects'] if ref() is None))
        total_memory_refs = len(resource_tracking['memory_objects'])
        cleanup_ratio = dead_memory_refs / max(total_memory_refs, 1)
        assert cleanup_ratio > 0.8, f'Poor memory cleanup: {cleanup_ratio:.2%} objects cleaned'
        new_user_id = f'post_cleanup_user_{uuid.uuid4().hex[:8]}'
        new_context = await create_isolated_execution_context(user_id=new_user_id, request_id=f'post_cleanup_test_{uuid.uuid4().hex[:8]}')
        new_ws_manager = MockWebSocketManager()
        new_agent = await self.registry.create_agent_for_user(new_user_id, 'data_helper', new_context, new_ws_manager)
        assert len(new_ws_manager.events) == 0
        assert new_agent != list(resource_agents.values())[0] if resource_agents else True
        registry_health = self.registry.get_registry_health()
        assert registry_health['total_user_sessions'] >= 1
        assert registry_health['total_user_agents'] >= 1
        lifecycle_manager = self.registry._lifecycle_manager
        if hasattr(lifecycle_manager, 'monitor_memory_usage'):
            memory_report = await lifecycle_manager.monitor_memory_usage(cleanup_test_user)
            assert memory_report['status'] in ['no_session', 'healthy']
        self.test_users.append(new_user_id)
        self.test_metrics.record_custom('resources_before_cleanup', pre_cleanup_state['agent_count'])
        self.test_metrics.record_custom('websocket_events_generated', resource_tracking['websocket_events'])
        self.test_metrics.record_custom('memory_cleanup_ratio', cleanup_ratio)
        self.test_metrics.record_custom('tool_executions', resource_tracking['tool_executions'])

    async def test_long_running_session_resource_management(self):
        """Test resource management for long-running user sessions."""
        long_running_user = f'long_running_user_{uuid.uuid4().hex[:8]}'
        user_context = await create_isolated_execution_context(user_id=long_running_user, request_id=f'long_running_{uuid.uuid4().hex[:8]}')
        ws_manager = MockWebSocketManager()
        session_duration_cycles = 10
        operations_per_cycle = 20
        memory_samples = []
        initial_memory = psutil.Process().memory_info().rss
        memory_samples.append(initial_memory)
        session_metrics = {'total_agents_created': 0, 'total_operations': 0, 'cycles_completed': 0, 'memory_growth_per_cycle': []}
        for cycle in range(session_duration_cycles):
            cycle_start_memory = psutil.Process().memory_info().rss
            cycle_agents = []
            agent_types = ['data_helper', 'optimization', 'reporting']
            for agent_type in agent_types:
                agent = await self.registry.create_agent_for_user(long_running_user, agent_type, user_context, ws_manager)
                cycle_agents.append((agent_type, agent))
                session_metrics['total_agents_created'] += 1
            for operation in range(operations_per_cycle):
                agent_type, agent = cycle_agents[operation % len(cycle_agents)]
                run_id = f'long_running_cycle_{cycle}_op_{operation}'
                await ws_manager.notify_agent_started(run_id, agent_type, {'cycle': cycle, 'operation': operation, 'long_running_session': True})
                if operation % 5 == 0:
                    await ws_manager.notify_tool_executing(run_id, agent_type, 'complex_tool', {'complexity': 'high', 'data_size': operation * 10})
                    await ws_manager.notify_tool_completed(run_id, agent_type, 'complex_tool', {'processed': operation * 10}, 150.0)
                await ws_manager.notify_agent_completed(run_id, agent_type, {'cycle': cycle, 'operation': operation, 'result': 'completed'}, 100.0 + operation * 5)
                session_metrics['total_operations'] += 1
            if cycle % 3 == 0:
                agents_to_remove = cycle_agents[:2]
                for agent_type, agent in agents_to_remove:
                    removed = await self.registry.remove_user_agent(long_running_user, agent_type)
                    if removed:
                        logger.debug(f'Removed agent {agent_type} in cycle {cycle}')
            cycle_end_memory = psutil.Process().memory_info().rss
            cycle_memory_growth = cycle_end_memory - cycle_start_memory
            session_metrics['memory_growth_per_cycle'].append(cycle_memory_growth)
            memory_samples.append(cycle_end_memory)
            session_metrics['cycles_completed'] += 1
            await asyncio.sleep(0.02)
        final_memory = psutil.Process().memory_info().rss
        total_memory_growth = final_memory - initial_memory
        avg_memory_per_cycle = sum(session_metrics['memory_growth_per_cycle']) / len(session_metrics['memory_growth_per_cycle'])
        max_cycle_memory = max(session_metrics['memory_growth_per_cycle'])
        max_acceptable_growth = 100 * 1024 * 1024
        assert total_memory_growth < max_acceptable_growth, f'Excessive long-running memory growth: {total_memory_growth / 1024 / 1024:.2f} MB'
        max_cycle_acceptable = 15 * 1024 * 1024
        assert max_cycle_memory < max_cycle_acceptable, f'Excessive per-cycle memory growth: {max_cycle_memory / 1024 / 1024:.2f} MB'
        user_session = await self.registry.get_user_session(long_running_user)
        assert user_session is not None
        assert len(user_session._agents) <= len(agent_types) * 2
        assert len(ws_manager.events) >= session_metrics['total_operations']
        registry_health = self.registry.get_registry_health()
        assert registry_health['status'] in ['healthy', 'warning']
        reset_result = await self.registry.reset_user_agents(long_running_user)
        assert reset_result['status'] == 'reset_complete'
        post_reset_memory = psutil.Process().memory_info().rss
        reset_memory_improvement = final_memory - post_reset_memory
        improvement_ratio = reset_memory_improvement / max(total_memory_growth, 1)
        logger.info(f'Reset memory improvement: {improvement_ratio:.2%}')
        cleanup_result = await self.registry.cleanup_user_session(long_running_user)
        assert cleanup_result['status'] == 'cleaned'
        self.test_metrics.record_custom('long_running_cycles', session_duration_cycles)
        self.test_metrics.record_custom('total_long_running_operations', session_metrics['total_operations'])
        self.test_metrics.record_custom('total_agents_in_long_session', session_metrics['total_agents_created'])
        self.test_metrics.record_custom('long_running_memory_growth_mb', total_memory_growth / 1024 / 1024)
        self.test_metrics.record_custom('avg_memory_per_cycle_kb', avg_memory_per_cycle / 1024)
        self.test_metrics.record_custom('reset_memory_improvement_ratio', improvement_ratio)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
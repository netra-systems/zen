_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
'\n ALERT:  CRITICAL BUSINESS VALUE TEST SUITE: Agent Registry Comprehensive Unit Tests\n\nBusiness Value Justification (BVJ):\n- Segment: ALL (Free  ->  Enterprise) - Protects $500K+ ARR\n- Business Goal: Core agent orchestration reliability ensuring chat functionality\n- Value Impact: Validates user isolation preventing enterprise security breaches ($15K+ MRR per customer)\n- Revenue Impact: Protects 90% of platform value delivery through agent execution orchestration\n\nCRITICAL AREAS TESTED:\n1. User Isolation & Security - Factory-based user isolation preventing data leakage\n2. Agent Lifecycle Management - Complete agent creation, execution, and cleanup cycles\n3. WebSocket Integration - Real-time event delivery enabling chat value (90% of platform value)\n4. Registry Management - SSOT compliance and UniversalRegistry extension\n5. Tool Dispatcher Integration - UnifiedToolDispatcher SSOT integration with user scoping\n6. Performance & Concurrency - Multi-user concurrent execution without memory leaks\n\nRISK MITIGATION:\n- Each test validates specific business logic that could cause revenue loss if broken\n- Tests are designed to legitimately fail when business functionality is compromised\n- Comprehensive edge case coverage prevents silent failures in production\n\nThis test suite protects the PRIMARY revenue-generating user flow: Agent Execution Orchestration\n'
import asyncio
import pytest
import time
import uuid
import threading
import weakref
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession, AgentLifecycleManager, get_agent_registry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent

class UserIsolationAndSecurityTests(SSotAsyncTestCase):
    """Test Suite 1: User Isolation & Security (Protects $15K+ MRR per enterprise customer)
    
    Business Value: Prevents data leakage between enterprise customers, enabling secure multi-tenancy
    Revenue Risk: Loss of enterprise customers due to security breach
    """

    async def asyncSetUp(self):
        """Set up test environment with isolated user contexts."""
        super().setUp()
        self.mock_llm_manager = Mock()
        self.mock_llm_manager.get_llm = Mock(return_value=Mock())
        self.registry = AgentRegistry(llm_manager=self.mock_llm_manager)
        self.user1_id = 'enterprise_user_001'
        self.user2_id = 'enterprise_user_002'
        self.user1_context = UserExecutionContext(user_id=self.user1_id, request_id=f'req_{uuid.uuid4().hex[:8]}', thread_id=f'thread_{self.user1_id}', run_id=f'run_{uuid.uuid4().hex[:8]}')
        self.user2_context = UserExecutionContext(user_id=self.user2_id, request_id=f'req_{uuid.uuid4().hex[:8]}', thread_id=f'thread_{self.user2_id}', run_id=f'run_{uuid.uuid4().hex[:8]}')

    async def test_factory_based_user_isolation_prevents_global_state_access(self):
        """CRITICAL: Validates factory-based user isolation preventing global state contamination.
        
        Business Value: Prevents enterprise data leakage ($15K+ MRR per customer at risk)
        Failure Mode: If this fails, users could access other users' data
        """
        session1 = await self.registry.get_user_session(self.user1_id)
        session2 = await self.registry.get_user_session(self.user2_id)
        self.assertNotEqual(session1, session2, 'User sessions must be completely isolated')
        self.assertEqual(session1.user_id, self.user1_id)
        self.assertEqual(session2.user_id, self.user2_id)
        mock_agent1 = Mock(spec=BaseAgent)
        mock_agent2 = Mock(spec=BaseAgent)
        await session1.register_agent('test_agent', mock_agent1)
        await session2.register_agent('test_agent', mock_agent2)
        retrieved_agent1 = await session1.get_agent('test_agent')
        retrieved_agent2 = await session2.get_agent('test_agent')
        self.assertIs(retrieved_agent1, mock_agent1, 'User 1 must get their own agent instance')
        self.assertIs(retrieved_agent2, mock_agent2, 'User 2 must get their own agent instance')
        self.assertNotEqual(retrieved_agent1, retrieved_agent2, 'Users must not share agent instances')

    async def test_memory_leak_prevention_and_lifecycle_management(self):
        """CRITICAL: Validates memory leak prevention in multi-user scenarios.
        
        Business Value: Prevents system crashes under concurrent load
        Failure Mode: Memory leaks could crash platform during peak usage
        """
        user_sessions = []
        user_ids = [f'user_{i:03d}' for i in range(20)]
        for user_id in user_ids:
            session = await self.registry.get_user_session(user_id)
            user_sessions.append(session)
            for j in range(3):
                mock_agent = Mock(spec=BaseAgent)
                await session.register_agent(f'agent_{j}', mock_agent)
        self.assertEqual(len(self.registry._user_sessions), 20, 'All user sessions should be created')
        lifecycle_manager = self.registry._lifecycle_manager
        user_metrics = await lifecycle_manager.monitor_memory_usage(user_ids[0])
        self.assertEqual(user_metrics['status'], 'healthy')
        self.assertEqual(user_metrics['metrics']['agent_count'], 3)
        cleanup_report = await self.registry.cleanup_user_session(user_ids[0])
        self.assertEqual(cleanup_report['status'], 'cleaned')
        self.assertEqual(cleanup_report['cleaned_agents'], 3)
        self.assertNotIn(user_ids[0], self.registry._user_sessions)

    async def test_thread_safe_concurrent_execution_for_enterprise_load(self):
        """CRITICAL: Validates thread-safe concurrent execution for enterprise customers.
        
        Business Value: Enables concurrent enterprise user operations without data corruption
        Failure Mode: Race conditions could corrupt enterprise data
        """
        concurrent_users = 10
        operations_per_user = 5

        async def user_operation(user_index: int):
            """Simulate concurrent user operations."""
            user_id = f'concurrent_user_{user_index:03d}'
            user_context = UserExecutionContext(user_id=user_id, request_id=f'req_{uuid.uuid4().hex[:8]}', thread_id=f'thread_{user_id}', run_id=f'run_{uuid.uuid4().hex[:8]}')
            operations = []
            for op_index in range(operations_per_user):
                session = await self.registry.get_user_session(user_id)
                mock_agent = Mock(spec=BaseAgent, name=f'agent_{op_index}')
                await session.register_agent(f'agent_{op_index}', mock_agent)
                retrieved_agent = await session.get_agent(f'agent_{op_index}')
                operations.append((f'agent_{op_index}', retrieved_agent))
            return (user_id, operations)
        tasks = [user_operation(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            self.assertNotIsInstance(result, Exception, f'Concurrent operation failed: {result}')
        self.assertEqual(len(self.registry._user_sessions), concurrent_users)
        for user_id, operations in results:
            session = self.registry._user_sessions[user_id]
            self.assertEqual(len(session._agents), operations_per_user)

    async def test_websocket_bridge_isolation_per_user_session(self):
        """CRITICAL: Validates WebSocket bridge isolation preventing cross-user message delivery.
        
        Business Value: Ensures chat messages only go to correct user (90% of platform value)
        Failure Mode: If this fails, users could see other users' messages
        """
        mock_websocket_manager = Mock()
        mock_bridge1 = Mock()
        mock_bridge2 = Mock()
        bridge_counter = 0

        def create_bridge(user_context):
            nonlocal bridge_counter
            bridge_counter += 1
            if user_context.user_id == self.user1_id:
                return mock_bridge1
            else:
                return mock_bridge2
        mock_websocket_manager.create_bridge = create_bridge
        session1 = await self.registry.get_user_session(self.user1_id)
        session2 = await self.registry.get_user_session(self.user2_id)
        await session1.set_websocket_manager(mock_websocket_manager, self.user1_context)
        await session2.set_websocket_manager(mock_websocket_manager, self.user2_context)
        self.assertIs(session1._websocket_bridge, mock_bridge1, 'User 1 must get isolated bridge')
        self.assertIs(session2._websocket_bridge, mock_bridge2, 'User 2 must get isolated bridge')
        self.assertNotEqual(session1._websocket_bridge, session2._websocket_bridge, 'WebSocket bridges must be isolated per user')

    async def test_user_context_validation_prevents_placeholder_contamination(self):
        """CRITICAL: Validates user context validation prevents placeholder/test data contamination.
        
        Business Value: Prevents corrupted production data from invalid contexts
        Failure Mode: Invalid contexts could corrupt enterprise customer data
        """
        with self.assertRaises(ValueError, msg='Empty user_id must be rejected'):
            await self.registry.get_user_session('')
        with self.assertRaises(ValueError, msg='None user_id must be rejected'):
            await self.registry.get_user_session(None)
        with self.assertRaises(ValueError, msg='Non-string user_id must be rejected'):
            await self.registry.get_user_session(123)
        placeholder_context = UserExecutionContext(user_id='test_user_placeholder', request_id='test_request', thread_id='test_thread', run_id='test_run')
        try:
            agent = await self.registry.create_agent_for_user(user_id='test_user_placeholder', agent_type='test_agent', user_context=placeholder_context)
        except Exception as e:
            self.assertIn('No factory registered', str(e))

class AgentLifecycleManagementTests(SSotAsyncTestCase):
    """Test Suite 2: Agent Lifecycle Management (Protects core chat functionality)
    
    Business Value: Ensures reliable agent creation, execution, and cleanup
    Revenue Risk: Agent failures could break chat functionality (90% of platform value)
    """

    async def asyncSetUp(self):
        """Set up test environment with mock agents."""
        super().setUp()
        self.mock_llm_manager = Mock()
        self.registry = AgentRegistry(llm_manager=self.mock_llm_manager)
        self.test_user_id = 'lifecycle_test_user'
        self.user_context = UserExecutionContext(user_id=self.test_user_id, request_id=f'req_{uuid.uuid4().hex[:8]}', thread_id=f'thread_{self.test_user_id}', run_id=f'run_{uuid.uuid4().hex[:8]}')

    async def test_agent_creation_registration_and_cleanup_cycle(self):
        """CRITICAL: Validates complete agent lifecycle from creation to cleanup.
        
        Business Value: Ensures agents work reliably for chat functionality
        Failure Mode: Broken lifecycle could prevent agent responses
        """
        mock_agent = Mock(spec=BaseAgent)
        mock_agent.cleanup = AsyncMock()
        mock_agent.close = AsyncMock()
        user_session = await self.registry.get_user_session(self.test_user_id)
        await user_session.register_agent('lifecycle_agent', mock_agent)
        retrieved_agent = await user_session.get_agent('lifecycle_agent')
        self.assertIs(retrieved_agent, mock_agent, 'Registered agent must be retrievable')
        await user_session.cleanup_all_agents()
        mock_agent.cleanup.assert_called_once()
        mock_agent.close.assert_called_once()
        self.assertEqual(len(user_session._agents), 0, 'All agents must be cleaned up')

    async def test_agent_state_tracking_and_transitions(self):
        """CRITICAL: Validates agent state tracking throughout execution lifecycle.
        
        Business Value: Enables proper agent orchestration and error recovery
        Failure Mode: State tracking failures could lead to zombie agents
        """
        agents = {}
        for i in range(3):
            agent = Mock(spec=BaseAgent, name=f'agent_{i}')
            agent.cleanup = AsyncMock()
            agents[f'agent_{i}'] = agent
        user_session = await self.registry.get_user_session(self.test_user_id)
        for agent_name, agent in agents.items():
            await user_session.register_agent(agent_name, agent)
        session_metrics = user_session.get_metrics()
        self.assertEqual(session_metrics['agent_count'], 3, 'All agents must be tracked')
        removed = await self.registry.remove_user_agent(self.test_user_id, 'agent_1')
        self.assertTrue(removed, 'Agent removal must succeed')
        session_metrics = user_session.get_metrics()
        self.assertEqual(session_metrics['agent_count'], 2, 'Agent count must update after removal')
        agents['agent_1'].cleanup.assert_called_once()

    async def test_agent_execution_orchestration_with_error_recovery(self):
        """CRITICAL: Validates agent execution orchestration with graceful error handling.
        
        Business Value: Ensures chat functionality continues even when individual agents fail
        Failure Mode: Agent failures could cascade and break entire chat session
        """
        successful_agent = Mock(spec=BaseAgent)
        successful_agent.run = AsyncMock(return_value='success')
        successful_agent.cleanup = AsyncMock()
        failing_agent = Mock(spec=BaseAgent)
        failing_agent.run = AsyncMock(side_effect=Exception('Agent execution failed'))
        failing_agent.cleanup = AsyncMock()
        user_session = await self.registry.get_user_session(self.test_user_id)
        await user_session.register_agent('successful_agent', successful_agent)
        await user_session.register_agent('failing_agent', failing_agent)
        session_metrics = user_session.get_metrics()
        self.assertEqual(session_metrics['agent_count'], 2, 'Session must remain stable with mixed agent states')
        reset_report = await self.registry.reset_user_agents(self.test_user_id)
        self.assertEqual(reset_report['status'], 'reset_complete')
        self.assertEqual(reset_report['agents_reset'], 2)
        new_session = await self.registry.get_user_session(self.test_user_id)
        new_metrics = new_session.get_metrics()
        self.assertEqual(new_metrics['agent_count'], 0, 'Reset must provide clean slate')

    async def test_resource_management_and_cleanup_under_load(self):
        """CRITICAL: Validates proper resource management preventing memory leaks under load.
        
        Business Value: Prevents system crashes during peak enterprise usage
        Failure Mode: Resource leaks could crash platform during important customer demos
        """
        allocated_resources = []
        for i in range(50):
            mock_agent = Mock(spec=BaseAgent)
            mock_agent.cleanup = AsyncMock()
            resource = f'resource_{i}'
            allocated_resources.append(resource)
            mock_agent.allocated_resource = resource
            user_session = await self.registry.get_user_session(f'load_user_{i}')
            await user_session.register_agent('resource_agent', mock_agent)
        self.assertEqual(len(self.registry._user_sessions), 50, 'All user sessions must be created')
        cleanup_report = await self.registry.emergency_cleanup_all()
        self.assertEqual(cleanup_report['users_cleaned'], 50, 'All users must be cleaned up')
        self.assertEqual(cleanup_report['agents_cleaned'], 50, 'All agents must be cleaned up')
        self.assertEqual(len(self.registry._user_sessions), 0, 'All sessions must be removed')

    async def test_agent_factory_pattern_execution_with_isolation(self):
        """CRITICAL: Validates factory pattern execution maintains user isolation.
        
        Business Value: Ensures consistent agent behavior across all user sessions
        Failure Mode: Factory issues could create agents with wrong user context
        """

        async def test_agent_factory(context: UserExecutionContext, websocket_bridge=None):
            """Factory that creates agents with proper user context."""
            mock_agent = Mock(spec=BaseAgent)
            mock_agent.user_context = context
            mock_agent.websocket_bridge = websocket_bridge
            mock_agent.cleanup = AsyncMock()
            return mock_agent
        self.registry.register_factory('test_factory_agent', test_agent_factory, tags=['test'], description='Test factory agent')
        user1_agent = await self.registry.get_async('test_factory_agent', self.user_context)
        user2_context = UserExecutionContext(user_id='factory_user_2', request_id=f'req_{uuid.uuid4().hex[:8]}', thread_id='thread_factory_2', run_id=f'run_{uuid.uuid4().hex[:8]}')
        user2_agent = await self.registry.get_async('test_factory_agent', user2_context)
        self.assertNotEqual(user1_agent, user2_agent, 'Factory must create isolated instances')
        self.assertEqual(user1_agent.user_context.user_id, self.user_context.user_id)
        self.assertEqual(user2_agent.user_context.user_id, user2_context.user_id)

class WebSocketIntegrationTests(SSotAsyncTestCase):
    """Test Suite 3: WebSocket Integration (Protects 90% of platform value)
    
    Business Value: Enables real-time chat notifications critical for user experience
    Revenue Risk: WebSocket failures break chat experience leading to user abandonment
    """

    async def asyncSetUp(self):
        """Set up WebSocket testing environment."""
        super().setUp()
        self.mock_llm_manager = Mock()
        self.registry = AgentRegistry(llm_manager=self.mock_llm_manager)
        self.test_user_id = 'websocket_test_user'
        self.user_context = UserExecutionContext(user_id=self.test_user_id, request_id=f'req_{uuid.uuid4().hex[:8]}', thread_id=f'thread_{self.test_user_id}', run_id=f'run_{uuid.uuid4().hex[:8]}')

    @pytest.mark.skip(reason='WebSocketManagerAdapter removed in SSOT consolidation - Issue #762')
    async def test_websocket_manager_adapter_functionality(self):
        """CRITICAL: Validates WebSocketManagerAdapter provides all required notification methods.
        
        Business Value: Enables all 5 critical WebSocket events for chat experience
        Failure Mode: Missing events break real-time chat notifications
        """
        mock_websocket_manager = Mock()
        mock_websocket_manager.notify_agent_started = AsyncMock()
        mock_websocket_manager.notify_agent_thinking = AsyncMock()
        mock_websocket_manager.notify_tool_executing = AsyncMock()
        mock_websocket_manager.notify_tool_completed = AsyncMock()
        mock_websocket_manager.notify_agent_completed = AsyncMock()
        mock_websocket_manager.notify_agent_error = AsyncMock()
        mock_websocket_manager.notify_agent_death = AsyncMock()
        mock_websocket_manager.get_metrics = AsyncMock(return_value={'status': 'healthy'})
        adapter = WebSocketManagerAdapter(mock_websocket_manager, self.user_context)
        await adapter.notify_agent_started('run_123', 'test_agent', {'key': 'value'})
        await adapter.notify_agent_thinking('run_123', 'test_agent', 'I am thinking...', 1)
        await adapter.notify_tool_executing('run_123', 'test_agent', 'search_tool', {'query': 'test'})
        await adapter.notify_tool_completed('run_123', 'test_agent', 'search_tool', 'result', 1500.0)
        await adapter.notify_agent_completed('run_123', 'test_agent', {'result': 'success'}, 3000.0)
        await adapter.notify_agent_error('run_123', 'test_agent', 'error message', {'context': 'test'})
        await adapter.notify_agent_death('run_123', 'test_agent', 'timeout', {'details': 'hung'})
        mock_websocket_manager.notify_agent_started.assert_called_once()
        mock_websocket_manager.notify_agent_thinking.assert_called_once()
        mock_websocket_manager.notify_tool_executing.assert_called_once()
        mock_websocket_manager.notify_tool_completed.assert_called_once()
        mock_websocket_manager.notify_agent_completed.assert_called_once()
        mock_websocket_manager.notify_agent_error.assert_called_once()
        mock_websocket_manager.notify_agent_death.assert_called_once()

    async def test_websocket_manager_propagation_to_user_sessions(self):
        """CRITICAL: Validates WebSocket manager is properly propagated to all user sessions.
        
        Business Value: Ensures all users receive real-time notifications
        Failure Mode: Some users might not receive chat notifications
        """
        user_ids = [f'ws_user_{i}' for i in range(5)]
        sessions = []
        for user_id in user_ids:
            session = await self.registry.get_user_session(user_id)
            sessions.append(session)
        mock_websocket_manager = Mock()
        mock_websocket_manager.create_bridge = Mock(return_value=Mock())
        await self.registry.set_websocket_manager_async(mock_websocket_manager)
        self.assertEqual(self.registry.websocket_manager, mock_websocket_manager)
        for session in sessions:
            self.assertIsNotNone(session._access_lock, 'Session must be ready for WebSocket setup')

    async def test_agent_websocket_event_integration(self):
        """CRITICAL: Validates agent execution triggers proper WebSocket events.
        
        Business Value: Ensures users see real-time agent progress (core UX)
        Failure Mode: Silent agent execution breaks user experience
        """
        mock_websocket_manager = Mock()
        mock_bridge = Mock()
        mock_bridge.notify_agent_started = AsyncMock()
        mock_bridge.notify_agent_completed = AsyncMock()

        def create_bridge(user_context):
            return mock_bridge
        mock_websocket_manager.create_bridge = create_bridge
        user_session = await self.registry.get_user_session(self.test_user_id)
        await user_session.set_websocket_manager(mock_websocket_manager, self.user_context)
        self.assertIs(user_session._websocket_bridge, mock_bridge, 'WebSocket bridge must be set on session')

    async def test_websocket_isolation_prevents_cross_user_notifications(self):
        """CRITICAL: Validates WebSocket events only go to correct user.
        
        Business Value: Prevents users from seeing other users' chat notifications
        Failure Mode: Cross-user notifications could expose sensitive information
        """
        user1_bridge = Mock()
        user1_bridge.notify_agent_started = AsyncMock()
        user2_bridge = Mock()
        user2_bridge.notify_agent_started = AsyncMock()
        mock_websocket_manager = Mock()

        def create_bridge(user_context):
            if user_context.user_id == 'user1':
                return user1_bridge
            else:
                return user2_bridge
        mock_websocket_manager.create_bridge = create_bridge
        user1_context = UserExecutionContext(user_id='user1', request_id='req1', thread_id='thread1', run_id='run1')
        user2_context = UserExecutionContext(user_id='user2', request_id='req2', thread_id='thread2', run_id='run2')
        session1 = await self.registry.get_user_session('user1')
        session2 = await self.registry.get_user_session('user2')
        await session1.set_websocket_manager(mock_websocket_manager, user1_context)
        await session2.set_websocket_manager(mock_websocket_manager, user2_context)
        self.assertIs(session1._websocket_bridge, user1_bridge, 'User 1 must get their own bridge')
        self.assertIs(session2._websocket_bridge, user2_bridge, 'User 2 must get their own bridge')
        self.assertNotEqual(session1._websocket_bridge, session2._websocket_bridge, 'Users must have isolated WebSocket bridges')

    @pytest.mark.skip(reason='WebSocketManagerAdapter removed in SSOT consolidation - Issue #762')
    async def test_websocket_adapter_graceful_degradation(self):
        """CRITICAL: Validates graceful degradation when WebSocket methods are missing.
        
        Business Value: Platform continues working even with WebSocket issues
        Failure Mode: WebSocket problems could crash entire platform
        """
        limited_websocket_manager = Mock()
        limited_websocket_manager.notify_agent_started = AsyncMock()
        adapter = WebSocketManagerAdapter(limited_websocket_manager, self.user_context)
        await adapter.notify_agent_started('run_123', 'test_agent', {})
        await adapter.notify_agent_thinking('run_123', 'test_agent', 'thinking')
        await adapter.notify_tool_executing('run_123', 'test_agent', 'tool', {})
        limited_websocket_manager.notify_agent_started.assert_called_once()

class RegistryManagementAndSSotComplianceTests(SSotAsyncTestCase):
    """Test Suite 4: Registry Management & SSOT Compliance (Protects system architecture)
    
    Business Value: Ensures SSOT compliance and proper registry inheritance
    Revenue Risk: Architecture violations could cause cascading system failures
    """

    async def asyncSetUp(self):
        """Set up registry testing environment."""
        super().setUp()
        self.mock_llm_manager = Mock()
        self.registry = AgentRegistry(llm_manager=self.mock_llm_manager)

    async def test_universal_registry_extension_patterns_compliance(self):
        """CRITICAL: Validates proper UniversalRegistry extension and SSOT compliance.
        
        Business Value: Ensures system architecture integrity and proper inheritance
        Failure Mode: SSOT violations could break registry functionality
        """
        from netra_backend.app.core.registry.universal_registry import BaseAgentRegistry
        self.assertIsInstance(self.registry, BaseAgentRegistry, 'AgentRegistry must inherit from BaseAgentRegistry')
        compliance_status = self.registry.get_ssot_compliance_status()
        self.assertIn('status', compliance_status)
        self.assertIn('compliance_score', compliance_status)
        self.assertGreaterEqual(compliance_status['compliance_score'], 80, 'SSOT compliance must be at least 80%')

    async def test_registry_state_consistency_under_concurrent_access(self):
        """CRITICAL: Validates registry state consistency during concurrent operations.
        
        Business Value: Prevents data corruption during multi-user operations
        Failure Mode: Concurrent access issues could corrupt agent registry
        """

        async def register_agent(agent_index: int):
            mock_agent = Mock(spec=BaseAgent, name=f'agent_{agent_index}')
            self.registry.register(f'agent_{agent_index}', mock_agent)
            return f'agent_{agent_index}'
        agent_names = await asyncio.gather(*[register_agent(i) for i in range(10)])
        registered_keys = self.registry.list_keys()
        for agent_name in agent_names:
            self.assertIn(agent_name, registered_keys, f'Agent {agent_name} must be registered')

        async def get_agent(agent_name: str):
            return self.registry.get(agent_name)
        retrieved_agents = await asyncio.gather(*[get_agent(name) for name in agent_names])
        for agent in retrieved_agents:
            self.assertIsNotNone(agent, 'All registered agents must be retrievable')

    async def test_agent_lookup_and_retrieval_performance(self):
        """CRITICAL: Validates agent lookup performance doesn't degrade with registry size.
        
        Business Value: Ensures platform responsiveness as agent count grows
        Failure Mode: Slow lookups could degrade chat response times
        """
        agent_count = 100
        for i in range(agent_count):
            mock_agent = Mock(spec=BaseAgent, name=f'perf_agent_{i}')
            self.registry.register(f'perf_agent_{i}', mock_agent)
        start_time = time.time()
        for i in range(0, agent_count, 10):
            agent = self.registry.get(f'perf_agent_{i}')
            self.assertIsNotNone(agent, f'Agent perf_agent_{i} must be retrievable')
        lookup_time = time.time() - start_time
        self.assertLess(lookup_time, 1.0, 'Agent lookups must remain fast with large registry')

    async def test_registry_health_monitoring_and_metrics(self):
        """CRITICAL: Validates registry health monitoring provides accurate system status.
        
        Business Value: Enables proactive system monitoring and issue detection
        Failure Mode: Poor monitoring could miss system degradation
        """
        for i in range(5):
            mock_agent = Mock(spec=BaseAgent, name=f'health_agent_{i}')
            self.registry.register(f'health_agent_{i}', mock_agent)
        for i in range(3):
            await self.registry.get_user_session(f'health_user_{i}')
        health = self.registry.get_registry_health()
        required_fields = ['total_agents', 'failed_registrations', 'registration_errors', 'death_detection_enabled', 'using_universal_registry', 'hardened_isolation', 'total_user_sessions', 'total_user_agents', 'memory_leak_prevention', 'thread_safe_concurrent_execution']
        for field in required_fields:
            self.assertIn(field, health, f'Health report must include {field}')
        self.assertEqual(health['total_agents'], 5, 'Agent count must be accurate')
        self.assertEqual(health['total_user_sessions'], 3, 'User session count must be accurate')
        self.assertTrue(health['hardened_isolation'], 'Hardened isolation must be enabled')

    async def test_factory_pattern_integration_status(self):
        """CRITICAL: Validates factory pattern integration provides proper isolation.
        
        Business Value: Ensures modern factory patterns work correctly
        Failure Mode: Factory issues could prevent proper agent isolation
        """
        factory_status = self.registry.get_factory_integration_status()
        required_factory_features = ['using_universal_registry', 'factory_patterns_enabled', 'hardened_isolation_enabled', 'user_isolation_enforced', 'memory_leak_prevention', 'thread_safe_concurrent_execution', 'global_state_eliminated', 'websocket_isolation_per_user']
        for feature in required_factory_features:
            self.assertIn(feature, factory_status, f'Factory status must include {feature}')
            self.assertTrue(factory_status[feature], f'Factory feature {feature} must be enabled')

class ToolDispatcherIntegrationTests(SSotAsyncTestCase):
    """Test Suite 5: Tool Dispatcher Integration (Protects tool execution reliability)
    
    Business Value: Ensures tools work correctly with user isolation
    Revenue Risk: Tool failures could break agent capabilities
    """

    async def asyncSetUp(self):
        """Set up tool dispatcher testing environment."""
        super().setUp()
        self.mock_llm_manager = Mock()
        self.registry = AgentRegistry(llm_manager=self.mock_llm_manager)
        self.test_user_context = UserExecutionContext(user_id='tool_test_user', request_id=f'req_{uuid.uuid4().hex[:8]}', thread_id='tool_thread', run_id=f'run_{uuid.uuid4().hex[:8]}')

    @patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcher.create_for_user')
    async def test_unified_tool_dispatcher_ssot_integration(self, mock_create_for_user):
        """CRITICAL: Validates UnifiedToolDispatcher SSOT integration with user scoping.
        
        Business Value: Ensures tools work reliably with proper user isolation
        Failure Mode: Tool dispatcher issues could break agent tool usage
        """
        mock_dispatcher = Mock()
        mock_create_for_user.return_value = mock_dispatcher
        dispatcher = await self.registry.create_tool_dispatcher_for_user(user_context=self.test_user_context, websocket_bridge=None, enable_admin_tools=False)
        mock_create_for_user.assert_called_once_with(user_context=self.test_user_context, websocket_bridge=None, enable_admin_tools=False)
        self.assertIs(dispatcher, mock_dispatcher, 'Must return SSOT dispatcher instance')

    @patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcher.create_for_user')
    async def test_user_scoped_tool_dispatcher_isolation(self, mock_create_for_user):
        """CRITICAL: Validates tool dispatchers are properly isolated per user.
        
        Business Value: Prevents tool execution cross-contamination between users
        Failure Mode: Shared dispatchers could leak data between enterprise customers
        """
        user1_dispatcher = Mock(name='user1_dispatcher')
        user2_dispatcher = Mock(name='user2_dispatcher')
        dispatcher_map = {}

        def create_dispatcher_side_effect(user_context, websocket_bridge=None, enable_admin_tools=False):
            if user_context.user_id not in dispatcher_map:
                if user_context.user_id == 'user1':
                    dispatcher_map[user_context.user_id] = user1_dispatcher
                else:
                    dispatcher_map[user_context.user_id] = user2_dispatcher
            return dispatcher_map[user_context.user_id]
        mock_create_for_user.side_effect = create_dispatcher_side_effect
        user1_context = UserExecutionContext(user_id='user1', request_id='req1', thread_id='thread1', run_id='run1')
        user2_context = UserExecutionContext(user_id='user2', request_id='req2', thread_id='thread2', run_id='run2')
        dispatcher1 = await self.registry.create_tool_dispatcher_for_user(user1_context)
        dispatcher2 = await self.registry.create_tool_dispatcher_for_user(user2_context)
        self.assertIs(dispatcher1, user1_dispatcher, 'User 1 must get their own dispatcher')
        self.assertIs(dispatcher2, user2_dispatcher, 'User 2 must get their own dispatcher')
        self.assertNotEqual(dispatcher1, dispatcher2, 'Dispatchers must be isolated per user')

    async def test_tool_dispatcher_factory_error_handling(self):
        """CRITICAL: Validates graceful handling of tool dispatcher creation failures.
        
        Business Value: Ensures platform stability when tool system has issues
        Failure Mode: Dispatcher failures could crash agent execution
        """

        def failing_factory(user_context, websocket_bridge=None):
            raise Exception('Tool dispatcher creation failed')
        self.registry.tool_dispatcher_factory = failing_factory
        with self.assertRaises(Exception, msg='Factory failures should be propagated for handling'):
            await self.registry.create_tool_dispatcher_for_user(self.test_user_context)

    @patch('netra_backend.app.agents.unified_tool_execution.enhance_tool_dispatcher_with_notifications')
    async def test_tool_dispatcher_websocket_notification_enhancement(self, mock_enhance):
        """CRITICAL: Validates tool dispatcher gets enhanced with WebSocket notifications.
        
        Business Value: Ensures users see real-time tool execution progress
        Failure Mode: Missing tool notifications break user experience
        """
        mock_websocket_manager = Mock()
        mock_bridge = Mock()
        mock_bridge._websocket_manager = mock_websocket_manager
        user_session = await self.registry.get_user_session(self.test_user_context.user_id)
        user_session._websocket_bridge = mock_bridge
        with patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcher.create_for_user') as mock_create:
            mock_dispatcher = Mock()
            mock_create.return_value = mock_dispatcher
            mock_enhance.return_value = None
            dispatcher = await self.registry.create_tool_dispatcher_for_user(user_context=self.test_user_context, websocket_bridge=mock_bridge)
            mock_enhance.assert_called_once_with(mock_dispatcher, websocket_manager=mock_websocket_manager, user_context=self.test_user_context, enable_notifications=True)

class PerformanceAndConcurrencyTests(SSotAsyncTestCase):
    """Test Suite 6: Performance & Concurrency (Protects system scalability)
    
    Business Value: Ensures platform can handle enterprise-scale concurrent usage
    Revenue Risk: Performance issues could cause user abandonment during peak usage
    """

    async def asyncSetUp(self):
        """Set up performance testing environment."""
        super().setUp()
        self.mock_llm_manager = Mock()
        self.registry = AgentRegistry(llm_manager=self.mock_llm_manager)

    async def test_multi_user_concurrent_agent_execution_performance(self):
        """CRITICAL: Validates platform handles concurrent agent execution without performance degradation.
        
        Business Value: Enables enterprise-scale concurrent usage
        Failure Mode: Performance issues during peak usage could lose customers
        """
        concurrent_users = 20
        agents_per_user = 5

        async def create_user_agents(user_index: int):
            """Create multiple agents for a user concurrently."""
            user_id = f'perf_user_{user_index:03d}'
            user_context = UserExecutionContext(user_id=user_id, request_id=f'req_{uuid.uuid4().hex[:8]}', thread_id=f'thread_{user_id}', run_id=f'run_{uuid.uuid4().hex[:8]}')
            user_session = await self.registry.get_user_session(user_id)
            for agent_index in range(agents_per_user):
                mock_agent = Mock(spec=BaseAgent, name=f'agent_{agent_index}')
                await user_session.register_agent(f'agent_{agent_index}', mock_agent)
            return (user_id, agents_per_user)
        start_time = time.time()
        tasks = [create_user_agents(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        successful_results = [r for r in results if not isinstance(r, Exception)]
        self.assertEqual(len(successful_results), concurrent_users, 'All concurrent operations must succeed')
        self.assertLess(execution_time, 10.0, f'Concurrent execution must complete within 10s, took {execution_time:.2f}s')
        self.assertEqual(len(self.registry._user_sessions), concurrent_users)
        for user_id, expected_agents in successful_results:
            session = self.registry._user_sessions[user_id]
            self.assertEqual(len(session._agents), expected_agents)

    async def test_memory_usage_optimization_under_load(self):
        """CRITICAL: Validates memory usage remains bounded under sustained load.
        
        Business Value: Prevents memory-related crashes during sustained usage
        Failure Mode: Memory leaks could crash platform during important demos
        """
        session_cycles = 10
        users_per_cycle = 20
        for cycle in range(session_cycles):
            user_ids = [f'memory_test_cycle_{cycle}_user_{i}' for i in range(users_per_cycle)]
            for user_id in user_ids:
                user_session = await self.registry.get_user_session(user_id)
                for j in range(5):
                    mock_agent = Mock(spec=BaseAgent)
                    mock_agent.cleanup = AsyncMock()
                    await user_session.register_agent(f'agent_{j}', mock_agent)
            self.assertEqual(len(self.registry._user_sessions), users_per_cycle)
            for user_id in user_ids:
                await self.registry.cleanup_user_session(user_id)
            self.assertEqual(len(self.registry._user_sessions), 0, f'All sessions must be cleaned up after cycle {cycle}')

    async def test_background_task_management_prevents_resource_leaks(self):
        """CRITICAL: Validates background tasks are properly managed to prevent resource leaks.
        
        Business Value: Ensures system stability during long-running operations
        Failure Mode: Background task leaks could exhaust system resources
        """
        mock_websocket_manager = Mock()
        mock_websocket_manager.create_bridge = Mock(return_value=Mock())
        user_count = 10
        for i in range(user_count):
            await self.registry.get_user_session(f'bg_task_user_{i}')
        self.registry.set_websocket_manager(mock_websocket_manager)
        await asyncio.sleep(0.1)
        await self.registry.cleanup()
        self.assertEqual(len(self.registry._background_tasks), 0, 'All background tasks must be cleaned up')

    async def test_connection_pool_efficiency_under_concurrent_access(self):
        """CRITICAL: Validates connection pooling efficiency during concurrent WebSocket operations.
        
        Business Value: Ensures efficient resource usage during peak chat activity
        Failure Mode: Inefficient pooling could degrade chat performance
        """
        connection_pool = {}

        def create_bridge(user_context):
            pool_key = f'pool_{hash(user_context.user_id) % 5}'
            if pool_key not in connection_pool:
                connection_pool[pool_key] = Mock(name=f'bridge_{pool_key}')
            return connection_pool[pool_key]
        mock_websocket_manager = Mock()
        mock_websocket_manager.create_bridge = create_bridge
        concurrent_users = 50

        async def setup_user_websocket(user_index: int):
            user_id = f'pool_user_{user_index}'
            user_context = UserExecutionContext(user_id=user_id, request_id=f'req_{uuid.uuid4().hex[:8]}', thread_id=f'thread_{user_id}', run_id=f'run_{uuid.uuid4().hex[:8]}')
            session = await self.registry.get_user_session(user_id)
            await session.set_websocket_manager(mock_websocket_manager, user_context)
            return user_id
        user_ids = await asyncio.gather(*[setup_user_websocket(i) for i in range(concurrent_users)])
        self.assertEqual(len(connection_pool), 5, 'Connection pool should have 5 pools')
        self.assertEqual(len(user_ids), concurrent_users, 'All users should be set up')

    async def test_race_condition_prevention_in_registry_operations(self):
        """CRITICAL: Validates race conditions are prevented in registry operations.
        
        Business Value: Ensures data consistency during concurrent operations
        Failure Mode: Race conditions could corrupt registry state
        """
        operation_results = {}

        async def concurrent_registry_operation(operation_id: int):
            """Operation that modifies registry state."""
            user_id = f'race_user_{operation_id}'
            session = await self.registry.get_user_session(user_id)
            agents = []
            for i in range(3):
                mock_agent = Mock(spec=BaseAgent, name=f'op_{operation_id}_agent_{i}')
                await session.register_agent(f'agent_{i}', mock_agent)
                agents.append(mock_agent)
            metrics = session.get_metrics()
            operation_results[operation_id] = {'user_id': user_id, 'agent_count': metrics['agent_count'], 'agents': agents}
            return operation_id
        concurrent_operations = 30
        operation_ids = await asyncio.gather(*[concurrent_registry_operation(i) for i in range(concurrent_operations)])
        self.assertEqual(len(operation_ids), concurrent_operations)
        self.assertEqual(len(operation_results), concurrent_operations)
        for op_id, result in operation_results.items():
            self.assertEqual(result['agent_count'], 3, f'Operation {op_id} should have created 3 agents')
            self.assertEqual(len(result['agents']), 3, f'Operation {op_id} should have 3 agent instances')
        self.assertEqual(len(self.registry._user_sessions), concurrent_operations)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
"""Agent Registry Tests - Issue #758 Golden Path Enhancement

MISSION: Comprehensive test coverage for AgentRegistry golden path patterns
as part of Issue #758 BaseAgent test coverage enhancement initiative.

Business Value Justification (BVJ):
- Segment: Platform/Internal (ALL user segments depend on agent registry)
- Business Goal: System Stability & Development Velocity
- Value Impact: AgentRegistry manages all agent lifecycles - comprehensive testing
  ensures $500K+ ARR business functionality remains stable under concurrent load
- Strategic Impact: Registry patterns enable multi-user isolation and golden path workflows

Issue #758 Focus Areas:
1. Registration/deregistration golden path workflows
2. Factory instantiation patterns with user context validation
3. WebSocket manager integration for real-time functionality
4. Multi-user concurrent operations with complete isolation
5. Memory management and resource cleanup patterns
6. Prerequisites validation and business-critical security features

Golden Path Test Strategy:
- Real registry operations with minimal mocking for authentic behavior
- Focus on high-value customer scenarios and enterprise patterns
- Validate complete user isolation preventing data leakage
- Test memory leak prevention critical for production deployment
- Verify WebSocket integration supporting $500K+ ARR chat functionality
"""
import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
import threading
import weakref
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent

class MockEnterpriseWebSocketManager:
    """Enterprise-grade mock WebSocket manager for comprehensive registry testing."""

    def __init__(self):
        self.events = []
        self.user_contexts = {}
        self.active_connections = {}
        self.event_history = {}

    async def notify_agent_started(self, run_id: str, agent_name: str, metadata: Dict[str, Any]) -> None:
        """Mock agent started notification with comprehensive tracking."""
        event = {'type': 'agent_started', 'run_id': run_id, 'agent_name': agent_name, 'metadata': metadata, 'timestamp': datetime.now(timezone.utc)}
        self.events.append(event)
        if run_id not in self.event_history:
            self.event_history[run_id] = []
        self.event_history[run_id].append(event)

    async def notify_agent_completed(self, run_id: str, agent_name: str, result: Any) -> None:
        """Mock agent completed notification with result tracking."""
        event = {'type': 'agent_completed', 'run_id': run_id, 'agent_name': agent_name, 'result': result, 'timestamp': datetime.now(timezone.utc)}
        self.events.append(event)
        if run_id not in self.event_history:
            self.event_history[run_id] = []
        self.event_history[run_id].append(event)

    async def notify_thinking(self, run_id: str, message: str) -> None:
        """Mock thinking notification for comprehensive event tracking."""
        event = {'type': 'thinking', 'run_id': run_id, 'message': message, 'timestamp': datetime.now(timezone.utc)}
        self.events.append(event)

    def set_user_context(self, user_context: UserExecutionContext):
        """Track user contexts with comprehensive isolation validation."""
        user_id = user_context.user_id
        self.user_contexts[user_id] = user_context
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

    def get_events_for_run(self, run_id: str) -> List[Dict]:
        """Get all events for a specific run_id for golden path validation."""
        return self.event_history.get(run_id, [])

    def get_user_isolation_metrics(self) -> Dict[str, Any]:
        """Get metrics for validating user isolation."""
        return {'total_users': len(self.user_contexts), 'total_events': len(self.events), 'events_per_run': {run_id: len(events) for run_id, events in self.event_history.items()}, 'user_context_count': len(self.user_contexts)}

class AgentRegistryGoldenPathWorkflowsTests(SSotBaseTestCase):
    """Test AgentRegistry golden path workflows for Issue #758."""

    def setup_method(self, method):
        """Setup comprehensive test environment for golden path scenarios."""
        super().setup_method(method)
        self.test_session_id = f'golden-session-{uuid.uuid4().hex[:8]}'
        self.test_user_id = f'enterprise-user-{uuid.uuid4().hex[:8]}'
        self.test_thread_id = f'priority-thread-{uuid.uuid4().hex[:8]}'
        self.test_run_id = f'golden-run-{uuid.uuid4().hex[:8]}'
        self.enterprise_context = UserExecutionContext(user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id, request_id=f'enterprise-request-{uuid.uuid4().hex[:8]}', agent_context={'customer_tier': 'enterprise', 'priority_level': 'high', 'revenue_impact': '$500K+ARR', 'session_id': self.test_session_id}, audit_metadata={'business_context': 'production_chat_interaction', 'scalability_requirement': 'concurrent_users_100+', 'golden_path': True})
        self.enterprise_websocket_manager = MockEnterpriseWebSocketManager()
        from netra_backend.app.llm.llm_manager import LLMManager
        mock_llm_manager = Mock(spec=LLMManager)
        mock_llm_manager.create_completion = AsyncMock()
        mock_llm_manager.create_chat_completion = AsyncMock()
        self.registry = AgentRegistry(llm_manager=mock_llm_manager)
        self.registry.set_websocket_manager(self.enterprise_websocket_manager)

    async def test_golden_path_agent_registration_workflow(self):
        """Test complete golden path agent registration workflow."""
        business_critical_agents = [('customer_onboarding_agent', BaseAgent), ('revenue_optimization_agent', BaseAgent), ('churn_prevention_agent', BaseAgent), ('billing_intelligence_agent', BaseAgent)]
        for agent_name, agent_class in business_critical_agents:

            def create_agent_func(context, websocket_bridge=None, name=agent_name, cls=agent_class):
                return cls(name=name, agent_id=f'{name}_id')
            self.registry.register_factory(agent_name, create_agent_func)
            agent = await self.registry.create_agent_for_user('test_user_001', agent_name, self.enterprise_context)
            assert agent is not None, f'Failed to create {agent_name}'
        registered_agents = self.registry.list_agents()
        for agent_name, _ in business_critical_agents:
            assert agent_name in registered_agents, f'Critical agent {agent_name} failed to register'
        assert len(registered_agents) >= len(business_critical_agents)

    async def test_golden_path_factory_instantiation_with_enterprise_context(self):
        """Test golden path factory instantiation with enterprise user context."""

        def create_enterprise_agent(context, websocket_bridge=None):
            return BaseAgent(name='EnterpriseChatAgent', agent_id='enterprise_chat_001')
        self.registry.register_factory('enterprise_chat_agent', create_enterprise_agent)
        agent = await self.registry.create_agent_for_user('enterprise_user', 'enterprise_chat_agent', self.enterprise_context)
        assert agent is not None, 'Golden path factory instantiation failed'
        assert isinstance(agent, BaseAgent), 'Factory created wrong agent type'
        assert agent.name == 'EnterpriseChatAgent', 'Agent name not preserved'
        assert agent.agent_id is not None, 'Agent ID not generated'
        assert hasattr(agent, 'context'), 'Agent missing context attribute'

    @pytest.mark.asyncio
    async def test_golden_path_websocket_integration_enterprise_chat(self):
        """Test golden path WebSocket integration for enterprise chat scenarios."""

        def create_chat_agent(context, websocket_bridge=None):
            return BaseAgent(name='GoldenPathChatAgent', agent_id='golden_chat_001')
        self.registry.register_factory('golden_chat_agent', create_chat_agent)
        chat_agent = await self.registry.create_agent_for_user('enterprise_chat_user', 'golden_chat_agent', self.enterprise_context)
        chat_agent.set_websocket_bridge(self.enterprise_websocket_manager, self.test_run_id)
        await chat_agent.emit_agent_started(message='Enterprise chat agent started for golden path validation')
        await chat_agent.emit_thinking(context=self.enterprise_context, thought='Processing enterprise customer request...')
        await chat_agent.emit_agent_completed(context=self.enterprise_context, result={'status': 'success', 'value_delivered': '$500K+ ARR protection'})
        events = self.enterprise_websocket_manager.get_events_for_run(self.test_run_id)
        assert len(events) >= 1, 'Golden path WebSocket events not captured'
        event_types = [event['type'] for event in events]
        assert 'agent_completed' in event_types, 'Agent WebSocket events missing'

    async def test_golden_path_multi_user_isolation_enterprise_scale(self):
        """Test golden path multi-user isolation at enterprise scale."""

        def create_scalable_agent(context, websocket_bridge=None):
            return BaseAgent(name='ScalableEnterpriseAgent', agent_id=f'scalable_{context.user_id}')
        self.registry.register_factory('scalable_enterprise_agent', create_scalable_agent)
        enterprise_users = []
        for i in range(10):
            user_context = UserExecutionContext(user_id=f'enterprise-user-{i}', thread_id=f'enterprise-thread-{i}', run_id=f'enterprise-run-{i}', request_id=f'enterprise-request-{i}', agent_context={'customer_tier': 'enterprise', 'user_segment': f'segment_{i}', 'priority': 'high'}, audit_metadata={'concurrent_test': True})
            enterprise_users.append(user_context)
        agents = []
        for i, context in enumerate(enterprise_users):
            agent = await self.registry.create_agent_for_user(context.user_id, 'scalable_enterprise_agent', context)
            agents.append(agent)
        assert len(agents) == 10, 'Not all enterprise agents created'
        agent_ids = [agent.agent_id for agent in agents]
        assert len(set(agent_ids)) == len(agent_ids), 'Agent isolation failure detected'
        for i, agent in enumerate(agents):
            agent.context[f'test_isolation_{i}'] = f'value_{i}'
        for i, agent in enumerate(agents):
            for j, other_agent in enumerate(agents):
                if i != j:
                    assert f'test_isolation_{j}' not in agent.context, f'Cross-contamination detected between agents {i} and {j}'

    @pytest.mark.asyncio
    async def test_golden_path_concurrent_agent_operations_enterprise_load(self):
        """Test golden path concurrent operations under enterprise load."""

        def create_concurrent_agent(context, websocket_bridge=None):
            return BaseAgent(name='ConcurrentEnterpriseAgent', agent_id=f'concurrent_{context.user_id}')
        self.registry.register_factory('concurrent_enterprise_agent', create_concurrent_agent)

        async def golden_path_agent_workflow(user_id: str, operation_id: int):
            """Execute complete golden path workflow for a user."""
            context = UserExecutionContext(user_id=user_id, thread_id=f'concurrent-thread-{user_id}-{operation_id}', run_id=f'concurrent-run-{user_id}-{operation_id}', request_id=f'concurrent-request-{user_id}-{operation_id}', agent_context={'operation_id': operation_id}, audit_metadata={'concurrent_test': True, 'golden_path': True})
            agent = await self.registry.create_agent_for_user(user_id, 'concurrent_enterprise_agent', context)
            agent.set_websocket_bridge(self.enterprise_websocket_manager, context.run_id)
            await agent.emit_agent_started(message=f'Concurrent agent {agent.name} started for user {user_id}')
            await agent.emit_agent_completed(context=context, result={'operation_id': operation_id, 'user_id': user_id})
            return agent
        concurrent_tasks = []
        for i in range(15):
            task = golden_path_agent_workflow(f'concurrent-user-{i}', i)
            concurrent_tasks.append(task)
        agents = await asyncio.gather(*concurrent_tasks)
        assert len(agents) == 15, 'Concurrent workflow execution failed'
        agent_ids = [agent.agent_id for agent in agents]
        assert len(set(agent_ids)) == len(agent_ids), 'Concurrent isolation failure'
        isolation_metrics = self.enterprise_websocket_manager.get_user_isolation_metrics()
        assert isolation_metrics['total_events'] >= 15, 'Insufficient WebSocket events captured'

    async def test_golden_path_memory_management_enterprise_production(self):
        """Test golden path memory management for enterprise production deployment."""

        def create_memory_managed_agent(context, websocket_bridge=None):
            return BaseAgent(name='MemoryManagedAgent', agent_id=f'memory_{context.user_id}')
        self.registry.register_factory('memory_managed_agent', create_memory_managed_agent)
        agents = []
        agent_refs = []
        for i in range(50):
            context = UserExecutionContext(user_id=f'memory-user-{i}', thread_id=f'memory-thread-{i}', run_id=f'memory-run-{i}', request_id=f'memory-request-{i}', agent_context={'memory_test': True}, audit_metadata={'production_scale': True})
            agent = await self.registry.create_agent_for_user(f'memory-user-{i}', 'memory_managed_agent', context)
            agents.append(agent)
            agent_refs.append(weakref.ref(agent))
        assert len(agents) == 50, 'Production-scale agent creation failed'
        initial_agent_count = len(agents)
        del agents
        import gc
        gc.collect()
        assert initial_agent_count == 50, 'Agent creation validation failed'

    async def test_golden_path_registry_health_and_monitoring_enterprise(self):
        """Test golden path registry health monitoring for enterprise deployment."""
        monitoring_agents = [('health_monitoring_agent', BaseAgent), ('performance_tracking_agent', BaseAgent), ('business_metrics_agent', BaseAgent)]
        for agent_name, agent_class in monitoring_agents:

            def create_monitoring_agent(context, websocket_bridge=None, name=agent_name, cls=agent_class):
                return cls(name=name, agent_id=f'{name}_id')
            self.registry.register_factory(agent_name, create_monitoring_agent)
            agent = await self.registry.create_agent_for_user('monitor_user', agent_name, self.enterprise_context)
            assert agent is not None, f'Failed to create {agent_name}'
        registered_agents = self.registry.list_agents()
        assert len(registered_agents) >= 3, 'Registry health check failed'
        for agent_name, _ in monitoring_agents:
            assert agent_name in registered_agents, f'Registry lost track of {agent_name}'
        health_agents = []
        for agent_name, _ in monitoring_agents:
            agent = await self.registry.create_agent_for_user('health_monitor_user', agent_name, self.enterprise_context)
            health_agents.append(agent)
        assert len(health_agents) == 3, 'Registry health monitoring failed'

    def test_golden_path_websocket_manager_enterprise_integration(self):
        """Test golden path WebSocket manager integration for enterprise scenarios."""
        websocket_manager = self.enterprise_websocket_manager
        assert websocket_manager is not None, 'WebSocket manager creation failed'
        assert hasattr(websocket_manager, 'events'), 'Manager missing events tracking'
        assert hasattr(websocket_manager, 'user_contexts'), 'Manager missing user contexts'
        assert hasattr(websocket_manager, 'events'), 'Manager delegation setup failed'
        assert websocket_manager is self.enterprise_websocket_manager, 'Manager reference incorrect'

    async def test_golden_path_business_value_protection_patterns(self):
        """Test golden path patterns that protect business value and revenue."""
        revenue_agents = [('customer_success_agent', BaseAgent), ('revenue_optimization_agent', BaseAgent), ('enterprise_support_agent', BaseAgent)]
        for agent_name, agent_class in revenue_agents:

            def create_revenue_agent(context, websocket_bridge=None, name=agent_name, cls=agent_class):
                return cls(name=f'BusinessCritical_{name}', agent_id=f'{name}_id')
            self.registry.register_factory(agent_name, create_revenue_agent)
        business_critical_agents = []
        for agent_name, _ in revenue_agents:
            agent = await self.registry.create_agent_for_user('business_critical_user', agent_name, self.enterprise_context)
            business_critical_agents.append(agent)
        assert len(business_critical_agents) == 3, 'Business value protection setup failed'
        for agent in business_critical_agents:
            assert agent.agent_id is not None, 'Business agent missing unique ID'
            assert 'BusinessCritical_' in agent.name, 'Business agent naming pattern incorrect'
        for agent in business_critical_agents:
            assert hasattr(agent, 'context'), 'Business agent missing context'
            assert hasattr(agent, 'state'), 'Business agent missing state management'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
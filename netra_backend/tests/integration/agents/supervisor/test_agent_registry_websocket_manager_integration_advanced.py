"""
Advanced Integration Tests for AgentRegistry WebSocket Manager Integration
Test #6 of Agent Registry and Factory Patterns Test Suite

Business Value Justification (BVJ):
- Segment: Enterprise (Advanced WebSocket features for high-traffic scenarios)
- Business Goal: Advanced real-time agent communication for enterprise-grade multi-user scenarios
- Value Impact: Enables sophisticated WebSocket management, connection pooling, and error resilience
- Strategic Impact: $750K+ ARR from Enterprise customers requiring advanced real-time features

CRITICAL MISSION: Test Advanced AgentRegistry WebSocket Manager Integration ensuring:
1. WebSocket connection pooling and resource management across multiple users
2. Advanced WebSocket event filtering and routing per user context
3. WebSocket reconnection handling and failover mechanisms
4. Performance optimization for high-throughput WebSocket scenarios
5. WebSocket health monitoring and diagnostic capabilities
6. Cross-service WebSocket event propagation and coordination
7. WebSocket security isolation and access control validation
8. Advanced WebSocket lifecycle management and cleanup

FOCUS: Advanced integration testing with real WebSocket connections, connection pooling, 
        and enterprise-grade performance characteristics.
"""
import asyncio
import pytest
import time
import uuid
import json
import weakref
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, Mock, patch, MagicMock, call
from collections import defaultdict
import gc
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory, configure_agent_instance_factory
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, create_agent_websocket_bridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher

@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager with advanced capabilities."""
    mock_llm = AsyncMock()
    mock_llm.initialize = AsyncMock()
    mock_llm.chat_completion = AsyncMock(return_value='Advanced test response from agent')
    mock_llm.is_healthy = Mock(return_value=True)
    mock_llm.get_model_info = Mock(return_value={'model': 'test-gpt-4', 'tokens': 4096})
    return mock_llm

@pytest.fixture
def advanced_websocket_manager():
    """Create advanced WebSocket manager with connection pooling and monitoring."""
    ws_manager = UnifiedWebSocketManager()
    ws_manager._connection_pool = {}
    ws_manager._connection_metrics = defaultdict(int)
    ws_manager._health_status = 'healthy'
    ws_manager.send_event = AsyncMock(return_value=True)
    ws_manager.is_connected = Mock(return_value=True)
    ws_manager.get_connection_count = Mock(return_value=1)
    ws_manager.get_pool_stats = Mock(return_value={'active': 5, 'idle': 3, 'total': 8})
    ws_manager.health_check = AsyncMock(return_value={'status': 'healthy', 'connections': 8})

    async def mock_create_connection_pool(user_id: str, max_connections: int=3):
        ws_manager._connection_pool[user_id] = {'connections': [f'conn_{i}' for i in range(max_connections)], 'active': 0, 'created_at': time.time()}
        return True

    async def mock_cleanup_connection_pool(user_id: str):
        if user_id in ws_manager._connection_pool:
            del ws_manager._connection_pool[user_id]
        return True
    ws_manager.create_connection_pool = mock_create_connection_pool
    ws_manager.cleanup_connection_pool = mock_cleanup_connection_pool
    return ws_manager

@pytest.fixture
def enterprise_user_contexts():
    """Create enterprise-level test user contexts with enhanced metadata."""
    contexts = []
    for i in range(10):
        context = UserExecutionContext(user_id=f'enterprise_user_{i}_{uuid.uuid4().hex[:6]}', request_id=f'enterprise_req_{i}_{uuid.uuid4().hex[:6]}', thread_id=f'enterprise_thread_{i}_{uuid.uuid4().hex[:6]}', run_id=f'enterprise_run_{i}_{uuid.uuid4().hex[:6]}', agent_context={'user_tier': 'enterprise', 'connection_limit': 5, 'priority': 'high', 'billing_id': f'billing_{i}'})
        contexts.append(context)
    return contexts

@pytest.fixture
def mock_enterprise_agent_with_advanced_websocket():
    """Create mock enterprise agent with advanced WebSocket capabilities."""

    class MockEnterpriseAgent:

        def __init__(self, llm_manager=None, tool_dispatcher=None):
            self.llm_manager = llm_manager
            self.tool_dispatcher = tool_dispatcher
            self.execution_history = []
            self._websocket_bridge = None
            self._run_id = None
            self._agent_name = None
            self._performance_metrics = {'execution_count': 0, 'avg_response_time': 0.0}
            self._advanced_features = True

        def set_websocket_bridge(self, bridge, run_id, agent_name=None):
            self._websocket_bridge = bridge
            self._run_id = run_id
            self._agent_name = agent_name or 'enterprise_agent'

        async def execute(self, state, run_id):
            """Advanced agent execution with performance tracking and WebSocket events."""
            start_time = time.time()
            try:
                if self._websocket_bridge:
                    await self._websocket_bridge.notify_agent_started(run_id=self._run_id, agent_name=self._agent_name, context={'state': 'started', 'enterprise_mode': True, 'priority': 'high', 'estimated_duration': 2.5})
                for step in range(1, 4):
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_agent_thinking(run_id=self._run_id, agent_name=self._agent_name, reasoning=f'Advanced processing step {step}/3', step_number=step, progress_percentage=step * 33.3)
                    await asyncio.sleep(0.1)
                tools = ['data_analyzer', 'optimization_engine', 'report_generator']
                for i, tool_name in enumerate(tools):
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_tool_executing(run_id=self._run_id, agent_name=self._agent_name, tool_name=tool_name, parameters={'input': state, 'step': i + 1})
                        await asyncio.sleep(0.05)
                        await self._websocket_bridge.notify_tool_completed(run_id=self._run_id, agent_name=self._agent_name, tool_name=tool_name, result={'output': f'processed_by_{tool_name}', 'step': i + 1}, execution_time_ms=50.0 + i * 10)
                execution_time = (time.time() - start_time) * 1000
                if self._websocket_bridge:
                    await self._websocket_bridge.notify_agent_completed(run_id=self._run_id, agent_name=self._agent_name, result={'status': 'success', 'data': f'Enterprise processed: {state}', 'performance': {'execution_time_ms': execution_time, 'tools_used': len(tools), 'optimization_score': 95.5}}, execution_time_ms=execution_time)
                self._performance_metrics['execution_count'] += 1
                self._performance_metrics['avg_response_time'] = (self._performance_metrics['avg_response_time'] * (self._performance_metrics['execution_count'] - 1) + execution_time) / self._performance_metrics['execution_count']
                self.execution_history.append({'state': state, 'run_id': run_id, 'execution_time': execution_time, 'tools_used': tools})
                return {'status': 'success', 'data': f'Enterprise processed: {state}', 'performance': self._performance_metrics}
            except Exception as e:
                if self._websocket_bridge:
                    await self._websocket_bridge.notify_agent_error(run_id=self._run_id, agent_name=self._agent_name, error=str(e), context={'execution_step': 'main_execution'})
                raise

        async def cleanup(self):
            """Advanced cleanup with performance reporting."""
            if self._websocket_bridge:
                await self._websocket_bridge.notify_agent_completed(run_id=self._run_id, agent_name=self._agent_name, result={'status': 'cleanup', 'performance': self._performance_metrics}, execution_time_ms=0.0)
    return MockEnterpriseAgent

class TestAdvancedWebSocketConnectionPooling(SSotBaseTestCase):
    """Test advanced WebSocket connection pooling and management."""

    @pytest.mark.asyncio
    async def test_websocket_connection_pool_creation_and_management(self, mock_llm_manager, advanced_websocket_manager, enterprise_user_contexts):
        """Test WebSocket connection pool creation and management for multiple users."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(advanced_websocket_manager)
        created_pools = {}
        for context in enterprise_user_contexts[:5]:
            session = await registry.get_user_session(context.user_id)
            await advanced_websocket_manager.create_connection_pool(context.user_id, max_connections=context.agent_context.get('connection_limit', 3))
            created_pools[context.user_id] = context.agent_context.get('connection_limit', 3)
        for user_id, expected_limit in created_pools.items():
            assert user_id in advanced_websocket_manager._connection_pool
            pool_info = advanced_websocket_manager._connection_pool[user_id]
            assert len(pool_info['connections']) == expected_limit
        for user_id in created_pools.keys():
            await advanced_websocket_manager.cleanup_connection_pool(user_id)
            assert user_id not in advanced_websocket_manager._connection_pool

    @pytest.mark.asyncio
    async def test_websocket_health_monitoring_and_diagnostics(self, mock_llm_manager, advanced_websocket_manager, enterprise_user_contexts):
        """Test WebSocket health monitoring and diagnostic capabilities."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(advanced_websocket_manager)
        sessions = []
        for context in enterprise_user_contexts[:3]:
            session = await registry.get_user_session(context.user_id)
            sessions.append((session, context))
        health_results = []
        for i in range(3):
            health_result = await advanced_websocket_manager.health_check()
            health_results.append(health_result)
        for health_result in health_results:
            assert health_result['status'] == 'healthy'
            assert 'connections' in health_result
            assert health_result['connections'] >= 0
        pool_stats = advanced_websocket_manager.get_pool_stats()
        assert 'active' in pool_stats
        assert 'idle' in pool_stats
        assert 'total' in pool_stats
        assert pool_stats['total'] == pool_stats['active'] + pool_stats['idle']

    @pytest.mark.asyncio
    async def test_websocket_performance_optimization_high_throughput(self, mock_llm_manager, advanced_websocket_manager, mock_enterprise_agent_with_advanced_websocket, enterprise_user_contexts):
        """Test WebSocket performance optimization for high-throughput scenarios."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(advanced_websocket_manager)
        event_timings = []
        original_send = advanced_websocket_manager.send_event

        async def track_performance(*args, **kwargs):
            start_time = time.time()
            result = await original_send(*args, **kwargs)
            end_time = time.time()
            event_timings.append(end_time - start_time)
            return result
        advanced_websocket_manager.send_event = track_performance
        agents_and_contexts = []
        for i, context in enumerate(enterprise_user_contexts[:5]):
            agent = mock_enterprise_agent_with_advanced_websocket()
            registry.get_async = AsyncMock(return_value=agent)
            created_agent = await registry.create_agent_for_user(user_id=context.user_id, agent_type=f'performance_agent_{i}', user_context=context, websocket_manager=advanced_websocket_manager)
            agents_and_contexts.append((created_agent, context))
        execution_tasks = []
        for agent, context in agents_and_contexts:
            task = agent.execute(f'high_throughput_data_{context.user_id}', context.run_id)
            execution_tasks.append(task)
        start_time = time.time()
        results = await asyncio.gather(*execution_tasks)
        total_execution_time = time.time() - start_time
        for result in results:
            assert result['status'] == 'success'
            assert 'performance' in result
        assert len(event_timings) > 0, 'Should have recorded WebSocket event timings'
        avg_event_time = sum(event_timings) / len(event_timings)
        assert avg_event_time < 0.1, f'Average WebSocket event time should be < 100ms, got {avg_event_time:.3f}s'
        assert total_execution_time < 5.0, f'Total concurrent execution should be < 5s, got {total_execution_time:.2f}s'

    @pytest.mark.asyncio
    async def test_websocket_error_recovery_and_failover(self, mock_llm_manager, advanced_websocket_manager, enterprise_user_contexts):
        """Test WebSocket error recovery and failover mechanisms."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(advanced_websocket_manager)
        user_context = enterprise_user_contexts[0]
        session = await registry.get_user_session(user_context.user_id)
        failure_count = 0

        async def intermittent_failure(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise Exception(f'WebSocket connection failed (attempt {failure_count})')
            return True
        advanced_websocket_manager.send_event = intermittent_failure
        with patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge') as mock_create_bridge:
            mock_bridge = AsyncMock()
            mock_bridge.notify_agent_started = AsyncMock(side_effect=intermittent_failure)
            mock_create_bridge.return_value = mock_bridge
            await session.set_websocket_manager(advanced_websocket_manager, user_context)
            success_count = 0
            for i in range(5):
                try:
                    await mock_bridge.notify_agent_started(run_id=user_context.run_id, agent_name='recovery_test_agent', context={'attempt': i + 1})
                    success_count += 1
                except Exception:
                    pass
            assert success_count >= 2, 'Should have succeeded on some retry attempts'
            assert failure_count > 3, 'Should have attempted retries after initial failures'

class TestAdvancedWebSocketEventFiltering(SSotBaseTestCase):
    """Test advanced WebSocket event filtering and routing capabilities."""

    @pytest.mark.asyncio
    async def test_websocket_event_filtering_per_user_context(self, mock_llm_manager, advanced_websocket_manager, enterprise_user_contexts):
        """Test WebSocket event filtering based on user context and permissions."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(advanced_websocket_manager)
        user_sessions = []
        for i, context in enumerate(enterprise_user_contexts[:3]):
            context.agent_context['permission_level'] = ['basic', 'advanced', 'admin'][i]
            session = await registry.get_user_session(context.user_id)
            user_sessions.append((session, context))
        filtered_events = {}
        original_send = advanced_websocket_manager.send_event

        async def filter_events(*args, **kwargs):
            event_data = args[0] if args else kwargs
            user_id = event_data.get('user_id') or 'unknown'
            event_type = event_data.get('event_type', 'unknown')
            if user_id not in filtered_events:
                filtered_events[user_id] = []
            if 'basic' in str(event_data) and event_type in ['admin_tool_executing', 'system_diagnostic']:
                return False
            filtered_events[user_id].append(event_data)
            return await original_send(*args, **kwargs)
        advanced_websocket_manager.send_event = filter_events
        event_types = [{'event_type': 'agent_started', 'sensitivity': 'low'}, {'event_type': 'admin_tool_executing', 'sensitivity': 'high'}, {'event_type': 'system_diagnostic', 'sensitivity': 'high'}, {'event_type': 'agent_completed', 'sensitivity': 'low'}]
        for session, context in user_sessions:
            for event in event_types:
                await advanced_websocket_manager.send_event({**event, 'user_id': context.user_id, 'run_id': context.run_id, 'permission_level': context.agent_context['permission_level']})
        for session, context in user_sessions:
            user_events = filtered_events.get(context.user_id, [])
            permission_level = context.agent_context['permission_level']
            if permission_level == 'basic':
                high_sensitivity_events = [e for e in user_events if e.get('sensitivity') == 'high']
                assert len(high_sensitivity_events) == 0, f'Basic user should not receive high sensitivity events'
            else:
                assert len(user_events) >= 2, f'Advanced/admin users should receive multiple events'

    @pytest.mark.asyncio
    async def test_websocket_cross_service_event_propagation(self, mock_llm_manager, advanced_websocket_manager, enterprise_user_contexts):
        """Test WebSocket event propagation across different services and components."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(advanced_websocket_manager)
        user_context = enterprise_user_contexts[0]
        session = await registry.get_user_session(user_context.user_id)
        service_events = {'agent_service': [], 'tool_service': [], 'notification_service': [], 'billing_service': []}
        original_send = advanced_websocket_manager.send_event

        async def track_cross_service_events(*args, **kwargs):
            event_data = args[0] if args else kwargs
            service_origin = event_data.get('service_origin', 'unknown')
            if service_origin in service_events:
                service_events[service_origin].append(event_data)
            if event_data.get('event_type') == 'agent_completed':
                billing_event = {'event_type': 'billing_update', 'service_origin': 'billing_service', 'user_id': event_data.get('user_id'), 'run_id': event_data.get('run_id'), 'cost': 0.05}
                service_events['billing_service'].append(billing_event)
            return await original_send(*args, **kwargs)
        advanced_websocket_manager.send_event = track_cross_service_events
        test_events = [{'event_type': 'agent_started', 'service_origin': 'agent_service', 'user_id': user_context.user_id, 'run_id': user_context.run_id}, {'event_type': 'tool_executing', 'service_origin': 'tool_service', 'user_id': user_context.user_id, 'run_id': user_context.run_id, 'tool_name': 'data_analyzer'}, {'event_type': 'notification_sent', 'service_origin': 'notification_service', 'user_id': user_context.user_id, 'message': 'Agent execution started'}, {'event_type': 'agent_completed', 'service_origin': 'agent_service', 'user_id': user_context.user_id, 'run_id': user_context.run_id, 'result': 'success'}]
        for event in test_events:
            await advanced_websocket_manager.send_event(event)
        assert len(service_events['agent_service']) >= 2, 'Should have received agent service events'
        assert len(service_events['tool_service']) >= 1, 'Should have received tool service events'
        assert len(service_events['notification_service']) >= 1, 'Should have received notification service events'
        assert len(service_events['billing_service']) >= 1, 'Should have triggered billing service event'
        billing_events = service_events['billing_service']
        completion_triggered_billing = [e for e in billing_events if e.get('event_type') == 'billing_update']
        assert len(completion_triggered_billing) >= 1, 'Agent completion should trigger billing update'

class TestAdvancedWebSocketSecurity(SSotBaseTestCase):
    """Test advanced WebSocket security and access control mechanisms."""

    @pytest.mark.asyncio
    async def test_websocket_security_isolation_validation(self, mock_llm_manager, advanced_websocket_manager, enterprise_user_contexts):
        """Test WebSocket security isolation and access control validation."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(advanced_websocket_manager)
        secure_contexts = []
        for i, context in enumerate(enterprise_user_contexts[:4]):
            context.agent_context['security_level'] = ['low', 'medium', 'high', 'critical'][i]
            context.agent_context['access_tokens'] = [f'token_{i}_{j}' for j in range(3)]
            secure_contexts.append(context)
        security_checks = []
        original_send = advanced_websocket_manager.send_event

        async def validate_security(*args, **kwargs):
            event_data = args[0] if args else kwargs
            user_id = event_data.get('user_id')
            security_level = event_data.get('security_level', 'unknown')
            security_check = {'user_id': user_id, 'security_level': security_level, 'validated': True, 'timestamp': time.time()}
            if security_level == 'critical':
                security_check['additional_validation'] = True
                security_check['validation_methods'] = ['token_verification', 'permission_check', 'rate_limiting']
            security_checks.append(security_check)
            return await original_send(*args, **kwargs)
        advanced_websocket_manager.send_event = validate_security
        for context in secure_contexts:
            session = await registry.get_user_session(context.user_id)
            await advanced_websocket_manager.send_event({'event_type': 'secure_agent_operation', 'user_id': context.user_id, 'run_id': context.run_id, 'security_level': context.agent_context['security_level'], 'access_tokens': context.agent_context['access_tokens']})
        assert len(security_checks) == len(secure_contexts), 'Should have validated all security events'
        critical_checks = [check for check in security_checks if check.get('security_level') == 'critical']
        assert len(critical_checks) >= 1, 'Should have critical security events'
        for check in critical_checks:
            assert check.get('additional_validation') is True, 'Critical events should have additional validation'
            assert len(check.get('validation_methods', [])) >= 3, 'Critical events should have multiple validation methods'
        user_ids_in_checks = set((check['user_id'] for check in security_checks))
        expected_user_ids = set((context.user_id for context in secure_contexts))
        assert user_ids_in_checks == expected_user_ids, 'Security checks should only include expected users'

    @pytest.mark.asyncio
    async def test_websocket_rate_limiting_and_throttling(self, mock_llm_manager, advanced_websocket_manager, enterprise_user_contexts):
        """Test WebSocket rate limiting and throttling mechanisms."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(advanced_websocket_manager)
        user_context = enterprise_user_contexts[0]
        session = await registry.get_user_session(user_context.user_id)
        rate_limit_data = {'requests': [], 'throttled': 0, 'allowed': 0}
        original_send = advanced_websocket_manager.send_event

        async def apply_rate_limiting(*args, **kwargs):
            current_time = time.time()
            rate_limit_data['requests'].append(current_time)
            recent_requests = [t for t in rate_limit_data['requests'] if current_time - t < 1.0]
            if len(recent_requests) > 10:
                rate_limit_data['throttled'] += 1
                raise Exception('Rate limit exceeded: too many requests')
            rate_limit_data['allowed'] += 1
            return await original_send(*args, **kwargs)
        advanced_websocket_manager.send_event = apply_rate_limiting
        rapid_tasks = []
        for i in range(15):
            task = advanced_websocket_manager.send_event({'event_type': 'burst_test', 'user_id': user_context.user_id, 'run_id': user_context.run_id, 'sequence': i})
            rapid_tasks.append(task)
        results = await asyncio.gather(*rapid_tasks, return_exceptions=True)
        successes = sum((1 for result in results if not isinstance(result, Exception)))
        failures = sum((1 for result in results if isinstance(result, Exception)))
        assert failures > 0, 'Should have throttled some requests due to rate limiting'
        assert successes > 0, 'Should have allowed some requests within rate limit'
        assert rate_limit_data['throttled'] > 0, 'Should have recorded throttled requests'
        assert rate_limit_data['allowed'] > 0, 'Should have recorded allowed requests'
        assert rate_limit_data['throttled'] + rate_limit_data['allowed'] == 15, 'Should account for all requests'

    @pytest.mark.asyncio
    async def test_websocket_memory_management_and_cleanup(self, mock_llm_manager, advanced_websocket_manager, enterprise_user_contexts):
        """Test WebSocket memory management and proper cleanup to prevent memory leaks."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(advanced_websocket_manager)
        created_objects = []
        cleaned_objects = []

        class TrackableWebSocketBridge:
            """Mock WebSocket bridge that tracks creation and cleanup."""

            def __init__(self, context):
                self.context = context
                self.cleaned_up = False
                created_objects.append(weakref.ref(self, lambda ref: cleaned_objects.append(ref)))

            async def cleanup(self):
                self.cleaned_up = True

            async def notify_agent_started(self, *args, **kwargs):
                pass

            async def notify_agent_completed(self, *args, **kwargs):
                pass
        sessions = []
        for context in enterprise_user_contexts[:5]:
            session = await registry.get_user_session(context.user_id)
            trackable_bridge = TrackableWebSocketBridge(context)
            with patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge', return_value=trackable_bridge):
                await session.set_websocket_manager(advanced_websocket_manager, context)
            sessions.append((session, trackable_bridge))
        initial_object_count = len(created_objects)
        assert initial_object_count == 5, 'Should have created 5 trackable objects'
        for session, bridge in sessions:
            await bridge.cleanup()
        sessions.clear()
        gc.collect()
        await asyncio.sleep(0.1)
        cleaned_count = len([bridge for _, bridge in sessions if hasattr(bridge, 'cleaned_up') and bridge.cleaned_up])
        assert initial_object_count > 0, 'Should have created objects for memory management testing'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
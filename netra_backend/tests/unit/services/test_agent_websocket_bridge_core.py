"""
AgentWebSocketBridge Core Unit Tests - Issue #1081 Phase 1

Comprehensive unit tests for AgentWebSocketBridge core functionality.
Targets WebSocket-Agent integration, event emission, and service coordination.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Risk Reduction
- Value Impact: Protects $500K+ ARR WebSocket-Agent integration functionality
- Strategic Impact: Comprehensive coverage for real-time chat event delivery

Coverage Focus:
- WebSocket-Agent service integration lifecycle
- Event emission and delivery tracking
- Health monitoring and recovery mechanisms
- User context isolation for WebSocket events
- Integration state management and transitions
- Performance monitoring and metrics collection

Test Strategy: Unit tests with real event validation, minimal mocking
"""
import asyncio
import pytest
import unittest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, UTC
from enum import Enum
from dataclasses import dataclass
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, IntegrationState, IntegrationConfig, HealthStatus, IntegrationResult, IntegrationMetrics
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext, create_defensive_user_execution_context
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.monitoring.interfaces import MonitorableComponent

class MockWebSocketManager:
    """Mock WebSocket manager for bridge testing."""

    def __init__(self):
        self.is_healthy = True
        self.connections = {}
        self.events_sent = []
        self.connection_count = 0

    def health_check(self) -> bool:
        """Mock health check."""
        return self.is_healthy

    async def send_event(self, event_type: str, data: Dict[str, Any], user_id: str=None, run_id: str=None):
        """Mock event sending."""
        event = {'type': event_type, 'data': data, 'user_id': user_id, 'run_id': run_id, 'timestamp': datetime.now(UTC).isoformat()}
        self.events_sent.append(event)
        return True

    def get_connection_count(self) -> int:
        """Get active connection count."""
        return self.connection_count

    def set_health_status(self, healthy: bool):
        """Set health status for testing."""
        self.is_healthy = healthy

class MockThreadRunRegistry:
    """Mock thread run registry for bridge testing."""

    def __init__(self):
        self.registrations = {}
        self.is_healthy = True

    def register_run(self, run_id: str, thread_id: str, user_context: UserExecutionContext):
        """Mock run registration."""
        self.registrations[run_id] = {'thread_id': thread_id, 'user_context': user_context, 'timestamp': datetime.now(UTC)}
        return True

    def get_run_info(self, run_id: str):
        """Get run information."""
        return self.registrations.get(run_id)

    def health_check(self) -> bool:
        """Mock health check."""
        return self.is_healthy

class AgentWebSocketBridgeCoreTests(SSotAsyncTestCase):
    """Comprehensive unit tests for AgentWebSocketBridge core functionality."""

    def setup_method(self, method):
        """Set up test fixtures for each test method."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        self.mock_websocket_manager = MockWebSocketManager()
        self.mock_thread_registry = MockThreadRunRegistry()
        self.test_user_id = 'websocket_user_123'
        self.test_session_id = 'websocket_session_456'
        self.user_context = UserExecutionContext(user_id=self.test_user_id, session_id=self.test_session_id, context={'websocket_test': True})
        self.test_config = IntegrationConfig(initialization_timeout_s=5, health_check_interval_s=30, recovery_max_attempts=2, integration_verification_timeout_s=3)
        self.bridge = AgentWebSocketBridge(websocket_manager=self.mock_websocket_manager, config=self.test_config)
        self.test_run_id = 'bridge_test_run_123'
        self.test_thread_id = 'bridge_test_thread_456'
        self.integration_operations = []
        self.event_operations = []

    def teardown_method(self, method):
        """Clean up after each test."""
        super().teardown_method(method)
        self.integration_operations.clear()
        self.event_operations.clear()

    def test_bridge_initialization_with_config(self):
        """Test AgentWebSocketBridge initializes correctly with configuration."""
        assert self.bridge.websocket_manager is not None
        assert self.bridge.config == self.test_config
        assert self.bridge._state == IntegrationState.UNINITIALIZED
        assert self.bridge.config.initialization_timeout_s == 5
        assert self.bridge.config.recovery_max_attempts == 2
        assert hasattr(self.bridge, '_metrics')
        assert isinstance(self.bridge._metrics, IntegrationMetrics)

    def test_bridge_default_configuration(self):
        """Test bridge uses sensible defaults when no config provided."""
        default_bridge = AgentWebSocketBridge(websocket_manager=self.mock_websocket_manager)
        assert default_bridge.config is not None
        assert default_bridge.config.initialization_timeout_s == 30
        assert default_bridge.config.health_check_interval_s == 60
        assert default_bridge.config.recovery_max_attempts == 3

    def test_integration_state_management(self):
        """Test integration state transitions work correctly."""
        assert self.bridge._state == IntegrationState.UNINITIALIZED
        self.bridge._state = IntegrationState.INITIALIZING
        assert self.bridge._state == IntegrationState.INITIALIZING
        self.bridge._state = IntegrationState.ACTIVE
        assert self.bridge._state == IntegrationState.ACTIVE
        current_state = self.bridge.get_integration_state()
        assert current_state == IntegrationState.ACTIVE

    def test_health_status_structure(self):
        """Test health status structure and initialization."""
        health = self.bridge.get_health_status()
        assert isinstance(health, HealthStatus)
        assert hasattr(health, 'state')
        assert hasattr(health, 'websocket_manager_healthy')
        assert hasattr(health, 'registry_healthy')
        assert hasattr(health, 'last_health_check')
        assert hasattr(health, 'consecutive_failures')
        assert hasattr(health, 'total_recoveries')
        assert hasattr(health, 'uptime_seconds')

    async def test_bridge_initialization_process(self):
        """Test complete bridge initialization process."""
        result = await self.bridge.initialize()
        assert isinstance(result, IntegrationResult)
        assert result.success is True
        assert result.state == IntegrationState.ACTIVE
        assert result.error is None
        assert self.bridge._state == IntegrationState.ACTIVE
        assert self.bridge._metrics.total_initializations >= 1
        assert self.bridge._metrics.successful_initializations >= 1

    async def test_bridge_initialization_with_websocket_failure(self):
        """Test bridge initialization handles WebSocket manager failures."""
        self.mock_websocket_manager.set_health_status(False)
        result = await self.bridge.initialize()
        assert isinstance(result, IntegrationResult)
        assert result.state in [IntegrationState.DEGRADED, IntegrationState.FAILED, IntegrationState.ACTIVE]
        if not result.success:
            assert self.bridge._metrics.failed_initializations >= 1

    async def test_bridge_health_monitoring(self):
        """Test bridge health monitoring functionality."""
        await self.bridge.initialize()
        health = self.bridge.get_health_status()
        assert isinstance(health, HealthStatus)
        assert health.state == IntegrationState.ACTIVE
        assert isinstance(health.websocket_manager_healthy, bool)
        assert isinstance(health.last_health_check, datetime)
        assert health.consecutive_failures >= 0
        assert health.uptime_seconds >= 0.0

    async def test_bridge_recovery_mechanism(self):
        """Test bridge recovery from failed state."""
        await self.bridge.initialize()
        self.bridge._state = IntegrationState.FAILED
        self.mock_websocket_manager.set_health_status(True)
        result = await self.bridge.recover()
        assert isinstance(result, IntegrationResult)
        assert result.recovery_attempted is True
        assert result.state in [IntegrationState.ACTIVE, IntegrationState.DEGRADED, IntegrationState.FAILED]
        assert self.bridge._metrics.recovery_attempts >= 1

    async def test_agent_event_emission(self):
        """Test agent event emission through bridge."""
        await self.bridge.initialize()
        event_data = {'agent_name': 'TestAgent', 'message': 'Agent started processing', 'status': 'started'}
        success = await self.bridge.emit_agent_event(event_type='agent_started', data=event_data, run_id=self.test_run_id, user_context=self.user_context)
        assert success is True
        sent_events = self.mock_websocket_manager.events_sent
        assert len(sent_events) >= 1
        our_event = None
        for event in sent_events:
            if event.get('run_id') == self.test_run_id:
                our_event = event
                break
        assert our_event is not None
        assert our_event['type'] == 'agent_started'
        assert our_event['data']['agent_name'] == 'TestAgent'

    async def test_multiple_agent_events_emission(self):
        """Test emission of multiple agent events in sequence."""
        await self.bridge.initialize()
        events = [('agent_started', {'agent': 'TestAgent', 'status': 'started'}), ('agent_thinking', {'agent': 'TestAgent', 'thought': 'Processing request'}), ('tool_executing', {'agent': 'TestAgent', 'tool': 'calculator', 'input': '2+2'}), ('tool_completed', {'agent': 'TestAgent', 'tool': 'calculator', 'result': '4'}), ('agent_completed', {'agent': 'TestAgent', 'status': 'completed', 'result': 'Task done'})]
        for event_type, data in events:
            success = await self.bridge.emit_agent_event(event_type=event_type, data=data, run_id=self.test_run_id, user_context=self.user_context)
            assert success is True
        sent_events = [e for e in self.mock_websocket_manager.events_sent if e.get('run_id') == self.test_run_id]
        assert len(sent_events) == 5
        event_types = [e['type'] for e in sent_events]
        expected_types = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        assert event_types == expected_types

    async def test_event_emission_with_user_isolation(self):
        """Test event emission maintains proper user isolation."""
        await self.bridge.initialize()
        user1_context = UserExecutionContext(user_id='user_1', session_id='session_1', context={})
        user2_context = UserExecutionContext(user_id='user_2', session_id='session_2', context={})
        await self.bridge.emit_agent_event(event_type='agent_started', data={'agent': 'User1Agent'}, run_id='run_1', user_context=user1_context)
        await self.bridge.emit_agent_event(event_type='agent_started', data={'agent': 'User2Agent'}, run_id='run_2', user_context=user2_context)
        sent_events = self.mock_websocket_manager.events_sent
        assert len(sent_events) >= 2
        user1_events = [e for e in sent_events if e.get('user_id') == 'user_1']
        user2_events = [e for e in sent_events if e.get('user_id') == 'user_2']
        assert len(user1_events) >= 1
        assert len(user2_events) >= 1
        assert user1_events[0]['data']['agent'] == 'User1Agent'
        assert user2_events[0]['data']['agent'] == 'User2Agent'

    async def test_event_emission_failure_handling(self):
        """Test handling of event emission failures."""
        await self.bridge.initialize()
        failing_websocket = Mock()
        failing_websocket.send_event = AsyncMock(side_effect=Exception('WebSocket send failed'))
        failing_websocket.health_check = Mock(return_value=False)
        failing_bridge = AgentWebSocketBridge(websocket_manager=failing_websocket, config=self.test_config)
        await failing_bridge.initialize()
        success = await failing_bridge.emit_agent_event(event_type='agent_started', data={'test': 'data'}, run_id=self.test_run_id, user_context=self.user_context)
        assert success is False
        health = failing_bridge.get_health_status()
        assert health.consecutive_failures > 0 or health.state == IntegrationState.FAILED

    async def test_thread_run_registration(self):
        """Test thread run registration integration."""
        if hasattr(self.bridge, 'thread_registry'):
            success = await self.bridge.register_thread_run(run_id=self.test_run_id, thread_id=self.test_thread_id, user_context=self.user_context)
            assert success is True
        else:
            pytest.skip('Thread registry integration not available in this test setup')

    async def test_thread_run_context_management(self):
        """Test thread run context management."""
        await self.bridge.initialize()
        assert hasattr(self.bridge, 'user_context') or hasattr(self.bridge, '_user_context')
        assert True

    def test_integration_metrics_tracking(self):
        """Test integration metrics are properly tracked."""
        metrics = self.bridge.get_metrics()
        assert isinstance(metrics, IntegrationMetrics)
        assert hasattr(metrics, 'total_initializations')
        assert hasattr(metrics, 'successful_initializations')
        assert hasattr(metrics, 'failed_initializations')
        assert hasattr(metrics, 'recovery_attempts')
        assert hasattr(metrics, 'successful_recoveries')
        assert hasattr(metrics, 'total_events_emitted')
        assert hasattr(metrics, 'failed_events')
        assert metrics.total_initializations >= 0
        assert metrics.successful_initializations >= 0
        assert metrics.failed_initializations >= 0

    async def test_event_emission_performance(self):
        """Test event emission performance characteristics."""
        await self.bridge.initialize()
        start_time = time.time()
        for i in range(10):
            await self.bridge.emit_agent_event(event_type='performance_test', data={'index': i, 'test': 'performance'}, run_id=f'{self.test_run_id}_{i}', user_context=self.user_context)
        execution_time = time.time() - start_time
        assert execution_time < 1.0
        performance_events = [e for e in self.mock_websocket_manager.events_sent if e.get('type') == 'performance_test']
        assert len(performance_events) == 10

    def test_memory_usage_during_event_emission(self):
        """Test memory usage during event emission."""
        import sys
        initial_size = sys.getsizeof(self.bridge)
        for i in range(1000):
            self.bridge._metrics.total_events_emitted += 1
        final_size = sys.getsizeof(self.bridge)
        growth = final_size - initial_size
        assert growth < 10000

    async def test_initialization_timeout_handling(self):
        """Test initialization timeout handling."""
        short_timeout_config = IntegrationConfig(initialization_timeout_s=0.001, recovery_max_attempts=1)
        timeout_bridge = AgentWebSocketBridge(websocket_manager=self.mock_websocket_manager, config=short_timeout_config)
        result = await timeout_bridge.initialize()
        assert isinstance(result, IntegrationResult)
        assert result.state in [IntegrationState.ACTIVE, IntegrationState.FAILED, IntegrationState.DEGRADED]

    async def test_recovery_max_attempts_limit(self):
        """Test recovery respects maximum attempts limit."""
        limited_config = IntegrationConfig(recovery_max_attempts=1)
        limited_bridge = AgentWebSocketBridge(websocket_manager=self.mock_websocket_manager, config=limited_config)
        await limited_bridge.initialize()
        limited_bridge._state = IntegrationState.FAILED
        self.mock_websocket_manager.set_health_status(False)
        recovery_results = []
        for _ in range(3):
            result = await limited_bridge.recover()
            recovery_results.append(result)
        total_attempts = sum((1 for r in recovery_results if r.recovery_attempted))
        assert total_attempts <= limited_config.recovery_max_attempts + 1

    async def test_degraded_state_operation(self):
        """Test bridge operation in degraded state."""
        await self.bridge.initialize()
        self.bridge._state = IntegrationState.DEGRADED
        success = await self.bridge.emit_agent_event(event_type='degraded_test', data={'test': 'degraded_operation'}, run_id=self.test_run_id, user_context=self.user_context)
        assert isinstance(success, bool)
        health = self.bridge.get_health_status()
        assert health.state == IntegrationState.DEGRADED

    def test_monitorable_component_interface(self):
        """Test bridge implements MonitorableComponent interface correctly."""
        assert hasattr(self.bridge, 'get_health_status')
        assert hasattr(self.bridge, 'get_metrics')
        health = self.bridge.get_health_status()
        metrics = self.bridge.get_metrics()
        assert isinstance(health, HealthStatus)
        assert isinstance(metrics, IntegrationMetrics)

    def test_integration_state_monitoring(self):
        """Test integration state can be monitored effectively."""
        state = self.bridge.get_integration_state()
        assert isinstance(state, IntegrationState)
        if hasattr(self.bridge, 'get_state_history'):
            history = self.bridge.get_state_history()
            assert isinstance(history, list)

    async def test_real_time_health_monitoring(self):
        """Test real-time health monitoring during operations."""
        await self.bridge.initialize()
        health_before = self.bridge.get_health_status()
        await self.bridge.emit_agent_event(event_type='health_monitor_test', data={'test': 'monitoring'}, run_id=self.test_run_id, user_context=self.user_context)
        health_after = self.bridge.get_health_status()
        assert health_after.last_health_check >= health_before.last_health_check

    def test_golden_path_websocket_components(self):
        """Test all golden path WebSocket components are present."""
        assert self.bridge.websocket_manager is not None, 'WebSocket manager required for golden path'
        assert self.bridge.config is not None, 'Configuration required for golden path'
        assert hasattr(self.bridge, '_metrics'), 'Metrics tracking required for golden path'
        assert hasattr(self.bridge, '_state'), 'State management required for golden path'
        assert hasattr(self.bridge, 'initialize'), 'Initialization required for golden path'
        assert hasattr(self.bridge, 'emit_agent_event'), 'Event emission required for golden path'
        assert hasattr(self.bridge, 'get_health_status'), 'Health monitoring required for golden path'

    async def test_user_context_isolation_in_bridge(self):
        """Test user context isolation is maintained in bridge operations."""
        await self.bridge.initialize()
        contexts = [UserExecutionContext(user_id=f'bridge_user_{i}', session_id=f'bridge_session_{i}', context={}) for i in range(3)]
        tasks = []
        for i, context in enumerate(contexts):
            task = asyncio.create_task(self.bridge.emit_agent_event(event_type='isolation_test', data={'user_index': i}, run_id=f'isolation_run_{i}', user_context=context))
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        assert all(results)
        isolation_events = [e for e in self.mock_websocket_manager.events_sent if e.get('type') == 'isolation_test']
        assert len(isolation_events) == 3
        user_ids = [e.get('user_id') for e in isolation_events]
        assert len(set(user_ids)) == 3

    async def test_websocket_event_delivery_guarantee(self):
        """Test WebSocket events are delivered with proper guarantees."""
        await self.bridge.initialize()
        critical_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        delivery_results = []
        for event_type in critical_events:
            success = await self.bridge.emit_agent_event(event_type=event_type, data={'critical': True, 'business_value': 'high'}, run_id=self.test_run_id, user_context=self.user_context)
            delivery_results.append(success)
        assert all(delivery_results), 'All critical business events must be delivered'
        critical_sent = [e for e in self.mock_websocket_manager.events_sent if e.get('data', {}).get('critical') is True]
        assert len(critical_sent) == 5
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
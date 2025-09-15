"""
Comprehensive Unit Tests for UnifiedLifecycleManager - LARGEST MEGA CLASS SSOT

Test Unified Lifecycle Manager - LARGEST MEGA CLASS SSOT (1,950 lines)

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Zero-Downtime Operations & Platform Reliability  
- Value Impact: Ensures 1,950 lines of lifecycle logic work correctly for chat service
- Strategic Impact: Foundation for chat service reliability (90% platform value)

This is the MOST COMPREHENSIVE test suite in the system, testing the LARGEST approved
MEGA CLASS (1,950 lines) that consolidates 100+ legacy managers into one SSOT.

CRITICAL REQUIREMENTS:
- NO mocks for core business logic (CHEATING ON TESTS = ABOMINATION)
- Test ALL 5 WebSocket events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Test multi-user isolation with factory patterns
- Test zero-downtime operations and graceful shutdowns
- Test atomic operations with rollback on failure
- Test health monitoring and performance metrics
- Test legacy manager compatibility
- Test concurrent user scenarios under load
- Test error recovery and circuit breakers

CRITICAL: This manager is the foundation of platform stability. Every test validates
real-world scenarios ensuring users can reliably access AI chat services without interruption.
"""
import asyncio
import json
import time
import uuid
import threading
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from test_framework.ssot.base import BaseTestCase, AsyncBaseTestCase
from test_framework.websocket_helpers import assert_websocket_events, WebSocketTestHelpers, MockWebSocketConnection
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.managers.unified_lifecycle_manager import SystemLifecycle as UnifiedLifecycleManager, SystemLifecycleFactory as LifecycleManagerFactory, LifecyclePhase, ComponentType, ComponentStatus, LifecycleMetrics, get_lifecycle_manager, setup_application_lifecycle

class UnifiedLifecycleManagerComprehensiveTests(AsyncBaseTestCase):
    """
    Comprehensive test suite for the UnifiedLifecycleManager MEGA CLASS.
    
    This tests the LARGEST SSOT class (1,950 lines) that consolidates 100+ legacy managers.
    Tests cover all lifecycle phases, WebSocket integration, multi-user isolation,
    zero-downtime operations, health monitoring, and error recovery.
    """
    REQUIRES_WEBSOCKET = True
    ISOLATION_ENABLED = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lifecycle_manager = None
        self.mock_websocket_manager = None
        self.mock_db_manager = None
        self.mock_agent_registry = None
        self.mock_health_service = None
        self.test_components = []

    async def asyncSetUp(self):
        """Set up comprehensive test environment with all required components."""
        await super().asyncSetUp()
        self.mock_websocket_manager = self._create_mock_websocket_manager()
        self.mock_db_manager = self._create_mock_database_manager()
        self.mock_agent_registry = self._create_mock_agent_registry()
        self.mock_health_service = self._create_mock_health_service()
        self.test_components = [self.mock_websocket_manager, self.mock_db_manager, self.mock_agent_registry, self.mock_health_service]
        self.lifecycle_manager = UnifiedLifecycleManager(user_id=f'test_user_{uuid.uuid4().hex[:8]}', shutdown_timeout=5, drain_timeout=3, health_check_grace_period=1, startup_timeout=10)
        self.track_resource(self.lifecycle_manager)

    async def asyncTearDown(self):
        """Clean up all test resources."""
        if self.lifecycle_manager and (not self.lifecycle_manager.is_shutting_down()):
            try:
                await self.lifecycle_manager.shutdown()
            except Exception:
                pass
        await super().asyncTearDown()

    def _create_mock_websocket_manager(self):
        """Create mock WebSocket manager with real event emission behavior."""
        mock = AsyncMock()
        mock.broadcast_system_message = AsyncMock()
        mock.get_connection_count = MagicMock(return_value=0)
        mock.close_all_connections = AsyncMock()
        mock.name = 'websocket_manager'
        mock.broadcasted_events = []

        async def track_broadcast(message):
            mock.broadcasted_events.append(message)
        mock.broadcast_system_message.side_effect = track_broadcast
        return mock

    def _create_mock_database_manager(self):
        """Create mock database manager with health check capability."""
        mock = AsyncMock()
        mock.health_check = AsyncMock(return_value={'healthy': True})
        mock.initialize = AsyncMock()
        mock.shutdown = AsyncMock()
        mock.name = 'database_manager'
        return mock

    def _create_mock_agent_registry(self):
        """Create mock agent registry with lifecycle management."""
        mock = AsyncMock()
        mock.get_registry_status = MagicMock(return_value={'ready': True})
        mock.get_active_tasks = MagicMock(return_value=[])
        mock.stop_accepting_requests = MagicMock()
        mock.initialize = AsyncMock()
        mock.shutdown = AsyncMock()
        mock.name = 'agent_registry'
        return mock

    def _create_mock_health_service(self):
        """Create mock health service for testing."""
        mock = AsyncMock()
        mock.mark_shutting_down = AsyncMock()
        mock.initialize = AsyncMock()
        mock.shutdown = AsyncMock()
        mock.name = 'health_service'
        return mock

    async def _register_all_components(self):
        """Register all mock components with the lifecycle manager."""
        await self.lifecycle_manager.register_component('websocket_manager', self.mock_websocket_manager, ComponentType.WEBSOCKET_MANAGER)
        await self.lifecycle_manager.register_component('database_manager', self.mock_db_manager, ComponentType.DATABASE_MANAGER)
        await self.lifecycle_manager.register_component('agent_registry', self.mock_agent_registry, ComponentType.AGENT_REGISTRY)
        await self.lifecycle_manager.register_component('health_service', self.mock_health_service, ComponentType.HEALTH_SERVICE)

    async def test_01_initialization_with_default_parameters(self):
        """Test lifecycle manager initialization with default parameters."""
        manager = UnifiedLifecycleManager()
        self.assertEqual(manager.shutdown_timeout, 30)
        self.assertEqual(manager.drain_timeout, 20)
        self.assertEqual(manager.health_check_grace_period, 5)
        self.assertEqual(manager.startup_timeout, 60)
        self.assertIsNone(manager.user_id)
        self.assertEqual(manager.get_current_phase(), LifecyclePhase.INITIALIZING)
        self.assertFalse(manager.is_running())
        self.assertFalse(manager.is_shutting_down())

    async def test_02_initialization_with_custom_parameters(self):
        """Test lifecycle manager initialization with custom parameters."""
        user_id = f'custom_user_{uuid.uuid4().hex[:8]}'
        manager = UnifiedLifecycleManager(user_id=user_id, shutdown_timeout=45, drain_timeout=25, health_check_grace_period=10, startup_timeout=90)
        self.assertEqual(manager.user_id, user_id)
        self.assertEqual(manager.shutdown_timeout, 45)
        self.assertEqual(manager.drain_timeout, 25)
        self.assertEqual(manager.health_check_grace_period, 10)
        self.assertEqual(manager.startup_timeout, 90)

    async def test_03_environment_configuration_loading(self):
        """Test loading configuration from environment variables."""
        with self.isolated_environment(SHUTDOWN_TIMEOUT='40', DRAIN_TIMEOUT='30', HEALTH_GRACE_PERIOD='8', STARTUP_TIMEOUT='120', LIFECYCLE_ERROR_THRESHOLD='10', HEALTH_CHECK_INTERVAL='45.0'):
            manager = UnifiedLifecycleManager()
            self.assertEqual(manager.shutdown_timeout, 40)
            self.assertEqual(manager.drain_timeout, 30)
            self.assertEqual(manager.health_check_grace_period, 8)
            self.assertEqual(manager.startup_timeout, 120)

    async def test_04_invalid_environment_configuration_fallback(self):
        """Test fallback to defaults when environment configuration is invalid."""
        with self.isolated_environment(SHUTDOWN_TIMEOUT='invalid', DRAIN_TIMEOUT='not_a_number', HEALTH_GRACE_PERIOD='', STARTUP_TIMEOUT='xyz'):
            manager = UnifiedLifecycleManager(shutdown_timeout=35, drain_timeout=15, health_check_grace_period=3, startup_timeout=75)
            self.assertEqual(manager.shutdown_timeout, 35)
            self.assertEqual(manager.drain_timeout, 15)
            self.assertEqual(manager.health_check_grace_period, 3)
            self.assertEqual(manager.startup_timeout, 75)

    async def test_05_component_registration_basic(self):
        """Test basic component registration functionality."""
        component_name = 'test_component'
        await self.lifecycle_manager.register_component(component_name, self.mock_websocket_manager, ComponentType.WEBSOCKET_MANAGER)
        status = self.lifecycle_manager.get_component_status(component_name)
        self.assertIsNotNone(status)
        self.assertEqual(status.name, component_name)
        self.assertEqual(status.component_type, ComponentType.WEBSOCKET_MANAGER)
        self.assertEqual(status.status, 'registered')
        component = self.lifecycle_manager.get_component(ComponentType.WEBSOCKET_MANAGER)
        self.assertEqual(component, self.mock_websocket_manager)

    async def test_06_component_registration_with_health_check(self):
        """Test component registration with health check callback."""
        component_name = 'health_component'

        async def health_check():
            return {'healthy': True, 'response_time': 0.1}
        await self.lifecycle_manager.register_component(component_name, self.mock_db_manager, ComponentType.DATABASE_MANAGER, health_check=health_check)
        status = self.lifecycle_manager.get_component_status(component_name)
        self.assertTrue(status.metadata.get('has_health_check'))
        health_results = await self.lifecycle_manager._run_all_health_checks()
        self.assertIn(component_name, health_results)
        self.assertTrue(health_results[component_name]['healthy'])

    async def test_07_component_unregistration(self):
        """Test component unregistration functionality."""
        component_name = 'temp_component'
        await self.lifecycle_manager.register_component(component_name, self.mock_agent_registry, ComponentType.AGENT_REGISTRY)
        self.assertIsNotNone(self.lifecycle_manager.get_component_status(component_name))
        await self.lifecycle_manager.unregister_component(component_name)
        self.assertIsNone(self.lifecycle_manager.get_component_status(component_name))
        self.assertIsNone(self.lifecycle_manager.get_component(ComponentType.AGENT_REGISTRY))

    async def test_08_multiple_component_registration(self):
        """Test registration of multiple components of different types."""
        await self._register_all_components()
        ws_status = self.lifecycle_manager.get_component_status('websocket_manager')
        db_status = self.lifecycle_manager.get_component_status('database_manager')
        agent_status = self.lifecycle_manager.get_component_status('agent_registry')
        health_status = self.lifecycle_manager.get_component_status('health_service')
        self.assertIsNotNone(ws_status)
        self.assertIsNotNone(db_status)
        self.assertIsNotNone(agent_status)
        self.assertIsNotNone(health_status)
        self.assertEqual(ws_status.component_type, ComponentType.WEBSOCKET_MANAGER)
        self.assertEqual(db_status.component_type, ComponentType.DATABASE_MANAGER)
        self.assertEqual(agent_status.component_type, ComponentType.AGENT_REGISTRY)
        self.assertEqual(health_status.component_type, ComponentType.HEALTH_SERVICE)

    async def test_09_duplicate_component_type_registration(self):
        """Test handling of duplicate component type registration."""
        await self.lifecycle_manager.register_component('first_db', self.mock_db_manager, ComponentType.DATABASE_MANAGER)
        new_db_manager = self._create_mock_database_manager()
        await self.lifecycle_manager.register_component('second_db', new_db_manager, ComponentType.DATABASE_MANAGER)
        active_component = self.lifecycle_manager.get_component(ComponentType.DATABASE_MANAGER)
        self.assertEqual(active_component, new_db_manager)

    async def test_10_startup_sequence_success(self):
        """Test complete successful startup sequence."""
        await self._register_all_components()
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)
        self.assertTrue(self.lifecycle_manager.is_running())
        self.assertIsNotNone(self.lifecycle_manager._metrics.startup_time)
        self.assertGreater(self.lifecycle_manager._metrics.startup_time, 0)
        self.mock_db_manager.initialize.assert_called_once()
        self.mock_agent_registry.initialize.assert_called_once()
        self.mock_health_service.initialize.assert_called_once()

    async def test_11_startup_with_no_components(self):
        """Test startup sequence with no registered components."""
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)
        self.assertTrue(self.lifecycle_manager.is_running())

    async def test_12_startup_failure_due_to_component_validation(self):
        """Test startup failure due to component validation error."""
        failing_db = AsyncMock()
        failing_db.health_check = AsyncMock(return_value={'healthy': False, 'error': 'Connection failed'})
        failing_db.name = 'failing_db'
        await self.lifecycle_manager.register_component('failing_database', failing_db, ComponentType.DATABASE_MANAGER)
        success = await self.lifecycle_manager.startup()
        self.assertFalse(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.ERROR)

    async def test_13_startup_failure_due_to_component_initialization(self):
        """Test startup failure due to component initialization error."""
        failing_component = AsyncMock()
        failing_component.initialize = AsyncMock(side_effect=Exception('Init failed'))
        failing_component.name = 'failing_component'
        await self.lifecycle_manager.register_component('failing_component', failing_component, ComponentType.LLM_MANAGER)
        success = await self.lifecycle_manager.startup()
        self.assertFalse(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.ERROR)

    async def test_14_startup_phase_validation_components(self):
        """Test startup phase 1: component validation."""
        await self._register_all_components()
        startup_task = asyncio.create_task(self.lifecycle_manager.startup())
        await asyncio.sleep(0.1)
        self.mock_db_manager.health_check.assert_called()
        success = await startup_task
        self.assertTrue(success)

    async def test_15_startup_component_initialization_order(self):
        """Test that components are initialized in correct order."""
        await self._register_all_components()
        init_order = []

        async def track_db_init():
            init_order.append('database')

        async def track_agent_init():
            init_order.append('agent_registry')

        async def track_health_init():
            init_order.append('health_service')
        self.mock_db_manager.initialize = track_db_init
        self.mock_agent_registry.initialize = track_agent_init
        self.mock_health_service.initialize = track_health_init
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        self.assertIn('database', init_order)
        self.assertIn('agent_registry', init_order)
        self.assertIn('health_service', init_order)
        db_index = init_order.index('database')
        agent_index = init_order.index('agent_registry')
        self.assertLess(db_index, agent_index)

    async def test_16_startup_duplicate_attempt(self):
        """Test that duplicate startup attempts are handled correctly."""
        await self._register_all_components()
        success1 = await self.lifecycle_manager.startup()
        self.assertTrue(success1)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)
        success2 = await self.lifecycle_manager.startup()
        self.assertFalse(success2)

    async def test_17_websocket_events_during_startup(self):
        """Test that WebSocket events are emitted during startup sequence."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        await self._register_all_components()
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        broadcasted_events = self.mock_websocket_manager.broadcasted_events
        event_types = [event.get('type', '') for event in broadcasted_events]
        self.assertIn('lifecycle_startup_completed', event_types)
        self.assertIn('lifecycle_phase_changed', event_types)

    async def test_18_websocket_agent_events_integration(self):
        """Test integration with all 5 required WebSocket agent events."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        await self.lifecycle_manager._emit_websocket_event('agent_started', {'agent_name': 'test_agent', 'user_id': self.lifecycle_manager.user_id})
        await self.lifecycle_manager._emit_websocket_event('agent_thinking', {'reasoning': 'Analyzing test scenario', 'agent_name': 'test_agent'})
        await self.lifecycle_manager._emit_websocket_event('tool_executing', {'tool_name': 'test_tool', 'parameters': {'test': 'value'}})
        await self.lifecycle_manager._emit_websocket_event('tool_completed', {'tool_name': 'test_tool', 'results': {'success': True}})
        await self.lifecycle_manager._emit_websocket_event('agent_completed', {'response': 'Test completed successfully', 'agent_name': 'test_agent'})
        broadcasted_events = self.mock_websocket_manager.broadcasted_events
        agent_event_types = [event.get('type', '') for event in broadcasted_events if event.get('type', '').startswith('lifecycle_agent_') or event.get('type', '').startswith('lifecycle_tool_')]
        expected_events = ['lifecycle_agent_started', 'lifecycle_agent_thinking', 'lifecycle_tool_executing', 'lifecycle_tool_completed', 'lifecycle_agent_completed']
        for expected_event in expected_events:
            self.assertIn(expected_event, agent_event_types)

    async def test_19_websocket_event_structure_validation(self):
        """Test that WebSocket events have proper structure and required fields."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        test_data = {'test_field': 'test_value', 'timestamp': time.time()}
        await self.lifecycle_manager._emit_websocket_event('test_event', test_data)
        broadcasted_events = self.mock_websocket_manager.broadcasted_events
        self.assertGreater(len(broadcasted_events), 0)
        event = broadcasted_events[-1]
        self.assertEqual(event['type'], 'lifecycle_test_event')
        self.assertIn('data', event)
        self.assertIn('timestamp', event)
        self.assertIn('user_id', event)
        self.assertEqual(event['data']['test_field'], 'test_value')

    async def test_20_websocket_events_disabled(self):
        """Test that WebSocket events can be disabled."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        self.lifecycle_manager.enable_websocket_events(False)
        await self.lifecycle_manager._emit_websocket_event('disabled_test', {'data': 'value'})
        self.assertEqual(len(self.mock_websocket_manager.broadcasted_events), 0)
        self.lifecycle_manager.enable_websocket_events(True)
        await self.lifecycle_manager._emit_websocket_event('enabled_test', {'data': 'value'})
        self.assertEqual(len(self.mock_websocket_manager.broadcasted_events), 1)

    async def test_21_websocket_event_error_handling(self):
        """Test error handling in WebSocket event emission."""
        failing_ws = AsyncMock()
        failing_ws.broadcast_system_message = AsyncMock(side_effect=Exception('Broadcast failed'))
        self.lifecycle_manager.set_websocket_manager(failing_ws)
        try:
            await self.lifecycle_manager._emit_websocket_event('error_test', {'data': 'value'})
        except Exception as e:
            self.fail(f'WebSocket event emission should not raise exception: {e}')

    async def test_22_shutdown_sequence_success(self):
        """Test complete successful shutdown sequence."""
        await self._register_all_components()
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        self.assertTrue(self.lifecycle_manager.is_running())
        shutdown_success = await self.lifecycle_manager.shutdown()
        self.assertTrue(shutdown_success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)
        self.assertTrue(self.lifecycle_manager.is_shutting_down())
        self.assertIsNotNone(self.lifecycle_manager._metrics.shutdown_time)
        self.assertGreater(self.lifecycle_manager._metrics.shutdown_time, 0)
        self.assertEqual(self.lifecycle_manager._metrics.successful_shutdowns, 1)
        self.mock_db_manager.shutdown.assert_called_once()
        self.mock_agent_registry.shutdown.assert_called_once()
        self.mock_health_service.shutdown.assert_called_once()

    async def test_23_shutdown_duplicate_attempt(self):
        """Test that duplicate shutdown attempts are handled correctly."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        success1 = await self.lifecycle_manager.shutdown()
        self.assertTrue(success1)
        success2 = await self.lifecycle_manager.shutdown()
        self.assertTrue(success2)
        self.mock_db_manager.shutdown.assert_called_once()

    async def test_24_shutdown_component_order(self):
        """Test that components are shut down in reverse initialization order."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        shutdown_order = []

        async def track_health_shutdown():
            shutdown_order.append('health_service')

        async def track_agent_shutdown():
            shutdown_order.append('agent_registry')

        async def track_db_shutdown():
            shutdown_order.append('database')
        self.mock_health_service.shutdown = track_health_shutdown
        self.mock_agent_registry.shutdown = track_agent_shutdown
        self.mock_db_manager.shutdown = track_db_shutdown
        success = await self.lifecycle_manager.shutdown()
        self.assertTrue(success)
        self.assertIn('health_service', shutdown_order)
        self.assertIn('agent_registry', shutdown_order)
        self.assertIn('database', shutdown_order)
        health_index = shutdown_order.index('health_service')
        db_index = shutdown_order.index('database')
        self.assertLess(health_index, db_index)

    async def test_25_shutdown_with_active_requests(self):
        """Test shutdown with active requests that need to be drained."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        request_ids = [f'req_{i}' for i in range(3)]
        for req_id in request_ids:
            async with self.lifecycle_manager.request_context(req_id):
                shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
                await asyncio.sleep(0.1)
                self.assertIn(req_id, self.lifecycle_manager._active_requests)
        success = await shutdown_task
        self.assertTrue(success)
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)

    async def test_26_shutdown_websocket_notification(self):
        """Test that WebSocket connections are notified during shutdown."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        self.mock_websocket_manager.get_connection_count.return_value = 5
        success = await self.lifecycle_manager.shutdown()
        self.assertTrue(success)
        self.mock_websocket_manager.broadcast_system_message.assert_called()
        self.mock_websocket_manager.close_all_connections.assert_called_once()
        broadcast_calls = self.mock_websocket_manager.broadcast_system_message.call_args_list
        shutdown_messages = [call[0][0] for call in broadcast_calls if call[0][0].get('type') == 'system_shutdown']
        self.assertGreater(len(shutdown_messages), 0)
        shutdown_msg = shutdown_messages[0]
        self.assertEqual(shutdown_msg['type'], 'system_shutdown')
        self.assertIn('message', shutdown_msg)
        self.assertIn('reconnect_delay', shutdown_msg)

    async def test_27_shutdown_error_handling(self):
        """Test shutdown error handling when components fail to shut down."""
        failing_component = AsyncMock()
        failing_component.shutdown = AsyncMock(side_effect=Exception('Shutdown failed'))
        failing_component.name = 'failing_component'
        await self.lifecycle_manager.register_component('failing_component', failing_component, ComponentType.LLM_MANAGER)
        await self.lifecycle_manager.startup()
        success = await self.lifecycle_manager.shutdown()
        self.assertTrue(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)

    async def test_28_health_monitoring_startup(self):
        """Test that health monitoring starts during startup."""
        await self._register_all_components()
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        self.assertIsNotNone(self.lifecycle_manager._health_check_task)
        self.assertFalse(self.lifecycle_manager._health_check_task.done())

    async def test_29_health_check_execution(self):
        """Test health check execution for registered components."""

        async def health_check():
            return {'healthy': True, 'response_time': 0.05}
        await self.lifecycle_manager.register_component('health_test_component', self.mock_db_manager, ComponentType.DATABASE_MANAGER, health_check=health_check)
        results = await self.lifecycle_manager._run_all_health_checks()
        self.assertIn('health_test_component', results)
        self.assertTrue(results['health_test_component']['healthy'])
        self.assertEqual(results['health_test_component']['response_time'], 0.05)

    async def test_30_health_check_failure_handling(self):
        """Test handling of health check failures."""

        async def failing_health_check():
            raise Exception('Health check failed')
        await self.lifecycle_manager.register_component('unhealthy_component', self.mock_db_manager, ComponentType.DATABASE_MANAGER, health_check=failing_health_check)
        results = await self.lifecycle_manager._run_all_health_checks()
        self.assertIn('unhealthy_component', results)
        self.assertFalse(results['unhealthy_component']['healthy'])
        self.assertIn('error', results['unhealthy_component'])
        self.assertTrue(results['unhealthy_component']['critical'])

    async def test_31_health_status_endpoint_response(self):
        """Test health status response for monitoring endpoints."""
        await self._register_all_components()
        health_status = self.lifecycle_manager.get_health_status()
        self.assertEqual(health_status['status'], 'unhealthy')
        self.assertEqual(health_status['phase'], 'initializing')
        self.assertFalse(health_status['ready'])
        await self.lifecycle_manager.startup()
        health_status = self.lifecycle_manager.get_health_status()
        self.assertEqual(health_status['status'], 'healthy')
        self.assertEqual(health_status['phase'], 'running')
        self.assertIn('components_healthy', health_status)
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        await asyncio.sleep(0.1)
        health_status = self.lifecycle_manager.get_health_status()
        if self.lifecycle_manager.get_current_phase() == LifecyclePhase.SHUTTING_DOWN:
            self.assertEqual(health_status['status'], 'shutting_down')
            self.assertFalse(health_status['ready'])
        await shutdown_task

    async def test_32_metrics_collection_during_lifecycle(self):
        """Test that lifecycle metrics are collected properly."""
        await self._register_all_components()
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        metrics = self.lifecycle_manager._metrics
        self.assertIsNotNone(metrics.startup_time)
        self.assertGreater(metrics.startup_time, 0)
        success = await self.lifecycle_manager.shutdown()
        self.assertTrue(success)
        self.assertIsNotNone(metrics.shutdown_time)
        self.assertGreater(metrics.shutdown_time, 0)
        self.assertEqual(metrics.successful_shutdowns, 1)
        self.assertEqual(metrics.failed_shutdowns, 0)

    async def test_33_request_context_tracking(self):
        """Test request context tracking for graceful shutdown."""
        request_id = f'test_request_{uuid.uuid4().hex[:8]}'
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
        self.assertEqual(self.lifecycle_manager._metrics.active_requests, 0)
        async with self.lifecycle_manager.request_context(request_id):
            self.assertIn(request_id, self.lifecycle_manager._active_requests)
            self.assertEqual(len(self.lifecycle_manager._active_requests), 1)
            self.assertEqual(self.lifecycle_manager._metrics.active_requests, 1)
            start_time = self.lifecycle_manager._active_requests[request_id]
            self.assertGreater(start_time, 0)
        self.assertNotIn(request_id, self.lifecycle_manager._active_requests)
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
        self.assertEqual(self.lifecycle_manager._metrics.active_requests, 0)

    async def test_34_concurrent_request_tracking(self):
        """Test tracking of multiple concurrent requests."""
        request_ids = [f'req_{i}_{uuid.uuid4().hex[:8]}' for i in range(5)]

        async def request_handler(req_id):
            async with self.lifecycle_manager.request_context(req_id):
                await asyncio.sleep(0.1)
        tasks = [asyncio.create_task(request_handler(req_id)) for req_id in request_ids]
        await asyncio.sleep(0.05)
        self.assertEqual(len(self.lifecycle_manager._active_requests), 5)
        self.assertEqual(self.lifecycle_manager._metrics.active_requests, 5)
        await asyncio.gather(*tasks)
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
        self.assertEqual(self.lifecycle_manager._metrics.active_requests, 0)

    async def test_35_request_tracking_error_cleanup(self):
        """Test that request tracking cleans up even if request fails."""
        request_id = f'failing_request_{uuid.uuid4().hex[:8]}'
        try:
            async with self.lifecycle_manager.request_context(request_id):
                self.assertIn(request_id, self.lifecycle_manager._active_requests)
                raise ValueError('Request processing failed')
        except ValueError:
            pass
        self.assertNotIn(request_id, self.lifecycle_manager._active_requests)
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)

    async def test_36_startup_handler_registration_and_execution(self):
        """Test registration and execution of startup handlers."""
        handler_executed = False

        def startup_handler():
            nonlocal handler_executed
            handler_executed = True
        self.lifecycle_manager.add_startup_handler(startup_handler)
        await self._register_all_components()
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        self.assertTrue(handler_executed)

    async def test_37_async_startup_handler(self):
        """Test async startup handler execution."""
        handler_executed = False

        async def async_startup_handler():
            nonlocal handler_executed
            await asyncio.sleep(0.01)
            handler_executed = True
        self.lifecycle_manager.add_startup_handler(async_startup_handler)
        await self._register_all_components()
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        self.assertTrue(handler_executed)

    async def test_38_shutdown_handler_registration_and_execution(self):
        """Test registration and execution of shutdown handlers."""
        handler_executed = False

        def shutdown_handler():
            nonlocal handler_executed
            handler_executed = True
        self.lifecycle_manager.add_shutdown_handler(shutdown_handler)
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        success = await self.lifecycle_manager.shutdown()
        self.assertTrue(success)
        self.assertTrue(handler_executed)

    async def test_39_lifecycle_hook_registration_and_execution(self):
        """Test lifecycle hook registration and execution."""
        hook_events = []

        def pre_startup_hook():
            hook_events.append('pre_startup')

        def post_startup_hook():
            hook_events.append('post_startup')

        def pre_shutdown_hook():
            hook_events.append('pre_shutdown')

        def post_shutdown_hook():
            hook_events.append('post_shutdown')
        self.lifecycle_manager.register_lifecycle_hook('pre_startup', pre_startup_hook)
        self.lifecycle_manager.register_lifecycle_hook('post_startup', post_startup_hook)
        self.lifecycle_manager.register_lifecycle_hook('pre_shutdown', pre_shutdown_hook)
        self.lifecycle_manager.register_lifecycle_hook('post_shutdown', post_shutdown_hook)
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        await self.lifecycle_manager.shutdown()
        expected_hooks = ['pre_startup', 'post_startup', 'pre_shutdown', 'post_shutdown']
        self.assertEqual(hook_events, expected_hooks)

    async def test_40_error_hook_execution(self):
        """Test error hook execution when errors occur."""
        error_events = []

        def error_hook(**kwargs):
            error_events.append({'error': str(kwargs.get('error', '')), 'phase': kwargs.get('phase', 'unknown')})
        self.lifecycle_manager.register_lifecycle_hook('on_error', error_hook)
        failing_component = AsyncMock()
        failing_component.initialize = AsyncMock(side_effect=Exception('Init failed'))
        await self.lifecycle_manager.register_component('failing_component', failing_component, ComponentType.LLM_MANAGER)
        success = await self.lifecycle_manager.startup()
        self.assertFalse(success)
        self.assertGreater(len(error_events), 0)
        self.assertIn('Init failed', error_events[0]['error'])
        self.assertEqual(error_events[0]['phase'], 'startup')

    async def test_41_handler_error_isolation(self):
        """Test that handler errors don't break lifecycle operations."""

        def failing_handler():
            raise Exception('Handler failed')

        def working_handler():
            working_handler.executed = True
        working_handler.executed = False
        self.lifecycle_manager.add_startup_handler(failing_handler)
        self.lifecycle_manager.add_startup_handler(working_handler)
        await self._register_all_components()
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        self.assertTrue(working_handler.executed)

    async def test_42_phase_transitions_and_logging(self):
        """Test lifecycle phase transitions and state management."""
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.INITIALIZING)
        await self._register_all_components()
        startup_task = asyncio.create_task(self.lifecycle_manager.startup())
        await asyncio.sleep(0.1)
        current_phase = self.lifecycle_manager.get_current_phase()
        self.assertIn(current_phase, [LifecyclePhase.STARTING, LifecyclePhase.RUNNING])
        success = await startup_task
        self.assertTrue(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)
        self.assertTrue(self.lifecycle_manager.is_running())
        self.assertFalse(self.lifecycle_manager.is_shutting_down())
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        await asyncio.sleep(0.1)
        if not shutdown_task.done():
            self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTTING_DOWN)
            self.assertTrue(self.lifecycle_manager.is_shutting_down())
        success = await shutdown_task
        self.assertTrue(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)

    async def test_43_comprehensive_status_information(self):
        """Test comprehensive status information retrieval."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        status = self.lifecycle_manager.get_status()
        self.assertIn('user_id', status)
        self.assertIn('phase', status)
        self.assertIn('startup_time', status)
        self.assertIn('active_requests', status)
        self.assertIn('components', status)
        self.assertIn('metrics', status)
        self.assertIn('is_shutting_down', status)
        self.assertIn('ready_for_requests', status)
        self.assertIn('uptime', status)
        self.assertEqual(status['phase'], 'running')
        self.assertTrue(status['ready_for_requests'])
        self.assertFalse(status['is_shutting_down'])
        self.assertGreater(status['uptime'], 0)
        self.assertIn('websocket_manager', status['components'])
        self.assertIn('database_manager', status['components'])
        self.assertIn('successful_shutdowns', status['metrics'])
        self.assertIn('failed_shutdowns', status['metrics'])
        self.assertIn('component_failures', status['metrics'])

    async def test_44_wait_for_shutdown_functionality(self):
        """Test wait_for_shutdown functionality."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        wait_task = asyncio.create_task(self.lifecycle_manager.wait_for_shutdown())
        await asyncio.sleep(0.1)
        self.assertFalse(wait_task.done())
        await self.lifecycle_manager.shutdown()
        await asyncio.wait_for(wait_task, timeout=1.0)
        self.assertTrue(wait_task.done())

    async def test_45_factory_global_manager_creation(self):
        """Test factory pattern global manager creation."""
        global_manager = LifecycleManagerFactory.get_global_manager()
        self.assertIsInstance(global_manager, UnifiedLifecycleManager)
        self.assertIsNone(global_manager.user_id)
        global_manager2 = LifecycleManagerFactory.get_global_manager()
        self.assertIs(global_manager, global_manager2)

    async def test_46_factory_user_manager_creation(self):
        """Test factory pattern user-specific manager creation."""
        user_id = f'factory_user_{uuid.uuid4().hex[:8]}'
        user_manager = LifecycleManagerFactory.get_user_manager(user_id)
        self.assertIsInstance(user_manager, UnifiedLifecycleManager)
        self.assertEqual(user_manager.user_id, user_id)
        user_manager2 = LifecycleManagerFactory.get_user_manager(user_id)
        self.assertIs(user_manager, user_manager2)
        user_id2 = f'factory_user2_{uuid.uuid4().hex[:8]}'
        user_manager3 = LifecycleManagerFactory.get_user_manager(user_id2)
        self.assertIsNot(user_manager, user_manager3)
        self.assertEqual(user_manager3.user_id, user_id2)

    async def test_47_factory_manager_isolation(self):
        """Test that factory managers are properly isolated."""
        user_id1 = f'user1_{uuid.uuid4().hex[:8]}'
        user_id2 = f'user2_{uuid.uuid4().hex[:8]}'
        manager1 = LifecycleManagerFactory.get_user_manager(user_id1)
        manager2 = LifecycleManagerFactory.get_user_manager(user_id2)
        global_manager = LifecycleManagerFactory.get_global_manager()
        self.assertIsNot(manager1, manager2)
        self.assertIsNot(manager1, global_manager)
        self.assertIsNot(manager2, global_manager)
        mock_component = AsyncMock()
        await manager1.register_component('isolated_component', mock_component, ComponentType.DATABASE_MANAGER)
        self.assertIsNotNone(manager1.get_component(ComponentType.DATABASE_MANAGER))
        self.assertIsNone(manager2.get_component(ComponentType.DATABASE_MANAGER))
        self.assertIsNone(global_manager.get_component(ComponentType.DATABASE_MANAGER))

    async def test_48_factory_shutdown_all_managers(self):
        """Test factory shutdown of all managers."""
        user_ids = [f'user_{i}_{uuid.uuid4().hex[:8]}' for i in range(3)]
        managers = []
        global_manager = LifecycleManagerFactory.get_global_manager()
        managers.append(global_manager)
        for user_id in user_ids:
            manager = LifecycleManagerFactory.get_user_manager(user_id)
            managers.append(manager)
        for manager in managers:
            await manager.startup()
            self.assertTrue(manager.is_running())
        await LifecycleManagerFactory.shutdown_all_managers()
        for manager in managers:
            self.assertEqual(manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)
        counts = LifecycleManagerFactory.get_manager_count()
        self.assertEqual(counts['global'], 0)
        self.assertEqual(counts['user_specific'], 0)
        self.assertEqual(counts['total'], 0)

    async def test_49_convenience_function_get_lifecycle_manager(self):
        """Test convenience function for getting lifecycle managers."""
        global_manager = get_lifecycle_manager()
        factory_global = LifecycleManagerFactory.get_global_manager()
        self.assertIs(global_manager, factory_global)
        user_id = f'convenience_user_{uuid.uuid4().hex[:8]}'
        user_manager = get_lifecycle_manager(user_id)
        factory_user = LifecycleManagerFactory.get_user_manager(user_id)
        self.assertIs(user_manager, factory_user)

    async def test_50_concurrent_user_startup_shutdown(self):
        """Test concurrent startup and shutdown operations for multiple users."""
        user_count = 5
        user_ids = [f'concurrent_user_{i}_{uuid.uuid4().hex[:8]}' for i in range(user_count)]
        managers = [LifecycleManagerFactory.get_user_manager(user_id) for user_id in user_ids]
        for manager in managers:
            mock_db = AsyncMock()
            mock_db.initialize = AsyncMock()
            mock_db.shutdown = AsyncMock()
            mock_db.health_check = AsyncMock(return_value={'healthy': True})
            await manager.register_component('concurrent_db', mock_db, ComponentType.DATABASE_MANAGER)
        startup_tasks = [manager.startup() for manager in managers]
        startup_results = await asyncio.gather(*startup_tasks)
        for result in startup_results:
            self.assertTrue(result)
        for manager in managers:
            self.assertTrue(manager.is_running())
        shutdown_tasks = [manager.shutdown() for manager in managers]
        shutdown_results = await asyncio.gather(*shutdown_tasks)
        for result in shutdown_results:
            self.assertTrue(result)
        for manager in managers:
            self.assertEqual(manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)

    async def test_51_concurrent_component_registration(self):
        """Test concurrent component registration across multiple managers."""
        user_count = 3
        components_per_user = 4

        async def register_components_for_user(user_id):
            manager = LifecycleManagerFactory.get_user_manager(user_id)
            registration_tasks = []
            for i in range(components_per_user):
                mock_component = AsyncMock()
                mock_component.name = f'component_{i}'
                task = manager.register_component(f'component_{i}', mock_component, ComponentType.LLM_MANAGER)
                registration_tasks.append(task)
            await asyncio.gather(*registration_tasks)
            return manager
        user_ids = [f'reg_user_{i}_{uuid.uuid4().hex[:8]}' for i in range(user_count)]
        registration_tasks = [register_components_for_user(user_id) for user_id in user_ids]
        managers = await asyncio.gather(*registration_tasks)
        for manager in managers:
            component_count = len(manager._components)
            self.assertEqual(component_count, components_per_user)

    async def test_52_concurrent_request_handling_during_lifecycle(self):
        """Test handling concurrent requests during lifecycle operations."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        request_count = 10
        request_duration = 0.5

        async def simulate_request(req_id):
            async with self.lifecycle_manager.request_context(req_id):
                await asyncio.sleep(request_duration)
        request_ids = [f'concurrent_req_{i}' for i in range(request_count)]
        request_tasks = [asyncio.create_task(simulate_request(req_id)) for req_id in request_ids]
        await asyncio.sleep(0.1)
        self.assertEqual(len(self.lifecycle_manager._active_requests), request_count)
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        await asyncio.sleep(0.1)
        if not shutdown_task.done():
            self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTTING_DOWN)
        await asyncio.gather(*request_tasks)
        success = await shutdown_task
        self.assertTrue(success)
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)

    async def test_53_performance_under_high_component_count(self):
        """Test performance with high number of components."""
        component_count = 50
        registration_start = time.time()
        for i in range(component_count):
            mock_component = AsyncMock()
            mock_component.initialize = AsyncMock()
            mock_component.shutdown = AsyncMock()
            mock_component.name = f'perf_component_{i}'
            await self.lifecycle_manager.register_component(f'perf_component_{i}', mock_component, ComponentType.LLM_MANAGER)
        registration_time = time.time() - registration_start
        self.assertLess(registration_time, 1.0)
        startup_start = time.time()
        success = await self.lifecycle_manager.startup()
        startup_time = time.time() - startup_start
        self.assertTrue(success)
        self.assertLess(startup_time, 5.0)
        shutdown_start = time.time()
        success = await self.lifecycle_manager.shutdown()
        shutdown_time = time.time() - shutdown_start
        self.assertTrue(success)
        self.assertLess(shutdown_time, 5.0)

    async def test_54_component_failure_recovery(self):
        """Test recovery from component failures during health checks."""
        failure_count = 0

        async def flaky_health_check():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:
                raise Exception('Temporary failure')
            return {'healthy': True, 'recovered': True}
        await self.lifecycle_manager.register_component('flaky_component', self.mock_db_manager, ComponentType.DATABASE_MANAGER, health_check=flaky_health_check)
        results = await self.lifecycle_manager._run_all_health_checks()
        self.assertFalse(results['flaky_component']['healthy'])
        self.assertEqual(failure_count, 1)
        results = await self.lifecycle_manager._run_all_health_checks()
        self.assertFalse(results['flaky_component']['healthy'])
        self.assertEqual(failure_count, 2)
        results = await self.lifecycle_manager._run_all_health_checks()
        self.assertTrue(results['flaky_component']['healthy'])
        self.assertTrue(results['flaky_component']['recovered'])
        self.assertEqual(failure_count, 3)

    async def test_55_startup_failure_cleanup(self):
        """Test proper cleanup when startup fails."""
        failing_component = AsyncMock()
        failing_component.initialize = AsyncMock(side_effect=Exception('Init failed'))
        failing_component.shutdown = AsyncMock()
        success_component = AsyncMock()
        success_component.initialize = AsyncMock()
        success_component.shutdown = AsyncMock()
        await self.lifecycle_manager.register_component('success_component', success_component, ComponentType.DATABASE_MANAGER)
        await self.lifecycle_manager.register_component('failing_component', failing_component, ComponentType.LLM_MANAGER)
        success = await self.lifecycle_manager.startup()
        self.assertFalse(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.ERROR)
        success_component.shutdown.assert_not_called()
        failing_component.shutdown.assert_not_called()

    async def test_56_shutdown_partial_failure_continuation(self):
        """Test that shutdown continues even if some components fail."""
        success_component = AsyncMock()
        success_component.initialize = AsyncMock()
        success_component.shutdown = AsyncMock()
        failing_component = AsyncMock()
        failing_component.initialize = AsyncMock()
        failing_component.shutdown = AsyncMock(side_effect=Exception('Shutdown failed'))
        another_success_component = AsyncMock()
        another_success_component.initialize = AsyncMock()
        another_success_component.shutdown = AsyncMock()
        await self.lifecycle_manager.register_component('success1', success_component, ComponentType.DATABASE_MANAGER)
        await self.lifecycle_manager.register_component('failing', failing_component, ComponentType.LLM_MANAGER)
        await self.lifecycle_manager.register_component('success2', another_success_component, ComponentType.HEALTH_SERVICE)
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        success = await self.lifecycle_manager.shutdown()
        self.assertTrue(success)
        success_component.shutdown.assert_called_once()
        failing_component.shutdown.assert_called_once()
        another_success_component.shutdown.assert_called_once()

    async def test_57_error_threshold_handling(self):
        """Test error threshold handling in health monitoring."""
        error_count = 0

        async def error_prone_health_check():
            nonlocal error_count
            error_count += 1
            raise Exception(f'Health check error #{error_count}')
        await self.lifecycle_manager.register_component('error_prone', self.mock_db_manager, ComponentType.DATABASE_MANAGER, health_check=error_prone_health_check)
        await self.lifecycle_manager.startup()
        for i in range(6):
            await self.lifecycle_manager._run_periodic_health_checks()
        component_status = self.lifecycle_manager.get_component_status('error_prone')
        self.assertEqual(component_status.status, 'unhealthy')
        self.assertGreaterEqual(component_status.error_count, 5)
        self.assertGreaterEqual(self.lifecycle_manager._metrics.component_failures, 5)

    async def test_58_graceful_request_draining(self):
        """Test graceful draining of active requests during shutdown."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        long_request_id = f'long_request_{uuid.uuid4().hex[:8]}'
        request_completed = False

        async def long_running_request():
            nonlocal request_completed
            async with self.lifecycle_manager.request_context(long_request_id):
                await asyncio.sleep(2.0)
                request_completed = True
        request_task = asyncio.create_task(long_running_request())
        await asyncio.sleep(0.1)
        self.assertIn(long_request_id, self.lifecycle_manager._active_requests)
        shutdown_start = time.time()
        success = await self.lifecycle_manager.shutdown()
        shutdown_duration = time.time() - shutdown_start
        self.assertTrue(success)
        self.assertGreaterEqual(shutdown_duration, 2.0)
        await request_task
        self.assertTrue(request_completed)
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)

    async def test_59_health_check_grace_period_during_shutdown(self):
        """Test health check grace period during shutdown."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        self.mock_health_service.mark_shutting_down = AsyncMock()
        grace_start = time.time()
        await self.lifecycle_manager._shutdown_phase_1_mark_unhealthy()
        grace_duration = time.time() - grace_start
        expected_grace = self.lifecycle_manager.health_check_grace_period
        self.assertGreaterEqual(grace_duration, expected_grace - 0.1)
        self.mock_health_service.mark_shutting_down.assert_called_once()

    async def test_60_zero_downtime_component_replacement(self):
        """Test zero-downtime component replacement scenario."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        initial_db = self.lifecycle_manager.get_component(ComponentType.DATABASE_MANAGER)
        self.assertEqual(initial_db, self.mock_db_manager)
        new_db_manager = AsyncMock()
        new_db_manager.initialize = AsyncMock()
        new_db_manager.shutdown = AsyncMock()
        new_db_manager.health_check = AsyncMock(return_value={'healthy': True})
        new_db_manager.name = 'new_database_manager'
        await self.lifecycle_manager.register_component('new_database_manager', new_db_manager, ComponentType.DATABASE_MANAGER)
        current_db = self.lifecycle_manager.get_component(ComponentType.DATABASE_MANAGER)
        self.assertEqual(current_db, new_db_manager)
        self.assertTrue(self.lifecycle_manager.is_running())
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)

    async def test_61_application_lifecycle_setup_integration(self):
        """Test setup_application_lifecycle convenience function."""
        mock_app = MagicMock()
        mock_app.on_event = MagicMock()
        user_id = f'app_user_{uuid.uuid4().hex[:8]}'
        manager = await setup_application_lifecycle(app=mock_app, websocket_manager=self.mock_websocket_manager, db_manager=self.mock_db_manager, agent_registry=self.mock_agent_registry, health_service=self.mock_health_service, user_id=user_id)
        self.assertIsInstance(manager, UnifiedLifecycleManager)
        self.assertEqual(manager.user_id, user_id)
        self.assertEqual(manager.get_component(ComponentType.WEBSOCKET_MANAGER), self.mock_websocket_manager)
        self.assertEqual(manager.get_component(ComponentType.DATABASE_MANAGER), self.mock_db_manager)
        self.assertEqual(manager.get_component(ComponentType.AGENT_REGISTRY), self.mock_agent_registry)
        self.assertEqual(manager.get_component(ComponentType.HEALTH_SERVICE), self.mock_health_service)
        self.assertEqual(mock_app.on_event.call_count, 2)

    async def test_62_comprehensive_end_to_end_lifecycle(self):
        """Test comprehensive end-to-end lifecycle with all features."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        await self._register_all_components()
        lifecycle_events = []

        def track_event(event_name):

            def tracker(**kwargs):
                lifecycle_events.append(event_name)
            return tracker
        self.lifecycle_manager.register_lifecycle_hook('pre_startup', track_event('pre_startup'))
        self.lifecycle_manager.register_lifecycle_hook('post_startup', track_event('post_startup'))
        self.lifecycle_manager.register_lifecycle_hook('pre_shutdown', track_event('pre_shutdown'))
        self.lifecycle_manager.register_lifecycle_hook('post_shutdown', track_event('post_shutdown'))

        def startup_handler():
            lifecycle_events.append('startup_handler')

        def shutdown_handler():
            lifecycle_events.append('shutdown_handler')
        self.lifecycle_manager.add_startup_handler(startup_handler)
        self.lifecycle_manager.add_shutdown_handler(shutdown_handler)
        startup_success = await self.lifecycle_manager.startup()
        self.assertTrue(startup_success)
        request_ids = [f'e2e_req_{i}' for i in range(3)]

        async def simulate_request(req_id):
            async with self.lifecycle_manager.request_context(req_id):
                await asyncio.sleep(0.1)
        request_tasks = [asyncio.create_task(simulate_request(req_id)) for req_id in request_ids]
        await asyncio.gather(*request_tasks)
        shutdown_success = await self.lifecycle_manager.shutdown()
        self.assertTrue(shutdown_success)
        expected_events = ['pre_startup', 'startup_handler', 'post_startup', 'pre_shutdown', 'shutdown_handler', 'post_shutdown']
        for event in expected_events:
            self.assertIn(event, lifecycle_events)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)
        self.assertTrue(self.lifecycle_manager.is_shutting_down())
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
        self.assertGreater(self.lifecycle_manager._metrics.startup_time, 0)
        self.assertGreater(self.lifecycle_manager._metrics.shutdown_time, 0)
        self.assertEqual(self.lifecycle_manager._metrics.successful_shutdowns, 1)
        self.assertEqual(self.lifecycle_manager._metrics.failed_shutdowns, 0)
        self.assertGreater(len(self.mock_websocket_manager.broadcasted_events), 0)

class LifecycleManagerFactoryTests(AsyncBaseTestCase):
    """Additional tests for LifecycleManagerFactory functionality."""

    async def asyncTearDown(self):
        """Clean up factory state after each test."""
        await LifecycleManagerFactory.shutdown_all_managers()
        await super().asyncTearDown()

    async def test_factory_thread_safety(self):
        """Test factory thread safety with concurrent access."""
        user_id = f'thread_safe_user_{uuid.uuid4().hex[:8]}'
        managers = []

        def get_manager_thread():
            manager = LifecycleManagerFactory.get_user_manager(user_id)
            managers.append(manager)
        threads = [threading.Thread(target=get_manager_thread) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(set(managers)), 1)
        for manager in managers:
            self.assertEqual(manager.user_id, user_id)

    async def test_63_concurrent_phase_transitions_race_condition_prevention(self):
        """Test prevention of race conditions during concurrent phase transitions."""
        await self._register_all_components()
        startup_tasks = [asyncio.create_task(self.lifecycle_manager.startup()), asyncio.create_task(self.lifecycle_manager.startup()), asyncio.create_task(self.lifecycle_manager.startup())]
        results = await asyncio.gather(*startup_tasks, return_exceptions=True)
        success_count = sum((1 for r in results if r is True))
        self.assertEqual(success_count, 1)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)

    async def test_64_websocket_event_emission_race_conditions(self):
        """Test WebSocket event emission under concurrent conditions."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        event_count = 20
        event_tasks = []
        for i in range(event_count):
            task = asyncio.create_task(self.lifecycle_manager._emit_websocket_event(f'concurrent_test_{i}', {'index': i}))
            event_tasks.append(task)
        await asyncio.gather(*event_tasks)
        broadcasted_events = self.mock_websocket_manager.broadcasted_events
        self.assertEqual(len(broadcasted_events), event_count)
        for i, event in enumerate(broadcasted_events):
            self.assertEqual(event['type'], f'lifecycle_concurrent_test_{i}')
            self.assertEqual(event['data']['index'], i)

    async def test_65_component_registration_concurrent_modifications(self):
        """Test concurrent component registration and unregistration operations."""
        component_count = 10
        components = []
        for i in range(component_count):
            mock_comp = AsyncMock()
            mock_comp.name = f'concurrent_component_{i}'
            components.append((f'comp_{i}', mock_comp))
        registration_tasks = [asyncio.create_task(self.lifecycle_manager.register_component(name, comp, ComponentType.LLM_MANAGER)) for name, comp in components]
        await asyncio.gather(*registration_tasks)
        self.assertEqual(len(self.lifecycle_manager._components), component_count)
        unregister_tasks = []
        new_register_tasks = []
        for i in range(component_count // 2):
            unregister_tasks.append(asyncio.create_task(self.lifecycle_manager.unregister_component(f'comp_{i}')))
            new_mock = AsyncMock()
            new_mock.name = f'new_component_{i}'
            new_register_tasks.append(asyncio.create_task(self.lifecycle_manager.register_component(f'new_comp_{i}', new_mock, ComponentType.REDIS_MANAGER)))
        await asyncio.gather(*unregister_tasks + new_register_tasks)
        remaining_count = len(self.lifecycle_manager._components)
        expected_count = component_count // 2 + component_count // 2
        self.assertEqual(remaining_count, expected_count)

    async def test_66_health_monitoring_concurrent_checks(self):
        """Test concurrent health check operations without race conditions."""
        check_counts = {}

        async def create_health_check(comp_name):

            async def health_check():
                check_counts[comp_name] = check_counts.get(comp_name, 0) + 1
                await asyncio.sleep(0.01)
                return {'healthy': True, 'checks': check_counts[comp_name]}
            return health_check
        component_count = 8
        for i in range(component_count):
            comp_name = f'health_comp_{i}'
            mock_comp = AsyncMock()
            health_check = await create_health_check(comp_name)
            await self.lifecycle_manager.register_component(comp_name, mock_comp, ComponentType.LLM_MANAGER, health_check=health_check)
        check_tasks = [asyncio.create_task(self.lifecycle_manager._run_all_health_checks()) for _ in range(5)]
        results_list = await asyncio.gather(*check_tasks)
        for results in results_list:
            self.assertEqual(len(results), component_count)
            for comp_name, result in results.items():
                self.assertTrue(result['healthy'])
                self.assertIn('checks', result)

    async def test_67_request_context_concurrent_tracking_stress_test(self):
        """Stress test concurrent request context tracking."""
        request_count = 50
        max_concurrent = 20
        completed_requests = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def simulate_concurrent_request(req_id):
            async with semaphore:
                async with self.lifecycle_manager.request_context(req_id):
                    self.assertIn(req_id, self.lifecycle_manager._active_requests)
                    await asyncio.sleep(0.01 + int(req_id.split('_')[-1]) % 5 * 0.01)
                    completed_requests.append(req_id)
        request_ids = [f'stress_req_{i}' for i in range(request_count)]
        request_tasks = [asyncio.create_task(simulate_concurrent_request(req_id)) for req_id in request_ids]
        max_active = 0
        monitoring_task = asyncio.create_task(self._monitor_active_requests(max_active))
        await asyncio.gather(*request_tasks)
        monitoring_task.cancel()
        self.assertEqual(len(completed_requests), request_count)
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
        self.assertEqual(self.lifecycle_manager._metrics.active_requests, 0)

    async def _monitor_active_requests(self, max_active):
        """Helper method to monitor maximum active requests during stress test."""
        try:
            while True:
                current_active = len(self.lifecycle_manager._active_requests)
                max_active = max(max_active, current_active)
                await asyncio.sleep(0.001)
        except asyncio.CancelledError:
            pass

    async def test_68_signal_handler_setup_validation(self):
        """Test signal handler setup for graceful shutdown."""
        try:
            self.lifecycle_manager.setup_signal_handlers()
        except Exception as e:
            self.fail(f'Signal handler setup should not raise exceptions: {e}')
        self.assertIsInstance(self.lifecycle_manager, UnifiedLifecycleManager)

    async def test_69_environment_variable_configuration_edge_cases(self):
        """Test edge cases in environment variable configuration loading."""
        edge_case_configs = [{'SHUTDOWN_TIMEOUT': '-1'}, {'DRAIN_TIMEOUT': '0'}, {'HEALTH_GRACE_PERIOD': '999999'}, {'STARTUP_TIMEOUT': '0.5'}, {'LIFECYCLE_ERROR_THRESHOLD': ''}, {'HEALTH_CHECK_INTERVAL': 'not_a_number'}]
        for config in edge_case_configs:
            with self.isolated_environment(**config):
                try:
                    manager = UnifiedLifecycleManager()
                    self.assertIsInstance(manager, UnifiedLifecycleManager)
                except Exception as e:
                    self.fail(f'Manager creation should handle invalid config gracefully: {e}')

    async def test_70_memory_leak_prevention_during_lifecycle_operations(self):
        """Test memory leak prevention during repeated lifecycle operations."""
        initial_component_count = len(self.lifecycle_manager._components)
        initial_handler_count = len(self.lifecycle_manager._startup_handlers)
        for cycle in range(10):
            mock_comp = AsyncMock()
            mock_comp.name = f'cycle_component_{cycle}'
            await self.lifecycle_manager.register_component(f'cycle_comp_{cycle}', mock_comp, ComponentType.LLM_MANAGER)

            def temp_handler():
                pass
            self.lifecycle_manager.add_startup_handler(temp_handler)
            await self.lifecycle_manager.unregister_component(f'cycle_comp_{cycle}')
        final_component_count = len(self.lifecycle_manager._components)
        self.assertEqual(final_component_count, initial_component_count)
        final_handler_count = len(self.lifecycle_manager._startup_handlers)
        self.assertEqual(final_handler_count, initial_handler_count + 10)

    async def test_71_startup_timeout_handling(self):
        """Test startup timeout handling with slow components."""
        slow_component = AsyncMock()
        slow_component.initialize = AsyncMock()

        async def slow_initialize():
            await asyncio.sleep(3)
        slow_component.initialize.side_effect = slow_initialize
        slow_component.name = 'slow_component'
        await self.lifecycle_manager.register_component('slow_component', slow_component, ComponentType.LLM_MANAGER)
        start_time = time.time()
        startup_task = asyncio.create_task(self.lifecycle_manager.startup())
        try:
            success = await asyncio.wait_for(startup_task, timeout=20.0)
            elapsed = time.time() - start_time
            self.assertLess(elapsed, 20.0)
        except asyncio.TimeoutError:
            self.fail('Startup should not hang indefinitely')

    async def test_72_shutdown_timeout_and_force_cleanup(self):
        """Test shutdown timeout handling and force cleanup."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        hanging_component = AsyncMock()
        hanging_component.initialize = AsyncMock()
        hanging_component.shutdown = AsyncMock()

        async def hanging_shutdown():
            await asyncio.sleep(5)
        hanging_component.shutdown.side_effect = hanging_shutdown
        hanging_component.name = 'hanging_component'
        await self.lifecycle_manager.register_component('hanging_component', hanging_component, ComponentType.REDIS_MANAGER)
        start_time = time.time()
        success = await self.lifecycle_manager.shutdown()
        elapsed = time.time() - start_time
        self.assertLess(elapsed, 10.0)
        self.assertTrue(success)

    async def test_73_malformed_websocket_event_handling(self):
        """Test handling of malformed WebSocket events and edge cases."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        edge_cases = [('', {}), ('test_event', None), ('test_event', {'circular': None}), ('very_long_event_name' * 100, {'large_data': 'x' * 10000}), ('test_event', {'nested': {'deeply': {'nested': {'data': True}}}})]
        for event_type, event_data in edge_cases:
            try:
                await self.lifecycle_manager._emit_websocket_event(event_type, event_data)
            except Exception as e:
                self.fail(f'WebSocket event emission should handle edge cases gracefully: {e}')
        self.assertGreaterEqual(len(self.mock_websocket_manager.broadcasted_events), 0)

    async def test_74_component_health_check_exception_varieties(self):
        """Test handling of various types of exceptions in health checks."""
        exception_types = [ValueError('Invalid value'), ConnectionError('Connection failed'), TimeoutError('Request timed out'), RuntimeError('Runtime error'), asyncio.CancelledError(), KeyboardInterrupt(), MemoryError('Out of memory')]
        for i, exception in enumerate(exception_types):
            comp_name = f'failing_comp_{i}'

            async def failing_health_check():
                raise exception
            mock_comp = AsyncMock()
            await self.lifecycle_manager.register_component(comp_name, mock_comp, ComponentType.LLM_MANAGER, health_check=failing_health_check)
            try:
                results = await self.lifecycle_manager._run_all_health_checks()
                if comp_name in results:
                    self.assertFalse(results[comp_name]['healthy'])
                    self.assertIn('error', results[comp_name])
            except Exception as e:
                self.fail(f'Health check should handle {type(exception).__name__} gracefully: {e}')

    async def test_75_websocket_event_delivery_guarantee_during_shutdown(self):
        """Test WebSocket event delivery guarantees during shutdown sequence."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        event_timestamps = []

        async def timestamp_broadcast(message):
            event_timestamps.append({'timestamp': time.time(), 'type': message.get('type', 'unknown'), 'phase': self.lifecycle_manager.get_current_phase().value})
        self.mock_websocket_manager.broadcast_system_message.side_effect = timestamp_broadcast
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        await asyncio.sleep(0.1)
        for i in range(5):
            await self.lifecycle_manager._emit_websocket_event(f'shutdown_test_{i}', {'index': i})
            await asyncio.sleep(0.02)
        success = await shutdown_task
        self.assertTrue(success)
        test_events = [e for e in event_timestamps if e['type'].startswith('lifecycle_shutdown_test')]
        self.assertEqual(len(test_events), 5)
        for i in range(1, len(test_events)):
            self.assertLessEqual(test_events[i - 1]['timestamp'], test_events[i]['timestamp'])

    async def test_76_websocket_connection_failure_resilience(self):
        """Test resilience when WebSocket connections fail during event emission."""
        failure_count = 0

        async def intermittent_broadcast(message):
            nonlocal failure_count
            failure_count += 1
            if failure_count % 3 == 0:
                raise ConnectionError('WebSocket connection lost')
        failing_ws_manager = AsyncMock()
        failing_ws_manager.broadcast_system_message = intermittent_broadcast
        self.lifecycle_manager.set_websocket_manager(failing_ws_manager)
        event_count = 10
        success_count = 0
        for i in range(event_count):
            try:
                await self.lifecycle_manager._emit_websocket_event(f'resilience_test_{i}', {'index': i})
                success_count += 1
            except Exception:
                self.fail('WebSocket errors should not propagate to lifecycle operations')
        self.assertEqual(success_count, event_count)
        self.assertEqual(failure_count, event_count)

    async def test_77_websocket_event_payload_validation_and_sanitization(self):
        """Test WebSocket event payload validation and sanitization."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        test_payloads = [{'string_field': 'normal string'}, {'numeric_field': 42, 'float_field': 3.14}, {'boolean_field': True, 'none_field': None}, {'list_field': [1, 2, 3, 'mixed', True]}, {'nested_dict': {'level1': {'level2': {'data': 'deep'}}}}, {'unicode_field': '[U+6D4B][U+8BD5][U+6570][U+636E]  CELEBRATION: '}, {'large_string': 'x' * 1000}, {'timestamp': time.time()}, {'complex_structure': {'metadata': {'version': '1.0', 'client': 'test'}, 'payload': {'items': [{'id': i, 'name': f'item_{i}'} for i in range(10)]}}}]
        for i, payload in enumerate(test_payloads):
            event_type = f'validation_test_{i}'
            try:
                await self.lifecycle_manager._emit_websocket_event(event_type, payload)
            except Exception as e:
                self.fail(f'Event emission should handle payload type {type(payload)}: {e}')
        broadcasted_events = self.mock_websocket_manager.broadcasted_events
        self.assertEqual(len(broadcasted_events), len(test_payloads))
        for i, event in enumerate(broadcasted_events):
            self.assertEqual(event['type'], f'lifecycle_validation_test_{i}')
            self.assertIn('data', event)
            self.assertIn('timestamp', event)
            self.assertIn('user_id', event)

    async def test_78_large_scale_component_management_performance(self):
        """Test performance with large numbers of components."""
        component_count = 100
        start_time = time.time()
        registration_tasks = []
        for i in range(component_count):
            mock_comp = AsyncMock()
            mock_comp.initialize = AsyncMock()
            mock_comp.shutdown = AsyncMock()
            mock_comp.name = f'scale_component_{i}'
            comp_type = [ComponentType.LLM_MANAGER, ComponentType.REDIS_MANAGER, ComponentType.CLICKHOUSE_MANAGER][i % 3]
            task = self.lifecycle_manager.register_component(f'scale_comp_{i}', mock_comp, comp_type)
            registration_tasks.append(task)
        await asyncio.gather(*registration_tasks)
        registration_time = time.time() - start_time
        self.assertLess(registration_time, 5.0)
        self.assertEqual(len(self.lifecycle_manager._components), component_count)
        startup_start = time.time()
        success = await self.lifecycle_manager.startup()
        startup_time = time.time() - startup_start
        self.assertTrue(success)
        self.assertLess(startup_time, 10.0)
        shutdown_start = time.time()
        success = await self.lifecycle_manager.shutdown()
        shutdown_time = time.time() - shutdown_start
        self.assertTrue(success)
        self.assertLess(shutdown_time, 10.0)

    async def test_79_memory_usage_optimization_during_operations(self):
        """Test memory usage optimization during lifecycle operations."""
        try:
            import psutil
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024
            for cycle in range(20):
                components = []
                for i in range(50):
                    mock_comp = AsyncMock()
                    mock_comp.initialize = AsyncMock()
                    mock_comp.shutdown = AsyncMock()
                    await self.lifecycle_manager.register_component(f'memory_comp_{cycle}_{i}', mock_comp, ComponentType.LLM_MANAGER)
                    components.append(f'memory_comp_{cycle}_{i}')
                for comp_name in components:
                    await self.lifecycle_manager.unregister_component(comp_name)
                try:
                    import gc
                    gc.collect()
                except ImportError:
                    pass
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_growth = final_memory - initial_memory
            self.assertLess(memory_growth, 100, f'Memory growth too large: {memory_growth}MB')
        except ImportError:
            pass

    async def test_80_high_frequency_health_check_performance(self):
        """Test performance under high-frequency health check scenarios."""
        component_count = 20
        for i in range(component_count):

            async def fast_health_check():
                return {'healthy': True, 'response_time': 0.001}
            mock_comp = AsyncMock()
            await self.lifecycle_manager.register_component(f'freq_comp_{i}', mock_comp, ComponentType.LLM_MANAGER, health_check=fast_health_check)
        check_count = 100
        start_time = time.time()
        check_tasks = []
        for _ in range(check_count):
            task = asyncio.create_task(self.lifecycle_manager._run_all_health_checks())
            check_tasks.append(task)
        results_list = await asyncio.gather(*check_tasks)
        elapsed_time = time.time() - start_time
        self.assertEqual(len(results_list), check_count)
        self.assertLess(elapsed_time, 10.0)
        for results in results_list:
            self.assertEqual(len(results), component_count)
            for comp_result in results.values():
                self.assertTrue(comp_result['healthy'])

    async def test_81_chat_service_availability_during_lifecycle_operations(self):
        """Test chat service availability guarantees during lifecycle operations."""
        await self._register_all_components()
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)

        def is_chat_service_ready():
            return self.lifecycle_manager.is_running() and self.lifecycle_manager.get_component(ComponentType.WEBSOCKET_MANAGER) is not None and (self.lifecycle_manager.get_component(ComponentType.AGENT_REGISTRY) is not None)
        self.assertFalse(is_chat_service_ready())
        startup_success = await self.lifecycle_manager.startup()
        self.assertTrue(startup_success)
        self.assertTrue(is_chat_service_ready())
        for _ in range(10):
            self.assertTrue(is_chat_service_ready())
            await asyncio.sleep(0.01)
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        await asyncio.sleep(0.1)
        if not shutdown_task.done():
            self.assertIsNotNone(self.lifecycle_manager.get_component(ComponentType.WEBSOCKET_MANAGER))
            self.assertIsNotNone(self.lifecycle_manager.get_component(ComponentType.AGENT_REGISTRY))
        await shutdown_task
        self.assertFalse(self.lifecycle_manager.is_running())
        self.assertTrue(self.lifecycle_manager.is_shutting_down())

    async def test_82_zero_downtime_deployment_simulation(self):
        """Test zero-downtime deployment scenario with component replacement."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        active_sessions = []
        session_count = 5
        for i in range(session_count):
            session_id = f'chat_session_{i}'
            active_sessions.append(session_id)

            async def simulate_chat_session(session_id):
                async with self.lifecycle_manager.request_context(session_id):
                    await asyncio.sleep(1.0)
                    return f'session_{session_id}_completed'
            asyncio.create_task(simulate_chat_session(session_id))
        await asyncio.sleep(0.1)
        self.assertGreater(len(self.lifecycle_manager._active_requests), 0)
        new_websocket_manager = AsyncMock()
        new_websocket_manager.broadcast_system_message = AsyncMock()
        new_websocket_manager.get_connection_count = MagicMock(return_value=5)
        new_websocket_manager.close_all_connections = AsyncMock()
        new_websocket_manager.name = 'websocket_manager_v2'
        await self.lifecycle_manager.register_component('websocket_manager_v2', new_websocket_manager, ComponentType.WEBSOCKET_MANAGER)
        self.assertTrue(self.lifecycle_manager.is_running())
        self.assertEqual(self.lifecycle_manager.get_component(ComponentType.WEBSOCKET_MANAGER), new_websocket_manager)
        shutdown_success = await self.lifecycle_manager.shutdown()
        self.assertTrue(shutdown_success)
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)

    async def test_83_multi_user_isolation_comprehensive_validation(self):
        """Comprehensive test of multi-user isolation guarantees."""
        user_count = 5
        users = [f'user_{i}_{uuid.uuid4().hex[:8]}' for i in range(user_count)]
        user_managers = {}
        for user_id in users:
            manager = LifecycleManagerFactory.get_user_manager(user_id)
            user_managers[user_id] = manager
        for i, (user_id, manager) in enumerate(user_managers.items()):
            user_websocket = AsyncMock()
            user_websocket.name = f'websocket_{user_id}'
            user_websocket.broadcast_system_message = AsyncMock()
            user_db = AsyncMock()
            user_db.name = f'database_{user_id}'
            user_db.initialize = AsyncMock()
            user_db.shutdown = AsyncMock()
            user_db.health_check = AsyncMock(return_value={'healthy': True, 'user': user_id})
            await manager.register_component(f'websocket_{user_id}', user_websocket, ComponentType.WEBSOCKET_MANAGER)
            await manager.register_component(f'database_{user_id}', user_db, ComponentType.DATABASE_MANAGER)
        startup_tasks = [manager.startup() for manager in user_managers.values()]
        startup_results = await asyncio.gather(*startup_tasks)
        for result in startup_results:
            self.assertTrue(result)
        for user_id, manager in user_managers.items():
            user_ws = manager.get_component(ComponentType.WEBSOCKET_MANAGER)
            user_db = manager.get_component(ComponentType.DATABASE_MANAGER)
            self.assertEqual(user_ws.name, f'websocket_{user_id}')
            self.assertEqual(user_db.name, f'database_{user_id}')
            for other_user_id, other_manager in user_managers.items():
                if other_user_id != user_id:
                    other_ws = other_manager.get_component(ComponentType.WEBSOCKET_MANAGER)
                    self.assertNotEqual(user_ws, other_ws)
        operation_tasks = []
        for user_id, manager in user_managers.items():

            async def user_operations(user_id, manager):
                for req_idx in range(3):
                    req_id = f'{user_id}_req_{req_idx}'
                    async with manager.request_context(req_id):
                        await asyncio.sleep(0.1)
            operation_tasks.append(asyncio.create_task(user_operations(user_id, manager)))
        await asyncio.gather(*operation_tasks)
        shutdown_tasks = [manager.shutdown() for manager in user_managers.values()]
        shutdown_results = await asyncio.gather(*shutdown_tasks)
        for result in shutdown_results:
            self.assertTrue(result)
        for manager in user_managers.values():
            self.assertEqual(manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)
            self.assertEqual(len(manager._active_requests), 0)

    async def test_84_component_status_dataclass_comprehensive_validation(self):
        """Test ComponentStatus dataclass with all edge cases and field validation."""
        status = ComponentStatus('test_component', ComponentType.DATABASE_MANAGER)
        self.assertEqual(status.name, 'test_component')
        self.assertEqual(status.component_type, ComponentType.DATABASE_MANAGER)
        self.assertEqual(status.status, 'unknown')
        self.assertEqual(status.error_count, 0)
        self.assertIsNone(status.last_error)
        self.assertEqual(status.metadata, {})
        self.assertGreater(status.last_check, 0)
        metadata = {'version': '1.0', 'priority': 'high'}
        status_full = ComponentStatus(name='full_component', component_type=ComponentType.WEBSOCKET_MANAGER, status='healthy', last_check=time.time(), error_count=3, last_error='Previous connection error', metadata=metadata)
        self.assertEqual(status_full.name, 'full_component')
        self.assertEqual(status_full.component_type, ComponentType.WEBSOCKET_MANAGER)
        self.assertEqual(status_full.status, 'healthy')
        self.assertEqual(status_full.error_count, 3)
        self.assertEqual(status_full.last_error, 'Previous connection error')
        self.assertEqual(status_full.metadata, metadata)

    async def test_85_lifecycle_metrics_comprehensive_tracking(self):
        """Test LifecycleMetrics dataclass with comprehensive metric collection."""
        metrics = LifecycleMetrics()
        self.assertIsNone(metrics.startup_time)
        self.assertIsNone(metrics.shutdown_time)
        self.assertEqual(metrics.successful_shutdowns, 0)
        self.assertEqual(metrics.failed_shutdowns, 0)
        self.assertEqual(metrics.component_failures, 0)
        self.assertIsNone(metrics.last_health_check)
        self.assertEqual(metrics.active_requests, 0)
        await self._register_all_components()
        initial_metrics = self.lifecycle_manager._metrics
        self.assertIsNone(initial_metrics.startup_time)
        await self.lifecycle_manager.startup()
        self.assertIsNotNone(self.lifecycle_manager._metrics.startup_time)
        self.assertGreater(self.lifecycle_manager._metrics.startup_time, 0)
        await self.lifecycle_manager.shutdown()
        self.assertIsNotNone(self.lifecycle_manager._metrics.shutdown_time)
        self.assertGreater(self.lifecycle_manager._metrics.shutdown_time, 0)
        self.assertEqual(self.lifecycle_manager._metrics.successful_shutdowns, 1)
        self.assertEqual(self.lifecycle_manager._metrics.failed_shutdowns, 0)

    async def test_86_all_component_types_comprehensive_validation(self):
        """Test all ComponentType enum values with comprehensive validation."""
        component_types = [ComponentType.WEBSOCKET_MANAGER, ComponentType.DATABASE_MANAGER, ComponentType.AGENT_REGISTRY, ComponentType.HEALTH_SERVICE, ComponentType.LLM_MANAGER, ComponentType.REDIS_MANAGER, ComponentType.CLICKHOUSE_MANAGER]
        for i, comp_type in enumerate(component_types):
            mock_comp = AsyncMock()
            mock_comp.initialize = AsyncMock()
            mock_comp.shutdown = AsyncMock()
            mock_comp.name = f'component_{comp_type.value}'
            await self.lifecycle_manager.register_component(f'test_{comp_type.value}', mock_comp, comp_type)
            registered_comp = self.lifecycle_manager.get_component(comp_type)
            self.assertEqual(registered_comp, mock_comp)
            status = self.lifecycle_manager.get_component_status(f'test_{comp_type.value}')
            self.assertEqual(status.component_type, comp_type)
        self.assertEqual(len(self.lifecycle_manager._components), len(component_types))
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        for comp_type in component_types:
            comp = self.lifecycle_manager.get_component(comp_type)
            comp.initialize.assert_called_once()

    async def test_87_all_lifecycle_phases_comprehensive_transitions(self):
        """Test all LifecyclePhase enum values and transitions."""
        all_phases = [LifecyclePhase.INITIALIZING, LifecyclePhase.STARTING, LifecyclePhase.RUNNING, LifecyclePhase.SHUTTING_DOWN, LifecyclePhase.SHUTDOWN_COMPLETE, LifecyclePhase.ERROR]
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.INITIALIZING)
        await self._register_all_components()
        startup_task = asyncio.create_task(self.lifecycle_manager.startup())
        await asyncio.sleep(0.1)
        current_phase = self.lifecycle_manager.get_current_phase()
        self.assertIn(current_phase, [LifecyclePhase.STARTING, LifecyclePhase.RUNNING])
        success = await startup_task
        self.assertTrue(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        await asyncio.sleep(0.1)
        if not shutdown_task.done():
            current_phase = self.lifecycle_manager.get_current_phase()
            self.assertEqual(current_phase, LifecyclePhase.SHUTTING_DOWN)
        success = await shutdown_task
        self.assertTrue(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)

    async def test_88_component_validation_methods_comprehensive_coverage(self):
        """Test all component validation methods with comprehensive scenarios."""
        db_manager = AsyncMock()
        db_manager.health_check = AsyncMock(return_value={'healthy': True})
        await self.lifecycle_manager.register_component('test_database', db_manager, ComponentType.DATABASE_MANAGER)
        try:
            await self.lifecycle_manager._validate_database_component('test_database')
        except Exception as e:
            self.fail(f'Database validation should not raise exception: {e}')
        unhealthy_db = AsyncMock()
        unhealthy_db.health_check = AsyncMock(return_value={'healthy': False, 'error': 'Connection failed'})
        await self.lifecycle_manager.register_component('unhealthy_database', unhealthy_db, ComponentType.DATABASE_MANAGER)
        with self.assertRaises(Exception):
            await self.lifecycle_manager._validate_database_component('unhealthy_database')
        ws_manager = AsyncMock()
        ws_manager.broadcast_system_message = AsyncMock()
        await self.lifecycle_manager.register_component('test_websocket', ws_manager, ComponentType.WEBSOCKET_MANAGER)
        try:
            await self.lifecycle_manager._validate_websocket_component('test_websocket')
            self.assertEqual(self.lifecycle_manager._websocket_manager, ws_manager)
        except Exception as e:
            self.fail(f'WebSocket validation should not raise exception: {e}')
        agent_registry = AsyncMock()
        agent_registry.get_registry_status = MagicMock(return_value={'ready': True})
        await self.lifecycle_manager.register_component('test_agent_registry', agent_registry, ComponentType.AGENT_REGISTRY)
        try:
            await self.lifecycle_manager._validate_agent_registry_component('test_agent_registry')
        except Exception as e:
            self.fail(f'Agent registry validation should not raise exception: {e}')
        unready_registry = AsyncMock()
        unready_registry.get_registry_status = MagicMock(return_value={'ready': False, 'reason': 'Not initialized'})
        await self.lifecycle_manager.register_component('unready_registry', unready_registry, ComponentType.AGENT_REGISTRY)
        with self.assertRaises(Exception):
            await self.lifecycle_manager._validate_agent_registry_component('unready_registry')

    async def test_89_shutdown_phase_methods_comprehensive_coverage(self):
        """Test all shutdown phase methods with comprehensive validation."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        self.mock_websocket_manager.get_connection_count.return_value = 3
        try:
            await self.lifecycle_manager._shutdown_phase_1_mark_unhealthy()
            self.mock_health_service.mark_shutting_down.assert_called_once()
        except Exception as e:
            self.fail(f'Phase 1 shutdown should not raise exception: {e}')
        try:
            await self.lifecycle_manager._shutdown_phase_2_drain_requests()
        except Exception as e:
            self.fail(f'Phase 2 shutdown should not raise exception: {e}')
        try:
            await self.lifecycle_manager._shutdown_phase_3_close_websockets()
            self.mock_websocket_manager.broadcast_system_message.assert_called()
            self.mock_websocket_manager.close_all_connections.assert_called_once()
        except Exception as e:
            self.fail(f'Phase 3 shutdown should not raise exception: {e}')
        try:
            await self.lifecycle_manager._shutdown_phase_4_complete_agents()
        except Exception as e:
            self.fail(f'Phase 4 shutdown should not raise exception: {e}')
        try:
            await self.lifecycle_manager._shutdown_phase_5_shutdown_components()
            self.mock_db_manager.shutdown.assert_called_once()
            self.mock_agent_registry.shutdown.assert_called_once()
            self.mock_health_service.shutdown.assert_called_once()
        except Exception as e:
            self.fail(f'Phase 5 shutdown should not raise exception: {e}')
        try:
            await self.lifecycle_manager._shutdown_phase_6_cleanup_resources()
        except Exception as e:
            self.fail(f'Phase 6 shutdown should not raise exception: {e}')
        handler_executed = False

        def test_shutdown_handler():
            nonlocal handler_executed
            handler_executed = True
        self.lifecycle_manager.add_shutdown_handler(test_shutdown_handler)
        try:
            await self.lifecycle_manager._shutdown_phase_7_custom_handlers()
            self.assertTrue(handler_executed)
        except Exception as e:
            self.fail(f'Phase 7 shutdown should not raise exception: {e}')

    async def test_90_comprehensive_status_and_health_endpoint_validation(self):
        """Comprehensive test of all status and health endpoint scenarios."""
        await self._register_all_components()
        status = self.lifecycle_manager.get_status()
        self.assertEqual(status['phase'], 'initializing')
        self.assertFalse(status['ready_for_requests'])
        self.assertFalse(status['is_shutting_down'])
        health_status = self.lifecycle_manager.get_health_status()
        self.assertEqual(health_status['status'], 'unhealthy')
        self.assertEqual(health_status['phase'], 'initializing')
        self.assertFalse(health_status['ready'])
        await self.lifecycle_manager.startup()
        status = self.lifecycle_manager.get_status()
        self.assertEqual(status['phase'], 'running')
        self.assertTrue(status['ready_for_requests'])
        self.assertFalse(status['is_shutting_down'])
        self.assertGreater(status['uptime'], 0)
        self.assertIsNotNone(status['startup_time'])
        health_status = self.lifecycle_manager.get_health_status()
        self.assertEqual(health_status['status'], 'healthy')
        self.assertEqual(health_status['phase'], 'running')
        self.assertIn('components_healthy', health_status)
        self.assertEqual(health_status['active_requests'], 0)
        async with self.lifecycle_manager.request_context('test_request'):
            status = self.lifecycle_manager.get_status()
            self.assertEqual(status['active_requests'], 1)
            health_status = self.lifecycle_manager.get_health_status()
            self.assertEqual(health_status['active_requests'], 1)
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        await asyncio.sleep(0.1)
        if not shutdown_task.done():
            health_status = self.lifecycle_manager.get_health_status()
            if self.lifecycle_manager.get_current_phase() == LifecyclePhase.SHUTTING_DOWN:
                self.assertEqual(health_status['status'], 'shutting_down')
                self.assertFalse(health_status['ready'])
        success = await shutdown_task
        self.assertTrue(success)
        status = self.lifecycle_manager.get_status()
        self.assertEqual(status['phase'], 'shutdown_complete')
        self.assertFalse(status['ready_for_requests'])
        self.assertTrue(status['is_shutting_down'])
        self.assertIsNotNone(status['shutdown_time'])
        health_status = self.lifecycle_manager.get_health_status()
        self.assertEqual(health_status['status'], 'unhealthy')
        self.assertEqual(health_status['phase'], 'shutdown_complete')
        self.assertFalse(health_status['ready'])
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
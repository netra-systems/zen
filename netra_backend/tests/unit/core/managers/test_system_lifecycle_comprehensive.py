"""
SystemLifecycle SSOT Unit Tests - Comprehensive Test Suite

This module tests the 1,251-line SystemLifecycle SSOT module that ensures zero-downtime 
deployments and service reliability protecting $500K+ ARR.

Business Value Protection:
- Zero-downtime deployments preventing revenue loss during updates
- Graceful shutdown preventing chat session interruption (90% of platform value)
- Health monitoring preventing undetected service failures
- Component coordination preventing cascade failures
- Multi-user isolation protecting enterprise customers ($15K+ MRR each)

Test Strategy:
- Unit tests with mocked dependencies for lifecycle phase logic
- Tests designed to legitimately fail to validate business logic
- Comprehensive coverage of all lifecycle phases and error scenarios
- Performance validation for startup/shutdown timing requirements
- Thread safety validation for concurrent user operations

CRITICAL: These tests protect the core infrastructure that enables reliable 
chat functionality - the primary source of business value.
"""
import asyncio
import pytest
import time
import uuid
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.managers.unified_lifecycle_manager import SystemLifecycle, SystemLifecycleFactory, LifecyclePhase, ComponentType, ComponentStatus, LifecycleMetrics, get_lifecycle_manager, setup_application_lifecycle

class TestSystemLifecyclePhaseTransitions(SSotAsyncTestCase):
    """
    Test lifecycle phase management and transitions.
    
    Business Value: Ensures proper phase transitions prevent service disruptions
    that could interrupt chat sessions (90% of platform value).
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.lifecycle = SystemLifecycle(user_id='test_user', shutdown_timeout=10, drain_timeout=5, health_check_grace_period=2, startup_timeout=15)

    async def test_initial_phase_is_initializing(self):
        """Test that new lifecycle manager starts in INITIALIZING phase."""
        assert self.lifecycle.get_current_phase() == LifecyclePhase.INITIALIZING
        assert not self.lifecycle.is_running()
        assert not self.lifecycle.is_shutting_down()
        status = self.lifecycle.get_health_status()
        assert status['status'] == 'unhealthy'
        assert not status['ready']

    async def test_startup_phase_transitions_success(self):
        """Test successful startup phase transitions."""
        mock_db = AsyncMock()
        mock_db.health_check = AsyncMock(return_value={'healthy': True})
        mock_db.initialize = AsyncMock()
        await self.lifecycle.register_component('test_db', mock_db, ComponentType.DATABASE_MANAGER)
        success = await self.lifecycle.startup()
        assert success
        assert self.lifecycle.get_current_phase() == LifecyclePhase.RUNNING
        assert self.lifecycle.is_running()
        assert not self.lifecycle.is_shutting_down()
        status = self.lifecycle.get_health_status()
        assert status['status'] == 'healthy'
        assert status['ready']
        metrics = self.lifecycle.get_status()
        assert metrics['startup_time'] > 0
        assert metrics['ready_for_requests']

    async def test_startup_failure_sets_error_phase(self):
        """Test that startup failures properly set ERROR phase."""
        mock_db = AsyncMock()
        mock_db.health_check = AsyncMock(return_value={'healthy': False, 'error': 'Connection failed'})
        await self.lifecycle.register_component('failing_db', mock_db, ComponentType.DATABASE_MANAGER)
        success = await self.lifecycle.startup()
        assert not success
        assert self.lifecycle.get_current_phase() == LifecyclePhase.ERROR
        status = self.lifecycle.get_health_status()
        assert status['status'] == 'unhealthy'
        assert not status['ready']

    async def test_shutdown_phase_transitions_success(self):
        """Test successful shutdown phase transitions."""
        await self.lifecycle._set_phase(LifecyclePhase.RUNNING)
        mock_health_service = AsyncMock()
        mock_health_service.mark_shutting_down = AsyncMock()
        await self.lifecycle.register_component('health_service', mock_health_service, ComponentType.HEALTH_SERVICE)
        success = await self.lifecycle.shutdown()
        assert success
        assert self.lifecycle.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE
        assert self.lifecycle.is_shutting_down()
        mock_health_service.mark_shutting_down.assert_called_once()
        metrics = self.lifecycle.get_status()
        assert metrics['shutdown_time'] > 0

    async def test_duplicate_shutdown_requests_handled_gracefully(self):
        """Test that duplicate shutdown requests don't cause issues."""
        await self.lifecycle._set_phase(LifecyclePhase.RUNNING)
        shutdown_task1 = asyncio.create_task(self.lifecycle.shutdown())
        await asyncio.sleep(0.01)
        shutdown_task2 = asyncio.create_task(self.lifecycle.shutdown())
        result1 = await shutdown_task1
        result2 = await shutdown_task2
        assert result1
        assert result2
        assert self.lifecycle.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE

    async def test_startup_from_invalid_phase_fails(self):
        """Test that startup from non-INITIALIZING phase fails properly."""
        await self.lifecycle._set_phase(LifecyclePhase.RUNNING)
        success = await self.lifecycle.startup()
        assert not success
        assert self.lifecycle.get_current_phase() == LifecyclePhase.RUNNING

    async def test_phase_transition_websocket_events(self):
        """Test that phase transitions emit proper WebSocket events."""
        mock_websocket_manager = AsyncMock()
        mock_websocket_manager.broadcast_system_message = AsyncMock()
        self.lifecycle.set_websocket_manager(mock_websocket_manager)
        await self.lifecycle._set_phase(LifecyclePhase.STARTING)
        mock_websocket_manager.broadcast_system_message.assert_called()
        call_args = mock_websocket_manager.broadcast_system_message.call_args[0][0]
        assert call_args['type'] == 'lifecycle_phase_changed'
        assert call_args['data']['new_phase'] == 'starting'
        assert call_args['data']['old_phase'] == 'initializing'

class TestSystemLifecycleComponentManagement(SSotAsyncTestCase):
    """
    Test component registration and management.
    
    Business Value: Ensures proper component coordination prevents cascade 
    failures that could bring down the entire platform.
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.lifecycle = SystemLifecycle(user_id='test_user')

    async def test_component_registration_success(self):
        """Test successful component registration."""
        mock_component = AsyncMock()
        mock_health_check = AsyncMock(return_value={'healthy': True})
        await self.lifecycle.register_component('test_component', mock_component, ComponentType.DATABASE_MANAGER, health_check=mock_health_check)
        registered_component = self.lifecycle.get_component(ComponentType.DATABASE_MANAGER)
        assert registered_component == mock_component
        status = self.lifecycle.get_component_status('test_component')
        assert status is not None
        assert status.name == 'test_component'
        assert status.component_type == ComponentType.DATABASE_MANAGER
        assert status.status == 'registered'
        assert status.metadata['has_health_check']
        assert 'test_component' in self.lifecycle._health_checks

    async def test_component_unregistration_success(self):
        """Test successful component unregistration."""
        mock_component = AsyncMock()
        mock_component.name = 'test_component'
        await self.lifecycle.register_component('test_component', mock_component, ComponentType.WEBSOCKET_MANAGER)
        assert self.lifecycle.get_component(ComponentType.WEBSOCKET_MANAGER) == mock_component
        await self.lifecycle.unregister_component('test_component')
        assert self.lifecycle.get_component(ComponentType.WEBSOCKET_MANAGER) is None
        assert self.lifecycle.get_component_status('test_component') is None

    async def test_component_validation_during_startup(self):
        """Test component validation during startup phase."""
        mock_db = AsyncMock()
        mock_db.health_check = AsyncMock(return_value={'healthy': True})
        await self.lifecycle.register_component('database', mock_db, ComponentType.DATABASE_MANAGER)
        result = await self.lifecycle._phase_validate_components()
        assert result
        mock_db.health_check.assert_called_once()
        status = self.lifecycle.get_component_status('database')
        assert status.status == 'validated'

    async def test_component_validation_failure_stops_startup(self):
        """Test that component validation failures prevent startup."""
        mock_db = AsyncMock()
        mock_db.health_check = AsyncMock(side_effect=Exception('Database connection failed'))
        await self.lifecycle.register_component('database', mock_db, ComponentType.DATABASE_MANAGER)
        result = await self.lifecycle._phase_validate_components()
        assert not result
        status = self.lifecycle.get_component_status('database')
        assert status.status == 'validation_failed'
        assert 'Database connection failed' in status.last_error
        assert status.error_count == 1

    async def test_component_initialization_order(self):
        """Test that components are initialized in correct order."""
        initialization_calls = []
        mock_db = AsyncMock()
        mock_db.initialize = AsyncMock(side_effect=lambda: initialization_calls.append('DATABASE'))
        mock_redis = AsyncMock()
        mock_redis.initialize = AsyncMock(side_effect=lambda: initialization_calls.append('REDIS'))
        mock_websocket = AsyncMock()
        mock_websocket.initialize = AsyncMock(side_effect=lambda: initialization_calls.append('WEBSOCKET'))
        await self.lifecycle.register_component('db', mock_db, ComponentType.DATABASE_MANAGER)
        await self.lifecycle.register_component('redis', mock_redis, ComponentType.REDIS_MANAGER)
        await self.lifecycle.register_component('websocket', mock_websocket, ComponentType.WEBSOCKET_MANAGER)
        result = await self.lifecycle._phase_initialize_components()
        assert result
        expected_order = ['DATABASE', 'REDIS', 'WEBSOCKET']
        assert initialization_calls == expected_order

    async def test_websocket_component_special_handling(self):
        """Test WebSocket component gets special lifecycle integration."""
        mock_websocket = AsyncMock()
        mock_websocket.broadcast_system_message = AsyncMock()
        await self.lifecycle.register_component('websocket', mock_websocket, ComponentType.WEBSOCKET_MANAGER)
        await self.lifecycle._validate_websocket_component('websocket')
        assert self.lifecycle._websocket_manager == mock_websocket

class TestSystemLifecycleHealthMonitoring(SSotAsyncTestCase):
    """
    Test health monitoring and status tracking.
    
    Business Value: Prevents undetected service failures that could cause
    silent chat disruptions affecting customer experience and revenue.
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.lifecycle = SystemLifecycle(user_id='test_user', health_check_interval=0.1)

    async def test_health_check_registration_and_execution(self):
        """Test health check registration and execution."""
        health_call_count = 0

        def mock_health_check():
            nonlocal health_call_count
            health_call_count += 1
            return {'healthy': True, 'check_count': health_call_count}
        mock_component = AsyncMock()
        await self.lifecycle.register_component('test_service', mock_component, ComponentType.HEALTH_SERVICE, health_check=mock_health_check)
        results = await self.lifecycle._run_all_health_checks()
        assert 'test_service' in results
        assert results['test_service']['healthy']
        assert results['test_service']['check_count'] == 1

    async def test_health_check_failure_tracking(self):
        """Test health check failure tracking and component status updates."""

        def failing_health_check():
            raise Exception('Service unavailable')
        mock_component = AsyncMock()
        await self.lifecycle.register_component('failing_service', mock_component, ComponentType.REDIS_MANAGER, health_check=failing_health_check)
        results = await self.lifecycle._run_all_health_checks()
        assert 'failing_service' in results
        assert not results['failing_service']['healthy']
        assert 'Service unavailable' in results['failing_service']['error']
        assert results['failing_service']['critical']

    async def test_periodic_health_monitoring_updates_status(self):
        """Test periodic health monitoring updates component status."""
        health_status = True

        def toggle_health_check():
            return {'healthy': health_status}
        mock_component = AsyncMock()
        await self.lifecycle.register_component('monitored_service', mock_component, ComponentType.LLM_MANAGER, health_check=toggle_health_check)
        await self.lifecycle._run_periodic_health_checks()
        status = self.lifecycle.get_component_status('monitored_service')
        assert status.status == 'healthy'
        assert status.error_count == 0
        health_status = False
        await self.lifecycle._run_periodic_health_checks()
        status = self.lifecycle.get_component_status('monitored_service')
        assert status.status == 'unhealthy'
        assert status.error_count == 1
        assert status.last_error is not None

    async def test_health_monitoring_websocket_events(self):
        """Test health monitoring emits WebSocket events."""
        mock_websocket = AsyncMock()
        mock_websocket.broadcast_system_message = AsyncMock()
        self.lifecycle.set_websocket_manager(mock_websocket)

        def mock_health_check():
            return {'healthy': True}
        mock_component = AsyncMock()
        await self.lifecycle.register_component('monitored_service', mock_component, ComponentType.AGENT_REGISTRY, health_check=mock_health_check)
        await self.lifecycle._run_periodic_health_checks()
        mock_websocket.broadcast_system_message.assert_called()
        call_args = mock_websocket.broadcast_system_message.call_args[0][0]
        assert call_args['type'] == 'lifecycle_health_status'
        assert 'results' in call_args['data']
        assert 'overall_health' in call_args['data']

    async def test_health_status_endpoint_responses(self):
        """Test health status responses for monitoring endpoints."""
        await self.lifecycle._set_phase(LifecyclePhase.RUNNING)
        status = self.lifecycle.get_health_status()
        assert status['status'] == 'healthy'
        assert status['phase'] == 'running'
        await self.lifecycle._set_phase(LifecyclePhase.STARTING)
        status = self.lifecycle.get_health_status()
        assert status['status'] == 'starting'
        assert not status['ready']
        await self.lifecycle._set_phase(LifecyclePhase.SHUTTING_DOWN)
        status = self.lifecycle.get_health_status()
        assert status['status'] == 'shutting_down'
        assert not status['ready']
        await self.lifecycle._set_phase(LifecyclePhase.ERROR)
        status = self.lifecycle.get_health_status()
        assert status['status'] == 'unhealthy'
        assert not status['ready']

class TestSystemLifecycleGracefulShutdown(SSotAsyncTestCase):
    """
    Test graceful shutdown functionality.
    
    Business Value: Ensures zero-downtime deployments and prevents chat session
    interruption during updates, protecting $500K+ ARR and user experience.
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.lifecycle = SystemLifecycle(user_id='test_user', shutdown_timeout=5, drain_timeout=2, health_check_grace_period=1)

    async def test_request_draining_during_shutdown(self):
        """Test active request draining during shutdown."""
        async with self.lifecycle.request_context('req1'):
            async with self.lifecycle.request_context('req2'):
                assert len(self.lifecycle._active_requests) == 2
                shutdown_task = asyncio.create_task(self.lifecycle.shutdown())
                await asyncio.sleep(0.1)
                assert len(self.lifecycle._active_requests) == 2
            assert len(self.lifecycle._active_requests) == 1
        assert len(self.lifecycle._active_requests) == 0
        success = await shutdown_task
        assert success

    async def test_request_drain_timeout_handling(self):
        """Test that request drain respects timeout."""
        self.lifecycle.drain_timeout = 0.1

        async def long_running_request():
            async with self.lifecycle.request_context('long_req'):
                await asyncio.sleep(1.0)
        request_task = asyncio.create_task(long_running_request())
        await asyncio.sleep(0.01)
        start_time = time.time()
        success = await self.lifecycle.shutdown()
        elapsed = time.time() - start_time
        assert success
        assert elapsed < 0.5
        request_task.cancel()
        try:
            await request_task
        except asyncio.CancelledError:
            pass

    async def test_websocket_shutdown_notification(self):
        """Test WebSocket connections receive shutdown notifications."""
        mock_websocket = AsyncMock()
        mock_websocket.broadcast_system_message = AsyncMock()
        mock_websocket.close_all_connections = AsyncMock()
        mock_websocket.get_connection_count = MagicMock(return_value=5)
        await self.lifecycle.register_component('websocket', mock_websocket, ComponentType.WEBSOCKET_MANAGER)
        success = await self.lifecycle.shutdown()
        assert success
        mock_websocket.broadcast_system_message.assert_called()
        shutdown_message = mock_websocket.broadcast_system_message.call_args[0][0]
        assert shutdown_message['type'] == 'system_shutdown'
        assert 'restarting' in shutdown_message['message']
        assert shutdown_message['reconnect_delay'] == 2000
        mock_websocket.close_all_connections.assert_called_once()

    async def test_component_shutdown_order(self):
        """Test components are shut down in reverse initialization order."""
        shutdown_calls = []
        mock_health = AsyncMock()
        mock_health.shutdown = AsyncMock(side_effect=lambda: shutdown_calls.append('HEALTH'))
        mock_websocket = AsyncMock()
        mock_websocket.shutdown = AsyncMock(side_effect=lambda: shutdown_calls.append('WEBSOCKET'))
        mock_db = AsyncMock()
        mock_db.shutdown = AsyncMock(side_effect=lambda: shutdown_calls.append('DATABASE'))
        await self.lifecycle.register_component('health', mock_health, ComponentType.HEALTH_SERVICE)
        await self.lifecycle.register_component('websocket', mock_websocket, ComponentType.WEBSOCKET_MANAGER)
        await self.lifecycle.register_component('db', mock_db, ComponentType.DATABASE_MANAGER)
        await self.lifecycle._shutdown_phase_5_shutdown_components()
        expected_order = ['HEALTH', 'WEBSOCKET', 'DATABASE']
        assert shutdown_calls == expected_order

    async def test_health_service_grace_period(self):
        """Test health service marking and grace period."""
        mock_health = AsyncMock()
        mock_health.mark_shutting_down = AsyncMock()
        await self.lifecycle.register_component('health', mock_health, ComponentType.HEALTH_SERVICE)
        start_time = time.time()
        await self.lifecycle._shutdown_phase_1_mark_unhealthy()
        elapsed = time.time() - start_time
        mock_health.mark_shutting_down.assert_called_once()
        assert elapsed >= self.lifecycle.health_check_grace_period

    async def test_agent_task_completion_during_shutdown(self):
        """Test agent tasks are allowed to complete during shutdown."""
        mock_agent_registry = AsyncMock()
        task1 = AsyncMock()
        task2 = AsyncMock()
        mock_agent_registry.get_active_tasks = AsyncMock(return_value=[task1, task2])
        mock_agent_registry.stop_accepting_requests = AsyncMock()
        await self.lifecycle.register_component('agents', mock_agent_registry, ComponentType.AGENT_REGISTRY)
        await self.lifecycle._shutdown_phase_4_complete_agents()
        mock_agent_registry.get_active_tasks.assert_called_once()
        mock_agent_registry.stop_accepting_requests.assert_called_once()

    async def test_shutdown_metrics_collection(self):
        """Test shutdown metrics are properly collected."""
        success = await self.lifecycle.shutdown()
        assert success
        status = self.lifecycle.get_status()
        assert status['shutdown_time'] > 0
        metrics = status['metrics']
        assert metrics['successful_shutdowns'] == 1
        assert metrics['failed_shutdowns'] == 0

class TestSystemLifecycleFactoryPattern(SSotAsyncTestCase):
    """
    Test factory pattern for user isolation.
    
    Business Value: Ensures multi-user isolation protecting enterprise customers
    ($15K+ MRR each) from data contamination and security breaches.
    """

    def setup_method(self, method):
        super().setup_method(method)
        SystemLifecycleFactory._global_manager = None
        SystemLifecycleFactory._user_managers.clear()

    def test_global_manager_singleton_behavior(self):
        """Test global manager follows singleton pattern."""
        manager1 = SystemLifecycleFactory.get_global_manager()
        manager2 = SystemLifecycleFactory.get_global_manager()
        assert manager1 is manager2
        assert manager1.user_id is None

    def test_user_specific_manager_isolation(self):
        """Test user-specific managers are properly isolated."""
        user1_id = 'user_123'
        user2_id = 'user_456'
        manager1 = SystemLifecycleFactory.get_user_manager(user1_id)
        manager2 = SystemLifecycleFactory.get_user_manager(user2_id)
        assert manager1 is not manager2
        assert manager1.user_id == user1_id
        assert manager2.user_id == user2_id
        manager1_again = SystemLifecycleFactory.get_user_manager(user1_id)
        assert manager1 is manager1_again

    def test_get_lifecycle_manager_convenience_function(self):
        """Test convenience function routes correctly."""
        global_manager = get_lifecycle_manager()
        assert global_manager.user_id is None
        user_id = 'test_user_789'
        user_manager = get_lifecycle_manager(user_id)
        assert user_manager.user_id == user_id
        assert global_manager is not user_manager

    async def test_shutdown_all_managers(self):
        """Test factory can shutdown all managed instances."""
        global_mgr = SystemLifecycleFactory.get_global_manager()
        user1_mgr = SystemLifecycleFactory.get_user_manager('user1')
        user2_mgr = SystemLifecycleFactory.get_user_manager('user2')
        await global_mgr._set_phase(LifecyclePhase.RUNNING)
        await user1_mgr._set_phase(LifecyclePhase.RUNNING)
        await user2_mgr._set_phase(LifecyclePhase.RUNNING)
        await SystemLifecycleFactory.shutdown_all_managers()
        assert global_mgr.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE
        assert user1_mgr.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE
        assert user2_mgr.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE
        assert SystemLifecycleFactory._global_manager is None
        assert len(SystemLifecycleFactory._user_managers) == 0

    def test_manager_count_tracking(self):
        """Test factory correctly tracks manager counts."""
        counts = SystemLifecycleFactory.get_manager_count()
        assert counts['global'] == 0
        assert counts['user_specific'] == 0
        assert counts['total'] == 0
        SystemLifecycleFactory.get_global_manager()
        counts = SystemLifecycleFactory.get_manager_count()
        assert counts['global'] == 1
        assert counts['total'] == 1
        SystemLifecycleFactory.get_user_manager('user1')
        SystemLifecycleFactory.get_user_manager('user2')
        counts = SystemLifecycleFactory.get_manager_count()
        assert counts['global'] == 1
        assert counts['user_specific'] == 2
        assert counts['total'] == 3

class TestSystemLifecycleThreadSafety(SSotAsyncTestCase):
    """
    Test thread safety and concurrent operations.
    
    Business Value: Ensures system stability under load preventing race conditions
    that could cause service failures during peak usage.
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.lifecycle = SystemLifecycle(user_id='test_user')

    async def test_concurrent_component_registration(self):
        """Test concurrent component registration is thread-safe."""

        async def register_component(name: str, comp_type: ComponentType):
            mock_component = AsyncMock()
            await self.lifecycle.register_component(name, mock_component, comp_type)
        tasks = [register_component('comp1', ComponentType.DATABASE_MANAGER), register_component('comp2', ComponentType.REDIS_MANAGER), register_component('comp3', ComponentType.WEBSOCKET_MANAGER), register_component('comp4', ComponentType.AGENT_REGISTRY), register_component('comp5', ComponentType.HEALTH_SERVICE)]
        await asyncio.gather(*tasks)
        assert len(self.lifecycle._components) == 5
        assert 'comp1' in self.lifecycle._components
        assert 'comp2' in self.lifecycle._components
        assert 'comp3' in self.lifecycle._components
        assert 'comp4' in self.lifecycle._components
        assert 'comp5' in self.lifecycle._components

    async def test_concurrent_health_checks(self):
        """Test concurrent health checks don't interfere."""
        call_counts = {}

        def create_health_check(name: str):

            def health_check():
                call_counts[name] = call_counts.get(name, 0) + 1
                return {'healthy': True, 'name': name}
            return health_check
        for i in range(5):
            name = f'service_{i}'
            mock_component = AsyncMock()
            await self.lifecycle.register_component(name, mock_component, ComponentType.LLM_MANAGER, health_check=create_health_check(name))
        tasks = [self.lifecycle._run_all_health_checks(), self.lifecycle._run_all_health_checks(), self.lifecycle._run_all_health_checks()]
        results = await asyncio.gather(*tasks)
        for result in results:
            assert len(result) == 5
            for i in range(5):
                service_name = f'service_{i}'
                assert service_name in result
                assert result[service_name]['healthy']
        for i in range(5):
            service_name = f'service_{i}'
            assert call_counts[service_name] == 3

    async def test_concurrent_request_tracking(self):
        """Test concurrent request tracking is thread-safe."""

        async def track_request(request_id: str):
            async with self.lifecycle.request_context(request_id):
                await asyncio.sleep(0.1)
        request_ids = [f'req_{i}' for i in range(10)]
        tasks = [track_request(req_id) for req_id in request_ids]
        await asyncio.gather(*tasks)
        assert len(self.lifecycle._active_requests) == 0
        metrics = self.lifecycle._metrics
        assert metrics.active_requests == 0

    async def test_phase_transition_thread_safety(self):
        """Test phase transitions are atomic and thread-safe."""

        async def attempt_phase_change(target_phase: LifecyclePhase):
            try:
                await self.lifecycle._set_phase(target_phase)
            except Exception:
                pass
        phases = [LifecyclePhase.STARTING, LifecyclePhase.RUNNING, LifecyclePhase.SHUTTING_DOWN, LifecyclePhase.ERROR]
        tasks = [attempt_phase_change(phase) for phase in phases]
        await asyncio.gather(*tasks, return_exceptions=True)
        final_phase = self.lifecycle.get_current_phase()
        assert final_phase in phases

class TestSystemLifecyclePerformance(SSotAsyncTestCase):
    """
    Test performance characteristics and timing requirements.
    
    Business Value: Ensures system meets performance SLAs for startup/shutdown
    times that affect deployment windows and service availability.
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.lifecycle = SystemLifecycle(user_id='test_user', startup_timeout=2, shutdown_timeout=2)

    async def test_startup_performance_requirements(self):
        """Test startup completes within performance requirements."""
        for i in range(3):
            mock_component = AsyncMock()
            mock_component.initialize = AsyncMock()
            mock_component.health_check = AsyncMock(return_value={'healthy': True})
            await self.lifecycle.register_component(f'component_{i}', mock_component, [ComponentType.DATABASE_MANAGER, ComponentType.REDIS_MANAGER, ComponentType.WEBSOCKET_MANAGER][i])
        start_time = time.time()
        success = await self.lifecycle.startup()
        elapsed = time.time() - start_time
        assert success
        assert elapsed < 1.0
        status = self.lifecycle.get_status()
        assert status['startup_time'] > 0
        assert status['startup_time'] < 1.0

    async def test_shutdown_performance_requirements(self):
        """Test shutdown completes within performance requirements."""
        await self.lifecycle._set_phase(LifecyclePhase.RUNNING)
        for i in range(3):
            mock_component = AsyncMock()
            mock_component.shutdown = AsyncMock()
            await self.lifecycle.register_component(f'component_{i}', mock_component, [ComponentType.HEALTH_SERVICE, ComponentType.WEBSOCKET_MANAGER, ComponentType.DATABASE_MANAGER][i])
        start_time = time.time()
        success = await self.lifecycle.shutdown()
        elapsed = time.time() - start_time
        assert success
        assert elapsed < 1.0
        status = self.lifecycle.get_status()
        assert status['shutdown_time'] > 0
        assert status['shutdown_time'] < 1.0

    async def test_health_check_performance(self):
        """Test health checks complete within performance requirements."""
        for i in range(10):
            mock_component = AsyncMock()

            def quick_health_check():
                return {'healthy': True, 'response_time': 'fast'}
            await self.lifecycle.register_component(f'service_{i}', mock_component, ComponentType.LLM_MANAGER, health_check=quick_health_check)
        start_time = time.time()
        results = await self.lifecycle._run_all_health_checks()
        elapsed = time.time() - start_time
        assert elapsed < 0.5
        assert len(results) == 10
        for result in results.values():
            assert result['healthy']

    async def test_memory_usage_monitoring(self):
        """Test system tracks memory usage during operations."""
        import psutil
        import os
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        self.lifecycle._metrics.memory_usage = initial_memory
        large_data = []
        for i in range(1000):
            mock_component = AsyncMock()
            large_data.append(mock_component)
        current_memory = process.memory_info().rss
        memory_increase = current_memory - initial_memory
        assert memory_increase >= 0
        assert self.lifecycle._metrics.memory_usage == initial_memory
        self.lifecycle._metrics.memory_usage = current_memory
        metrics = self.lifecycle.get_all_metrics()
        assert 'memory_usage' in metrics
        assert metrics['memory_usage'] == current_memory

class TestSystemLifecycleErrorHandling(SSotAsyncTestCase):
    """
    Test error handling and recovery scenarios.
    
    Business Value: Ensures system gracefully handles failures without causing
    cascading failures that could bring down the entire platform.
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.lifecycle = SystemLifecycle(user_id='test_user')

    async def test_startup_component_initialization_failure(self):
        """Test startup handles component initialization failures gracefully."""
        mock_component = AsyncMock()
        mock_component.initialize = AsyncMock(side_effect=Exception('Initialization failed'))
        await self.lifecycle.register_component('failing_component', mock_component, ComponentType.DATABASE_MANAGER)
        success = await self.lifecycle.startup()
        assert not success
        assert self.lifecycle.get_current_phase() == LifecyclePhase.ERROR
        status = self.lifecycle.get_component_status('failing_component')
        assert status.status == 'initialization_failed'
        assert 'Initialization failed' in status.last_error
        assert status.error_count == 1

    async def test_shutdown_component_failure_continues_shutdown(self):
        """Test shutdown continues even if components fail to shut down."""
        await self.lifecycle._set_phase(LifecyclePhase.RUNNING)
        mock_good_component = AsyncMock()
        mock_good_component.shutdown = AsyncMock()
        mock_bad_component = AsyncMock()
        mock_bad_component.shutdown = AsyncMock(side_effect=Exception('Shutdown failed'))
        await self.lifecycle.register_component('good_component', mock_good_component, ComponentType.HEALTH_SERVICE)
        await self.lifecycle.register_component('bad_component', mock_bad_component, ComponentType.WEBSOCKET_MANAGER)
        success = await self.lifecycle.shutdown()
        assert success
        assert self.lifecycle.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE
        mock_good_component.shutdown.assert_called_once()
        mock_bad_component.shutdown.assert_called_once()
        bad_status = self.lifecycle.get_component_status('bad_component')
        assert bad_status.status == 'shutdown_failed'
        assert 'Shutdown failed' in bad_status.last_error

    async def test_health_check_exception_handling(self):
        """Test health check exceptions are properly handled."""

        def failing_health_check():
            raise RuntimeError('Health check crashed')

        def working_health_check():
            return {'healthy': True}
        mock_component1 = AsyncMock()
        mock_component2 = AsyncMock()
        await self.lifecycle.register_component('failing_service', mock_component1, ComponentType.REDIS_MANAGER, health_check=failing_health_check)
        await self.lifecycle.register_component('working_service', mock_component2, ComponentType.LLM_MANAGER, health_check=working_health_check)
        results = await self.lifecycle._run_all_health_checks()
        assert not results['failing_service']['healthy']
        assert 'Health check crashed' in results['failing_service']['error']
        assert results['failing_service']['critical']
        assert results['working_service']['healthy']

    async def test_lifecycle_hook_exception_handling(self):
        """Test lifecycle hook exceptions don't break lifecycle flow."""
        hook_calls = []

        def working_hook(**kwargs):
            hook_calls.append('working')

        def failing_hook(**kwargs):
            hook_calls.append('failing')
            raise ValueError('Hook failed')

        def another_working_hook(**kwargs):
            hook_calls.append('another_working')
        self.lifecycle.register_lifecycle_hook('pre_startup', working_hook)
        self.lifecycle.register_lifecycle_hook('pre_startup', failing_hook)
        self.lifecycle.register_lifecycle_hook('pre_startup', another_working_hook)
        await self.lifecycle._execute_lifecycle_hooks('pre_startup')
        assert 'working' in hook_calls
        assert 'failing' in hook_calls
        assert 'another_working' in hook_calls

    async def test_request_context_exception_handling(self):
        """Test request context properly handles exceptions."""
        exception_raised = False
        try:
            async with self.lifecycle.request_context('test_request'):
                assert 'test_request' in self.lifecycle._active_requests
                raise ValueError('Request processing failed')
        except ValueError:
            exception_raised = True
        assert exception_raised
        assert 'test_request' not in self.lifecycle._active_requests
        assert len(self.lifecycle._active_requests) == 0

    async def test_websocket_event_emission_failure_handling(self):
        """Test WebSocket event emission failures don't break lifecycle."""
        mock_websocket = AsyncMock()
        mock_websocket.broadcast_system_message = AsyncMock(side_effect=Exception('WebSocket broadcast failed'))
        self.lifecycle.set_websocket_manager(mock_websocket)
        await self.lifecycle._emit_websocket_event('test_event', {'data': 'test'})
        mock_websocket.broadcast_system_message.assert_called_once()
        assert self.lifecycle.get_current_phase() == LifecyclePhase.INITIALIZING
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
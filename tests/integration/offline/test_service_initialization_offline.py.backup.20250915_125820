"""
Offline Service Initialization Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure service initialization works without external dependencies
- Value Impact: Validates core service startup sequences, dependency injection, and configuration loading
- Strategic Impact: Enables testing of critical startup paths without requiring Docker infrastructure

These tests validate service initialization integration without requiring
external services like Redis or PostgreSQL. They focus on:
1. Service factory pattern initialization
2. Dependency injection container setup
3. Configuration loading during startup
4. Service health checks and readiness
5. Graceful error handling during startup
6. Service lifecycle management
"""
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from contextlib import asynccontextmanager
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.mocks.service_mocks import MockServiceDependency, MockConfigurationManager, MockServiceContainer

class TestServiceInitializationOffline(SSotBaseTestCase):
    """Offline integration tests for service initialization."""

    def setup_method(self, method=None):
        """Setup with mock services and configuration."""
        super().setup_method(method)
        self.mock_config_manager = MockConfigurationManager()
        self.mock_container = MockServiceContainer()
        self.mock_db_service = MockServiceDependency('database', startup_delay=0.1)
        self.mock_auth_service = MockServiceDependency('auth', startup_delay=0.05)
        self.mock_cache_service = MockServiceDependency('cache', startup_delay=0.02)
        self.mock_messaging_service = MockServiceDependency('messaging', startup_delay=0.08)
        self.mock_container.register_singleton('config', self.mock_config_manager)
        self.mock_container.register_singleton('database', self.mock_db_service)
        self.mock_container.register_singleton('auth', self.mock_auth_service)
        self.mock_container.register_singleton('cache', self.mock_cache_service)
        self.mock_container.register_singleton('messaging', self.mock_messaging_service)

    def teardown_method(self, method=None):
        """Cleanup mock services."""
        try:
            services = [self.mock_db_service, self.mock_auth_service, self.mock_cache_service, self.mock_messaging_service]
            for service in services:
                try:
                    if hasattr(service, 'stop'):
                        asyncio.create_task(service.stop())
                except Exception as e:
                    self.record_metric(f'cleanup_error_{service.name}', str(e))
        finally:
            super().teardown_method(method)

    @pytest.mark.integration
    async def test_configuration_loading_during_startup(self):
        """
        Test configuration loading integration during service startup.
        
        Validates that configuration is loaded correctly and available
        to all services during initialization.
        """
        config = await self.mock_config_manager.load_configuration()
        assert self.mock_config_manager.loaded == True
        assert isinstance(config, dict)
        assert len(config) > 0
        essential_keys = ['SERVICE_NAME', 'ENVIRONMENT', 'DATABASE_URL', 'SECRET_KEY']
        for key in essential_keys:
            assert key in config, f'Essential config key {key} missing'
            assert config[key] is not None, f'Essential config key {key} is None'
        staging_config = await self.mock_config_manager.load_configuration(['staging.env'])
        assert staging_config['ENVIRONMENT'] == 'staging'
        assert staging_config['DEBUG'] == 'false'
        production_config = await self.mock_config_manager.load_configuration(['production.env'])
        assert production_config['ENVIRONMENT'] == 'production'
        assert production_config['DEBUG'] == 'false'
        validation_errors = self.mock_config_manager.validate_configuration()
        assert isinstance(validation_errors, list)
        assert len(validation_errors) == 0, f'Configuration validation failed: {validation_errors}'
        service_name = self.mock_config_manager.get_config('SERVICE_NAME')
        assert service_name == 'test_service'
        default_value = self.mock_config_manager.get_config('NONEXISTENT_KEY', 'default')
        assert default_value == 'default'
        start_time = time.time()
        await self.mock_config_manager.load_configuration()
        load_time = time.time() - start_time
        assert load_time < 1.0, f'Configuration loading took too long: {load_time:.3f}s'
        self.record_metric('config_keys_loaded', len(config))
        self.record_metric('config_validation_errors', len(validation_errors))
        self.record_metric('config_load_time_seconds', load_time)
        self.record_metric('configuration_loading_integration_passed', True)

    @pytest.mark.integration
    async def test_service_container_initialization(self):
        """
        Test service container initialization and dependency injection.
        
        Validates that the dependency injection container correctly manages
        service lifecycles and dependencies.
        """
        assert 'config' in self.mock_container.singletons
        assert 'database' in self.mock_container.singletons
        assert 'auth' in self.mock_container.singletons
        config_service = await self.mock_container.get_service('config')
        assert config_service is self.mock_config_manager
        db_service = await self.mock_container.get_service('database')
        assert db_service is self.mock_db_service
        with pytest.raises(ValueError, match='Service nonexistent not registered'):
            await self.mock_container.get_service('nonexistent')
        await self.mock_container.initialize_all_services()
        assert self.mock_config_manager.loaded
        assert self.mock_db_service.initialized
        assert self.mock_auth_service.initialized
        assert self.mock_cache_service.initialized
        assert self.mock_messaging_service.initialized
        assert len(self.mock_container.initialization_order) > 0
        assert 'config' in self.mock_container.initialization_order

        async def create_logger_service():
            logger = MockServiceDependency('logger', startup_delay=0.01)
            await logger.initialize()
            return logger
        self.mock_container.register_factory('logger', create_logger_service)
        logger1 = await self.mock_container.get_service('logger')
        logger2 = await self.mock_container.get_service('logger')
        assert logger1 is logger2
        assert logger1.initialized
        self.record_metric('registered_singletons', len(self.mock_container.singletons))
        self.record_metric('registered_factories', len(self.mock_container.factories))
        self.record_metric('initialization_order_count', len(self.mock_container.initialization_order))
        self.record_metric('service_container_integration_passed', True)

    @pytest.mark.integration
    async def test_service_startup_sequence_integration(self):
        """
        Test service startup sequence integration with proper ordering.
        
        Validates that services start up in the correct order and handle
        dependencies appropriately.
        """
        services = [self.mock_cache_service, self.mock_auth_service, self.mock_messaging_service, self.mock_db_service]
        startup_times = {}
        for service in services:
            start_time = time.time()
            await service.initialize()
            await service.start()
            startup_times[service.name] = time.time() - start_time
            assert service.is_healthy(), f'Service {service.name} not healthy after startup'
        assert startup_times['cache'] < startup_times['auth']
        assert startup_times['auth'] < startup_times['messaging']
        assert startup_times['messaging'] < startup_times['database']
        total_sequential_time = sum(startup_times.values())
        assert total_sequential_time > 0.2, 'Sequential startup should take measurable time'
        for service in services:
            service.initialized = False
            service.started = False
            service.healthy = False
        parallel_start_time = time.time()
        init_tasks = [service.initialize() for service in services]
        await asyncio.gather(*init_tasks)
        start_tasks = [service.start() for service in services]
        await asyncio.gather(*start_tasks)
        parallel_total_time = time.time() - parallel_start_time
        assert parallel_total_time < total_sequential_time * 0.8, f'Parallel startup ({parallel_total_time:.3f}s) not significantly faster than sequential ({total_sequential_time:.3f}s)'
        for service in services:
            assert service.is_healthy(), f'Service {service.name} not healthy after parallel startup'
        test_service = MockServiceDependency('test_dependency_validation')
        with pytest.raises(RuntimeError, match='not initialized before start'):
            await test_service.start()
        await test_service.initialize()
        await test_service.start()
        assert test_service.is_healthy()
        self.record_metric('sequential_startup_time_seconds', total_sequential_time)
        self.record_metric('parallel_startup_time_seconds', parallel_total_time)
        self.record_metric('startup_time_improvement_ratio', total_sequential_time / parallel_total_time)
        self.record_metric('services_started_successfully', len(services))
        self.record_metric('service_startup_sequence_integration_passed', True)

    @pytest.mark.integration
    async def test_service_health_monitoring_integration(self):
        """
        Test service health monitoring integration.
        
        Validates that health checks work correctly and provide
        useful information about service status.
        """
        await self.mock_container.initialize_all_services()
        services = [self.mock_db_service, self.mock_auth_service, self.mock_cache_service, self.mock_messaging_service]
        for service in services:
            await service.start()
        health_status = {}
        for service in services:
            health_status[service.name] = service.is_healthy()
            assert health_status[service.name], f'Service {service.name} should be healthy'
        overall_health = all(health_status.values())
        assert overall_health, f'Overall system health failed: {health_status}'
        self.mock_db_service.healthy = False
        degraded_health = {service.name: service.is_healthy() for service in services}
        assert not degraded_health['database'], 'Database service should be unhealthy'
        assert degraded_health['auth'], 'Auth service should still be healthy'
        assert degraded_health['cache'], 'Cache service should still be healthy'
        overall_degraded_health = all(degraded_health.values())
        assert not overall_degraded_health, 'Overall health should be degraded'
        self.mock_db_service.healthy = True
        recovered_health = {service.name: service.is_healthy() for service in services}
        overall_recovered_health = all(recovered_health.values())
        assert overall_recovered_health, f'Health should be recovered: {recovered_health}'
        health_check_start = time.time()
        for _ in range(100):
            for service in services:
                service.is_healthy()
        health_check_time = time.time() - health_check_start
        assert health_check_time < 0.5, f'Health checks took too long: {health_check_time:.3f}s'
        avg_health_check_time = health_check_time / (100 * len(services))
        assert avg_health_check_time < 0.001, f'Average health check too slow: {avg_health_check_time * 1000:.3f}ms'
        self.record_metric('services_monitored', len(services))
        self.record_metric('initial_health_status', overall_health)
        self.record_metric('health_degradation_detected', not overall_degraded_health)
        self.record_metric('health_recovery_detected', overall_recovered_health)
        self.record_metric('health_check_performance_ms', avg_health_check_time * 1000)
        self.record_metric('service_health_monitoring_integration_passed', True)

    @pytest.mark.integration
    async def test_startup_error_handling_integration(self):
        """
        Test startup error handling and recovery integration.
        
        Validates that startup errors are handled gracefully and
        provide useful debugging information.
        """
        error_prone_service = MockServiceDependency('error_service')
        init_error = RuntimeError('Initialization failed - missing config')
        error_prone_service.set_startup_error(init_error)
        with pytest.raises(RuntimeError, match='Initialization failed'):
            await error_prone_service.initialize()
        assert not error_prone_service.initialized
        assert not error_prone_service.is_healthy()
        startup_error_service = MockServiceDependency('startup_error_service')
        await startup_error_service.initialize()
        assert startup_error_service.initialized
        startup_error = RuntimeError('Service startup failed - port in use')
        startup_error_service.set_startup_error(startup_error)
        with pytest.raises(RuntimeError, match='Service startup failed'):
            await startup_error_service.start()
        assert not startup_error_service.started
        assert not startup_error_service.is_healthy()
        error_container = MockServiceContainer()
        error_container.register_singleton('error_service', error_prone_service)
        error_container.register_singleton('normal_service', self.mock_cache_service)
        try:
            await error_container.initialize_all_services()
        except RuntimeError:
            pass
        normal_service = await error_container.get_service('normal_service')
        invalid_config_manager = MockConfigurationManager()
        invalid_config_manager.config = {'SERVICE_NAME': 'test'}
        validation_errors = invalid_config_manager.validate_configuration()
        assert len(validation_errors) > 0
        assert any(('DATABASE_URL' in error for error in validation_errors))
        assert any(('SECRET_KEY' in error for error in validation_errors))
        error_prone_service._startup_error = None
        await error_prone_service.initialize()
        assert error_prone_service.initialized
        await error_prone_service.start()
        assert error_prone_service.started
        assert error_prone_service.is_healthy()
        slow_service = MockServiceDependency('slow_service', startup_delay=2.0)
        try:
            await asyncio.wait_for(slow_service.initialize(), timeout=0.5)
            assert False, 'Should have timed out'
        except asyncio.TimeoutError:
            pass
        assert not slow_service.initialized
        await asyncio.wait_for(slow_service.initialize(), timeout=3.0)
        assert slow_service.initialized
        self.record_metric('initialization_errors_handled', 1)
        self.record_metric('startup_errors_handled', 1)
        self.record_metric('config_validation_errors_detected', len(validation_errors))
        self.record_metric('timeout_errors_handled', 1)
        self.record_metric('error_recovery_successful', True)
        self.record_metric('startup_error_handling_integration_passed', True)

    @pytest.mark.integration
    async def test_service_lifecycle_management_integration(self):
        """
        Test complete service lifecycle management integration.
        
        Validates the entire service lifecycle from startup to shutdown.
        """
        test_service = MockServiceDependency('lifecycle_test')
        assert not test_service.initialized
        assert not test_service.started
        assert not test_service.is_healthy()
        await test_service.initialize()
        assert test_service.initialized
        assert not test_service.started
        assert not test_service.is_healthy()
        await test_service.start()
        assert test_service.initialized
        assert test_service.started
        assert test_service.is_healthy()
        await test_service.stop()
        assert test_service.initialized
        assert not test_service.started
        assert not test_service.is_healthy()
        lifecycle_services = [MockServiceDependency('lifecycle_1', 0.02), MockServiceDependency('lifecycle_2', 0.03), MockServiceDependency('lifecycle_3', 0.01)]
        init_start = time.time()
        await asyncio.gather(*[svc.initialize() for svc in lifecycle_services])
        init_time = time.time() - init_start
        for service in lifecycle_services:
            assert service.initialized
        start_start = time.time()
        await asyncio.gather(*[svc.start() for svc in lifecycle_services])
        start_time = time.time() - start_start
        for service in lifecycle_services:
            assert service.is_healthy()
        stop_start = time.time()
        await asyncio.gather(*[svc.stop() for svc in reversed(lifecycle_services)])
        stop_time = time.time() - stop_start
        for service in lifecycle_services:
            assert not service.is_healthy()
        assert stop_time <= start_time * 1.5, f'Shutdown took too long compared to startup: {stop_time:.3f}s vs {start_time:.3f}s'
        restart_service = MockServiceDependency('restart_test')
        await restart_service.initialize()
        await restart_service.start()
        assert restart_service.is_healthy()
        await restart_service.stop()
        assert not restart_service.is_healthy()
        await restart_service.start()
        assert restart_service.is_healthy()
        lifecycle_container = MockServiceContainer()
        for i, service in enumerate(lifecycle_services):
            service.initialized = False
            service.started = False
            service.healthy = False
            lifecycle_container.register_singleton(f'service_{i}', service)
        container_init_start = time.time()
        await lifecycle_container.initialize_all_services()
        container_init_time = time.time() - container_init_start
        for service in lifecycle_services:
            assert service.initialized
        assert len(lifecycle_container.initialization_order) == len(lifecycle_services)
        for service in lifecycle_services:
            await service.start()
        health_states = [service.is_healthy() for service in lifecycle_services]
        assert all(health_states), f'Not all services healthy: {health_states}'
        self.record_metric('single_service_lifecycle_completed', True)
        self.record_metric('batch_init_time_seconds', init_time)
        self.record_metric('batch_start_time_seconds', start_time)
        self.record_metric('batch_stop_time_seconds', stop_time)
        self.record_metric('container_init_time_seconds', container_init_time)
        self.record_metric('services_in_lifecycle_test', len(lifecycle_services))
        self.record_metric('restart_capability_verified', True)
        self.record_metric('service_lifecycle_management_integration_passed', True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
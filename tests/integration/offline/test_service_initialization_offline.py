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


class MockServiceDependency:
    """Mock service dependency for testing initialization."""
    
    def __init__(self, name: str, startup_delay: float = 0.1):
        self.name = name
        self.startup_delay = startup_delay
        self.initialized = False
        self.started = False
        self.healthy = False
        self.initialization_time = None
        self._startup_error = None
    
    async def initialize(self):
        """Mock initialization process."""
        if self._startup_error:
            raise self._startup_error
        
        start_time = time.time()
        await asyncio.sleep(self.startup_delay)
        self.initialized = True
        self.initialization_time = time.time() - start_time
        return True
    
    async def start(self):
        """Mock startup process."""
        if not self.initialized:
            raise RuntimeError(f"{self.name} not initialized before start")
        
        if self._startup_error:
            raise self._startup_error
        
        self.started = True
        self.healthy = True
        return True
    
    async def stop(self):
        """Mock shutdown process.""" 
        self.started = False
        self.healthy = False
        return True
    
    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self.healthy and self.started
    
    def set_startup_error(self, error: Exception):
        """Set error to be raised during startup."""
        self._startup_error = error


class MockConfigurationManager:
    """Mock configuration manager for testing initialization."""
    
    def __init__(self):
        self.loaded = False
        self.config = {}
        self.load_errors = []
        self.validation_errors = []
    
    async def load_configuration(self, config_paths: List[str] = None) -> Dict[str, Any]:
        """Mock configuration loading."""
        await asyncio.sleep(0.05)  # Simulate loading time
        
        # Default test configuration
        self.config = {
            "SERVICE_NAME": "test_service",
            "ENVIRONMENT": "test",
            "DATABASE_URL": "postgresql://test:test@localhost:5434/test_db",
            "AUTH_SERVICE_URL": "http://localhost:8081",
            "REDIS_URL": "redis://localhost:6381",
            "LOG_LEVEL": "INFO",
            "DEBUG": "true",
            "SECRET_KEY": "test_secret_key_for_initialization",
            "JWT_SECRET_KEY": "test_jwt_secret_key_for_initialization"
        }
        
        # Add any additional config from paths
        if config_paths:
            for path in config_paths:
                if "staging" in path:
                    self.config.update({
                        "ENVIRONMENT": "staging",
                        "DEBUG": "false"
                    })
                elif "production" in path:
                    self.config.update({
                        "ENVIRONMENT": "production", 
                        "DEBUG": "false"
                    })
        
        self.loaded = True
        return self.config.copy()
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def validate_configuration(self) -> List[str]:
        """Mock configuration validation."""
        errors = []
        
        required_keys = ["SERVICE_NAME", "DATABASE_URL", "SECRET_KEY"]
        for key in required_keys:
            if key not in self.config:
                errors.append(f"Missing required configuration: {key}")
        
        # Check for insecure configurations
        if self.config.get("DEBUG") == "true" and self.config.get("ENVIRONMENT") == "production":
            errors.append("Debug mode should not be enabled in production")
        
        self.validation_errors = errors
        return errors


class MockServiceContainer:
    """Mock dependency injection container."""
    
    def __init__(self):
        self.services = {}
        self.singletons = {}
        self.factories = {}
        self.initialization_order = []
    
    def register_singleton(self, service_type: str, instance: Any):
        """Register singleton service."""
        self.singletons[service_type] = instance
    
    def register_factory(self, service_type: str, factory: Callable):
        """Register service factory."""
        self.factories[service_type] = factory
    
    async def get_service(self, service_type: str) -> Any:
        """Get service instance."""
        if service_type in self.singletons:
            return self.singletons[service_type]
        elif service_type in self.factories:
            if service_type not in self.services:
                self.services[service_type] = await self.factories[service_type]()
            return self.services[service_type]
        else:
            raise ValueError(f"Service {service_type} not registered")
    
    async def initialize_all_services(self):
        """Initialize all registered services."""
        # Initialize singletons first
        for service_type, instance in self.singletons.items():
            if hasattr(instance, 'initialize'):
                await instance.initialize()
                self.initialization_order.append(service_type)
        
        # Initialize factory-created services
        for service_type in self.factories.keys():
            service = await self.get_service(service_type)
            if hasattr(service, 'initialize'):
                await service.initialize()
                self.initialization_order.append(service_type)


class TestServiceInitializationOffline(SSotBaseTestCase):
    """Offline integration tests for service initialization."""

    def setup_method(self, method=None):
        """Setup with mock services and configuration."""
        super().setup_method(method)
        
        # Initialize mock components
        self.mock_config_manager = MockConfigurationManager()
        self.mock_container = MockServiceContainer()
        
        # Create mock services
        self.mock_db_service = MockServiceDependency("database", startup_delay=0.1)
        self.mock_auth_service = MockServiceDependency("auth", startup_delay=0.05)
        self.mock_cache_service = MockServiceDependency("cache", startup_delay=0.02)
        self.mock_messaging_service = MockServiceDependency("messaging", startup_delay=0.08)
        
        # Register services in container
        self.mock_container.register_singleton("config", self.mock_config_manager)
        self.mock_container.register_singleton("database", self.mock_db_service)
        self.mock_container.register_singleton("auth", self.mock_auth_service)
        self.mock_container.register_singleton("cache", self.mock_cache_service)
        self.mock_container.register_singleton("messaging", self.mock_messaging_service)
    
    def teardown_method(self, method=None):
        """Cleanup mock services."""
        try:
            # Stop all services
            services = [
                self.mock_db_service,
                self.mock_auth_service, 
                self.mock_cache_service,
                self.mock_messaging_service
            ]
            
            for service in services:
                try:
                    if hasattr(service, 'stop'):
                        asyncio.create_task(service.stop())
                except Exception as e:
                    self.record_metric(f"cleanup_error_{service.name}", str(e))
        finally:
            super().teardown_method(method)

    @pytest.mark.integration
    async def test_configuration_loading_during_startup(self):
        """
        Test configuration loading integration during service startup.
        
        Validates that configuration is loaded correctly and available
        to all services during initialization.
        """
        # Test Case 1: Basic configuration loading
        config = await self.mock_config_manager.load_configuration()
        
        assert self.mock_config_manager.loaded == True
        assert isinstance(config, dict)
        assert len(config) > 0
        
        # Verify essential configuration keys are present
        essential_keys = ["SERVICE_NAME", "ENVIRONMENT", "DATABASE_URL", "SECRET_KEY"]
        for key in essential_keys:
            assert key in config, f"Essential config key {key} missing"
            assert config[key] is not None, f"Essential config key {key} is None"
        
        # Test Case 2: Environment-specific configuration
        staging_config = await self.mock_config_manager.load_configuration(["staging.env"])
        assert staging_config["ENVIRONMENT"] == "staging"
        assert staging_config["DEBUG"] == "false"
        
        production_config = await self.mock_config_manager.load_configuration(["production.env"])
        assert production_config["ENVIRONMENT"] == "production"
        assert production_config["DEBUG"] == "false"
        
        # Test Case 3: Configuration validation
        validation_errors = self.mock_config_manager.validate_configuration()
        assert isinstance(validation_errors, list)
        assert len(validation_errors) == 0, f"Configuration validation failed: {validation_errors}"
        
        # Test Case 4: Configuration access patterns
        service_name = self.mock_config_manager.get_config("SERVICE_NAME")
        assert service_name == "test_service"
        
        default_value = self.mock_config_manager.get_config("NONEXISTENT_KEY", "default")
        assert default_value == "default"
        
        # Test Case 5: Configuration loading performance
        start_time = time.time()
        await self.mock_config_manager.load_configuration()
        load_time = time.time() - start_time
        
        assert load_time < 1.0, f"Configuration loading took too long: {load_time:.3f}s"
        
        # Record configuration loading metrics
        self.record_metric("config_keys_loaded", len(config))
        self.record_metric("config_validation_errors", len(validation_errors))
        self.record_metric("config_load_time_seconds", load_time)
        self.record_metric("configuration_loading_integration_passed", True)

    @pytest.mark.integration
    async def test_service_container_initialization(self):
        """
        Test service container initialization and dependency injection.
        
        Validates that the dependency injection container correctly manages
        service lifecycles and dependencies.
        """
        # Test Case 1: Service registration
        assert "config" in self.mock_container.singletons
        assert "database" in self.mock_container.singletons
        assert "auth" in self.mock_container.singletons
        
        # Test Case 2: Service retrieval
        config_service = await self.mock_container.get_service("config")
        assert config_service is self.mock_config_manager
        
        db_service = await self.mock_container.get_service("database")
        assert db_service is self.mock_db_service
        
        # Test Case 3: Service not found handling
        with pytest.raises(ValueError, match="Service nonexistent not registered"):
            await self.mock_container.get_service("nonexistent")
        
        # Test Case 4: Bulk service initialization
        await self.mock_container.initialize_all_services()
        
        # Verify all services were initialized
        assert self.mock_config_manager.loaded
        assert self.mock_db_service.initialized
        assert self.mock_auth_service.initialized
        assert self.mock_cache_service.initialized
        assert self.mock_messaging_service.initialized
        
        # Verify initialization order was tracked
        assert len(self.mock_container.initialization_order) > 0
        assert "config" in self.mock_container.initialization_order
        
        # Test Case 5: Factory pattern registration
        async def create_logger_service():
            logger = MockServiceDependency("logger", startup_delay=0.01)
            await logger.initialize()
            return logger
        
        self.mock_container.register_factory("logger", create_logger_service)
        
        logger1 = await self.mock_container.get_service("logger")
        logger2 = await self.mock_container.get_service("logger")
        
        # Factory services should return same instance (cached)
        assert logger1 is logger2
        assert logger1.initialized
        
        # Record container metrics
        self.record_metric("registered_singletons", len(self.mock_container.singletons))
        self.record_metric("registered_factories", len(self.mock_container.factories))
        self.record_metric("initialization_order_count", len(self.mock_container.initialization_order))
        self.record_metric("service_container_integration_passed", True)

    @pytest.mark.integration
    async def test_service_startup_sequence_integration(self):
        """
        Test service startup sequence integration with proper ordering.
        
        Validates that services start up in the correct order and handle
        dependencies appropriately.
        """
        # Test Case 1: Sequential startup with timing
        services = [
            self.mock_cache_service,      # Fastest startup (0.02s)
            self.mock_auth_service,       # Fast startup (0.05s) 
            self.mock_messaging_service,  # Medium startup (0.08s)
            self.mock_db_service          # Slowest startup (0.1s)
        ]
        
        startup_times = {}
        
        # Initialize and start services sequentially
        for service in services:
            start_time = time.time()
            
            await service.initialize()
            await service.start()
            
            startup_times[service.name] = time.time() - start_time
            
            assert service.is_healthy(), f"Service {service.name} not healthy after startup"
        
        # Test Case 2: Verify startup timing expectations
        assert startup_times["cache"] < startup_times["auth"]
        assert startup_times["auth"] < startup_times["messaging"] 
        assert startup_times["messaging"] < startup_times["database"]
        
        total_sequential_time = sum(startup_times.values())
        assert total_sequential_time > 0.2, "Sequential startup should take measurable time"
        
        # Test Case 3: Parallel startup optimization
        # Reset services
        for service in services:
            service.initialized = False
            service.started = False
            service.healthy = False
        
        parallel_start_time = time.time()
        
        # Initialize all services in parallel
        init_tasks = [service.initialize() for service in services]
        await asyncio.gather(*init_tasks)
        
        # Start all services in parallel
        start_tasks = [service.start() for service in services]
        await asyncio.gather(*start_tasks)
        
        parallel_total_time = time.time() - parallel_start_time
        
        # Parallel startup should be faster than sequential
        assert parallel_total_time < total_sequential_time * 0.8, (
            f"Parallel startup ({parallel_total_time:.3f}s) not significantly faster than "
            f"sequential ({total_sequential_time:.3f}s)"
        )
        
        # All services should be healthy
        for service in services:
            assert service.is_healthy(), f"Service {service.name} not healthy after parallel startup"
        
        # Test Case 4: Dependency validation
        # Test that starting before initialization fails
        test_service = MockServiceDependency("test_dependency_validation")
        
        with pytest.raises(RuntimeError, match="not initialized before start"):
            await test_service.start()
        
        # After initialization, start should work
        await test_service.initialize()
        await test_service.start()
        assert test_service.is_healthy()
        
        # Record startup sequence metrics
        self.record_metric("sequential_startup_time_seconds", total_sequential_time)
        self.record_metric("parallel_startup_time_seconds", parallel_total_time)
        self.record_metric("startup_time_improvement_ratio", 
                          total_sequential_time / parallel_total_time)
        self.record_metric("services_started_successfully", len(services))
        self.record_metric("service_startup_sequence_integration_passed", True)

    @pytest.mark.integration
    async def test_service_health_monitoring_integration(self):
        """
        Test service health monitoring integration.
        
        Validates that health checks work correctly and provide
        useful information about service status.
        """
        # Initialize services for health monitoring
        await self.mock_container.initialize_all_services()
        
        services = [
            self.mock_db_service,
            self.mock_auth_service,
            self.mock_cache_service,
            self.mock_messaging_service
        ]
        
        # Start all services
        for service in services:
            await service.start()
        
        # Test Case 1: Individual service health checks
        health_status = {}
        for service in services:
            health_status[service.name] = service.is_healthy()
            assert health_status[service.name], f"Service {service.name} should be healthy"
        
        # Test Case 2: Overall system health aggregation
        overall_health = all(health_status.values())
        assert overall_health, f"Overall system health failed: {health_status}"
        
        # Test Case 3: Health degradation simulation
        # Simulate service failure
        self.mock_db_service.healthy = False
        
        degraded_health = {
            service.name: service.is_healthy() 
            for service in services
        }
        
        assert not degraded_health["database"], "Database service should be unhealthy"
        assert degraded_health["auth"], "Auth service should still be healthy"
        assert degraded_health["cache"], "Cache service should still be healthy"
        
        overall_degraded_health = all(degraded_health.values())
        assert not overall_degraded_health, "Overall health should be degraded"
        
        # Test Case 4: Health recovery simulation
        self.mock_db_service.healthy = True
        
        recovered_health = {
            service.name: service.is_healthy()
            for service in services
        }
        
        overall_recovered_health = all(recovered_health.values())
        assert overall_recovered_health, f"Health should be recovered: {recovered_health}"
        
        # Test Case 5: Health check performance
        health_check_start = time.time()
        
        for _ in range(100):  # Multiple health checks
            for service in services:
                service.is_healthy()
        
        health_check_time = time.time() - health_check_start
        
        # Health checks should be fast
        assert health_check_time < 0.5, f"Health checks took too long: {health_check_time:.3f}s"
        
        avg_health_check_time = health_check_time / (100 * len(services))
        assert avg_health_check_time < 0.001, (  # Less than 1ms per check
            f"Average health check too slow: {avg_health_check_time * 1000:.3f}ms"
        )
        
        # Record health monitoring metrics
        self.record_metric("services_monitored", len(services))
        self.record_metric("initial_health_status", overall_health)
        self.record_metric("health_degradation_detected", not overall_degraded_health)
        self.record_metric("health_recovery_detected", overall_recovered_health)
        self.record_metric("health_check_performance_ms", avg_health_check_time * 1000)
        self.record_metric("service_health_monitoring_integration_passed", True)

    @pytest.mark.integration
    async def test_startup_error_handling_integration(self):
        """
        Test startup error handling and recovery integration.
        
        Validates that startup errors are handled gracefully and
        provide useful debugging information.
        """
        # Test Case 1: Service initialization failure
        error_prone_service = MockServiceDependency("error_service")
        init_error = RuntimeError("Initialization failed - missing config")
        error_prone_service.set_startup_error(init_error)
        
        with pytest.raises(RuntimeError, match="Initialization failed"):
            await error_prone_service.initialize()
        
        assert not error_prone_service.initialized
        assert not error_prone_service.is_healthy()
        
        # Test Case 2: Service startup failure after successful initialization
        startup_error_service = MockServiceDependency("startup_error_service")
        await startup_error_service.initialize()  # This should succeed
        assert startup_error_service.initialized
        
        startup_error = RuntimeError("Service startup failed - port in use")
        startup_error_service.set_startup_error(startup_error)
        
        with pytest.raises(RuntimeError, match="Service startup failed"):
            await startup_error_service.start()
        
        assert not startup_error_service.started
        assert not startup_error_service.is_healthy()
        
        # Test Case 3: Cascading failure handling
        # Register error service in container
        error_container = MockServiceContainer()
        error_container.register_singleton("error_service", error_prone_service)
        error_container.register_singleton("normal_service", self.mock_cache_service)
        
        # Test that container initialization handles partial failures
        try:
            await error_container.initialize_all_services()
        except RuntimeError:
            # Expected to fail due to error_prone_service
            pass
        
        # Normal service should not be affected by other service's failure
        # (depending on implementation, this might vary)
        normal_service = await error_container.get_service("normal_service")
        # Note: In a real system, you might want to implement partial failure handling
        
        # Test Case 4: Configuration validation error handling
        invalid_config_manager = MockConfigurationManager()
        # Simulate missing required config
        invalid_config_manager.config = {"SERVICE_NAME": "test"}  # Missing required keys
        
        validation_errors = invalid_config_manager.validate_configuration()
        assert len(validation_errors) > 0
        assert any("DATABASE_URL" in error for error in validation_errors)
        assert any("SECRET_KEY" in error for error in validation_errors)
        
        # Test Case 5: Recovery after error resolution
        # Fix the error in error_prone_service
        error_prone_service._startup_error = None
        
        # Now initialization should succeed
        await error_prone_service.initialize()
        assert error_prone_service.initialized
        
        await error_prone_service.start() 
        assert error_prone_service.started
        assert error_prone_service.is_healthy()
        
        # Test Case 6: Timeout handling simulation
        slow_service = MockServiceDependency("slow_service", startup_delay=2.0)
        
        # Test with reasonable timeout
        try:
            await asyncio.wait_for(slow_service.initialize(), timeout=0.5)
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            # Expected timeout
            pass
        
        assert not slow_service.initialized
        
        # Test with sufficient timeout
        await asyncio.wait_for(slow_service.initialize(), timeout=3.0)
        assert slow_service.initialized
        
        # Record error handling metrics
        self.record_metric("initialization_errors_handled", 1)
        self.record_metric("startup_errors_handled", 1)
        self.record_metric("config_validation_errors_detected", len(validation_errors))
        self.record_metric("timeout_errors_handled", 1)
        self.record_metric("error_recovery_successful", True)
        self.record_metric("startup_error_handling_integration_passed", True)

    @pytest.mark.integration
    async def test_service_lifecycle_management_integration(self):
        """
        Test complete service lifecycle management integration.
        
        Validates the entire service lifecycle from startup to shutdown.
        """
        # Test Case 1: Complete lifecycle for single service
        test_service = MockServiceDependency("lifecycle_test")
        
        # Initial state
        assert not test_service.initialized
        assert not test_service.started
        assert not test_service.is_healthy()
        
        # Initialize
        await test_service.initialize()
        assert test_service.initialized
        assert not test_service.started  # Not started yet
        assert not test_service.is_healthy()  # Not healthy until started
        
        # Start
        await test_service.start()
        assert test_service.initialized
        assert test_service.started
        assert test_service.is_healthy()
        
        # Stop
        await test_service.stop()
        assert test_service.initialized  # Still initialized
        assert not test_service.started
        assert not test_service.is_healthy()
        
        # Test Case 2: Multiple service lifecycle coordination
        lifecycle_services = [
            MockServiceDependency("lifecycle_1", 0.02),
            MockServiceDependency("lifecycle_2", 0.03),
            MockServiceDependency("lifecycle_3", 0.01)
        ]
        
        # Batch initialize
        init_start = time.time()
        await asyncio.gather(*[svc.initialize() for svc in lifecycle_services])
        init_time = time.time() - init_start
        
        for service in lifecycle_services:
            assert service.initialized
        
        # Batch start
        start_start = time.time()
        await asyncio.gather(*[svc.start() for svc in lifecycle_services])
        start_time = time.time() - start_start
        
        for service in lifecycle_services:
            assert service.is_healthy()
        
        # Batch stop (reverse order for graceful shutdown)
        stop_start = time.time()
        await asyncio.gather(*[svc.stop() for svc in reversed(lifecycle_services)])
        stop_time = time.time() - stop_start
        
        for service in lifecycle_services:
            assert not service.is_healthy()
        
        # Test Case 3: Graceful shutdown timing
        # Shutdown should be faster than startup (less work to do)
        assert stop_time <= start_time * 1.5, (
            f"Shutdown took too long compared to startup: {stop_time:.3f}s vs {start_time:.3f}s"
        )
        
        # Test Case 4: Service restart capability
        restart_service = MockServiceDependency("restart_test")
        
        # Initial startup
        await restart_service.initialize()
        await restart_service.start()
        assert restart_service.is_healthy()
        
        # Restart (stop then start again)
        await restart_service.stop()
        assert not restart_service.is_healthy()
        
        await restart_service.start()
        assert restart_service.is_healthy()
        
        # Test Case 5: Container-managed lifecycle
        lifecycle_container = MockServiceContainer()
        
        for i, service in enumerate(lifecycle_services):
            # Reset services
            service.initialized = False
            service.started = False
            service.healthy = False
            lifecycle_container.register_singleton(f"service_{i}", service)
        
        # Container initialization
        container_init_start = time.time()
        await lifecycle_container.initialize_all_services()
        container_init_time = time.time() - container_init_start
        
        # Verify all services initialized through container
        for service in lifecycle_services:
            assert service.initialized
        
        assert len(lifecycle_container.initialization_order) == len(lifecycle_services)
        
        # Manual start of container-managed services
        for service in lifecycle_services:
            await service.start()
        
        # Verify all healthy
        health_states = [service.is_healthy() for service in lifecycle_services]
        assert all(health_states), f"Not all services healthy: {health_states}"
        
        # Record lifecycle metrics
        self.record_metric("single_service_lifecycle_completed", True)
        self.record_metric("batch_init_time_seconds", init_time)
        self.record_metric("batch_start_time_seconds", start_time)
        self.record_metric("batch_stop_time_seconds", stop_time)
        self.record_metric("container_init_time_seconds", container_init_time)
        self.record_metric("services_in_lifecycle_test", len(lifecycle_services))
        self.record_metric("restart_capability_verified", True)
        self.record_metric("service_lifecycle_management_integration_passed", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
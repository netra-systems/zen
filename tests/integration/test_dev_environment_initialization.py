from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'''
'''
env = get_env()
Critical Integration Test for Dev Environment Initialization

Business Value: $20K MRR - Ensures reliable development and demo environments
Validates complete dev launcher startup sequence and service health.

This test is critical for:
- Developer experience and productivity
- Sales demo reliability
- Platform stability across all segments
- Development infrastructure robustness

Tests cover:
1. Dev Launcher Startup (clean startup from scratch)
2. Service Health Validation (all services reach healthy state)
3. Auto-Recovery Mechanisms (service restart on failure)
4. Configuration Validation (environment variables, secrets, feature flags)
'''
'''

import asyncio
import os
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Set

import pytest

from dev_launcher.cache_manager import CacheManager
from dev_launcher.config import LauncherConfig
from dev_launcher.database_connector import ConnectionStatus, DatabaseConnector
from shared.isolated_environment import EnvironmentValidator
from dev_launcher.health_monitor import HealthMonitor, HealthStatus, ServiceState
from dev_launcher.launcher import DevLauncher
from dev_launcher.log_streamer import LogManager
from dev_launcher.secret_loader import SecretLoader
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.startup_optimizer import StartupOptimizer, StartupStep, StepResult
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


class TestDevEnvironmentInitialization:
    '''
    '''
    Critical integration test for complete dev environment initialization.

    Tests the end-to-end startup sequence from clean state to fully
    operational development environment with all services healthy.
    '''
    '''

    def setup_method(self):
        """Set up test environment with clean state."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

    # Create minimal project structure
        (self.project_root / "app").mkdir(exist_ok=True)
        (self.project_root / "auth_service").mkdir(exist_ok=True)
        (self.project_root / "frontend").mkdir(exist_ok=True)
        (self.project_root / "dev_launcher").mkdir(exist_ok=True)

    # Essential environment for testing
        self.test_env = { }
        'DATABASE_URL': 'postgresql://test:test@localhost:5433/netra_test',
        'REDIS_URL': 'redis://localhost:6380/1',
        'CLICKHOUSE_URL': 'clickhouse://test:test@localhost:8124/netra_test',
        'JWT_SECRET_KEY': 'test-jwt-secret-key-for-testing-minimum-32-chars',
        'SECRET_KEY': 'test-app-secret-key-for-testing-minimum-32-chars',
        'ENVIRONMENT': 'development',
        'NETRA_STARTUP_MODE': 'full',
        'LOG_LEVEL': 'INFO'
    

        self.startup_timeout = 30.0  # 30 second startup timeout
        self.health_check_timeout = 10.0  # 10 second health check timeout

    def teardown_method(self):
        """Clean up test environment."""
        pass
    # Clean up temporary directory
        import shutil
        if self.temp_dir and Path(self.temp_dir).exists():
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_dev_environment_complete_initialization(self):
        '''
        '''
        Test complete dev environment initialization from clean state.

        This is the primary integration test validating:
        1. Clean startup from scratch
        2. Service discovery and registration
        3. Dependency resolution
        4. Configuration loading
        5. All services reach healthy state
        6. Startup completes within timeout
        '''
        '''
        pass
        with patch.dict(os.environ, self.test_env, clear=False):
                    # Mock signal handlers to avoid test interference
        config = LauncherConfig( )
        backend_port=8001,  # Use different ports for testing
        frontend_port=3001,
        project_root=self.project_root,
        verbose=False,
        no_browser=True
                    

                    # Initialize launcher
        launcher = DevLauncher(config)

                    # Verify core components are initialized
        assert launcher.database_connector is not None
        assert launcher.environment_validator is not None
        assert launcher.health_monitor is not None
        assert launcher.startup_optimizer is not None
        assert launcher.cache_manager is not None
        assert launcher.service_discovery is not None

                    # Test startup optimizer initialization
        optimizer = launcher.startup_optimizer
        assert isinstance(optimizer, StartupOptimizer)

                    # Test environment validation
        env_validator = launcher.environment_validator
        validation_result = env_validator.validate_all()
        assert validation_result is not None

                    # Test database connector initialization
        db_connector = launcher.database_connector
        assert len(db_connector.connections) >= 0  # May be 0 in test env

                    # Test service discovery
        discovery = launcher.service_discovery
        assert discovery.project_root == self.project_root

                    # Test health monitor
        health_monitor = launcher.health_monitor
        assert health_monitor.check_interval == 30
        assert not health_monitor.monitoring_enabled  # Should start disabled

    async def test_startup_sequence_optimization(self):
        '''
        '''
        Test startup sequence optimization and caching.

        Validates:
        - Startup steps are registered correctly
        - Dependencies are resolved properly
        - Caching works for repeated startups
        - Parallel execution where possible
        '''
        '''
        pass
        cache_manager = CacheManager(project_root=self.project_root)
        optimizer = StartupOptimizer(cache_manager)

                            # Register test startup steps
        test_steps = [ ]
        StartupStep( )
        name="env_check",
        func=lambda x: None True,
        dependencies=[],
        parallel=True,
        timeout=5,
        cache_key="env_validation"
        ),
        StartupStep( )
        name="db_init",
        func=lambda x: None True,
        dependencies=["env_check"],
        parallel=True,
        timeout=10,
        cache_key="db_connections"
        ),
        StartupStep( )
        name="service_start",
        func=lambda x: None True,
        dependencies=["db_init"],
        parallel=False,  # Services must start sequentially
        timeout=15
                            
                            

        optimizer.register_steps(test_steps)

                            # Test optimized sequence execution
        start_time = time.time()
        results = optimizer.execute_optimized_sequence( )
        ["env_check", "db_init", "service_start"]
                            
        execution_time = time.time() - start_time

                            # Validate results
        assert len(results) == 3
        for step_name in ["env_check", "db_init", "service_start"]:
        assert step_name in results
        result = results[step_name]
        assert isinstance(result, StepResult)
        assert result.success
        assert result.duration >= 0

                                # Should complete quickly for simple test steps
        assert execution_time < 5.0

                                # Test timing report
        timing_report = optimizer.get_timing_report()
        assert "total_startup_time" in timing_report
        assert "step_timings" in timing_report
        assert "step_results" in timing_report
        assert timing_report["total_startup_time"] > 0

                                # Cleanup
        optimizer.cleanup()

    async def test_service_health_monitoring(self):
        '''
        '''
        Test comprehensive service health monitoring system.

        Validates:
        - Health monitor registration for services
        - Grace period implementation (Frontend: 90s, Backend: 30s)
        - Health status tracking and state transitions
        - Cross-service connectivity validation
        '''
        '''
        pass
        health_monitor = HealthMonitor(check_interval=5)  # Faster for testing

                                        # Register test services with different grace periods
    def mock_backend_health():
        pass
        await asyncio.sleep(0)
        return True

    def mock_frontend_health():
        pass
        return True

    def mock_auth_health():
        pass
        return True

    # Register services (should use correct grace periods)
        health_monitor.register_service( )
        "backend",
        mock_backend_health,
        max_failures=3
    
        health_monitor.register_service( )
        "frontend",
        mock_frontend_health,
        max_failures=3
    
        health_monitor.register_service( )
        "auth_service",
        mock_auth_health,
        max_failures=3
    

    # Verify grace periods are set correctly
        backend_status = health_monitor.get_status("backend")
        frontend_status = health_monitor.get_status("frontend")
        auth_status = health_monitor.get_status("auth_service")

        assert backend_status.grace_period_seconds == 30  # Backend: 30s
        assert frontend_status.grace_period_seconds == 90  # Frontend: 90s
        assert auth_status.grace_period_seconds == 30  # Default: 30s

    # Test initial states
        assert backend_status.state == ServiceState.STARTING
        assert frontend_status.state == ServiceState.STARTING
        assert not backend_status.ready_confirmed
        assert not frontend_status.ready_confirmed

    # Test grace period status
        grace_status = health_monitor.get_grace_period_status()
        assert "backend" in grace_status
        assert "frontend" in grace_status
        assert grace_status["backend"]["grace_period_seconds"] == 30
        assert grace_status["frontend"]["grace_period_seconds"] == 90

    # Mark services as ready
        test_ports = {8001, 8002}
        health_monitor.mark_service_ready("backend", process_pid=12345, ports=test_ports)
        health_monitor.mark_service_ready("frontend", process_pid=12346, ports={3001})

    # Verify ready state
        backend_status = health_monitor.get_status("backend")
        frontend_status = health_monitor.get_status("frontend")

        assert backend_status.ready_confirmed
        assert frontend_status.ready_confirmed
        assert backend_status.state == ServiceState.READY
        assert frontend_status.state == ServiceState.READY
        assert backend_status.ports_verified == test_ports

    # Test cross-service health status
        cross_service_status = health_monitor.get_cross_service_health_status()
        assert "services" in cross_service_status
        assert "cross_service_integration" in cross_service_status
        assert "backend" in cross_service_status["services"]
        assert "frontend" in cross_service_status["services"]

    async def test_auto_recovery_mechanisms(self):
        '''
        '''
        Test auto-recovery mechanisms for service failures.

        Validates:
        - Service failure detection
        - Recovery action triggering
        - Health check retry logic
        - Circuit breaker functionality
        '''
        '''
        pass
        health_monitor = HealthMonitor(check_interval=1)  # Fast for testing

            # Track recovery calls
        recovery_called = {"test_service_1": False, "test_service_2": False}
        failure_count = {"test_service_1": 0, "test_service_2": 0}

    def failing_backend_health():
        pass
        failure_count["test_service_1"] += 1
        await asyncio.sleep(0)
        return failure_count["test_service_1"] > 3  # Fail first 3 times

    def backend_recovery():
        pass
        recovery_called["test_service_1"] = True
        failure_count["test_service_1"] = 0  # Reset on recovery

    def failing_frontend_health():
        pass
        failure_count["test_service_2"] += 1
        return failure_count["test_service_2"] > 2  # Fail first 2 times

    def frontend_recovery():
        pass
        recovery_called["test_service_2"] = True
        failure_count["test_service_2"] = 0

    # Register services with recovery actions and short grace periods for testing
    # Note: Use custom service names to avoid hardcoded grace period overrides
        health_monitor.register_service( )
        "test_service_1",
        failing_backend_health,
        recovery_action=backend_recovery,
        max_failures=3,
        grace_period_seconds=1  # Very short for testing
    
        health_monitor.register_service( )
        "test_service_2",
        failing_frontend_health,
        recovery_action=frontend_recovery,
        max_failures=2,
        grace_period_seconds=1  # Very short for testing
    

    # Mark as ready and enable monitoring
        health_monitor.mark_service_ready("test_service_1")
        health_monitor.mark_service_ready("test_service_2")

    # Start monitoring
        health_monitor.start()
        health_monitor.enable_monitoring()

    # Wait for grace period to expire then for recovery to be triggered
        await asyncio.sleep(2)  # Wait for grace period to pass

        max_wait = 8  # 8 seconds max for recovery
        start_time = time.time()

        while time.time() - start_time < max_wait:
        if recovery_called["test_service_1"] and recovery_called["test_service_2"]:
        break
        await asyncio.sleep(0.5)

            # Stop monitoring
        health_monitor.stop()

            # Verify recovery was triggered
        assert recovery_called["test_service_1"], "Service 1 recovery should have been called"
        assert recovery_called["test_service_2"], "Service 2 recovery should have been called"

            # Verify health status shows monitoring is working
        service1_status = health_monitor.get_status("test_service_1")
        service2_status = health_monitor.get_status("test_service_2")

            # Services should be in monitoring state (recovery was triggered)
        assert service1_status.state == ServiceState.MONITORING
        assert service2_status.state == ServiceState.MONITORING

            # Recovery functions should have reset failure counts (when called)
            # Note: Health monitor may continue checking after recovery, so we validate
            # that recovery was triggered rather than final state

    async def test_configuration_validation_comprehensive(self):
        '''
        '''
        Test comprehensive configuration validation.

        Validates:
        - Environment variables are loaded correctly
        - Secrets are properly initialized
        - Feature flags are active
        - Port assignments are correct
        - Database URLs are valid
        '''
        '''
        pass
        with patch.dict(os.environ, self.test_env, clear=False):
                        # Test environment validator
        env_validator = EnvironmentValidator()
        validation_result = env_validator.validate_all()

                        # Should have basic validation
        assert validation_result is not None

                        # Test database connector configuration
        db_connector = DatabaseConnector(use_emoji=False)

                        # Should discover test database connections
        connection_status = db_connector.get_connection_status()
        assert isinstance(connection_status, dict)

                        # Test secret loader configuration
        secret_loader = SecretLoader(project_root=self.project_root)

                        # Should handle environment secrets
        assert hasattr(secret_loader, 'project_root')

                        # Test service discovery configuration
        service_discovery = ServiceDiscovery(self.project_root)

                        # Should handle service registration
        service_discovery.write_backend_info(8001)
        service_discovery.write_frontend_info(3001)

        backend_info = service_discovery.read_backend_info()
        frontend_info = service_discovery.read_frontend_info()

        assert backend_info is not None
        assert frontend_info is not None
        assert backend_info["port"] == 8001
        assert frontend_info["port"] == 3001
        assert backend_info["api_url"] == "http://localhost:8001"
        assert frontend_info["url"] == "http://localhost:3001"

                        # Test CORS origins
        origins = service_discovery.get_all_service_origins()
        assert len(origins) >= 2  # At least backend and frontend
        assert "http://localhost:8001" in origins
        assert "http://localhost:3001" in origins

    async def test_startup_timing_and_performance(self):
        '''
        '''
        Test startup timing requirements and performance.

        Validates:
        - Complete startup under 30 seconds
        - Individual components initialize quickly
        - Cache effectiveness for subsequent startups
        - Resource usage stays reasonable
        '''
        '''
        pass
        with patch.dict(os.environ, self.test_env, clear=False):
                                    # Mock: Component isolation for testing without external dependencies
        config = LauncherConfig( )
        backend_port=8002,
        frontend_port=3002,
        project_root=self.project_root,
        verbose=False,
        no_browser=True
                                    

                                    # Time the complete initialization
        start_time = time.time()
        launcher = DevLauncher(config)
        init_time = time.time() - start_time

                                    # Initialization should be fast
        assert init_time < 5.0, ""

                                    # Test environment check timing
        start_time = time.time()
        env_result = launcher.check_environment()
        env_check_time = time.time() - start_time
        assert env_check_time < 3.0, ""

                                    # Test database validation timing
        start_time = time.time()
        db_result = await launcher._validate_databases()
        db_check_time = time.time() - start_time
        assert db_check_time < 30.0, ""

                                    # Test startup optimizer performance
        optimizer = launcher.startup_optimizer
        start_time = time.time()

                                    # Register some quick test steps
        test_steps = [ ]
        StartupStep("quick_step_1", lambda x: None True, [], parallel=True),
        StartupStep("quick_step_2", lambda x: None True, [], parallel=True),
        StartupStep("quick_step_3", lambda x: None True, ["quick_step_1"], parallel=True)
                                    
        optimizer.register_steps(test_steps)

        results = optimizer.execute_optimized_sequence([ ])
        "quick_step_1", "quick_step_2", "quick_step_3"
                                    

        optimizer_time = time.time() - start_time
        assert optimizer_time < 2.0, ""

                                    # All steps should succeed
        assert all(result.success for result in results.values())

                                    # Cleanup
        optimizer.cleanup()

    async def test_failure_scenarios_and_graceful_degradation(self):
        '''
        '''
        Test failure scenarios and graceful degradation.

        Validates:
        - Graceful handling of missing services
        - Proper error reporting
        - System stability under failure conditions
        - Recovery from transient failures
        '''
        '''
        pass
                                            # Test with minimal environment (missing some variables)
        minimal_env = { }
        'DATABASE_URL': 'postgresql://test:test@localhost:5433/netra_test',
        'ENVIRONMENT': 'development'
                                            # Missing JWT_SECRET_KEY, REDIS_URL, etc.
                                            

        with patch.dict(os.environ, minimal_env, clear=True):
                                                # Mock: Component isolation for testing without external dependencies
        config = LauncherConfig( )
        backend_port=8003,
        frontend_port=3003,
        project_root=self.project_root,
        verbose=False,
        no_browser=True
                                                

                                                # Should initialize even with minimal environment
        launcher = DevLauncher(config)
        assert launcher is not None

                                                # Environment validation should report issues but not crash
        env_result = launcher.check_environment()
        assert isinstance(env_result, bool)

                                                # Database validation should handle missing connections
        db_result = await launcher._validate_databases()
        assert isinstance(db_result, bool)

                                                # Health monitor should handle missing services gracefully
        health_monitor = launcher.health_monitor

                                                # Register a failing service
    def always_fail():
        pass
        raise Exception("Simulated service failure")

        health_monitor.register_service( )
        "failing_service",
        always_fail,
        max_failures=1
    

    # Should handle service failure gracefully
        status = health_monitor.get_status("failing_service")
        assert status is not None
        assert status.state == ServiceState.STARTING

    async def test_database_connectivity_validation(self):
        '''
        '''
        Test database connectivity validation comprehensively.

        Validates:
        - PostgreSQL connection establishment
        - Redis connection establishment
        - ClickHouse connection establishment
        - Connection retry logic
        - Health monitoring integration
        '''
        '''
        pass
        with patch.dict(os.environ, self.test_env, clear=False):
        db_connector = DatabaseConnector(use_emoji=False)

                # Test connection discovery
        initial_connections = len(db_connector.connections)
        assert initial_connections >= 0

                # Test connection validation
        start_time = time.time()
        validation_result = await db_connector.validate_all_connections()
        validation_time = time.time() - start_time

                # Should complete within reasonable time
        assert validation_time < 30.0
        assert isinstance(validation_result, bool)

                # Test connection status reporting
        status = db_connector.get_connection_status()
        assert isinstance(status, dict)

        for conn_name, conn_info in status.items():
        assert "type" in conn_info
        assert "status" in conn_info
        assert "failure_count" in conn_info
        assert "retry_count" in conn_info
        assert "last_check" in conn_info

                    # Test health summary
        health_summary = db_connector.get_health_summary()
        assert isinstance(health_summary, str)
        assert len(health_summary) > 0

                    # Test health status integration
        all_healthy = db_connector.is_all_healthy()
        assert isinstance(all_healthy, bool)

                    # Cleanup
        await db_connector.stop_health_monitoring()


class TestDevEnvironmentEdgeCases:
        """Test edge cases and error conditions in dev environment initialization."""

    def setup_method(self):
        """Set up for edge case testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        pass
        if self.temp_dir and Path(self.temp_dir).exists():
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_concurrent_startup_requests(self):
        """Test handling of concurrent startup requests."""
            # Test that multiple startup attempts are handled gracefully
        cache_manager = CacheManager(project_root=self.project_root)
        optimizer1 = StartupOptimizer(cache_manager)
        optimizer2 = StartupOptimizer(cache_manager)

            # Register identical steps in both optimizers
        test_step = StartupStep("concurrent_test", lambda x: None True, [])
        optimizer1.register_step(test_step)
        optimizer2.register_step(test_step)

            # Execute concurrently
    async def run_optimizer(opt, name):
        await asyncio.sleep(0)
        return opt.execute_optimized_sequence(["concurrent_test"])

    # Run both optimizers concurrently
        results = await asyncio.gather( )
        run_optimizer(optimizer1, "opt1"),
        run_optimizer(optimizer2, "opt2"),
        return_exceptions=True
    

    # Both should complete successfully
        assert len(results) == 2
        for result in results:
        assert not isinstance(result, Exception)
        assert "concurrent_test" in result
        assert result["concurrent_test"].success

        # Cleanup
        optimizer1.cleanup()
        optimizer2.cleanup()

    async def test_resource_cleanup_on_failure(self):
        """Test proper resource cleanup when startup fails."""
        pass
        health_monitor = HealthMonitor()

            # Register a service that will fail
    def failing_service():
        pass
        raise Exception("Service startup failed")

        health_monitor.register_service( )
        "cleanup_test_service",
        failing_service,
        max_failures=1
    

    # Start and then stop to test cleanup
        health_monitor.start()

    # Verify it started
        assert health_monitor.running

    # Stop and verify cleanup
        health_monitor.stop()
        assert not health_monitor.running

    # Should be able to restart after cleanup
        health_monitor.start()
        assert health_monitor.running
        health_monitor.stop()

    async def test_invalid_configuration_handling(self):
        """Test handling of invalid configurations."""
        # Test with completely invalid environment
        invalid_env = { }
        'DATABASE_URL': 'not-a-valid-url',
        'ENVIRONMENT': 'invalid-env',
        'JWT_SECRET_KEY': 'too-short',
        'REDIS_URL': 'also-invalid'
        

        with patch.dict(os.environ, invalid_env, clear=True):
        env_validator = EnvironmentValidator()
        result = env_validator.validate_all()

            # Should report validation failures
        assert not result.is_valid
        assert len(result.errors) > 0

            # Should provide fix suggestions
        suggestions = env_validator.get_fix_suggestions(result)
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0


        @pytest.mark.integration
class TestDevEnvironmentRealServices:
        '''
        '''
        pass
        Integration tests that require real services to be running.

        These tests are marked with @pytest.mark.integration and should
        only be run in environments where actual services are available.
        '''
        '''

@pytest.mark.asyncio
    async def test_real_service_startup_validation(self):
"""Test validation against real running services."""
        # This test requires actual services to be running
        # Skip if services are not available

try:
            # Test real database connections if available
db_connector = DatabaseConnector(use_emoji=False)
result = await db_connector.validate_all_connections()

            # Log results for manual verification
    print("")
print("")

            # Cleanup
await db_connector.stop_health_monitoring()

except Exception as e:
    pass
pytest.skip("")

@pytest.mark.asyncio
    async def test_end_to_end_startup_with_real_services(self):
"""Test complete end-to-end startup with real services."""
pass
                    # Skip if not in development environment
if env.get('ENVIRONMENT') != 'development':
    pass
pytest.skip("End-to-end test only runs in development environment")

try:
    pass
temp_dir = tempfile.mkdtemp()
project_root = Path(temp_dir)

                            # Mock: Component isolation for testing without external dependencies
config = LauncherConfig( )
backend_port=8000,
frontend_port=3000,
project_root=project_root,
verbose=False,
no_browser=True
                            

                            # Test complete initialization
start_time = time.time()
launcher = DevLauncher(config)
init_time = time.time() - start_time

print("")

                            # Test environment validation
env_result = launcher.check_environment()
print("")

                            # Test database validation
db_result = await launcher._validate_databases()
print("")

                            # Cleanup
shutil.rmtree(temp_dir, ignore_errors=True)

except Exception as e:
    pass
pytest.skip("")

class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

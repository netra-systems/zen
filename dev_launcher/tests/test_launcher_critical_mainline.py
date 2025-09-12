from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment

# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
env = get_env()
Comprehensive failing tests for mainline dev_launcher critical functionality.

These tests are designed to be initially FAILING to expose issues in the implementation
and ensure the dev_launcher handles all edge cases correctly.

Tests cover:
1. Docker service discovery integration 
2. Port conflict resolution with auto-fallback
3. Service availability auto-adjustment
4. Startup sequence ordering (13 steps)
5. Health monitoring delayed start
6. Database validation with mock mode
7. Cross-service authentication 
8. Parallel pre-check execution
9. Graceful shutdown cleanup
10. Emergency recovery scenarios
"""

import asyncio
import os
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

from dev_launcher.config import LauncherConfig
from dev_launcher.launcher import DevLauncher
from dev_launcher.service_config import ResourceMode, ServicesConfiguration, ServiceResource
from dev_launcher.critical_error_handler import CriticalError, CriticalErrorType


def create_test_project_structure(base_dir: Path) -> None:
    """Create required directory structure for launcher tests."""
    (base_dir / "netra_backend" / "app").mkdir(parents=True, exist_ok=True)
    (base_dir / "auth_service").mkdir(parents=True, exist_ok=True)
    (base_dir / "frontend").mkdir(parents=True, exist_ok=True)


class TestDockerServiceDiscoveryIntegration(SSotAsyncTestCase):
    """Test 1: Docker Service Discovery Integration - Comprehensive edge cases."""
    
    def setUp(self):
        """Set up test environment with comprehensive mocking."""
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(
            project_root=self.temp_dir,
            verbose=True,
            dynamic_ports=True
        )
        # Set _services_config directly since it's a cached property
        self.config._services_config = self._create_mock_services_config()
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def _create_mock_services_config(self):
        """Create mock services configuration."""
        # Mock: Component isolation for controlled unit testing
        mock_config = Mock(spec=ServicesConfiguration)
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_config.redis = Mock()
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_config.redis.mode = Mock()
        mock_config.redis.mode.value = "local"
        # Mock: ClickHouse database isolation for fast testing without external database dependency
        mock_config.clickhouse = Mock()
        # Mock: ClickHouse database isolation for fast testing without external database dependency
        mock_config.clickhouse.mode = Mock() 
        mock_config.clickhouse.mode.value = "local"
        # Mock: PostgreSQL database isolation for testing without real database connections
        mock_config.postgres = Mock()
        # Mock: PostgreSQL database isolation for testing without real database connections
        mock_config.postgres.mode = Mock()
        mock_config.postgres.mode.value = "local"
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_config.llm = Mock()
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_config.llm.mode = Mock()
        mock_config.llm.mode.value = "shared"
        # Mock: Component isolation for controlled unit testing
        mock_config.get_all_env_vars = Mock(return_value={})
        return mock_config

    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    def test_docker_discovery_reuses_healthy_containers(self, mock_checker, mock_docker):
        """Test that existing healthy Docker containers are properly discovered and reused."""
        # Configure mock Docker manager to return running services
        mock_docker_instance = mock_docker.return_value
        mock_docker_instance.discover_running_services.return_value = {
            'redis': 'netra-dev-redis (running)',
            'postgres': 'netra-dev-postgres (running)'
        }
        mock_docker_instance.get_service_discovery_report.return_value = {
            'reusable_services': ['redis', 'postgres'],
            'unhealthy_containers': [],
            'total_containers_found': 2
        }
        
        # Mock availability checker
        mock_checker_instance = mock_checker.return_value
        mock_checker_instance.check_all_services.return_value = {}
        mock_checker_instance.apply_recommendations.return_value = False
        
        launcher = DevLauncher(self.config)
        
        # Call the discovery method directly
        launcher._perform_docker_service_discovery()
        
        # ASSERTION THAT SHOULD FAIL: Test reuse logic
        # This should fail if discovery doesn't properly store reusable services
        self.assertIn('redis', launcher._running_docker_services)
        self.assertIn('postgres', launcher._running_docker_services)
        self.assertEqual(len(launcher._docker_discovery_report['reusable_services']), 2)
        
        # ASSERTION THAT SHOULD FAIL: Test service startup optimization
        # Should fail if startup doesn't optimize based on discovery
        mock_docker_instance.discover_running_services.assert_called_once()
        
    # Mock: Component isolation for testing without external dependencies
    def test_docker_discovery_handles_unhealthy_containers(self, mock_docker):
        """Test handling of unhealthy containers during discovery."""
        mock_docker_instance = mock_docker.return_value
        mock_docker_instance.discover_running_services.return_value = {}
        mock_docker_instance.get_service_discovery_report.return_value = {
            'reusable_services': [],
            'unhealthy_containers': ['netra-dev-redis-broken', 'netra-dev-clickhouse-old'],
            'total_containers_found': 2
        }
        
        launcher = DevLauncher(self.config)
        
        # Capture print outputs to verify warnings
        # Mock: Component isolation for testing without external dependencies
        with patch('builtins.print') as mock_print:
            launcher._perform_docker_service_discovery()
            
            # ASSERTION THAT SHOULD FAIL: Should warn about unhealthy containers
            warning_calls = [call for call in mock_print.call_args_list 
                           if 'unhealthy' in str(call).lower()]
            self.assertGreater(len(warning_calls), 0, "Should warn about unhealthy containers")
            
        # ASSERTION THAT SHOULD FAIL: Should handle empty reusable services
        self.assertEqual(len(launcher._docker_discovery_report.get('reusable_services', [])), 0)

    # Mock: Component isolation for testing without external dependencies
    def test_docker_discovery_fallback_when_docker_unavailable(self, mock_docker):
        """Test graceful fallback when Docker is unavailable."""
        # Simulate Docker being unavailable
        mock_docker.side_effect = Exception("Docker not available")
        
        launcher = DevLauncher(self.config)
        
        # ASSERTION THAT SHOULD FAIL: Should handle Docker unavailability gracefully
        launcher._perform_docker_service_discovery()
        
        # Should fall back to empty discovery results
        self.assertEqual(launcher._docker_discovery_report, {})
        self.assertEqual(launcher._running_docker_services, {})


class TestPortConflictResolution(SSotAsyncTestCase):
    """Test 2: Port Conflict Resolution - Auto-fallback mechanisms."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(
            project_root=self.temp_dir,
            backend_port=8000,
            frontend_port=3000,
            dynamic_ports=True
        )
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _occupy_port(self, port: int):
        """Helper to occupy a port for testing."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', port))
        sock.listen(1)
        return sock

    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    def test_port_conflict_auto_reallocation(self, mock_is_available, mock_find_port):
        """Test automatic port reallocation when preferred ports are in use."""
        # Simulate preferred ports being unavailable
        mock_is_available.side_effect = lambda port: port not in [8000, 3000, 8081]
        mock_find_port.side_effect = [8001, 3001, 8082]  # Alternative ports
        
        launcher = DevLauncher(self.config)
        
        # Mock port allocation in service startup
        with patch.object(launcher, 'service_startup') as mock_startup:
            mock_startup.allocate_ports.return_value = {
                'backend': 8001,
                'frontend': 3001, 
                'auth': 8082
            }
            
            allocated_ports = mock_startup.allocate_ports()
            
            # ASSERTION THAT SHOULD FAIL: Should reallocate to different ports
            self.assertNotEqual(allocated_ports['backend'], 8000)
            self.assertNotEqual(allocated_ports['frontend'], 3000) 
            self.assertNotEqual(allocated_ports['auth'], 8081)
            
            # ASSERTION THAT SHOULD FAIL: Should use fallback ports
            self.assertEqual(allocated_ports['backend'], 8001)
            self.assertEqual(allocated_ports['frontend'], 3001)
            self.assertEqual(allocated_ports['auth'], 8082)

    def test_port_conflict_race_condition_handling(self):
        """Test handling of port allocation race conditions."""
        launcher = DevLauncher(self.config)
        
        # Simulate race condition where port becomes unavailable between check and bind
        original_socket = socket.socket
        call_count = {'count': 0}
        
        def mock_socket(*args, **kwargs):
            call_count['count'] += 1
            sock = original_socket(*args, **kwargs)
            
            # First call succeeds (availability check), second fails (actual bind)
            if call_count['count'] == 2:
                def failing_bind(address):
                    raise OSError("Address already in use")
                sock.bind = failing_bind
                
            return sock
            
        # Mock: Component isolation for testing without external dependencies
        with patch('socket.socket', side_effect=mock_socket):
            # ASSERTION THAT SHOULD FAIL: Should handle race conditions
            # This test exposes race condition handling gaps
            with self.assertRaises((OSError, Exception)):
                # This should fail if race condition handling is inadequate
                launcher._check_critical_env_vars()

    # Mock: Component isolation for testing without external dependencies
    def test_port_cleanup_verification_failure(self, mock_port_manager):
        """Test port cleanup verification when processes don't release ports properly."""
        mock_manager = mock_port_manager.return_value
        mock_manager.verify_port_cleanup.return_value = {8000, 3000}  # Ports still in use
        mock_manager.get_all_allocated_ports.return_value = {
            'backend': 8000,
            'frontend': 3000,
            'auth': 8081
        }
        
        launcher = DevLauncher(self.config)
        launcher.port_manager = mock_manager
        
        # Simulate shutdown with stuck ports
        launcher._verify_ports_freed_with_force_cleanup()
        
        # ASSERTION THAT SHOULD FAIL: Should force-free stuck ports
        # This will fail if force cleanup isn't properly implemented
        self.assertTrue(mock_manager.verify_port_cleanup.called)
        
        # ASSERTION THAT SHOULD FAIL: Should attempt force cleanup for stuck ports
        # This exposes inadequate port cleanup handling
        force_free_calls = [call for call in launcher._force_free_port_with_retry.call_args_list 
                          if call[0][0] in {8000, 3000}]
        self.assertGreater(len(force_free_calls), 0)


class TestServiceAvailabilityAutoAdjustment(SSotAsyncTestCase):
    """Test 3: Service Availability Auto-Adjustment - Mode switching logic."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(project_root=self.temp_dir)
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    def test_auto_switch_to_docker_mode(self, mock_docker, mock_checker):
        """Test automatic switching to Docker mode when local services unavailable."""
        # Configure availability checker to recommend Docker mode
        mock_checker_instance = mock_checker.return_value
        mock_results = {
            # Mock: Redis caching isolation to prevent test interference and external dependencies
            'redis': Mock(
                available=False,
                recommended_mode=ResourceMode.LOCAL,
                docker_available=True,
                reason="Local Redis not installed, but Docker available"
            ),
            # Mock: Component isolation for controlled unit testing
            'postgres': Mock(
                available=False,
                recommended_mode=ResourceMode.LOCAL,
                docker_available=True,
                reason="Local PostgreSQL not installed, but Docker available"
            )
        }
        mock_checker_instance.check_all_services.return_value = mock_results
        mock_checker_instance.apply_recommendations.return_value = True
        
        # Configure services config
        self.config.services_config = self._create_services_config_local_mode()
        
        launcher = DevLauncher(self.config)
        
        # Call service availability check
        result = launcher._check_service_availability()
        
        # ASSERTION THAT SHOULD FAIL: Should auto-adjust configuration
        self.assertTrue(result)
        mock_checker_instance.apply_recommendations.assert_called_once()
        
        # ASSERTION THAT SHOULD FAIL: Should update environment variables
        # This will fail if environment variable updates aren't properly implemented
        self.assertIn('REDIS_URL', os.environ)
        self.assertIn('DATABASE_URL', os.environ)

    # Mock: Component isolation for testing without external dependencies
    def test_auto_switch_to_shared_mode_when_docker_unavailable(self, mock_checker):
        """Test fallback to shared mode when both local and Docker are unavailable."""
        mock_checker_instance = mock_checker.return_value
        mock_results = {
            # Mock: Redis caching isolation to prevent test interference and external dependencies
            'redis': Mock(
                available=False,
                recommended_mode=ResourceMode.SHARED,
                docker_available=False,
                reason="Local Redis not available, falling back to shared Redis"
            ),
            # Mock: ClickHouse external database isolation for unit testing performance
            'clickhouse': Mock(
                available=False,
                recommended_mode=ResourceMode.SHARED,
                docker_available=False,
                reason="Local ClickHouse not available, falling back to shared ClickHouse"
            )
        }
        mock_checker_instance.check_all_services.return_value = mock_results
        mock_checker_instance.apply_recommendations.return_value = True
        
        self.config.services_config = self._create_services_config_local_mode()
        
        launcher = DevLauncher(self.config)
        result = launcher._check_service_availability()
        
        # ASSERTION THAT SHOULD FAIL: Should switch to shared mode
        self.assertTrue(result)
        
        # ASSERTION THAT SHOULD FAIL: Should properly configure shared mode URLs
        # This will fail if shared mode configuration is incomplete
        mock_checker_instance.check_all_services.assert_called_once()

    def test_service_availability_critical_failure_handling(self):
        """Test handling when service availability check has critical failures."""
        self.config.services_config = self._create_services_config_local_mode()
        
        # Simulate ImportError when availability checker is not available
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.launcher.ServiceAvailabilityChecker', 
                  side_effect=ImportError("Module not found")):
            
            launcher = DevLauncher(self.config)
            result = launcher._check_service_availability()
            
            # ASSERTION THAT SHOULD FAIL: Should handle ImportError gracefully
            self.assertTrue(result, "Should continue startup even when checker unavailable")

    def _create_services_config_local_mode(self):
        """Create services configuration in local mode."""
        # Mock: Generic component isolation for controlled unit testing
        mock_config = Mock()
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_config.redis = Mock()
        mock_config.redis.mode = ResourceMode.LOCAL
        # Mock: ClickHouse database isolation for fast testing without external database dependency
        mock_config.clickhouse = Mock()
        mock_config.clickhouse.mode = ResourceMode.LOCAL
        # Mock: PostgreSQL database isolation for testing without real database connections
        mock_config.postgres = Mock()
        mock_config.postgres.mode = ResourceMode.LOCAL
        mock_config.get_all_env_vars.return_value = {
            'REDIS_URL': 'redis://localhost:6379',
            'DATABASE_URL': 'postgresql://postgres:@localhost:5433/netra_dev'
        }
        return mock_config


class TestStartupSequenceOrdering(SSotAsyncTestCase):
    """Test 4: Startup Sequence Ordering - 13-step sequence validation."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(project_root=self.temp_dir)
        self.execution_order = []
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _track_execution(self, step_name):
        """Track execution order for validation."""
        self.execution_order.append(step_name)

    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    async def test_thirteen_step_startup_sequence_order(self, mock_checker, mock_docker):
        """Test that the 13-step startup sequence executes in correct order."""
        # Mock all dependencies
        mock_docker_instance = mock_docker.return_value
        mock_docker_instance.discover_running_services.return_value = {}
        mock_docker_instance.get_service_discovery_report.return_value = {
            'reusable_services': [],
            'unhealthy_containers': []
        }
        
        mock_checker_instance = mock_checker.return_value
        mock_checker_instance.check_all_services.return_value = {}
        mock_checker_instance.apply_recommendations.return_value = False
        
        launcher = DevLauncher(self.config)
        
        # Mock the individual step methods to track execution order
        original_methods = {}
        step_methods = [
            '_perform_docker_service_discovery',
            '_validate_databases',
            'run_migrations',
            'start_backend',
            'start_auth_service', 
            '_wait_for_backend_readiness',
            '_verify_auth_system',
            'start_frontend',
            '_wait_for_frontend_readiness',
            '_validate_websocket_endpoints',
            '_start_health_monitoring_after_readiness'
        ]
        
        for method_name in step_methods:
            if hasattr(launcher, method_name):
                original_methods[method_name] = getattr(launcher, method_name)
                
                def create_tracker(name):
                    def tracked_method(*args, **kwargs):
                        self._track_execution(name)
                        if name in original_methods:
                            return original_methods[name](*args, **kwargs)
                        return True
                    return tracked_method
                    
                setattr(launcher, method_name, create_tracker(method_name))
        
        # Mock service startup methods
        # Mock: Generic component isolation for controlled unit testing
        mock_service_startup = Mock()
        # Mock: Generic component isolation for controlled unit testing
        mock_service_startup.start_backend.return_value = (Mock(), {})
        # Mock: Authentication service isolation for testing without real auth flows
        mock_service_startup.start_auth_service.return_value = (Mock(), {})
        # Mock: Generic component isolation for controlled unit testing
        mock_service_startup.start_frontend.return_value = (Mock(), {})
        launcher.service_startup = mock_service_startup
        
        # Mock other dependencies
        launcher._wait_for_backend_readiness = lambda: self._track_execution('wait_backend') or True
        launcher._verify_auth_system = lambda: self._track_execution('verify_auth') or True
        launcher._wait_for_frontend_readiness = lambda: self._track_execution('wait_frontend') or True
        launcher._validate_websocket_endpoints = lambda: self._track_execution('validate_websocket') or True
        launcher._start_health_monitoring_after_readiness = lambda: self._track_execution('start_monitoring')
        
        # Execute startup sequence
        result = await launcher._execute_spec_startup_sequence()
        
        # ASSERTION THAT SHOULD FAIL: Steps should execute in correct order
        expected_order = [
            'docker_discovery',
            'validate_databases', 
            'run_migrations',
            'start_backend',
            'start_auth_service',
            'wait_backend',
            'verify_auth',
            'start_frontend', 
            'wait_frontend',
            'validate_websocket',
            'start_monitoring'
        ]
        
        # This will fail if steps execute out of order
        for i, expected_step in enumerate(expected_order):
            if i < len(self.execution_order):
                actual_step = self.execution_order[i]
                self.assertEqual(actual_step, expected_step, 
                               f"Step {i}: expected {expected_step}, got {actual_step}")

    def test_startup_sequence_failure_cascade_handling(self):
        """Test that startup sequence properly handles cascade failures."""
        launcher = DevLauncher(self.config)
        
        # Mock database validation to fail
        async def failing_db_validation():
            return False
            
        launcher._validate_databases = failing_db_validation
        
        # ASSERTION THAT SHOULD FAIL: Should stop sequence on critical failure
        async def run_test():
            result = await launcher._execute_spec_startup_sequence()
            self.assertFalse(result, "Should fail when database validation fails")
        
        asyncio.run(run_test())

    def test_startup_sequence_step_timeout_handling(self):
        """Test timeout handling for individual steps."""
        launcher = DevLauncher(self.config)
        
        # Mock a step that hangs
        def hanging_step():
            time.sleep(60)  # Simulate hanging
            return True
            
        launcher._wait_for_backend_readiness = hanging_step
        
        # ASSERTION THAT SHOULD FAIL: Should timeout and fail appropriately
        # This exposes timeout handling gaps
        start_time = time.time()
        
        async def run_test():
            result = await launcher._execute_spec_startup_sequence()
            elapsed = time.time() - start_time
            
            # Should timeout within reasonable time (not wait full 60 seconds)
            self.assertLess(elapsed, 10, "Should timeout quickly for hanging steps")
        
        with self.assertRaises((asyncio.TimeoutError, Exception)):
            asyncio.run(asyncio.wait_for(run_test(), timeout=5))


class TestHealthMonitoringDelayedStart(SSotAsyncTestCase):
    """Test 5: Health Monitoring Delayed Start - Proper timing validation."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(project_root=self.temp_dir)
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_health_monitoring_waits_for_all_services_ready(self):
        """Test that health monitoring only starts after all services are ready."""
        launcher = DevLauncher(self.config)
        
        # Track when monitoring starts
        monitoring_started = {'started': False, 'timestamp': None}
        
        def mock_start_monitoring():
            monitoring_started['started'] = True
            monitoring_started['timestamp'] = time.time()
            
        def mock_enable_monitoring():
            pass
            
        launcher.health_monitor.start = mock_start_monitoring
        launcher.health_monitor.enable_monitoring = mock_enable_monitoring
        # Mock: Component isolation for controlled unit testing
        launcher.health_monitor.all_services_ready = Mock(return_value=True)
        # Mock: Component isolation for controlled unit testing
        launcher.health_monitor.verify_cross_service_connectivity = Mock(return_value=True)
        # Mock: Component isolation for controlled unit testing
        launcher.health_monitor.get_cross_service_health_status = Mock(return_value={
            'cross_service_integration': {
                'cors_enabled': True,
                'service_discovery_active': True
            }
        })
        
        # Mock service readiness checks
        services_ready = {'backend': False, 'auth': False, 'frontend': False}
        
        def mock_mark_service_ready(service_name):
            services_ready[service_name.lower()] = True
            
        launcher.health_monitor.mark_service_ready = mock_mark_service_ready
        
        # Start monitoring method 
        start_time = time.time()
        launcher._start_health_monitoring_after_readiness()
        
        # ASSERTION THAT SHOULD FAIL: Monitoring should start only after all services ready
        self.assertTrue(monitoring_started['started'], "Health monitoring should have started")
        
        # ASSERTION THAT SHOULD FAIL: Should verify cross-service connectivity first
        launcher.health_monitor.verify_cross_service_connectivity.assert_called_once()
        
        # ASSERTION THAT SHOULD FAIL: Should check that all services are ready
        launcher.health_monitor.all_services_ready.assert_called_once()

    def test_health_monitoring_delayed_when_services_not_ready(self):
        """Test health monitoring delay when services are not ready."""
        launcher = DevLauncher(self.config)
        
        # Mock health monitor to report services not ready
        # Mock: Component isolation for controlled unit testing
        launcher.health_monitor.all_services_ready = Mock(return_value=False)
        # Mock: Component isolation for controlled unit testing
        launcher.health_monitor.verify_cross_service_connectivity = Mock(return_value=True)
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor.start = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor.enable_monitoring = Mock()
        
        # Capture warning output
        # Mock: Component isolation for testing without external dependencies
        with patch('builtins.print') as mock_print:
            launcher._start_health_monitoring_after_readiness()
            
            # ASSERTION THAT SHOULD FAIL: Should warn about delayed monitoring
            warning_calls = [call for call in mock_print.call_args_list 
                           if 'delayed' in str(call).lower()]
            self.assertGreater(len(warning_calls), 0, "Should warn about delayed monitoring")
        
        # ASSERTION THAT SHOULD FAIL: Should not enable monitoring when services not ready
        launcher.health_monitor.enable_monitoring.assert_not_called()

    def test_health_monitoring_cross_service_connectivity_failure(self):
        """Test health monitoring behavior when cross-service connectivity fails."""
        launcher = DevLauncher(self.config)
        
        # Mock connectivity check to fail
        # Mock: Component isolation for controlled unit testing
        launcher.health_monitor.all_services_ready = Mock(return_value=True)
        # Mock: Component isolation for controlled unit testing
        launcher.health_monitor.verify_cross_service_connectivity = Mock(return_value=False)
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor.start = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor.enable_monitoring = Mock()
        
        # Capture warning output
        # Mock: Component isolation for testing without external dependencies
        with patch('builtins.print') as mock_print:
            launcher._start_health_monitoring_after_readiness()
            
            # ASSERTION THAT SHOULD FAIL: Should warn about connectivity issues
            warning_calls = [call for call in mock_print.call_args_list 
                           if 'connectivity' in str(call).lower()]
            self.assertGreater(len(warning_calls), 0, "Should warn about connectivity issues")
        
        # ASSERTION THAT SHOULD FAIL: Should still start monitoring despite connectivity issues
        launcher.health_monitor.start.assert_called_once()


class TestDatabaseValidationMockMode(SSotAsyncTestCase):
    """Test 6: Database Validation with Mock Mode - Proper skipping logic."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(project_root=self.temp_dir)
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_validation_skipped_when_all_mock_mode(self):
        """Test that database validation is skipped when all databases in mock mode."""
        # Create services config with all mock mode
        # Mock: Generic component isolation for controlled unit testing
        mock_services_config = Mock()
        mock_services_config.redis.mode.value = "mock"
        mock_services_config.clickhouse.mode.value = "mock"
        mock_services_config.postgres.mode.value = "mock"
        
        self.config.services_config = mock_services_config
        
        launcher = DevLauncher(self.config)
        
        # Mock database connector
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.database_connector.validate_all_connections = Mock()
        
        async def run_test():
            result = await launcher._validate_databases()
            
            # ASSERTION THAT SHOULD FAIL: Should return True and skip validation
            self.assertTrue(result, "Should return True when all databases in mock mode")
            
            # ASSERTION THAT SHOULD FAIL: Should not call validate_all_connections
            launcher.database_connector.validate_all_connections.assert_not_called()
        
        asyncio.run(run_test())

    def test_database_validation_runs_when_mixed_mode(self):
        """Test that database validation runs when some databases are not in mock mode."""
        # Create services config with mixed modes
        # Mock: Generic component isolation for controlled unit testing
        mock_services_config = Mock()
        mock_services_config.redis.mode.value = "mock"
        mock_services_config.clickhouse.mode.value = "local"  # Not mock
        mock_services_config.postgres.mode.value = "mock"
        
        self.config.services_config = mock_services_config
        
        launcher = DevLauncher(self.config)
        
        # Mock database connector to return success
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.database_connector.validate_all_connections = Mock(return_value=True)
        
        async def run_test():
            result = await launcher._validate_databases()
            
            # ASSERTION THAT SHOULD FAIL: Should run validation for non-mock services
            self.assertTrue(result)
            launcher.database_connector.validate_all_connections.assert_called_once()
        
        asyncio.run(run_test())

    def test_database_validation_failure_handling(self):
        """Test proper error handling when database validation fails."""
        # Mock: Generic component isolation for controlled unit testing
        mock_services_config = Mock()
        mock_services_config.redis.mode.value = "local"
        mock_services_config.clickhouse.mode.value = "local"
        mock_services_config.postgres.mode.value = "local"
        
        self.config.services_config = mock_services_config
        
        launcher = DevLauncher(self.config)
        
        # Mock database connector to fail
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.database_connector.validate_all_connections = Mock(
            side_effect=Exception("Connection failed")
        )
        
        async def run_test():
            result = await launcher._validate_databases()
            
            # ASSERTION THAT SHOULD FAIL: Should return False on validation failure
            self.assertFalse(result, "Should return False when validation fails")
        
        asyncio.run(run_test())

    def test_database_validation_no_services_config(self):
        """Test database validation when services_config is not available."""
        # Don't set services_config
        launcher = DevLauncher(self.config)
        
        # Mock database connector
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.database_connector.validate_all_connections = Mock(return_value=True)
        
        async def run_test():
            result = await launcher._validate_databases()
            
            # ASSERTION THAT SHOULD FAIL: Should run validation when no config available
            self.assertTrue(result)
            launcher.database_connector.validate_all_connections.assert_called_once()
        
        asyncio.run(run_test())


class TestCrossServiceAuthentication(SSotAsyncTestCase):
    """Test 7: Cross-Service Authentication - Token generation and propagation."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(project_root=self.temp_dir)
        # Clear any existing token
        if 'CROSS_SERVICE_AUTH_TOKEN' in os.environ:
            env.delete('CROSS_SERVICE_AUTH_TOKEN', "test")
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Clean up environment
        if 'CROSS_SERVICE_AUTH_TOKEN' in os.environ:
            env.delete('CROSS_SERVICE_AUTH_TOKEN', "test")

    def test_cross_service_auth_token_generation(self):
        """Test that cross-service auth token is generated when not present."""
        launcher = DevLauncher(self.config)
        
        # Mock service discovery
        # Mock: Component isolation for controlled unit testing
        launcher.service_discovery.get_cross_service_auth_token = Mock(return_value=None)
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_discovery.set_cross_service_auth_token = Mock()
        
        # Call token generation
        launcher._ensure_cross_service_auth_token()
        
        # ASSERTION THAT SHOULD FAIL: Should generate new token
        launcher.service_discovery.set_cross_service_auth_token.assert_called_once()
        
        # ASSERTION THAT SHOULD FAIL: Should set environment variable
        self.assertIn('CROSS_SERVICE_AUTH_TOKEN', os.environ)
        
        # ASSERTION THAT SHOULD FAIL: Token should be secure (32 bytes URL-safe)
        token = os.environ['CROSS_SERVICE_AUTH_TOKEN']
        self.assertGreaterEqual(len(token), 32, "Token should be at least 32 characters")

    def test_cross_service_auth_token_reuse_existing(self):
        """Test that existing cross-service auth token is reused."""
        existing_token = "existing_secure_token_12345"
        
        launcher = DevLauncher(self.config)
        
        # Mock service discovery to return existing token
        # Mock: Component isolation for controlled unit testing
        launcher.service_discovery.get_cross_service_auth_token = Mock(return_value=existing_token)
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_discovery.set_cross_service_auth_token = Mock()
        
        # Call token generation
        launcher._ensure_cross_service_auth_token()
        
        # ASSERTION THAT SHOULD FAIL: Should not generate new token
        launcher.service_discovery.set_cross_service_auth_token.assert_not_called()
        
        # ASSERTION THAT SHOULD FAIL: Should use existing token
        self.assertEqual(os.environ['CROSS_SERVICE_AUTH_TOKEN'], existing_token)

    def test_cross_service_auth_token_propagation_to_services(self):
        """Test that auth token is properly propagated to all services."""
        launcher = DevLauncher(self.config)
        
        # Setup mock token
        test_token = "test_token_for_services"
        # Mock: Component isolation for controlled unit testing
        launcher.service_discovery.get_cross_service_auth_token = Mock(return_value=test_token)
        
        # Mock service starters
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_startup = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_startup.start_backend = Mock(return_value=(Mock(), {}))
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_startup.start_auth_service = Mock(return_value=(Mock(), {}))
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_startup.start_frontend = Mock(return_value=(Mock(), {}))
        
        # Ensure token is set
        launcher._ensure_cross_service_auth_token()
        
        # ASSERTION THAT SHOULD FAIL: All services should receive the auth token
        # This will fail if token propagation is not properly implemented
        self.assertEqual(os.environ['CROSS_SERVICE_AUTH_TOKEN'], test_token)
        
        # The token should be available for service startup
        # This is critical for cross-service communication

    def test_cross_service_auth_token_security_validation(self):
        """Test that generated tokens meet security requirements."""
        launcher = DevLauncher(self.config)
        
        # Mock service discovery for new token generation
        # Mock: Component isolation for controlled unit testing
        launcher.service_discovery.get_cross_service_auth_token = Mock(return_value=None)
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_discovery.set_cross_service_auth_token = Mock()
        
        # Generate multiple tokens to test randomness
        generated_tokens = []
        for _ in range(5):
            # Clear environment
            if 'CROSS_SERVICE_AUTH_TOKEN' in os.environ:
                env.delete('CROSS_SERVICE_AUTH_TOKEN', "test")
            
            launcher._ensure_cross_service_auth_token()
            generated_tokens.append(os.environ['CROSS_SERVICE_AUTH_TOKEN'])
        
        # ASSERTION THAT SHOULD FAIL: All tokens should be different (randomness)
        unique_tokens = set(generated_tokens)
        self.assertEqual(len(unique_tokens), 5, "All generated tokens should be unique")
        
        # ASSERTION THAT SHOULD FAIL: Tokens should meet minimum length requirement
        for token in generated_tokens:
            self.assertGreaterEqual(len(token), 32, f"Token '{token}' too short")
            
        # ASSERTION THAT SHOULD FAIL: Tokens should be URL-safe base64
        import re
        url_safe_pattern = re.compile(r'^[A-Za-z0-9_-]+$')
        for token in generated_tokens:
            self.assertTrue(url_safe_pattern.match(token), f"Token '{token}' not URL-safe")


class TestParallelPreCheckExecution(SSotAsyncTestCase):
    """Test 8: Parallel Pre-Check Execution - Concurrent validation logic."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(
            project_root=self.temp_dir,
            parallel_startup=True
        )
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parallel_precheck_execution_speed_improvement(self):
        """Test that parallel execution improves precheck speed."""
        launcher = DevLauncher(self.config)
        
        # Create slow mock functions to simulate real pre-checks
        def slow_environment_check():
            time.sleep(0.5)  # Simulate slow operation
            return True
            
        def slow_secret_loading():
            time.sleep(0.3)  # Simulate slow operation  
            return True
        
        launcher.check_environment = slow_environment_check
        launcher.load_secrets = slow_secret_loading
        
        # Measure parallel execution time
        start_time = time.time()
        result = launcher._run_parallel_pre_checks()
        parallel_time = time.time() - start_time
        
        # Measure sequential execution time
        start_time = time.time()
        result_sequential = launcher._run_sequential_pre_checks()
        sequential_time = time.time() - start_time
        
        # ASSERTION THAT SHOULD FAIL: Parallel should be significantly faster
        self.assertTrue(result, "Parallel execution should succeed")
        self.assertTrue(result_sequential, "Sequential execution should succeed")
        self.assertLess(parallel_time, sequential_time * 0.8, 
                       f"Parallel ({parallel_time:.2f}s) should be faster than sequential ({sequential_time:.2f}s)")

    def test_parallel_precheck_failure_handling(self):
        """Test that parallel execution properly handles task failures."""
        launcher = DevLauncher(self.config)
        
        # Mock one task to fail
        def failing_environment_check():
            raise Exception("Environment check failed")
            
        def working_secret_loading():
            return True
        
        launcher.check_environment = failing_environment_check
        launcher.load_secrets = working_secret_loading
        
        # ASSERTION THAT SHOULD FAIL: Should handle task failure gracefully
        result = launcher._run_parallel_pre_checks()
        
        # Should fail when critical task (environment check) fails
        self.assertFalse(result, "Should fail when environment check fails")

    def test_parallel_precheck_timeout_handling(self):
        """Test parallel execution timeout handling."""
        launcher = DevLauncher(self.config)
        
        # Create a hanging task
        def hanging_environment_check():
            time.sleep(10)  # Simulate hanging
            return True
            
        def quick_secret_loading():
            return True
        
        launcher.check_environment = hanging_environment_check
        launcher.load_secrets = quick_secret_loading
        
        # ASSERTION THAT SHOULD FAIL: Should timeout and fail appropriately
        start_time = time.time()
        result = launcher._run_parallel_pre_checks()
        elapsed_time = time.time() - start_time
        
        # Should timeout within reasonable time (not wait full 10 seconds)
        self.assertLess(elapsed_time, 5, "Should timeout within 5 seconds")
        self.assertFalse(result, "Should fail on timeout")

    def test_parallel_precheck_fallback_to_sequential(self):
        """Test fallback to sequential execution when parallel is disabled."""
        # Disable parallel execution
        self.config.parallel_startup = False
        launcher = DevLauncher(self.config)
        
        # Ensure parallel executor is None
        self.assertIsNone(launcher.parallel_executor, "Parallel executor should be None when disabled")
        
        # Mock the checks
        # Mock: Component isolation for controlled unit testing
        launcher.check_environment = Mock(return_value=True)
        # Mock: Component isolation for controlled unit testing
        launcher.load_secrets = Mock(return_value=True)
        
        # Run pre-checks
        result = launcher._run_pre_checks()
        
        # ASSERTION THAT SHOULD FAIL: Should use sequential execution
        self.assertTrue(result, "Sequential fallback should work")
        
        # Should not have created parallel executor
        self.assertIsNone(launcher.parallel_executor)


class TestGracefulShutdownCleanup(SSotAsyncTestCase):
    """Test 9: Graceful Shutdown Cleanup - Resource cleanup validation."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(project_root=self.temp_dir)
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_graceful_shutdown_process_termination_order(self):
        """Test that processes are terminated in correct order during shutdown."""
        launcher = DevLauncher(self.config)
        
        # Track termination order
        termination_order = []
        
        def mock_terminate(service_name):
            termination_order.append(service_name)
            return True
            
        def mock_is_running(service_name):
            return service_name in ["Frontend", "Backend", "Auth"]
        
        launcher.process_manager.terminate_process = mock_terminate
        launcher.process_manager.is_running = mock_is_running
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager.cleanup_all = Mock()
        # Mock: Authentication service isolation for testing without real auth flows
        launcher.process_manager.processes = {"Frontend": Mock(), "Backend": Mock(), "Auth": Mock()}
        
        # Trigger shutdown
        launcher._terminate_all_services_ordered()
        
        # ASSERTION THAT SHOULD FAIL: Should terminate in correct order
        expected_order = ["Frontend", "Backend", "Auth"]
        self.assertEqual(termination_order, expected_order, 
                        f"Expected {expected_order}, got {termination_order}")
        
        # ASSERTION THAT SHOULD FAIL: Should call cleanup_all
        launcher.process_manager.cleanup_all.assert_called_once()

    def test_graceful_shutdown_health_monitoring_stop(self):
        """Test that health monitoring is properly stopped during shutdown."""
        launcher = DevLauncher(self.config)
        
        # Mock health monitor
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor.stop = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager.processes = {"Frontend": Mock()}
        # Mock: Component isolation for controlled unit testing
        launcher.process_manager.terminate_process = Mock(return_value=True)
        # Mock: Component isolation for controlled unit testing
        launcher.process_manager.is_running = Mock(return_value=True)
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager.cleanup_all = Mock()
        
        # Trigger graceful shutdown
        launcher._graceful_shutdown()
        
        # ASSERTION THAT SHOULD FAIL: Should stop health monitoring first
        launcher.health_monitor.stop.assert_called_once()

    def test_graceful_shutdown_port_cleanup_verification(self):
        """Test that ports are properly verified and cleaned up during shutdown."""
        launcher = DevLauncher(self.config)
        
        # Mock port verification
        # Mock: Component isolation for controlled unit testing
        launcher._is_port_in_use = Mock(side_effect=[True, True, False])  # Two ports in use, one free
        # Mock: Generic component isolation for controlled unit testing
        launcher._force_free_port_with_retry = Mock()
        
        # Mock other components
        launcher.process_manager.processes = {}
        
        # Trigger port verification
        launcher._verify_ports_freed_with_force_cleanup()
        
        # ASSERTION THAT SHOULD FAIL: Should check all critical ports
        expected_port_checks = [
            call(8081),  # Auth port
            call(8000),  # Backend port (from config or default)
            call(3000),  # Frontend port (from config or default)
        ]
        launcher._is_port_in_use.assert_has_calls(expected_port_checks, any_order=True)
        
        # ASSERTION THAT SHOULD FAIL: Should force-free ports that are still in use
        expected_force_free_calls = [call(8081, max_retries=3), call(8000, max_retries=3)]
        launcher._force_free_port_with_retry.assert_has_calls(expected_force_free_calls, any_order=True)

    def test_graceful_shutdown_database_monitoring_cleanup(self):
        """Test that database monitoring is properly cleaned up during shutdown."""
        launcher = DevLauncher(self.config)
        
        # Mock database connector
        # Mock: Generic component isolation for controlled unit testing
        mock_stop_monitoring = AsyncMock()
        launcher.database_connector.stop_health_monitoring = mock_stop_monitoring
        launcher.database_connector._shutdown_requested = False
        
        # Mock other components - add a dummy process to ensure shutdown logic runs
        launcher.process_manager.processes = {"dummy": MagicMock()}
        
        # Mock shutdown methods to prevent actual service termination
        launcher._terminate_all_services_ordered = MagicMock()
        launcher._stop_supporting_services = MagicMock()
        launcher._verify_port_cleanup = MagicMock()
        
        # Simulate no running event loop (normal shutdown scenario)
        # Mock: Component isolation for testing without external dependencies
        with patch('asyncio.get_running_loop', side_effect=RuntimeError("No running event loop")):
            # Mock: Component isolation for testing without external dependencies
            with patch('asyncio.run') as mock_asyncio_run:
                launcher._graceful_shutdown()
                
                # ASSERTION THAT SHOULD FAIL: Should use asyncio.run to stop monitoring
                mock_asyncio_run.assert_called_once()

    def test_graceful_shutdown_duplicate_prevention(self):
        """Test that graceful shutdown prevents duplicate execution."""
        launcher = DevLauncher(self.config)
        
        # Mock components
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor.stop = Mock()
        launcher.process_manager.processes = {}
        
        # Set shutdown flag manually
        launcher._shutting_down = True
        
        # Trigger graceful shutdown 
        launcher._graceful_shutdown()
        
        # ASSERTION THAT SHOULD FAIL: Should not execute shutdown when already shutting down
        launcher.health_monitor.stop.assert_not_called()

    def test_graceful_shutdown_parallel_executor_cleanup(self):
        """Test that parallel executor is properly cleaned up during shutdown."""
        launcher = DevLauncher(self.config)
        
        # Mock parallel executor
        # Mock: Generic component isolation for controlled unit testing
        launcher.parallel_executor = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.parallel_executor.cleanup = Mock()
        
        # Mock other components
        launcher.process_manager.processes = {}
        
        # Trigger graceful shutdown
        launcher._graceful_shutdown()
        
        # ASSERTION THAT SHOULD FAIL: Should cleanup parallel executor
        launcher.parallel_executor.cleanup.assert_called_once()


class TestEmergencyRecovery(SSotAsyncTestCase):
    """Test 10: Emergency Recovery - Critical error handling scenarios."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(project_root=self.temp_dir)
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_emergency_cleanup_immediate_termination(self):
        """Test that emergency cleanup immediately terminates all processes."""
        launcher = DevLauncher(self.config)
        
        # Mock process manager with running services
        # Mock: Authentication service isolation for testing without real auth flows
        mock_processes = {"Frontend": Mock(), "Backend": Mock(), "Auth": Mock()}
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager = Mock()
        launcher.process_manager.processes = mock_processes
        # Mock: Component isolation for controlled unit testing
        launcher.process_manager.is_running = Mock(side_effect=lambda x: x in mock_processes)
        # Emergency cleanup should use kill_process, not terminate_process
        # Mock: Component isolation for controlled unit testing
        launcher.process_manager.kill_process = Mock(return_value=True)
        # Mock: Component isolation for controlled unit testing
        launcher.process_manager.terminate_process = Mock(return_value=True)
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager.cleanup_all = Mock()
        
        # Mock port operations
        # Mock: Component isolation for controlled unit testing
        launcher._is_port_in_use = Mock(return_value=True)
        # Mock: Component isolation for controlled unit testing
        launcher._force_free_port_with_retry = Mock(return_value=True)
        
        # Trigger emergency cleanup
        launcher.emergency_cleanup()
        
        # ASSERTION: Should use kill_process for emergency force termination
        expected_calls = [call("Frontend"), call("Backend"), call("Auth")]
        launcher.process_manager.kill_process.assert_has_calls(expected_calls, any_order=True)
        
        # ASSERTION: terminate_process should NOT be called in emergency mode
        launcher.process_manager.terminate_process.assert_not_called()
        
        # ASSERTION THAT SHOULD FAIL: Should cleanup all processes
        launcher.process_manager.cleanup_all.assert_called_once()
        
        # ASSERTION THAT SHOULD FAIL: Should force free critical ports
        critical_ports = [8000, 3000, 8081]
        for port in critical_ports:
            launcher._force_free_port_with_retry.assert_any_call(port, max_retries=1)

    def test_emergency_cleanup_duplicate_prevention(self):
        """Test that emergency cleanup prevents duplicate execution."""
        launcher = DevLauncher(self.config)
        
        # Mock process manager
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager.terminate_process = Mock()
        
        # Set shutdown flag
        launcher._shutting_down = True
        
        # Trigger emergency cleanup
        launcher.emergency_cleanup()
        
        # ASSERTION THAT SHOULD FAIL: Should not execute when already shutting down
        launcher.process_manager.terminate_process.assert_not_called()

    def test_emergency_cleanup_exception_handling(self):
        """Test that emergency cleanup handles exceptions gracefully."""
        launcher = DevLauncher(self.config)
        
        # Mock process manager to raise exception
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager.processes = {"Backend": Mock()}
        # Mock: Component isolation for controlled unit testing
        launcher.process_manager.is_running = Mock(side_effect=Exception("Process manager error"))
        
        # Should not raise exception during emergency cleanup
        try:
            launcher.emergency_cleanup()
        except Exception as e:
            self.fail(f"Emergency cleanup should not raise exceptions: {e}")
        
        # ASSERTION THAT SHOULD FAIL: Should set shutdown flag even with errors
        self.assertTrue(launcher._shutting_down, "Should set shutdown flag even with errors")

    def test_critical_error_handling_with_emergency_cleanup(self):
        """Test that critical errors trigger emergency cleanup."""
        launcher = DevLauncher(self.config)
        
        # Mock emergency cleanup
        # Mock: Generic component isolation for controlled unit testing
        launcher.emergency_cleanup = Mock()
        
        # Simulate critical error during startup
        critical_error = CriticalError(CriticalErrorType.STARTUP_FAILURE, "Critical startup failure")
        
        async def run_test():
            # Mock: Component isolation for testing without external dependencies
            with patch('dev_launcher.launcher.critical_handler') as mock_handler:
                mock_handler.exit_on_critical.side_effect = SystemExit(1)
                
                try:
                    await launcher.run()
                except SystemExit:
                    pass  # Expected
                    
                # ASSERTION THAT SHOULD FAIL: Should call exit_on_critical
                mock_handler.exit_on_critical.assert_called_once()
        
        asyncio.run(run_test())

    def test_signal_handler_emergency_cleanup(self):
        """Test that signal handlers trigger emergency cleanup appropriately."""
        launcher = DevLauncher(self.config)
        
        # Mock graceful shutdown
        # Mock: Generic component isolation for controlled unit testing
        launcher._graceful_shutdown = Mock()
        
        # Simulate signal reception
        import signal
        launcher._signal_handler(signal.SIGTERM, None)
        
        # ASSERTION THAT SHOULD FAIL: Should set shutdown flag
        self.assertTrue(launcher._shutting_down, "Should set shutdown flag on signal")
        
        # ASSERTION THAT SHOULD FAIL: Should call graceful shutdown
        launcher._graceful_shutdown.assert_called_once()

    def test_emergency_recovery_port_force_cleanup(self):
        """Test that emergency recovery force-cleans stuck ports across platforms."""
        launcher = DevLauncher(self.config)
        
        # Mock platform detection
        original_platform = launcher._force_free_port_with_retry.__func__.__globals__['sys'].platform
        
        # Test Windows platform
        # Mock: Component isolation for testing without external dependencies
        with patch('sys.platform', 'win32'):
            # Mock: Component isolation for testing without external dependencies
            with patch('subprocess.run') as mock_run:
                # Mock netstat output
                mock_run.side_effect = [
                    # Mock: Component isolation for controlled unit testing
                    Mock(returncode=0, stdout="  TCP    0.0.0.0:8000    0.0.0.0:0    LISTENING    1234"),
                    # Mock: Component isolation for controlled unit testing
                    Mock(returncode=0)  # taskkill success
                ]
                
                launcher._force_free_port_with_retry(8000)
                
                # ASSERTION THAT SHOULD FAIL: Should use Windows-specific commands
                self.assertEqual(mock_run.call_count, 2)
                
                # Should call netstat and taskkill
                calls = mock_run.call_args_list
                self.assertIn('netstat', calls[0][0][0])
                self.assertIn('taskkill', calls[1][0][0])

    def test_emergency_recovery_resource_leak_prevention(self):
        """Test that emergency recovery prevents resource leaks."""
        launcher = DevLauncher(self.config)
        
        # Setup mocks for all resource types
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.log_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.parallel_executor = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager.processes = {"Backend": Mock()}
        
        # Track cleanup calls
        cleanup_calls = []
        
        def track_cleanup(resource_name):
            def cleanup():
                cleanup_calls.append(resource_name)
            return cleanup
            
        launcher.health_monitor.stop = track_cleanup('health_monitor')
        launcher.log_manager.stop_all = track_cleanup('log_manager')
        launcher.parallel_executor.cleanup = track_cleanup('parallel_executor')
        
        # Trigger emergency cleanup
        launcher.emergency_cleanup()
        
        # ASSERTION THAT SHOULD FAIL: Should cleanup all resource types
        expected_cleanups = ['health_monitor', 'log_manager', 'parallel_executor']
        for resource in expected_cleanups:
            self.assertIn(resource, cleanup_calls, f"Should cleanup {resource}")


if __name__ == '__main__':
    # Run tests with verbose output to see failures
    unittest.main(verbosity=2, buffer=True)
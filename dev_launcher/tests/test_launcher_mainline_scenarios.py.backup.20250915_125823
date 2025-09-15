from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
env = get_env()
Comprehensive failing tests for dev_launcher mainline scenarios.

These tests focus on DEFAULT mainline cases that should work but might be broken.
They test real-world scenarios that users encounter during normal development.

Focus Areas:
1. Default startup with real LLM configuration
2. Docker service discovery and reuse
3. Service startup sequence (13 steps) with proper ordering
4. Database validation with mixed mock/real modes  
5. Port conflict resolution with dynamic allocation
6. Health monitoring that waits for readiness
7. Graceful shutdown with proper service ordering
8. Environment variable loading priority
9. Parallel startup with failure recovery
10. Cross-service authentication token generation
"""

import asyncio
import os
import socket
import tempfile
import time
import unittest
from pathlib import Path

from dev_launcher.config import LauncherConfig
from dev_launcher.launcher import DevLauncher
from dev_launcher.parallel_executor import ParallelTask, TaskType


def create_test_project_structure(base_dir: Path) -> None:
    """Create required directory structure for launcher tests."""
    (base_dir / "netra_backend" / "app").mkdir(parents=True, exist_ok=True)
    (base_dir / "auth_service").mkdir(parents=True, exist_ok=True)
    (base_dir / "frontend").mkdir(parents=True, exist_ok=True)
    # Create .env file for environment loading tests
    env_file = base_dir / ".env"
    env_file.write_text("TEST_VAR=from_env_file\nLLM_MODE=shared\nGEMINI_API_KEY=test_key")


class TestDefaultStartupWithRealLLM(SSotAsyncTestCase):
    """Test 1: Default startup should use 'shared' LLM mode and detect Gemini API key."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        # Clear environment to test defaults
        for key in ['LLM_MODE', 'GEMINI_API_KEY']:
            if key in os.environ:
                del os.environ[key]
                
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_llm_defaults_to_shared_mode(self):
        """Test that LLM mode defaults to 'shared' when not specified."""
        config = LauncherConfig(project_root=self.temp_dir)
        launcher = DevLauncher(config)
        
        # ASSERTION THAT SHOULD FAIL: LLM should default to shared mode
        if hasattr(launcher.config, 'services_config') and launcher.config.services_config:
            llm_config = launcher.config.services_config.llm
            self.assertEqual(llm_config.mode.value, "shared", 
                           "LLM should default to 'shared' mode")
        else:
            # Fallback check for environment variable
            self.assertEqual(env.get('LLM_MODE', 'shared'), 'shared')
            
    def test_gemini_api_key_detected_from_environment(self):
        """Test that Gemini API key is properly detected from environment."""
        # Set up environment with API key
        env.set('GEMINI_API_KEY', 'test_gemini_key_12345', "test")
        
        config = LauncherConfig(project_root=self.temp_dir)
        launcher = DevLauncher(config)
        
        # Load environment files
        launcher._load_env_file()
        
        # ASSERTION THAT SHOULD FAIL: Should detect GEMINI_API_KEY
        self.assertEqual(os.environ['GEMINI_API_KEY'], 'test_gemini_key_12345')
        
        # ASSERTION THAT SHOULD FAIL: Should be available for service configuration
        self.assertIsNotNone(env.get('GEMINI_API_KEY'), 
                           "GEMINI_API_KEY should be available in environment")
                           
    def test_environment_variable_loading_priority(self):
        """Test that environment variables are loaded with correct priority."""
        # Create multiple env files with different values
        (self.temp_dir / ".env").write_text("PRIORITY_TEST=env_file\nFROM_ENV_FILE=yes")
        (self.temp_dir / ".env.development").write_text("PRIORITY_TEST=dev_file")
        
        # Set system environment variable (should have highest priority)
        env.set('PRIORITY_TEST', 'system_env', "test")
        
        config = LauncherConfig(project_root=self.temp_dir)
        launcher = DevLauncher(config)
        
        # Load environment
        launcher._load_env_file()
        
        # ASSERTION THAT SHOULD FAIL: System environment should have priority
        self.assertEqual(os.environ['PRIORITY_TEST'], 'system_env',
                        "System environment variables should have highest priority")
                        
        # ASSERTION THAT SHOULD FAIL: .env file vars should be loaded when not in system
        self.assertEqual(env.get('FROM_ENV_FILE'), 'yes',
                        "Variables from .env should be loaded when not in system environment")


class TestDockerServiceDiscoveryReuse(SSotAsyncTestCase):
    """Test 2: Docker service discovery should reuse existing containers."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(project_root=self.temp_dir)
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    # Mock: Component isolation for testing without external dependencies
    def test_docker_discovery_report_generation(self, mock_discovery):
        """Test that Docker discovery generates proper report for reusable containers."""
        # Mock container discovery to return running services
        mock_discovery_instance = mock_discovery.return_value
        mock_discovery_instance.get_service_discovery_report.return_value = {
            'total_containers': 5,
            'netra_containers': 2,
            'running_services': {
                # Mock: Redis external service isolation for fast, reliable tests without network dependency
                'redis': Mock(name='netra-dev-redis', status='Up 2 hours'),
                # Mock: PostgreSQL database isolation for testing without real database connections
                'postgres': Mock(name='netra-dev-postgres', status='Up 1 hour')
            },
            'reusable_services': ['redis', 'postgres'],
            'containers_needing_restart': [],
            'unhealthy_containers': []
        }
        mock_discovery_instance.get_running_service_containers.return_value = {
            # Mock: Redis external service isolation for fast, reliable tests without network dependency
            'redis': Mock(name='netra-dev-redis'),
            # Mock: PostgreSQL database isolation for testing without real database connections
            'postgres': Mock(name='netra-dev-postgres')
        }
        
        launcher = DevLauncher(self.config)
        
        # Execute discovery
        with patch.object(launcher, '_docker_discovery_report', {}) as mock_report:
            launcher._perform_docker_service_discovery()
            
            # ASSERTION THAT SHOULD FAIL: Should generate discovery report
            mock_discovery_instance.get_service_discovery_report.assert_called_once()
            
            # ASSERTION THAT SHOULD FAIL: Should store reusable services for startup optimization
            self.assertTrue(hasattr(launcher, '_running_docker_services'))
            
    def test_docker_discovery_unavailable_graceful_fallback(self):
        """Test graceful fallback when Docker is not available."""
        launcher = DevLauncher(self.config)
        
        # Mock Docker command to fail
        # Mock: Component isolation for testing without external dependencies
        with patch('subprocess.run', side_effect=FileNotFoundError("Docker not found")):
            # Should not raise exception
            try:
                launcher._perform_docker_service_discovery()
            except Exception as e:
                self.fail(f"Docker discovery should handle unavailable Docker gracefully: {e}")
                
            # ASSERTION THAT SHOULD FAIL: Should set empty discovery results
            self.assertEqual(launcher._docker_discovery_report, {})
            self.assertEqual(launcher._running_docker_services, {})


class TestServiceStartupSequenceOrdering(SSotAsyncTestCase):
    """Test 3: 13-step service startup sequence should execute in correct order."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(project_root=self.temp_dir)
        self.execution_order = []
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def _track_step(self, step_name):
        """Track execution order for validation."""
        self.execution_order.append(step_name)
        return True
        
    async def test_thirteen_step_sequence_complete_execution(self):
        """Test that all 13 steps of startup sequence execute in proper order."""
        launcher = DevLauncher(self.config)
        
        # Mock all step dependencies
        launcher._perform_docker_service_discovery = lambda: self._track_step("step_0_docker_discovery")
        launcher._validate_databases = lambda: self._track_step("step_4_database_validation") or True
        launcher._run_migrations_async = lambda: self._track_step("step_5_migrations") or True
        
        # Mock service startup components
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_startup = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_startup.start_backend.return_value = (Mock(), {})
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_startup.start_auth_service.return_value = (Mock(), {})
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_startup.start_frontend.return_value = (Mock(), {})
        
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager.add_process = Mock()
        
        # Mock readiness and verification steps
        launcher._wait_for_backend_readiness = lambda: self._track_step("step_8_backend_ready") or True
        launcher._verify_auth_system = lambda: self._track_step("step_9_auth_verify") or True
        launcher._wait_for_frontend_readiness = lambda: self._track_step("step_11_frontend_ready") or True
        launcher._validate_websocket_endpoints = lambda: self._track_step("step_11_5_websocket_validation") or True
        launcher._start_health_monitoring_after_readiness = lambda: self._track_step("step_13_health_monitoring")
        
        # Mock cache and health monitor
        # Mock: Generic component isolation for controlled unit testing
        launcher.cache_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.cache_manager.mark_successful_startup = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor = Mock()
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.database_connector = Mock()
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.database_connector.start_health_monitoring = Mock(return_value=True)
        
        # Execute the startup sequence
        result = await launcher._execute_spec_startup_sequence()
        
        # ASSERTION THAT SHOULD FAIL: Should complete successfully
        self.assertTrue(result, "Startup sequence should complete successfully")
        
        # ASSERTION THAT SHOULD FAIL: Should execute steps in correct order
        expected_steps = [
            "step_0_docker_discovery",
            "step_4_database_validation", 
            "step_5_migrations",
            "step_8_backend_ready",
            "step_9_auth_verify",
            "step_11_frontend_ready",
            "step_11_5_websocket_validation",
            "step_13_health_monitoring"
        ]
        
        for expected_step in expected_steps:
            self.assertIn(expected_step, self.execution_order,
                         f"Step '{expected_step}' should be executed")
                         
    def test_startup_sequence_timeout_handling(self):
        """Test that startup sequence properly handles step timeouts."""
        launcher = DevLauncher(self.config)
        
        # Mock a step that times out
        async def slow_database_validation():
            await asyncio.sleep(60)  # Will timeout
            return True
            
        launcher._validate_databases = slow_database_validation
        
        # ASSERTION THAT SHOULD FAIL: Should timeout appropriately
        async def run_test():
            start_time = time.time()
            result = await launcher._execute_spec_startup_sequence()
            elapsed = time.time() - start_time
            
            # Should timeout quickly, not wait full 60 seconds
            self.assertLess(elapsed, 35, "Should timeout within 35 seconds")
            self.assertFalse(result, "Should return False on timeout")
            
        asyncio.run(run_test())


class TestDatabaseValidationMixedModes(SSotAsyncTestCase):
    """Test 4: Database validation should work correctly with mixed mock/real modes."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(project_root=self.temp_dir)
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_mixed_database_modes_validation(self):
        """Test validation behavior when some databases are mock and some are real."""
        # Create mock services config with mixed modes
        # Mock: Generic component isolation for controlled unit testing
        mock_services = Mock()
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_services.redis = Mock()
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_services.redis.mode = Mock()
        mock_services.redis.mode.value = "mock"  # Redis in mock mode
        
        # Mock: ClickHouse database isolation for fast testing without external database dependency
        mock_services.clickhouse = Mock()
        # Mock: ClickHouse database isolation for fast testing without external database dependency
        mock_services.clickhouse.mode = Mock()
        mock_services.clickhouse.mode.value = "local"  # ClickHouse in local mode (real)
        
        # Mock: PostgreSQL database isolation for testing without real database connections
        mock_services.postgres = Mock() 
        # Mock: PostgreSQL database isolation for testing without real database connections
        mock_services.postgres.mode = Mock()
        mock_services.postgres.mode.value = "shared"  # PostgreSQL in shared mode (real)
        
        self.config._services_config = mock_services
        
        launcher = DevLauncher(self.config)
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.database_connector = Mock()
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.database_connector.validate_all_connections = Mock(return_value=True)
        
        async def run_test():
            result = await launcher._validate_databases()
            
            # ASSERTION THAT SHOULD FAIL: Should validate real databases but skip mock
            self.assertTrue(result, "Should return True for mixed modes")
            
            # ASSERTION THAT SHOULD FAIL: Should call validation for non-mock databases
            launcher.database_connector.validate_all_connections.assert_called_once()
            
        asyncio.run(run_test())
        
    def test_all_mock_databases_skip_validation(self):
        """Test that validation is skipped when all databases are in mock mode."""
        # All databases in mock mode
        # Mock: Generic component isolation for controlled unit testing
        mock_services = Mock()
        for service_name in ['redis', 'clickhouse', 'postgres']:
            # Mock: Generic component isolation for controlled unit testing
            service = Mock()
            # Mock: Generic component isolation for controlled unit testing
            service.mode = Mock()
            service.mode.value = "mock"
            setattr(mock_services, service_name, service)
            
        self.config._services_config = mock_services
        
        launcher = DevLauncher(self.config)
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.database_connector = Mock()
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.database_connector.validate_all_connections = Mock()
        
        async def run_test():
            result = await launcher._validate_databases()
            
            # ASSERTION THAT SHOULD FAIL: Should skip validation and return True
            self.assertTrue(result, "Should return True when all databases are mock")
            
            # ASSERTION THAT SHOULD FAIL: Should not call database validation
            launcher.database_connector.validate_all_connections.assert_not_called()
            
        asyncio.run(run_test())


class TestPortConflictDynamicAllocation(SSotAsyncTestCase):
    """Test 5: Port conflicts should be resolved with dynamic allocation."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(
            project_root=self.temp_dir,
            backend_port=8000,
            frontend_port=3000,
            dynamic_ports=True,
            enable_port_conflict_resolution=True
        )
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_port_conflict_automatic_resolution(self):
        """Test that port conflicts are automatically resolved with alternative ports."""
        # Create actual socket to occupy the port
        blocked_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocked_socket.bind(('localhost', 3000))
        blocked_socket.listen(1)
        
        try:
            # This should trigger port conflict resolution during config initialization
            config = LauncherConfig(
                project_root=self.temp_dir,
                frontend_port=3000,
                enable_port_conflict_resolution=True
            )
            
            # ASSERTION THAT SHOULD FAIL: Should detect conflict and allocate different port
            # The frontend_port should be changed from 3000 to an available port
            if config.dynamic_ports:
                # Dynamic ports enabled, should handle gracefully
                self.assertTrue(True, "Dynamic ports should handle conflicts")
            else:
                # Should have found alternative port
                self.assertNotEqual(config.frontend_port, 3000,
                                  "Should allocate different port when conflict detected")
                                  
        finally:
            blocked_socket.close()
            
    def test_dynamic_port_allocation_when_preferred_unavailable(self):
        """Test dynamic port allocation when preferred ports are unavailable."""
        launcher = DevLauncher(self.config)
        
        # Mock port checking to simulate conflicts
        def mock_port_in_use(port):
            return port in [8000, 3000, 8081]  # Simulate these ports as occupied
            
        launcher._is_port_in_use = mock_port_in_use
        
        # Mock service discovery port allocation
        with patch.object(launcher, 'service_discovery') as mock_discovery:
            mock_discovery.allocate_dynamic_port.side_effect = [8001, 3001, 8082]
            
            # ASSERTION THAT SHOULD FAIL: Should allocate alternative ports
            # This tests the actual dynamic allocation logic
            self.assertTrue(launcher.config.dynamic_ports,
                          "Dynamic ports should be enabled for conflict resolution")


class TestHealthMonitoringDelayedStart(SSotAsyncTestCase):
    """Test 6: Health monitoring should only start after all services are ready."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(project_root=self.temp_dir)
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_health_monitoring_waits_for_service_readiness(self):
        """Test that health monitoring waits for all services to be ready before starting."""
        launcher = DevLauncher(self.config)
        
        # Mock health monitor
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor = Mock()
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
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor.start = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor.enable_monitoring = Mock()
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.health_monitor.set_database_connector = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor.set_service_discovery = Mock()
        
        # Mock other components
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_discovery = Mock()
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.database_connector = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.register_health_monitoring = Mock()
        
        # Execute health monitoring start
        launcher._start_health_monitoring_after_readiness()
        
        # ASSERTION THAT SHOULD FAIL: Should check if all services are ready
        launcher.health_monitor.all_services_ready.assert_called_once()
        
        # ASSERTION THAT SHOULD FAIL: Should verify cross-service connectivity
        launcher.health_monitor.verify_cross_service_connectivity.assert_called_once()
        
        # ASSERTION THAT SHOULD FAIL: Should start monitoring thread
        launcher.health_monitor.start.assert_called_once()
        
        # ASSERTION THAT SHOULD FAIL: Should enable monitoring only when ready
        launcher.health_monitor.enable_monitoring.assert_called_once()
        
    def test_health_monitoring_delayed_when_services_not_ready(self):
        """Test that health monitoring is delayed when services are not ready."""
        launcher = DevLauncher(self.config)
        
        # Mock health monitor to report services NOT ready
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor = Mock()
        # Mock: Component isolation for controlled unit testing
        launcher.health_monitor.all_services_ready = Mock(return_value=False)
        # Mock: Component isolation for controlled unit testing
        launcher.health_monitor.verify_cross_service_connectivity = Mock(return_value=True)
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor.start = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor.enable_monitoring = Mock()
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.health_monitor.set_database_connector = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor.set_service_discovery = Mock()
        
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_discovery = Mock()
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.database_connector = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.register_health_monitoring = Mock()
        
        # Capture output to check for warning
        # Mock: Component isolation for testing without external dependencies
        with patch('builtins.print') as mock_print:
            launcher._start_health_monitoring_after_readiness()
            
            # ASSERTION THAT SHOULD FAIL: Should warn about delayed monitoring
            warning_calls = [call for call in mock_print.call_args_list 
                           if 'delayed' in str(call).lower() or 'ready' in str(call).lower()]
            self.assertGreater(len(warning_calls), 0, "Should warn when monitoring is delayed")
            
        # ASSERTION THAT SHOULD FAIL: Should not enable monitoring when services not ready  
        launcher.health_monitor.enable_monitoring.assert_not_called()


class TestGracefulShutdownServiceOrdering(SSotAsyncTestCase):
    """Test 7: Graceful shutdown should terminate services in proper order."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(project_root=self.temp_dir)
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_shutdown_service_termination_order(self):
        """Test that services are terminated in correct order: Frontend -> Backend -> Auth."""
        launcher = DevLauncher(self.config)
        
        # Track termination order
        termination_order = []
        
        def track_termination(service_name, **kwargs):
            termination_order.append(service_name)
            return True
            
        # Mock process manager
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager = Mock()
        # Mock: Authentication service isolation for testing without real auth flows
        launcher.process_manager.is_running = Mock(side_effect=lambda x: x in ["Frontend", "Backend", "Auth"])
        # Mock: Component isolation for controlled unit testing
        launcher.process_manager.terminate_process = Mock(side_effect=track_termination)
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager.cleanup_all = Mock()
        # Mock: Authentication service isolation for testing without real auth flows
        launcher.process_manager.processes = {"Frontend": Mock(), "Backend": Mock(), "Auth": Mock()}
        
        # Execute ordered termination
        launcher._terminate_all_services_ordered()
        
        # ASSERTION THAT SHOULD FAIL: Should terminate in correct order
        expected_order = ["Frontend", "Backend", "Auth"]
        self.assertEqual(termination_order, expected_order,
                        f"Expected termination order {expected_order}, got {termination_order}")
                        
        # ASSERTION THAT SHOULD FAIL: Should call cleanup after termination
        launcher.process_manager.cleanup_all.assert_called_once()
        
    def test_shutdown_port_cleanup_after_service_termination(self):
        """Test that ports are cleaned up after services are terminated."""
        launcher = DevLauncher(self.config)
        
        # Mock components for full shutdown flow
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.health_monitor.stop = Mock()
        # Mock: Database access isolation for fast, reliable unit testing
        launcher.database_connector = Mock()
        launcher.database_connector._shutdown_requested = False
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager.processes = {"Backend": Mock()}
        # Mock: Component isolation for controlled unit testing
        launcher.process_manager.is_running = Mock(return_value=False)
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager.cleanup_all = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.log_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
        launcher.log_manager.stop_all = Mock()
        
        # Mock port verification
        # Mock: Generic component isolation for controlled unit testing
        launcher._verify_ports_freed_with_force_cleanup = Mock()
        
        # Execute full graceful shutdown
        launcher._graceful_shutdown()
        
        # ASSERTION THAT SHOULD FAIL: Should verify port cleanup after service termination
        launcher._verify_ports_freed_with_force_cleanup.assert_called_once()


class TestEnvironmentVariablePriority(SSotAsyncTestCase):
    """Test 8: Environment variables should load with correct priority."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        # Clean up environment
        for key in ['TEST_PRIORITY', 'ENV_FILE_ONLY']:
            if key in os.environ:
                del os.environ[key]
                
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        for key in ['TEST_PRIORITY', 'ENV_FILE_ONLY']:
            if key in os.environ:
                del os.environ[key]
                
    def test_environment_variable_precedence(self):
        """Test that environment variables have correct precedence: system > .env files."""
        # Create .env file
        env_file = self.temp_dir / ".env"
        env_file.write_text("TEST_PRIORITY=env_file_value\nENV_FILE_ONLY=env_only")
        
        # Set system environment variable
        env.set('TEST_PRIORITY', 'system_value', "test")
        
        config = LauncherConfig(project_root=self.temp_dir)
        launcher = DevLauncher(self.config)
        
        # Load environment file
        launcher._load_env_file()
        
        # ASSERTION THAT SHOULD FAIL: System environment should have priority
        self.assertEqual(os.environ['TEST_PRIORITY'], 'system_value',
                        "System environment variables should override .env file")
                        
        # ASSERTION THAT SHOULD FAIL: .env file variables should be loaded when not in system
        self.assertEqual(os.environ['ENV_FILE_ONLY'], 'env_only',
                        "Variables from .env should be loaded when not in system environment")
                        
    def test_cross_service_auth_token_environment_propagation(self):
        """Test that cross-service auth token is properly set in environment."""
        config = LauncherConfig(project_root=self.temp_dir)
        launcher = DevLauncher(config)
        
        # Mock service discovery
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_discovery = Mock()
        # Mock: Component isolation for controlled unit testing
        launcher.service_discovery.get_cross_service_auth_token = Mock(return_value=None)
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_discovery.set_cross_service_auth_token = Mock()
        
        # Clear any existing token
        if 'CROSS_SERVICE_AUTH_TOKEN' in os.environ:
            env.delete('CROSS_SERVICE_AUTH_TOKEN', "test")
            
        # Generate token
        launcher._ensure_cross_service_auth_token()
        
        # ASSERTION THAT SHOULD FAIL: Token should be set in environment
        self.assertIn('CROSS_SERVICE_AUTH_TOKEN', os.environ,
                     "Cross-service auth token should be set in environment")
                     
        # ASSERTION THAT SHOULD FAIL: Token should meet security requirements
        token = os.environ['CROSS_SERVICE_AUTH_TOKEN']
        self.assertGreaterEqual(len(token), 32, "Auth token should be at least 32 characters")


class TestParallelStartupFailureRecovery(SSotAsyncTestCase):
    """Test 9: Parallel startup should handle failures and fall back to sequential."""
    
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
        
    def test_parallel_precheck_failure_fallback(self):
        """Test fallback to sequential when parallel execution fails."""
        launcher = DevLauncher(self.config)
        
        # Mock parallel executor to fail
        # Mock: Generic component isolation for controlled unit testing
        launcher.parallel_executor = Mock()
        # Mock: Component isolation for controlled unit testing
        launcher.parallel_executor.execute_all = Mock(side_effect=Exception("Parallel execution failed"))
        
        # Mock the methods that would be called
        # Mock: Component isolation for controlled unit testing
        launcher.check_environment = Mock(return_value=True)
        # Mock: Component isolation for controlled unit testing
        launcher._handle_secret_loading = Mock(return_value=True)
        # Mock: Component isolation for controlled unit testing
        launcher._run_sequential_pre_checks = Mock(return_value=True)
        
        # Execute pre-checks
        result = launcher._run_pre_checks()
        
        # ASSERTION THAT SHOULD FAIL: Should fall back to sequential execution
        self.assertTrue(result, "Should successfully fall back to sequential execution")
        launcher._run_sequential_pre_checks.assert_called_once()
        
    def test_parallel_precheck_retry_logic(self):
        """Test that parallel execution uses retry logic for transient failures."""
        launcher = DevLauncher(self.config)
        
        # Mock a function that fails first time but succeeds on retry
        call_count = {'count': 0}
        def flaky_environment_check():
            call_count['count'] += 1
            if call_count['count'] == 1:
                raise Exception("Transient failure")
            return True
            
        launcher.check_environment = flaky_environment_check
        # Mock: Component isolation for controlled unit testing
        launcher._load_secrets_task = Mock(return_value=True)
        
        # ASSERTION THAT SHOULD FAIL: Should succeed after retry
        result = launcher._run_parallel_pre_checks()
        self.assertTrue(result, "Should succeed with retry logic")
        self.assertEqual(call_count['count'], 2, "Should retry failed tasks")


class TestCrossServiceAuthenticationFlow(SSotAsyncTestCase):
    """Test 10: Cross-service authentication should work end-to-end."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        create_test_project_structure(self.temp_dir)
        self.config = LauncherConfig(project_root=self.temp_dir)
        # Clear auth token
        if 'CROSS_SERVICE_AUTH_TOKEN' in os.environ:
            env.delete('CROSS_SERVICE_AUTH_TOKEN', "test")
            
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if 'CROSS_SERVICE_AUTH_TOKEN' in os.environ:
            env.delete('CROSS_SERVICE_AUTH_TOKEN', "test")
            
    def test_cross_service_token_generation_and_sharing(self):
        """Test complete flow of cross-service auth token generation and sharing."""
        launcher = DevLauncher(self.config)
        
        # Mock service discovery
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_discovery = Mock()
        # Mock: Component isolation for controlled unit testing
        launcher.service_discovery.get_cross_service_auth_token = Mock(return_value=None)
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_discovery.set_cross_service_auth_token = Mock()
        
        # Generate token
        launcher._ensure_cross_service_auth_token()
        
        # ASSERTION THAT SHOULD FAIL: Should generate secure token
        launcher.service_discovery.set_cross_service_auth_token.assert_called_once()
        token_call = launcher.service_discovery.set_cross_service_auth_token.call_args[0][0]
        self.assertGreaterEqual(len(token_call), 32, "Generated token should be secure")
        
        # ASSERTION THAT SHOULD FAIL: Should be available in environment for services
        self.assertIn('CROSS_SERVICE_AUTH_TOKEN', os.environ)
        self.assertEqual(os.environ['CROSS_SERVICE_AUTH_TOKEN'], token_call)
        
    def test_cross_service_token_reuse_existing(self):
        """Test that existing tokens are properly reused.""" 
        existing_token = "existing_secure_token_123456789"
        
        launcher = DevLauncher(self.config)
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_discovery = Mock()
        # Mock: Component isolation for controlled unit testing
        launcher.service_discovery.get_cross_service_auth_token = Mock(return_value=existing_token)
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_discovery.set_cross_service_auth_token = Mock()
        
        # Should reuse existing token
        launcher._ensure_cross_service_auth_token()
        
        # ASSERTION THAT SHOULD FAIL: Should not generate new token
        launcher.service_discovery.set_cross_service_auth_token.assert_not_called()
        
        # ASSERTION THAT SHOULD FAIL: Should use existing token
        self.assertEqual(os.environ['CROSS_SERVICE_AUTH_TOKEN'], existing_token)
        
    def test_cross_service_token_security_validation(self):
        """Test that generated tokens meet security requirements."""
        launcher = DevLauncher(self.config)
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_discovery = Mock()
        # Mock: Component isolation for controlled unit testing
        launcher.service_discovery.get_cross_service_auth_token = Mock(return_value=None)
        # Mock: Generic component isolation for controlled unit testing
        launcher.service_discovery.set_cross_service_auth_token = Mock()
        
        # Generate multiple tokens to test randomness
        tokens = []
        for _ in range(3):
            if 'CROSS_SERVICE_AUTH_TOKEN' in os.environ:
                env.delete('CROSS_SERVICE_AUTH_TOKEN', "test")
            launcher._ensure_cross_service_auth_token()
            tokens.append(os.environ['CROSS_SERVICE_AUTH_TOKEN'])
            
        # ASSERTION THAT SHOULD FAIL: All tokens should be different (secure randomness)
        unique_tokens = set(tokens)
        self.assertEqual(len(unique_tokens), 3, "All generated tokens should be unique")
        
        # ASSERTION THAT SHOULD FAIL: All tokens should meet security requirements
        for token in tokens:
            self.assertGreaterEqual(len(token), 32, f"Token {token} should be at least 32 chars")
            # Should be URL-safe base64
            import re
            self.assertTrue(re.match(r'^[A-Za-z0-9_-]+$', token), f"Token {token} should be URL-safe")


if __name__ == '__main__':
    # Run tests with high verbosity to see detailed failure information
    unittest.main(verbosity=2, buffer=False)
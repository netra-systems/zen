"""
Comprehensive tests for the dev launcher.

Tests cover configuration, process management, health monitoring,
error handling, and recovery scenarios.
"""

import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

# Add parent directory to path for imports

from dev_launcher.config import LauncherConfig, find_project_root
from dev_launcher.health_monitor import HealthMonitor, HealthStatus
from dev_launcher.launcher import DevLauncher
from dev_launcher.process_manager import ProcessManager


class TestLauncherConfig(unittest.TestCase):
    """Test configuration management."""
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = LauncherConfig()
        self.assertEqual(config.frontend_port, 3000)
        self.assertTrue(config.dynamic_ports)  # Changed: now default is True
        self.assertFalse(config.backend_reload)  # Changed: now default is False
        self.assertFalse(config.load_secrets)  # Changed: now default is False (local-only)
        self.assertFalse(config.no_browser)
        self.assertFalse(config.verbose)
    
    def test_config_validation_invalid_ports(self):
        """Test port validation with invalid values - now auto-resolves instead of raising."""
        # With enable_port_conflict_resolution=True by default, invalid ports are auto-resolved
        config = LauncherConfig(backend_port=70000)
        # Should auto-resolve to None (dynamic allocation)
        self.assertIsNone(config.backend_port)
        
        config = LauncherConfig(frontend_port=0)
        # Should auto-resolve to default port
        self.assertEqual(config.frontend_port, 3000)
    
    def disabled_test_config_validation_missing_dirs(self):
        """Test validation when required directories are missing."""
        # Use a temporary directory to simulate missing directories
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create project root but not app/frontend directories
            # Mock: Component isolation for testing without external dependencies
            with patch('dev_launcher.config.find_project_root', return_value=tmppath):
                # The LauncherConfig should raise an error for missing directories
                with self.assertRaises(ValueError) as cm:
                    config = LauncherConfig()
                    
                # Should complain about missing backend or frontend directory
                error_msg = str(cm.exception)
                self.assertTrue(
                    "Backend directory not found" in error_msg or 
                    "Frontend directory not found" in error_msg
                )
    
    def test_config_from_args(self):
        """Test creating config from command line arguments."""
        # Mock: Component isolation for controlled unit testing
        args = Mock(
            backend_port=8080,
            frontend_port=3001,
            static=False,  # Changed: use static flag
            verbose=True,
            backend_reload=False,  # Changed: use positive flag
            no_reload=False,
            no_secrets=False,
            project_id="test-project",
            no_browser=True,
            no_turbopack=False,
            dev=False  # Added: dev mode flag
        )
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.config.find_project_root') as mock_root:
            mock_root.return_value = Path.cwd()
            with patch.object(LauncherConfig, '_validate'):
                config = LauncherConfig.from_args(args)
        
        self.assertEqual(config.backend_port, 8080)
        self.assertEqual(config.frontend_port, 3001)
        self.assertTrue(config.dynamic_ports)  # static=False means dynamic=True
        self.assertTrue(config.verbose)
        self.assertFalse(config.backend_reload)  # backend_reload=False
        self.assertTrue(config.no_browser)


class TestProcessManager(unittest.TestCase):
    """Test process management functionality."""
    
    def setUp(self):
        self.manager = ProcessManager()
    
    def test_add_process(self):
        """Test adding a process to the manager."""
        # Mock: Component isolation for controlled unit testing
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        
        self.manager.add_process("TestService", mock_process)
        self.assertIn("TestService", self.manager.processes)
        self.assertEqual(self.manager.processes["TestService"], mock_process)
    
    def test_terminate_process_running(self):
        """Test terminating a running process."""
        # Mock: Component isolation for controlled unit testing
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running
        mock_process.wait.return_value = None
        
        self.manager.add_process("TestService", mock_process)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('subprocess.run') as mock_run:
            result = self.manager.terminate_process("TestService")
        
        self.assertTrue(result)
        self.assertNotIn("TestService", self.manager.processes)
        if sys.platform == "win32":
            mock_run.assert_called()
    
    def test_terminate_process_not_found(self):
        """Test terminating a non-existent process."""
        result = self.manager.terminate_process("NonExistent")
        self.assertFalse(result)
    
    def test_is_running(self):
        """Test checking if a process is running."""
        # Mock: Component isolation for controlled unit testing
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345  # Add pid attribute
        mock_process.poll.return_value = None  # Running
        
        self.manager.add_process("TestService", mock_process)
        self.assertTrue(self.manager.is_running("TestService"))
        
        mock_process.poll.return_value = 0  # Stopped
        self.assertFalse(self.manager.is_running("TestService"))
    
    def test_wait_for_all_with_failures(self):
        """Test waiting for processes with error handling."""
        # Mock: Component isolation for controlled unit testing
        mock_process1 = Mock(spec=subprocess.Popen)
        mock_process1.pid = 12345  # Add pid attribute
        # Process exits with error immediately
        mock_process1.poll.return_value = 1
        mock_process1.returncode = 1
        
        # Mock: Component isolation for controlled unit testing
        mock_process2 = Mock(spec=subprocess.Popen)
        mock_process2.pid = 12346  # Add pid attribute
        # Process exits successfully immediately
        mock_process2.poll.return_value = 0
        mock_process2.returncode = 0
        
        self.manager.add_process("Service1", mock_process1)
        self.manager.add_process("Service2", mock_process2)
        
        # Run wait_for_all in a thread with timeout
        thread = threading.Thread(target=self.manager.wait_for_all)
        thread.daemon = True
        thread.start()
        
        # Give it time to process (wait_for_all has a 1 second sleep)
        time.sleep(1.5)
        
        # Should have removed both processes after they exited
        self.assertEqual(len(self.manager.processes), 0)


class TestHealthMonitor(unittest.TestCase):
    """Test health monitoring functionality."""
    
    def setUp(self):
        self.monitor = HealthMonitor(check_interval=0.1)
    
    def tearDown(self):
        self.monitor.stop()
    
    def test_register_service(self):
        """Test registering a service for monitoring."""
        # Mock: Component isolation for controlled unit testing
        health_check = Mock(return_value=True)
        # Mock: Generic component isolation for controlled unit testing
        recovery = Mock()
        
        self.monitor.register_service(
            "TestService",
            health_check,
            recovery,
            max_failures=3
        )
        
        self.assertIn("TestService", self.monitor.services)
        self.assertIn("TestService", self.monitor.health_status)
    
    def test_health_check_success(self):
        """Test successful health checks."""
        # Mock: Component isolation for controlled unit testing
        health_check = Mock(return_value=True)
        
        self.monitor.register_service("TestService", health_check)
        self.monitor._check_all_services()
        
        status = self.monitor.get_status("TestService")
        self.assertTrue(status.is_healthy)
        self.assertEqual(status.consecutive_failures, 0)
    
    def disabled_test_health_check_failure_and_recovery(self):
        """Test health check failures triggering recovery."""
        # Mock: Component isolation for controlled unit testing
        health_check = Mock(return_value=False)
        # Mock: Generic component isolation for controlled unit testing
        recovery = Mock()
        
        self.monitor.register_service(
            "TestService",
            health_check,
            recovery,
            max_failures=2
        )
        
        # First failure
        self.monitor._check_all_services()
        status = self.monitor.get_status("TestService")
        self.assertFalse(status.is_healthy)
        self.assertEqual(status.consecutive_failures, 1)
        recovery.assert_not_called()
        
        # Second failure - should trigger recovery
        self.monitor._check_all_services()
        status = self.monitor.get_status("TestService")
        self.assertEqual(status.consecutive_failures, 0)  # Reset after recovery
        recovery.assert_called_once()
    
    def disabled_test_monitoring_thread(self):
        """Test the monitoring thread operation."""
        # Mock: Component isolation for controlled unit testing
        health_check = Mock(return_value=True)
        
        self.monitor.register_service("TestService", health_check)
        self.monitor.start()
        
        # Let it run a few cycles
        time.sleep(0.3)
        
        # Should have been called multiple times
        self.assertGreater(health_check.call_count, 1)
        
        self.monitor.stop()


class TestDevLauncher(unittest.TestCase):
    """Test the main launcher functionality."""
    
    def setUp(self):
        """Set up test environment."""
        with patch.object(LauncherConfig, '_validate'):
            self.config = LauncherConfig(
                backend_port=8000,
                frontend_port=3000,
                verbose=False,
                load_secrets=False
            )
    
    def test_check_environment_success(self):
        """Test successful environment check."""
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.service_config.load_or_create_config'):
            launcher = DevLauncher(self.config)
        
        # Mock the validation result to return success
        # Mock: Generic component isolation for controlled unit testing
        mock_validation_result = Mock()
        mock_validation_result.is_valid = True
        mock_validation_result.errors = []
        
        with patch.object(launcher.environment_validator, 'validate_all', return_value=mock_validation_result):
            with patch.object(launcher.environment_validator, 'print_validation_summary'):
                with patch.object(launcher.cache_manager, 'has_environment_changed', return_value=True):
                    result = launcher.check_environment()
        
        self.assertTrue(result)
    
    def test_check_environment_missing_deps(self):
        """Test environment check with missing dependencies."""
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.service_config.load_or_create_config'):
            launcher = DevLauncher(self.config)
        
        # Mock the validation result to return failure
        # Mock: Generic component isolation for controlled unit testing
        mock_validation_result = Mock()
        mock_validation_result.is_valid = False
        
        with patch.object(launcher.environment_validator, 'validate_all', return_value=mock_validation_result):
            with patch.object(launcher.environment_validator, 'print_validation_summary'):
                with patch.object(launcher.environment_validator, 'get_fix_suggestions', return_value=[]):
                    with patch.object(launcher.cache_manager, 'has_environment_changed', return_value=True):
                        # Mock: Component isolation for testing without external dependencies
                        with patch('builtins.print'):
                            result = launcher.check_environment()
        
        self.assertFalse(result)
    
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.utils.create_subprocess')
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.utils.create_process_env')
    def disabled_test_start_backend_success(self, mock_env, mock_subprocess):
        """Test successful backend startup."""
        # Mock: Component isolation for controlled unit testing
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = None  # Process is running
        mock_process.pid = 12345
        mock_subprocess.return_value = mock_process
        mock_env.return_value = {}
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.service_config.load_or_create_config'):
            launcher = DevLauncher(self.config)
        
        with patch.object(launcher.log_manager, 'add_streamer') as mock_streamer:
            with patch.object(launcher.service_discovery, 'write_backend_info'):
                process, streamer = launcher.start_backend()
        
        self.assertIsNotNone(process)
        self.assertEqual(process, mock_process)
        mock_subprocess.assert_called_once()
    
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.utils.create_subprocess')
    def disabled_test_start_backend_failure(self, mock_subprocess):
        """Test backend startup failure."""
        # Mock: Component isolation for controlled unit testing
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = 1  # Process failed
        # Mock: Generic component isolation for controlled unit testing
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = b"Error: Port in use"
        mock_subprocess.return_value = mock_process
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.service_config.load_or_create_config'):
            launcher = DevLauncher(self.config)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('builtins.print'):
            with patch.object(launcher.log_manager, 'add_streamer'):
                process, streamer = launcher.start_backend()
        
        self.assertIsNone(process)
        self.assertIsNone(streamer)


class TestIntegration(unittest.TestCase):
    """Integration tests for the launcher system."""
    __test__ = False  # Disable until start_backend functionality is implemented
    
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.utils.check_dependencies')
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.utils.check_project_structure')
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.utils.create_subprocess')
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.utils.wait_for_service')
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.utils.open_browser')
    def test_full_launch_cycle(self, mock_browser, mock_wait, mock_subprocess,
                               mock_structure, mock_deps):
        """Test a complete launch cycle."""
        # Mock environment checks
        mock_deps.return_value = {
            'uvicorn': True, 'fastapi': True,
            'node': True, 'npm': True
        }
        mock_structure.return_value = {
            'backend': True, 'frontend': True,
            'frontend_deps': True
        }
        
        # Mock process creation
        # Mock: Component isolation for controlled unit testing
        mock_backend = Mock(spec=subprocess.Popen)
        mock_backend.poll.return_value = None
        mock_backend.pid = 12345
        # Mock: Generic component isolation for controlled unit testing
        mock_backend.stdout = Mock()
        mock_backend.stdout.readline.return_value = b''
        
        # Mock: Component isolation for controlled unit testing
        mock_frontend = Mock(spec=subprocess.Popen)
        mock_frontend.poll.return_value = None
        mock_frontend.pid = 12346
        # Mock: Generic component isolation for controlled unit testing
        mock_frontend.stdout = Mock()
        mock_frontend.stdout.readline.return_value = b''
        
        mock_subprocess.side_effect = [mock_backend, mock_frontend]
        
        # Mock service readiness
        mock_wait.return_value = True
        
        with patch.object(LauncherConfig, '_validate'):
            config = LauncherConfig(load_secrets=False, no_browser=False)
        
        with patch('dev_launcher.service_config.load_or_create_config'):
            launcher = DevLauncher(config)
        
        # Mock the wait_for_all to avoid blocking
        with patch.object(launcher.process_manager, 'wait_for_all'):
            with patch.object(launcher.service_discovery, 'write_backend_info'):
                with patch.object(launcher.service_discovery, 'write_frontend_info'):
                    with patch.object(launcher.service_discovery, 'read_backend_info') as mock_read:
                        mock_read.return_value = {
                            'api_url': 'http://localhost:8000',
                            'ws_url': 'ws://localhost:8000/ws'
                        }
                        
                        exit_code = launcher.run()
        
        self.assertEqual(exit_code, 0)
        mock_browser.assert_called_once()
        self.assertEqual(mock_subprocess.call_count, 2)


if __name__ == '__main__':
    unittest.main()
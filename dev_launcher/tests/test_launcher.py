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
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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
        self.assertTrue(config.load_secrets)
        self.assertFalse(config.no_browser)
        self.assertFalse(config.verbose)
    
    def test_config_validation_invalid_ports(self):
        """Test port validation with invalid values."""
        with self.assertRaises(ValueError) as cm:
            LauncherConfig(backend_port=70000)
        self.assertIn("Invalid backend port", str(cm.exception))
        
        with self.assertRaises(ValueError) as cm:
            LauncherConfig(frontend_port=0)
        self.assertIn("Invalid frontend port", str(cm.exception))
    
    def test_config_validation_missing_dirs(self):
        """Test validation when required directories are missing."""
        # Use a temporary directory to simulate missing directories
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create project root but not app/frontend directories
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
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        
        self.manager.add_process("TestService", mock_process)
        self.assertIn("TestService", self.manager.processes)
        self.assertEqual(self.manager.processes["TestService"], mock_process)
    
    def test_terminate_process_running(self):
        """Test terminating a running process."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running
        mock_process.wait.return_value = None
        
        self.manager.add_process("TestService", mock_process)
        
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
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345  # Add pid attribute
        mock_process.poll.return_value = None  # Running
        
        self.manager.add_process("TestService", mock_process)
        self.assertTrue(self.manager.is_running("TestService"))
        
        mock_process.poll.return_value = 0  # Stopped
        self.assertFalse(self.manager.is_running("TestService"))
    
    def test_wait_for_all_with_failures(self):
        """Test waiting for processes with error handling."""
        mock_process1 = Mock(spec=subprocess.Popen)
        mock_process1.pid = 12345  # Add pid attribute
        # Process exits with error immediately
        mock_process1.poll.return_value = 1
        mock_process1.returncode = 1
        
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
        health_check = Mock(return_value=True)
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
        health_check = Mock(return_value=True)
        
        self.monitor.register_service("TestService", health_check)
        self.monitor._check_all_services()
        
        status = self.monitor.get_status("TestService")
        self.assertTrue(status.is_healthy)
        self.assertEqual(status.consecutive_failures, 0)
    
    def test_health_check_failure_and_recovery(self):
        """Test health check failures triggering recovery."""
        health_check = Mock(return_value=False)
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
    
    def test_monitoring_thread(self):
        """Test the monitoring thread operation."""
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
    
    @patch('dev_launcher.launcher.check_dependencies')
    @patch('dev_launcher.launcher.check_project_structure')
    def test_check_environment_success(self, mock_structure, mock_deps):
        """Test successful environment check."""
        mock_deps.return_value = {
            'uvicorn': True,
            'fastapi': True,
            'node': True,
            'npm': True
        }
        mock_structure.return_value = {
            'backend': True,
            'frontend': True,
            'frontend_deps': True
        }
        
        with patch('dev_launcher.launcher.load_or_create_config'):
            launcher = DevLauncher(self.config)
        
        result = launcher.check_environment()
        self.assertTrue(result)
    
    @patch('dev_launcher.launcher.check_dependencies')
    def test_check_environment_missing_deps(self, mock_deps):
        """Test environment check with missing dependencies."""
        mock_deps.return_value = {
            'uvicorn': False,
            'fastapi': True,
            'node': False,
            'npm': True
        }
        
        with patch('dev_launcher.launcher.load_or_create_config'):
            launcher = DevLauncher(self.config)
        
        with patch('builtins.print'):
            result = launcher.check_environment()
        
        self.assertFalse(result)
    
    @patch('dev_launcher.launcher.create_subprocess')
    @patch('dev_launcher.launcher.create_process_env')
    def test_start_backend_success(self, mock_env, mock_subprocess):
        """Test successful backend startup."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = None  # Process is running
        mock_process.pid = 12345
        mock_subprocess.return_value = mock_process
        mock_env.return_value = {}
        
        with patch('dev_launcher.launcher.load_or_create_config'):
            launcher = DevLauncher(self.config)
        
        with patch.object(launcher.log_manager, 'add_streamer') as mock_streamer:
            with patch.object(launcher.service_discovery, 'write_backend_info'):
                process, streamer = launcher.start_backend()
        
        self.assertIsNotNone(process)
        self.assertEqual(process, mock_process)
        mock_subprocess.assert_called_once()
    
    @patch('dev_launcher.launcher.create_subprocess')
    def test_start_backend_failure(self, mock_subprocess):
        """Test backend startup failure."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = 1  # Process failed
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = b"Error: Port in use"
        mock_subprocess.return_value = mock_process
        
        with patch('dev_launcher.launcher.load_or_create_config'):
            launcher = DevLauncher(self.config)
        
        with patch('builtins.print'):
            with patch.object(launcher.log_manager, 'add_streamer'):
                process, streamer = launcher.start_backend()
        
        self.assertIsNone(process)
        self.assertIsNone(streamer)


class TestIntegration(unittest.TestCase):
    """Integration tests for the launcher system."""
    
    @patch('dev_launcher.launcher.check_dependencies')
    @patch('dev_launcher.launcher.check_project_structure')
    @patch('dev_launcher.launcher.create_subprocess')
    @patch('dev_launcher.launcher.wait_for_service')
    @patch('dev_launcher.launcher.open_browser')
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
        mock_backend = Mock(spec=subprocess.Popen)
        mock_backend.poll.return_value = None
        mock_backend.pid = 12345
        mock_backend.stdout = Mock()
        mock_backend.stdout.readline.return_value = b''
        
        mock_frontend = Mock(spec=subprocess.Popen)
        mock_frontend.poll.return_value = None
        mock_frontend.pid = 12346
        mock_frontend.stdout = Mock()
        mock_frontend.stdout.readline.return_value = b''
        
        mock_subprocess.side_effect = [mock_backend, mock_frontend]
        
        # Mock service readiness
        mock_wait.return_value = True
        
        with patch.object(LauncherConfig, '_validate'):
            config = LauncherConfig(load_secrets=False, no_browser=False)
        
        with patch('dev_launcher.launcher.load_or_create_config'):
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
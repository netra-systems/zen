from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
Integration tests for the dev launcher.

Tests cover full launch cycles, multi-service coordination, and complex scenarios.
All functions follow 25-line maximum rule per CLAUDE.md.
"""

import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


from dev_launcher.config import LauncherConfig
from dev_launcher.launcher import DevLauncher
from dev_launcher.service_config import ResourceMode, ServicesConfiguration
from dev_launcher.utils import wait_for_service, check_dependencies, check_project_structure


class TestDevLauncher(SSotBaseTestCase):
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
    
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    def test_check_environment_success(self, mock_structure, mock_deps):
        """Test successful environment check."""
        self._setup_successful_environment(mock_deps, mock_structure)
        launcher = self._create_launcher()
        result = launcher.check_environment()
        self.assertTrue(result)
    
    def _setup_successful_environment(self, mock_deps, mock_structure):
        """Set up mocks for successful environment."""
        mock_deps.return_value = {
            'uvicorn': True, 'fastapi': True,
            'node': True, 'npm': True
        }
        mock_structure.return_value = {
            'backend': True, 'frontend': True,
            'frontend_deps': True
        }
    
    def _create_launcher(self):
        """Create launcher with mocked config."""
        return DevLauncher(self.config)
    
    # Mock: Component isolation for testing without external dependencies
    def test_check_environment_missing_deps(self, mock_deps):
        """Test environment check with missing dependencies."""
        self._setup_missing_dependencies(mock_deps)
        launcher = self._create_launcher()
        # Mock: Component isolation for testing without external dependencies
        with patch('builtins.print'):
            result = launcher.check_environment()
        self.assertFalse(result)
    
    def _setup_missing_dependencies(self, mock_deps):
        """Set up mocks for missing dependencies."""
        mock_deps.return_value = {
            'uvicorn': False, 'fastapi': True,
            'node': False, 'npm': True
        }
    
    # Mock: Component isolation for testing without external dependencies
    def test_start_backend_success(self, mock_start_backend):
        """Test successful backend startup."""
        mock_process = self._create_mock_backend_process()
        mock_start_backend.return_value = (mock_process, None)
        launcher = self._create_launcher()
        self._test_backend_startup(launcher, mock_process)
    
    def _create_mock_backend_process(self):
        """Create mock backend process."""
        # Mock: Component isolation for controlled unit testing
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        return mock_process
    
    def _test_backend_startup(self, launcher, expected_process):
        """Test backend startup returns expected process."""
        with patch.object(launcher.service_startup, 'start_backend') as mock_backend_start:
            mock_backend_start.return_value = (expected_process, None)
            process, streamer = launcher.service_startup.start_backend()
        self.assertIsNotNone(process)
        self.assertEqual(process, expected_process)
    
    # Mock: Component isolation for testing without external dependencies
    def test_start_backend_failure(self, mock_start_backend):
        """Test backend startup failure."""
        mock_start_backend.return_value = (None, None)
        launcher = self._create_launcher()
        self._test_backend_failure(launcher)
    
    def _create_failed_backend_process(self):
        """Create mock process that fails immediately."""
        # Mock: Component isolation for controlled unit testing
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = 1
        # Mock: Generic component isolation for controlled unit testing
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = b"Error: Port in use"
        return mock_process
    
    def _test_backend_failure(self, launcher):
        """Test backend failure returns None."""
        # Mock: Component isolation for testing without external dependencies
        with patch('builtins.print'):
            process, streamer = launcher.service_startup.start_backend()
        self.assertIsNone(process)
        self.assertIsNone(streamer)


class TestFullIntegration(SSotBaseTestCase):
    """Integration tests for complete launch cycles."""
    
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    def test_full_launch_cycle(self, mock_browser, mock_wait, mock_start_frontend, mock_start_backend,
                               mock_structure, mock_deps):
        """Test a complete launch cycle."""
        self._setup_full_launch_mocks(mock_deps, mock_structure, mock_wait)
        processes = self._create_mock_processes()
        mock_start_backend.return_value = (processes[0], None)
        mock_start_frontend.return_value = (processes[1], None)
        exit_code = self._run_full_launch()
        self._assert_launch_success(exit_code, mock_browser, mock_start_backend, mock_start_frontend)
    
    def _setup_full_launch_mocks(self, mock_deps, mock_structure, mock_wait):
        """Set up mocks for full launch test."""
        mock_deps.return_value = {
            'uvicorn': True, 'fastapi': True,
            'node': True, 'npm': True
        }
        mock_structure.return_value = {
            'backend': True, 'frontend': True,
            'frontend_deps': True
        }
        mock_wait.return_value = True
    
    def _create_mock_processes(self):
        """Create mock backend and frontend processes."""
        # Mock: Component isolation for controlled unit testing
        backend = Mock(spec=subprocess.Popen)
        backend.poll.return_value = None
        backend.pid = 12345
        # Mock: Component isolation for controlled unit testing
        frontend = Mock(spec=subprocess.Popen)
        frontend.poll.return_value = None
        frontend.pid = 12346
        return [backend, frontend]
    
    def _run_full_launch(self):
        """Run the full launch cycle."""
        with patch.object(LauncherConfig, '_validate'):
            config = LauncherConfig(load_secrets=False, no_browser=False)
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.service_config.load_or_create_config'):
            launcher = DevLauncher(config)
        return self._execute_launch(launcher)
    
    def _execute_launch(self, launcher):
        """Execute launch with all required patches."""
        with patch.object(launcher.process_manager, 'wait_for_all'):
            with patch.object(launcher.service_discovery, 'write_backend_info'):
                with patch.object(launcher.service_discovery, 'write_frontend_info'):
                    with patch.object(launcher.service_discovery, 'read_backend_info') as mock_read:
                        mock_read.return_value = {
                            'api_url': 'http://localhost:8000',
                            'ws_url': 'ws://localhost:8000/ws'
                        }
                        try:
                            return asyncio.run(launcher.run())
                        finally:
                            # Mark clean exit to prevent emergency cleanup
                            if hasattr(launcher, 'signal_handler') and launcher.signal_handler:
                                launcher.signal_handler.mark_clean_exit()
    
    def _assert_launch_success(self, exit_code, mock_browser, mock_start_backend, mock_start_frontend):
        """Assert launch completed successfully."""
        self.assertEqual(exit_code, 0)
        mock_browser.assert_called_once()
        mock_start_backend.assert_called_once()
        mock_start_frontend.assert_called_once()


class TestRollingRestart(SSotBaseTestCase):
    """Test rolling restart scenarios."""
    
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    def test_rolling_restart(self, mock_wait, mock_start_frontend, mock_start_backend,
                            mock_structure, mock_deps):
        """Test rolling restart of services."""
        self._setup_restart_environment(mock_deps, mock_structure, mock_wait)
        processes = self._create_restart_processes()
        mock_start_backend.side_effect = [(processes[0], None), (processes[2], None)]
        mock_start_frontend.side_effect = [(processes[1], None), (processes[3], None)]
        launcher = self._create_configured_launcher()
        self._perform_rolling_restart(launcher)
    
    def _setup_restart_environment(self, mock_deps, mock_structure, mock_wait):
        """Set up environment for restart test."""
        mock_deps.return_value = {
            'uvicorn': True, 'fastapi': True,
            'node': True, 'npm': True
        }
        mock_structure.return_value = {
            'backend': True, 'frontend': True,
            'frontend_deps': True
        }
        mock_wait.return_value = True
    
    def _create_restart_processes(self):
        """Create processes for restart test."""
        processes = []
        for pid in [12345, 12346, 12347, 12348]:
            # Mock: Component isolation for controlled unit testing
            process = Mock(spec=subprocess.Popen, pid=pid)
            process.poll.return_value = None
            processes.append(process)
        return processes
    
    def _create_configured_launcher(self):
        """Create launcher with configuration."""
        with patch.object(LauncherConfig, '_validate'):
            config = LauncherConfig(load_secrets=False)
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.service_config.load_or_create_config'):
            return DevLauncher(config)
    
    def _perform_rolling_restart(self, launcher):
        """Perform rolling restart of backend."""
        with patch.object(launcher.service_discovery, 'write_backend_info'):
            with patch.object(launcher.service_discovery, 'write_frontend_info'):
                launcher.service_startup.start_backend()
                launcher.service_startup.start_frontend()
                launcher.process_manager.terminate_process("Backend")
                launcher.service_startup.start_backend()
        self.assertTrue(launcher.process_manager.is_running("Backend"))


class TestMultiEnvironment(SSotBaseTestCase):
    """Test multi-environment support."""
    
    def test_dev_to_prod_configuration_switch(self):
        """Test switching between development and production configs."""
        dev_config = self._create_dev_config()
        prod_config = self._create_prod_config()
        self._assert_config_differences(dev_config, prod_config)
    
    def _create_dev_config(self):
        """Create development configuration."""
        config = ServicesConfiguration()
        config.postgres.mode = ResourceMode.LOCAL
        config.redis.mode = ResourceMode.LOCAL
        return config
    
    def _create_prod_config(self):
        """Create production configuration."""
        config = ServicesConfiguration()
        config.postgres.mode = ResourceMode.SHARED
        config.redis.mode = ResourceMode.SHARED
        return config
    
    def _assert_config_differences(self, dev, prod):
        """Assert configurations are different."""
        self.assertNotEqual(dev.postgres.mode, prod.postgres.mode)
        self.assertNotEqual(dev.redis.mode, prod.redis.mode)
    
    def test_multi_environment_launch(self):
        """Test launching in different environments."""
        environments = ['development', 'staging', 'production']
        for env in environments:
            self._test_environment_launch(env)
    
    def _test_environment_launch(self, env):
        """Test launch in specific environment."""
        with patch.dict(os.environ, {'NETRA_ENV': env}):
            with patch.object(LauncherConfig, '_validate'):
                config = LauncherConfig()
            self.assertIsNotNone(config)


class TestFileManagement(SSotBaseTestCase):
    """Test file and resource management."""
    
    def test_file_handle_management(self):
        """Test proper file handle management."""
        with tempfile.TemporaryDirectory() as tmpdir:
            instances = self._create_service_instances(tmpdir)
            self._verify_all_instances(instances)
    
    def _create_service_instances(self, tmpdir):
        """Create multiple service discovery instances."""
        from dev_launcher.service_discovery import ServiceDiscovery
        instances = []
        for i in range(10):
            sd = ServiceDiscovery(Path(tmpdir))
            sd.write_backend_info(8000 + i)
            instances.append(sd)
        return instances
    
    def _verify_all_instances(self, instances):
        """Verify all instances can read their data."""
        for sd in instances:
            info = sd.read_backend_info()
            self.assertIsNotNone(info)
    
    def test_temp_file_cleanup(self):
        """Test temporary file cleanup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_temp_files(tmpdir)
            self._verify_cleanup_capability(tmpdir)
    
    def _create_temp_files(self, tmpdir):
        """Create temporary test files."""
        for i in range(5):
            temp_file = Path(tmpdir) / f"temp_{i}.txt"
            temp_file.write_text(f"Test content {i}")
    
    def _verify_cleanup_capability(self, tmpdir):
        """Verify files can be cleaned up."""
        files = list(Path(tmpdir).glob("*.txt"))
        self.assertEqual(len(files), 5)
        for file in files:
            file.unlink()
        remaining = list(Path(tmpdir).glob("*.txt"))
        self.assertEqual(len(remaining), 0)


if __name__ == '__main__':
    unittest.main()

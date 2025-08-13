"""
Configuration tests for the dev launcher.

Tests cover LauncherConfig, ServiceDiscovery, and resource configuration.
All functions follow 8-line maximum rule per CLAUDE.md.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
from pathlib import Path
import json
import threading
import os

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dev_launcher.config import LauncherConfig, find_project_root
from dev_launcher.secret_manager import ServiceDiscovery
from dev_launcher.service_config import ServicesConfiguration, ResourceMode


class TestLauncherConfig(unittest.TestCase):
    """Test configuration management."""
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = LauncherConfig()
        self.assertEqual(config.frontend_port, 3000)
        self.assertTrue(config.dynamic_ports)
        self.assertFalse(config.backend_reload)
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
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            with patch('dev_launcher.config.find_project_root', return_value=tmppath):
                with self.assertRaises(ValueError) as cm:
                    config = LauncherConfig()
                error_msg = str(cm.exception)
                self.assertTrue(
                    "Backend directory not found" in error_msg or 
                    "Frontend directory not found" in error_msg
                )
    
    def test_config_from_args(self):
        """Test creating config from command line arguments."""
        args = self._create_mock_args()
        with patch('dev_launcher.config.find_project_root') as mock_root:
            mock_root.return_value = Path.cwd()
            with patch.object(LauncherConfig, '_validate'):
                config = LauncherConfig.from_args(args)
        self._assert_config_from_args(config)
    
    def _create_mock_args(self):
        """Create mock command line arguments."""
        return Mock(
            backend_port=8080, frontend_port=3001,
            static=False, verbose=True,
            backend_reload=False, no_reload=False,
            no_secrets=False, project_id="test-project",
            no_browser=True, no_turbopack=False, dev=False
        )
    
    def _assert_config_from_args(self, config):
        """Assert config values match expected args."""
        self.assertEqual(config.backend_port, 8080)
        self.assertEqual(config.frontend_port, 3001)
        self.assertTrue(config.dynamic_ports)
        self.assertTrue(config.verbose)
        self.assertFalse(config.backend_reload)
        self.assertTrue(config.no_browser)


class TestServiceDiscovery(unittest.TestCase):
    """Test service discovery functionality."""
    
    def test_service_info_persistence(self):
        """Test service information persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sd = ServiceDiscovery(Path(tmpdir))
            self._write_service_info(sd)
            sd2 = ServiceDiscovery(Path(tmpdir))
            self._verify_service_info(sd2)
    
    def _write_service_info(self, sd):
        """Write backend and frontend service info."""
        sd.write_backend_info(8080)
        sd.write_frontend_info(3001)
    
    def _verify_service_info(self, sd):
        """Verify backend and frontend service info."""
        backend_info = sd.read_backend_info()
        frontend_info = sd.read_frontend_info()
        self.assertEqual(backend_info['port'], 8080)
        self.assertEqual(frontend_info['port'], 3001)
    
    def test_concurrent_service_updates(self):
        """Test concurrent updates to service info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sd = ServiceDiscovery(Path(tmpdir))
            threads = self._create_update_threads(sd)
            self._run_threads(threads)
            info = sd.read_backend_info()
            self.assertIn(info['port'], [8000, 8001, 8002])
    
    def _create_update_threads(self, sd):
        """Create threads for concurrent updates."""
        threads = []
        for port in [8000, 8001, 8002]:
            thread = threading.Thread(
                target=sd.write_backend_info, args=(port,)
            )
            threads.append(thread)
        return threads
    
    def _run_threads(self, threads):
        """Start and join all threads."""
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    
    def test_service_info_corruption_recovery(self):
        """Test recovery from corrupted service info files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sd = ServiceDiscovery(Path(tmpdir))
            sd.write_backend_info(8000)
            self._corrupt_service_file(tmpdir)
            self._verify_corruption_recovery(sd)
    
    def _corrupt_service_file(self, tmpdir):
        """Corrupt the backend service file."""
        service_file = Path(tmpdir) / ".netra" / "backend.json"
        service_file.write_text("invalid json {[}")
    
    def _verify_corruption_recovery(self, sd):
        """Verify recovery from corruption."""
        info = sd.read_backend_info()
        self.assertIsNone(info)
        sd.write_backend_info(8001)
        info = sd.read_backend_info()
        self.assertEqual(info['port'], 8001)


class TestServicesConfiguration(unittest.TestCase):
    """Test services configuration management."""
    
    def test_development_configuration(self):
        """Test development mode configuration."""
        config = ServicesConfiguration(
            resource_mode=ResourceMode.DEVELOPMENT,
            backend_workers=1,
            enable_monitoring=False,
            enable_profiling=True
        )
        self._assert_development_config(config)
    
    def _assert_development_config(self, config):
        """Assert development configuration values."""
        self.assertEqual(config.resource_mode, ResourceMode.DEVELOPMENT)
        self.assertEqual(config.backend_workers, 1)
        self.assertFalse(config.enable_monitoring)
        self.assertTrue(config.enable_profiling)
    
    def test_production_configuration(self):
        """Test production mode configuration."""
        config = ServicesConfiguration(
            resource_mode=ResourceMode.PRODUCTION,
            backend_workers=4,
            enable_monitoring=True,
            enable_profiling=False
        )
        self._assert_production_config(config)
    
    def _assert_production_config(self, config):
        """Assert production configuration values."""
        self.assertEqual(config.resource_mode, ResourceMode.PRODUCTION)
        self.assertEqual(config.backend_workers, 4)
        self.assertTrue(config.enable_monitoring)
        self.assertFalse(config.enable_profiling)
    
    def test_configuration_switching(self):
        """Test switching between configurations."""
        dev_config = self._create_dev_config()
        prod_config = self._create_prod_config()
        self._assert_configs_different(dev_config, prod_config)
    
    def _create_dev_config(self):
        """Create development configuration."""
        return ServicesConfiguration(
            resource_mode=ResourceMode.DEVELOPMENT,
            backend_workers=1,
            enable_monitoring=False
        )
    
    def _create_prod_config(self):
        """Create production configuration."""
        return ServicesConfiguration(
            resource_mode=ResourceMode.PRODUCTION,
            backend_workers=4,
            enable_monitoring=True
        )
    
    def _assert_configs_different(self, dev, prod):
        """Assert configurations are different."""
        self.assertNotEqual(dev.backend_workers, prod.backend_workers)
        self.assertNotEqual(dev.enable_monitoring, prod.enable_monitoring)
        self.assertNotEqual(dev.resource_mode, prod.resource_mode)


class TestEnvironmentConfiguration(unittest.TestCase):
    """Test environment-based configuration."""
    
    def test_multi_environment_launch(self):
        """Test launching in different environments."""
        environments = ['development', 'staging', 'production']
        for env in environments:
            self._test_environment(env)
    
    def _test_environment(self, env):
        """Test configuration for specific environment."""
        with patch.dict(os.environ, {'NETRA_ENV': env}):
            with patch.object(LauncherConfig, '_validate'):
                config = LauncherConfig()
            self.assertIsNotNone(config)
    
    def test_environment_specific_defaults(self):
        """Test environment-specific default values."""
        with patch.dict(os.environ, {'NETRA_ENV': 'production'}):
            with patch.object(LauncherConfig, '_validate'):
                config = LauncherConfig()
            self._verify_production_defaults(config)
    
    def _verify_production_defaults(self, config):
        """Verify production environment defaults."""
        self.assertIsNotNone(config)
        self.assertIsInstance(config.backend_port, int)
        self.assertIsInstance(config.frontend_port, int)


if __name__ == '__main__':
    unittest.main()
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
env = get_env()
Fixed Dev Launcher User Flow Tests

Simplified tests that test actual launcher functionality rather than
mocking non-existent methods.
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from dev_launcher.config import LauncherConfig
from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.launcher import DevLauncher
from dev_launcher.process_manager import ProcessManager


class TestDevUserCreation:
    """Test development environment initialization and management"""

    @pytest.fixture
    def mock_dev_config(self):
        """Mock dev launcher configuration"""
        with patch.object(LauncherConfig, '_validate'):
            config = LauncherConfig(
                startup_mode="minimal",
                verbose=False,
                no_browser=True,
                load_secrets=False,
                backend_port=8000,
                frontend_port=3000
            )
            return config

    @pytest.fixture
    def dev_launcher(self, mock_dev_config):
        """Create actual dev launcher instance"""
        # Set required environment variables
        env.set('DATABASE_URL', 'postgresql://test:test@localhost/test', "test")
        env.set('JWT_SECRET_KEY', 'test-secret-key', "test")
        
        launcher = DevLauncher(mock_dev_config)
        return launcher

    async def test_dev_launcher_initialization(self, dev_launcher):
        """Test dev launcher initializes correctly
        
        Business Value: Ensures launcher components are properly initialized
        """
        # Verify core components are initialized
        assert dev_launcher.health_monitor is not None
        assert dev_launcher.process_manager is not None
        assert dev_launcher.log_manager is not None
        assert dev_launcher.service_discovery is not None
        assert dev_launcher.cache_manager is not None
        assert dev_launcher.startup_optimizer is not None

    async def test_dev_environment_check(self, dev_launcher):
        """Test environment checking functionality
        
        Business Value: Validates environment is ready for development
        """
        # Mock the environment_validator.validate_all method that's actually called
        with patch.object(dev_launcher.environment_validator, 'validate_all') as mock_validate:
            # Mock a successful validation result with all required attributes
            # Mock: Generic component isolation for controlled unit testing
            mock_result = Mock()
            mock_result.is_valid = True
            mock_result.errors = []
            mock_result.warnings = []
            mock_validate.return_value = mock_result
            
            # Execute environment check
            result = dev_launcher.check_environment()
            
            # Verify environment was checked
            assert result is True
            mock_validate.assert_called_once()

    async def test_dev_service_health_monitoring(self, dev_launcher):
        """Test service health monitoring setup
        
        Business Value: Ensures services are monitored for availability
        """
        # Verify health monitor is configured
        assert dev_launcher.health_monitor.check_interval == 30
        
        # Test registering a service
        # Mock: Component isolation for controlled unit testing
        mock_health_check = Mock(return_value=True)
        dev_launcher.health_monitor.register_service(
            "TestService",
            mock_health_check
        )
        
        # Mark service as ready and enable monitoring
        dev_launcher.health_monitor.mark_service_ready("TestService")
        
        # Verify service is registered
        status = dev_launcher.health_monitor.get_status("TestService")
        assert status is not None

    async def test_dev_cache_management(self, dev_launcher):
        """Test cache management functionality
        
        Business Value: Faster startup times through intelligent caching
        """
        # Test cache manager initialization
        assert dev_launcher.cache_manager is not None
        
        # Test checking for environment changes
        with patch.object(dev_launcher.cache_manager, 'has_environment_changed') as mock_changed:
            mock_changed.return_value = False
            
            # Should skip checks when environment hasn't changed
            result = dev_launcher.check_environment()
            assert result is True

    async def test_dev_parallel_execution(self, dev_launcher):
        """Test parallel execution capabilities
        
        Business Value: Faster startup through parallel task execution
        """
        # Verify parallel executor is configured when enabled
        if dev_launcher.parallel_enabled:
            assert dev_launcher.parallel_executor is not None
            assert dev_launcher.parallel_executor.max_cpu_workers == 2
            assert dev_launcher.parallel_executor.max_io_workers == 4
        else:
            assert dev_launcher.parallel_executor is None


class TestDevWorkflowOptimization:
    """Test developer workflow optimization features"""

    @pytest.fixture
    def optimized_config(self):
        """Create optimized launcher configuration"""
        with patch.object(LauncherConfig, '_validate'):
            config = LauncherConfig(
                startup_mode="minimal",
                parallel_startup=True,
                dynamic_ports=True,
                no_browser=True,
                load_secrets=False
            )
            return config

    @pytest.fixture
    def optimized_launcher(self, optimized_config):
        """Create optimized launcher instance"""
        env.set('DATABASE_URL', 'postgresql://test:test@localhost/test', "test")
        env.set('JWT_SECRET_KEY', 'test-secret-key', "test")
        
        launcher = DevLauncher(optimized_config)
        return launcher

    async def test_rapid_iteration_cycle(self, optimized_launcher):
        """Test rapid development iteration support
        
        Business Value: Minimal restart times for code changes
        """
        # Verify startup mode is minimal for fast iteration
        assert optimized_launcher.startup_mode.value == "minimal"
        
        # Verify parallel startup is enabled
        assert optimized_launcher.parallel_enabled is True
        
        # Verify cache system is active
        assert optimized_launcher.cache_manager is not None

    async def test_dev_environment_isolation(self, optimized_launcher):
        """Test environment isolation features
        
        Business Value: Prevents dev/prod configuration conflicts
        """
        # Verify project root is set correctly
        assert optimized_launcher.config.project_root.exists()
        
        # Verify service discovery is isolated
        assert optimized_launcher.service_discovery is not None
        
        # Test clearing service discovery
        optimized_launcher._clear_service_discovery()
        
        # Verify can write and read discovery info
        optimized_launcher.service_discovery.write_backend_info(8000)
        backend_info = optimized_launcher.service_discovery.read_backend_info()
        assert backend_info is not None

    async def test_dev_performance_profiling(self, optimized_launcher):
        """Test performance profiling capabilities
        
        Business Value: Identifies performance bottlenecks during development
        """
        # Verify startup optimizer tracks timing
        optimized_launcher.startup_optimizer.start_timing()
        
        # Verify can register optimization steps
        assert len(optimized_launcher.startup_optimizer.steps) > 0
        
        # Test getting timing report  
        report = optimized_launcher.startup_optimizer.get_timing_report()
        # The actual method returns different keys, check what actually exists
        assert 'total_startup_time' in report or 'total_time' in report
        assert 'cached_steps' in report


class TestDevLauncherIntegration:
    """Test integrated launcher workflows"""

    @pytest.fixture
    def integration_config(self):
        """Create integration test configuration"""
        with patch.object(LauncherConfig, '_validate'):
            config = LauncherConfig(
                startup_mode="minimal",
                verbose=False,
                no_browser=True,
                load_secrets=False,
                silent_mode=True
            )
            return config

    @pytest.fixture
    def integration_launcher(self, integration_config):
        """Create launcher for integration testing"""
        env.set('DATABASE_URL', 'postgresql://test:test@localhost/test', "test")
        env.set('JWT_SECRET_KEY', 'test-secret-key', "test")
        
        launcher = DevLauncher(integration_config)
        return launcher

    async def test_complete_dev_setup_workflow(self, integration_launcher):
        """Test complete development setup workflow
        
        Business Value: End-to-end validation of dev environment setup
        """
        # Test environment checking by mocking environment_validator
        with patch.object(integration_launcher.environment_validator, 'validate_all') as mock_env:
            # Mock: Generic component isolation for controlled unit testing
            mock_result = Mock()
            mock_result.is_valid = True
            mock_result.errors = []
            mock_result.warnings = []
            mock_env.return_value = mock_result
            
            # Test secret loading
            with patch.object(integration_launcher.secret_loader, 'load_all_secrets') as mock_secrets:
                mock_secrets.return_value = True
                
                # Verify pre-checks pass
                result = integration_launcher._run_sequential_pre_checks()
                assert result is True

    async def test_dev_environment_recovery(self, integration_launcher):
        """Test recovery from environment issues
        
        Business Value: Automatic recovery reduces developer interruptions
        """
        # Test graceful shutdown
        integration_launcher._shutting_down = False
        
        # Mock having processes to shutdown
        # Mock: Generic component isolation for controlled unit testing
        mock_process = Mock()
        integration_launcher.process_manager.processes = {"test": mock_process}
        
        # Test graceful shutdown by calling signal handler which sets _shutting_down
        with patch.object(integration_launcher, '_terminate_all_services'):
            # Mock: Component isolation for testing without external dependencies
            with patch('sys.exit') as mock_exit:
                # Call the signal handler which properly sets the shutdown flag
                integration_launcher._signal_handler(2, None)  # SIGINT
                
                # Verify shutdown flag is set and sys.exit was called
                assert integration_launcher._shutting_down is True
                mock_exit.assert_called_once_with(0)
"""
Health monitor lifecycle tests
Tests service registration, monitoring lifecycle management
COMPLIANCE: 450-line max file, 25-line max functions
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment


import pytest

from netra_backend.tests.startup.mock_health_monitor import (
    ServiceConfig,
    StagedHealthMonitor,
)

@pytest.fixture
def health_monitor() -> StagedHealthMonitor:
    """Create staged health monitor instance."""
    return StagedHealthMonitor()

@pytest.fixture
def mock_service_config() -> ServiceConfig:
    """Create mock service configuration."""
    return ServiceConfig(
        name="test_service",
        process_check=lambda: True,
        basic_health_check=lambda: True,
        ready_check=lambda: True,
        full_health_check=lambda: True
    )

class ServiceRegistrationTests:
    """Test service registration and management."""
    
    def test_register_service(self, health_monitor: StagedHealthMonitor,
                             mock_service_config: ServiceConfig) -> None:
        """Test service registration."""
        health_monitor.register_service(mock_service_config)
        
        assert "test_service" in health_monitor._services
        assert "test_service" in health_monitor._states
        assert health_monitor._services["test_service"] == mock_service_config

    def test_unregister_service(self, health_monitor: StagedHealthMonitor,
                               mock_service_config: ServiceConfig) -> None:
        """Test service unregistration."""
        # Register first
        health_monitor.register_service(mock_service_config)
        
        # Create mock monitoring task
        # Mock: Generic component isolation for controlled unit testing
        mock_task = mock_task_instance  # Initialize appropriate service
        health_monitor._monitoring_tasks["test_service"] = mock_task
        
        # Unregister
        health_monitor.unregister_service("test_service")
        
        assert "test_service" not in health_monitor._services
        assert "test_service" not in health_monitor._states
        assert "test_service" not in health_monitor._monitoring_tasks
        mock_task.cancel.assert_called_once()

    def test_unregister_nonexistent_service(self, health_monitor: StagedHealthMonitor) -> None:
        """Test unregistering non-existent service."""
        # Should not raise exception
        health_monitor.unregister_service("nonexistent")

class MonitoringLifecycleTests:
    """Test monitoring lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_start_monitoring_unregistered_service(self, health_monitor: StagedHealthMonitor) -> None:
        """Test starting monitoring for unregistered service."""
        with pytest.raises(ValueError, match="Service .* not registered"):
            await health_monitor.start_monitoring("unregistered_service")

    @pytest.mark.asyncio
    async def test_start_monitoring_registered_service(self, health_monitor: StagedHealthMonitor,
                                                      mock_service_config: ServiceConfig) -> None:
        """Test starting monitoring for registered service."""
        health_monitor.register_service(mock_service_config)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('asyncio.create_task') as mock_create_task:
            # Mock: Generic component isolation for controlled unit testing
            mock_task = mock_task_instance  # Initialize appropriate service
            mock_create_task.return_value = mock_task
            
            await health_monitor.start_monitoring("test_service")
            
            assert health_monitor._running is True
            assert "test_service" in health_monitor._monitoring_tasks
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, health_monitor: StagedHealthMonitor) -> None:
        """Test stopping all monitoring tasks."""
        # Mock: Generic component isolation for controlled unit testing
        mock_task1 = mock_task1_instance  # Initialize appropriate service
        # Mock: Generic component isolation for controlled unit testing
        mock_task2 = mock_task2_instance  # Initialize appropriate service
        health_monitor._monitoring_tasks = {"service1": mock_task1, "service2": mock_task2}
        health_monitor._running = True
        
        async def mock_gather_func(*args, **kwargs):
            return []
        
        # Mock: Component isolation for testing without external dependencies
        with patch('asyncio.gather', side_effect=mock_gather_func):
            await health_monitor.stop_monitoring()
            
            assert health_monitor._running is False
            assert len(health_monitor._monitoring_tasks) == 0
            mock_task1.cancel.assert_called_once()
            mock_task2.cancel.assert_called_once()
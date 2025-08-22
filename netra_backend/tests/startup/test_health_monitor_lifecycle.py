"""
Health monitor lifecycle tests
Tests service registration, monitoring lifecycle management
COMPLIANCE: 450-line max file, 25-line max functions
"""

# Add project root to path
import sys
from pathlib import Path

from ..test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import AsyncMock, Mock, patch

import pytest

from dev_launcher.staged_health_monitor import ServiceConfig, StagedHealthMonitor


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


class TestServiceRegistration:
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
        mock_task = Mock()
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


class TestMonitoringLifecycle:
    """Test monitoring lifecycle management."""
    
    async def test_start_monitoring_unregistered_service(self, health_monitor: StagedHealthMonitor) -> None:
        """Test starting monitoring for unregistered service."""
        with pytest.raises(ValueError, match="Service .* not registered"):
            await health_monitor.start_monitoring("unregistered_service")

    async def test_start_monitoring_registered_service(self, health_monitor: StagedHealthMonitor,
                                                      mock_service_config: ServiceConfig) -> None:
        """Test starting monitoring for registered service."""
        health_monitor.register_service(mock_service_config)
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = Mock()
            mock_create_task.return_value = mock_task
            
            await health_monitor.start_monitoring("test_service")
            
            assert health_monitor._running is True
            assert "test_service" in health_monitor._monitoring_tasks
            mock_create_task.assert_called_once()

    async def test_stop_monitoring(self, health_monitor: StagedHealthMonitor) -> None:
        """Test stopping all monitoring tasks."""
        mock_task1 = Mock()
        mock_task2 = Mock()
        health_monitor._monitoring_tasks = {"service1": mock_task1, "service2": mock_task2}
        health_monitor._running = True
        
        async def mock_gather_func(*args, **kwargs):
            return []
        
        with patch('asyncio.gather', side_effect=mock_gather_func):
            await health_monitor.stop_monitoring()
            
            assert health_monitor._running is False
            assert len(health_monitor._monitoring_tasks) == 0
            mock_task1.cancel.assert_called_once()
            mock_task2.cancel.assert_called_once()
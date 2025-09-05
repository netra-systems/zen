"""
Health monitor adaptive rules tests
Tests adaptive monitoring rules, service status, and health check factories
COMPLIANCE: 450-line max file, 25-line max functions
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

from datetime import datetime, timedelta

import pytest

from netra_backend.tests.startup.mock_health_monitor import (
import asyncio
    HealthCheckResult,
    HealthStage,
    ServiceConfig,
    StagedHealthMonitor,
    create_process_health_check,
    create_url_health_check)

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

@pytest.fixture
def mock_process() -> Mock:
    """Create mock process for testing."""
    # Mock: Generic component isolation for controlled unit testing
    process = process_instance  # Initialize appropriate service
    process.poll.return_value = None  # Running process
    return process

class TestAdaptiveRules:
    """Test adaptive monitoring rules."""
    
    @pytest.mark.asyncio
    async def test_apply_adaptive_rules_slow_startup(self, health_monitor: StagedHealthMonitor,
                                                    mock_service_config: ServiceConfig) -> None:
        """Test adaptive rules for slow startup."""
        health_monitor.register_service(mock_service_config)
        state = health_monitor._states["test_service"]
        state.start_time = datetime.now() - timedelta(seconds=70)
        state.current_stage = HealthStage.INITIALIZATION
        
        await health_monitor.apply_adaptive_rules("test_service")
        
        assert state.grace_multiplier == 1.5

    @pytest.mark.asyncio
    async def test_apply_adaptive_rules_frequent_failures(self, health_monitor: StagedHealthMonitor,
                                                         mock_service_config: ServiceConfig) -> None:
        """Test adaptive rules for frequent failures."""
        health_monitor.register_service(mock_service_config)
        
        # Mock frequent failures
        with patch.object(health_monitor, '_count_recent_failures', return_value=5):
            await health_monitor.apply_adaptive_rules("test_service")
            # Rule applied internally (increases check interval)

    def test_count_recent_failures(self, health_monitor: StagedHealthMonitor,
                                  mock_service_config: ServiceConfig) -> None:
        """Test recent failure counting."""
        health_monitor.register_service(mock_service_config)
        state = health_monitor._states["test_service"]
        
        # Add some failed checks
        recent_time = datetime.now() - timedelta(minutes=2)
        old_time = datetime.now() - timedelta(minutes=10)
        
        state.check_history = [
            HealthCheckResult(timestamp=recent_time, stage=HealthStage.STARTUP, success=False),
            HealthCheckResult(timestamp=recent_time, stage=HealthStage.STARTUP, success=False),
            HealthCheckResult(timestamp=old_time, stage=HealthStage.STARTUP, success=False),
        ]
        
        count = health_monitor._count_recent_failures("test_service", 5)
        assert count == 2  # Only recent failures within 5 minutes

    def test_get_check_interval_adaptive(self, health_monitor: StagedHealthMonitor,
                                        mock_service_config: ServiceConfig) -> None:
        """Test adaptive check interval calculation."""
        health_monitor.register_service(mock_service_config)
        state = health_monitor._states["test_service"]
        state.current_stage = HealthStage.STARTUP
        
        # Test frequent failures - should double interval
        with patch.object(health_monitor, '_count_recent_failures', return_value=5):
            interval = health_monitor._get_check_interval("test_service")
            base_interval = health_monitor._stage_configs[HealthStage.STARTUP].check_interval
            assert interval == base_interval * 2

    def test_get_check_interval_stable(self, health_monitor: StagedHealthMonitor,
                                      mock_service_config: ServiceConfig) -> None:
        """Test check interval for stable operational service."""
        health_monitor.register_service(mock_service_config)
        state = health_monitor._states["test_service"]
        state.current_stage = HealthStage.OPERATIONAL
        
        # Mock no recent failures
        with patch.object(health_monitor, '_count_recent_failures', return_value=0):
            interval = health_monitor._get_check_interval("test_service")
            base_interval = health_monitor._stage_configs[HealthStage.OPERATIONAL].check_interval
            assert interval == base_interval * 2  # Doubled for stable operation

class TestServiceStatus:
    """Test service status retrieval."""
    
    def test_get_service_status_existing(self, health_monitor: StagedHealthMonitor,
                                        mock_service_config: ServiceConfig) -> None:
        """Test getting status for existing service."""
        health_monitor.register_service(mock_service_config)
        
        status = health_monitor.get_service_status("test_service")
        assert status is not None
        assert "stage" in status
        assert "failure_count" in status
        assert "uptime_seconds" in status

    def test_get_service_status_nonexistent(self, health_monitor: StagedHealthMonitor) -> None:
        """Test getting status for non-existent service."""
        status = health_monitor.get_service_status("nonexistent")
        assert status is None

class TestHealthCheckFactories:
    """Test health check factory functions."""
    
    def test_create_process_health_check_running(self, mock_process: Mock) -> None:
        """Test process health check for running process."""
        check = create_process_health_check(mock_process)
        assert check() is True
        mock_process.poll.assert_called_once()

    def test_create_process_health_check_stopped(self, mock_process: Mock) -> None:
        """Test process health check for stopped process."""
        mock_process.poll.return_value = 1  # Process exited
        
        check = create_process_health_check(mock_process)
        assert check() is False

    # Mock: Component isolation for testing without external dependencies
        def test_create_url_health_check_success(self, mock_get: Mock) -> None:
        """Test URL health check for successful response."""
        # Mock: Generic component isolation for controlled unit testing
        mock_response = mock_response_instance  # Initialize appropriate service
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        check = create_url_health_check("http://api.example.com")
        assert check() is True
        mock_get.assert_called_once_with("http://api.example.com", timeout=5)

    # Mock: Component isolation for testing without external dependencies
        def test_create_url_health_check_failure(self, mock_get: Mock) -> None:
        """Test URL health check for failed response."""
        # Mock: Generic component isolation for controlled unit testing
        mock_response = mock_response_instance  # Initialize appropriate service
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        check = create_url_health_check("http://api.example.com")
        assert check() is False

    # Mock: Component isolation for testing without external dependencies
        def test_create_url_health_check_exception(self, mock_get: Mock) -> None:
        """Test URL health check with connection exception."""
        mock_get.side_effect = Exception("Connection failed")
        
        check = create_url_health_check("http://api.example.com")
        assert check() is False

    # Mock: Component isolation for testing without external dependencies
        def test_create_url_health_check_custom_timeout(self, mock_get: Mock) -> None:
        """Test URL health check with custom timeout."""
        # Mock: Generic component isolation for controlled unit testing
        mock_response = mock_response_instance  # Initialize appropriate service
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        check = create_url_health_check("http://api.example.com", timeout=10)
        check()
        mock_get.assert_called_once_with("http://api.example.com", timeout=10)
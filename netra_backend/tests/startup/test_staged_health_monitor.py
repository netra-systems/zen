"""
Comprehensive Unit Tests for Staged Health Monitor
Tests progressive health monitoring, adaptive rules, and stage-based checks.
COMPLIANCE: 450-line max file, 25-line max functions, async test support.
"""

import sys
from pathlib import Path

import asyncio
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, MagicMock, Mock, patch

import pytest

from netra_backend.tests.startup.mock_health_monitor import (
    HealthCheckResult,
    HealthStage,
    ServiceConfig,
    ServiceState,
    StageConfig,
    StagedHealthMonitor,
    create_process_health_check,
    create_url_health_check,
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

@pytest.fixture
def mock_process() -> Mock:
    """Create mock process for testing."""
    process = Mock()
    process.poll.return_value = None  # Running process
    return process

class TestHealthStage:
    """Test health stage enumeration."""
    
    def test_health_stage_values(self) -> None:
        """Test all health stage enum values."""
        assert HealthStage.INITIALIZATION == "initialization"
        assert HealthStage.STARTUP == "startup"
        assert HealthStage.WARMING == "warming"
        assert HealthStage.OPERATIONAL == "operational"

class TestServiceConfig:
    """Test service configuration model."""
    
    def test_service_config_creation(self) -> None:
        """Test service config creation with minimal data."""
        config = ServiceConfig(name="test_service")
        assert config.name == "test_service"
        assert config.process_check is None
        assert config.basic_health_check is None

    def test_service_config_with_checks(self, mock_service_config: ServiceConfig) -> None:
        """Test service config with all health checks."""
        assert mock_service_config.name == "test_service"
        assert mock_service_config.process_check is not None
        assert mock_service_config.basic_health_check is not None

class TestHealthCheckResult:
    """Test health check result model."""
    
    def test_health_check_result_creation(self) -> None:
        """Test health check result creation."""
        result = HealthCheckResult(
            stage=HealthStage.STARTUP,
            success=True,
            check_duration_ms=150
        )
        assert result.stage == HealthStage.STARTUP
        assert result.success is True
        assert result.check_duration_ms == 150
        assert result.error_message is None

    def test_health_check_result_with_error(self) -> None:
        """Test health check result with error."""
        result = HealthCheckResult(
            stage=HealthStage.OPERATIONAL,
            success=False,
            error_message="Service unavailable",
            check_duration_ms=5000
        )
        assert result.success is False
        assert result.error_message == "Service unavailable"

class TestStageConfig:
    """Test stage configuration dataclass."""
    
    def test_stage_config_creation(self) -> None:
        """Test stage config creation."""
        config = StageConfig(
            duration_seconds=60,
            check_interval=10,
            max_failures=5,
            check_function_name="basic_health_check"
        )
        assert config.duration_seconds == 60
        assert config.check_interval == 10
        assert config.max_failures == 5
        assert config.check_function_name == "basic_health_check"

class TestServiceState:
    """Test service state dataclass."""
    
    def test_service_state_creation(self) -> None:
        """Test service state creation with defaults."""
        start_time = datetime.now()
        state = ServiceState(start_time=start_time)
        assert state.start_time == start_time
        assert state.current_stage == HealthStage.INITIALIZATION
        assert state.failure_count == 0
        assert state.last_check is None
        assert len(state.check_history) == 0
        assert state.grace_multiplier == 1.0

class TestStagedHealthMonitorInit:
    """Test staged health monitor initialization."""
    
    def test_monitor_init(self, health_monitor: StagedHealthMonitor) -> None:
        """Test monitor initialization."""
        assert len(health_monitor._services) == 0
        assert len(health_monitor._states) == 0
        assert len(health_monitor._monitoring_tasks) == 0
        assert health_monitor._running is False

    def test_init_stage_configs(self, health_monitor: StagedHealthMonitor) -> None:
        """Test stage configuration initialization."""
        configs = health_monitor._stage_configs
        assert HealthStage.INITIALIZATION in configs
        assert HealthStage.STARTUP in configs
        assert HealthStage.WARMING in configs
        assert HealthStage.OPERATIONAL in configs
        
        init_config = configs[HealthStage.INITIALIZATION]
        assert init_config.duration_seconds == 30
        assert init_config.check_function_name == "process_check"

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
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = Mock()
            mock_create_task.return_value = mock_task
            
            await health_monitor.start_monitoring("test_service")
            
            assert health_monitor._running is True
            assert "test_service" in health_monitor._monitoring_tasks
            mock_create_task.assert_called_once()
    @pytest.mark.asyncio
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

class TestHealthChecks:
    """Test health check execution."""
    @pytest.mark.asyncio
    async def test_check_service_health_success(self, health_monitor: StagedHealthMonitor,
                                               mock_service_config: ServiceConfig) -> None:
        """Test successful health check."""
        health_monitor.register_service(mock_service_config)
        
        with patch.object(health_monitor, '_process_check_result') as mock_process:
            await health_monitor._check_service_health("test_service")
            mock_process.assert_called_once()
            
            # Check the result passed to _process_check_result
            result = mock_process.call_args[0][1]
            assert result.success is True
            assert result.stage == HealthStage.INITIALIZATION
    @pytest.mark.asyncio
    async def test_check_service_health_failure(self, health_monitor: StagedHealthMonitor) -> None:
        """Test health check with failing function."""
        failing_config = ServiceConfig(
            name="failing_service",
            process_check=lambda: False
        )
        health_monitor.register_service(failing_config)
        
        with patch.object(health_monitor, '_process_check_result') as mock_process:
            await health_monitor._check_service_health("failing_service")
            
            result = mock_process.call_args[0][1]
            assert result.success is False
    @pytest.mark.asyncio
    async def test_check_service_health_exception(self, health_monitor: StagedHealthMonitor) -> None:
        """Test health check with exception."""
        async def raise_exception():
            raise Exception("Health check failed")
        
        exception_config = ServiceConfig(
            name="exception_service",
            process_check=raise_exception
        )
        health_monitor.register_service(exception_config)
        
        with patch.object(health_monitor, '_process_check_result') as mock_process:
            await health_monitor._check_service_health("exception_service")
            
            result = mock_process.call_args[0][1]
            assert result.success is False
            assert "Health check failed" in result.error_message
    @pytest.mark.asyncio
    async def test_check_service_health_no_function(self, health_monitor: StagedHealthMonitor) -> None:
        """Test health check when no function is available."""
        no_check_config = ServiceConfig(name="no_check_service")
        health_monitor.register_service(no_check_config)
        
        # Should return without error when no check function
        await health_monitor._check_service_health("no_check_service")

class TestCheckResultProcessing:
    """Test health check result processing."""
    @pytest.mark.asyncio
    async def test_process_check_result_success(self, health_monitor: StagedHealthMonitor,
                                               mock_service_config: ServiceConfig) -> None:
        """Test processing successful check result."""
        health_monitor.register_service(mock_service_config)
        result = HealthCheckResult(stage=HealthStage.STARTUP, success=True)
        
        await health_monitor._process_check_result("test_service", result)
        
        state = health_monitor._states["test_service"]
        assert state.failure_count == 0
        assert len(state.check_history) == 1
    @pytest.mark.asyncio
    async def test_process_check_result_failure(self, health_monitor: StagedHealthMonitor,
                                               mock_service_config: ServiceConfig) -> None:
        """Test processing failed check result."""
        health_monitor.register_service(mock_service_config)
        result = HealthCheckResult(stage=HealthStage.STARTUP, success=False)
        
        with patch.object(health_monitor, '_handle_failure') as mock_handle:
            await health_monitor._process_check_result("test_service", result)
            
            state = health_monitor._states["test_service"]
            assert state.failure_count == 1
            mock_handle.assert_called_once()
    @pytest.mark.asyncio
    async def test_handle_failure_within_threshold(self, health_monitor: StagedHealthMonitor,
                                                  mock_service_config: ServiceConfig) -> None:
        """Test failure handling within threshold."""
        health_monitor.register_service(mock_service_config)
        result = HealthCheckResult(stage=HealthStage.STARTUP, success=False)
        
        # Should log warning but not error
        await health_monitor._handle_failure("test_service", result)
    @pytest.mark.asyncio
    async def test_handle_failure_exceeds_threshold(self, health_monitor: StagedHealthMonitor,
                                                   mock_service_config: ServiceConfig) -> None:
        """Test failure handling when exceeding threshold."""
        health_monitor.register_service(mock_service_config)
        state = health_monitor._states["test_service"]
        state.current_stage = HealthStage.STARTUP
        state.failure_count = 10  # Exceeds threshold of 10
        
        result = HealthCheckResult(stage=HealthStage.STARTUP, success=False)
        
        # Should log error
        await health_monitor._handle_failure("test_service", result)

class TestStageProgression:
    """Test service stage progression."""
    @pytest.mark.asyncio
    async def test_update_service_stage_progression(self, health_monitor: StagedHealthMonitor,
                                                   mock_service_config: ServiceConfig) -> None:
        """Test service stage progression over time."""
        health_monitor.register_service(mock_service_config)
        state = health_monitor._states["test_service"]
        
        # Mock time progression
        old_time = datetime.now() - timedelta(seconds=95)
        state.start_time = old_time
        
        await health_monitor._update_service_stage("test_service")
        
        # Should have progressed to WARMING stage (90+ seconds)
        assert state.current_stage == HealthStage.WARMING
        assert state.failure_count == 0  # Reset on stage change

    def test_calculate_stage_initialization(self, health_monitor: StagedHealthMonitor) -> None:
        """Test stage calculation for initialization period."""
        stage = health_monitor._calculate_stage(25)  # 25 seconds
        assert stage == HealthStage.INITIALIZATION

    def test_calculate_stage_startup(self, health_monitor: StagedHealthMonitor) -> None:
        """Test stage calculation for startup period."""
        stage = health_monitor._calculate_stage(45)  # 45 seconds
        assert stage == HealthStage.STARTUP

    def test_calculate_stage_warming(self, health_monitor: StagedHealthMonitor) -> None:
        """Test stage calculation for warming period."""
        stage = health_monitor._calculate_stage(120)  # 120 seconds
        assert stage == HealthStage.WARMING

    def test_calculate_stage_operational(self, health_monitor: StagedHealthMonitor) -> None:
        """Test stage calculation for operational period."""
        stage = health_monitor._calculate_stage(300)  # 300 seconds
        assert stage == HealthStage.OPERATIONAL

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
        
        await health_monitor._apply_adaptive_rules("test_service")
        
        assert state.grace_multiplier == 1.5
    @pytest.mark.asyncio
    async def test_apply_adaptive_rules_frequent_failures(self, health_monitor: StagedHealthMonitor,
                                                         mock_service_config: ServiceConfig) -> None:
        """Test adaptive rules for frequent failures."""
        health_monitor.register_service(mock_service_config)
        
        # Mock frequent failures
        with patch.object(health_monitor, '_count_recent_failures', return_value=5):
            await health_monitor._apply_adaptive_rules("test_service")
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

    @patch('requests.get')
    def test_create_url_health_check_success(self, mock_get: Mock) -> None:
        """Test URL health check for successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        check = create_url_health_check("http://api.example.com")
        assert check() is True
        mock_get.assert_called_once_with("http://api.example.com", timeout=5)

    @patch('requests.get')
    def test_create_url_health_check_failure(self, mock_get: Mock) -> None:
        """Test URL health check for failed response."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        check = create_url_health_check("http://api.example.com")
        assert check() is False

    @patch('requests.get')
    def test_create_url_health_check_exception(self, mock_get: Mock) -> None:
        """Test URL health check with connection exception."""
        mock_get.side_effect = Exception("Connection failed")
        
        check = create_url_health_check("http://api.example.com")
        assert check() is False

    @patch('requests.get')
    def test_create_url_health_check_custom_timeout(self, mock_get: Mock) -> None:
        """Test URL health check with custom timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        check = create_url_health_check("http://api.example.com", timeout=10)
        check()
        mock_get.assert_called_once_with("http://api.example.com", timeout=10)
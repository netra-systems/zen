"""
Health monitor check tests
Tests health check execution, result processing, and stage progression
COMPLIANCE: 450-line max file, 25-line max functions
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

from datetime import datetime, timedelta

import pytest

from netra_backend.tests.startup.mock_health_monitor import (
    HealthCheckResult,
    HealthStage,
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
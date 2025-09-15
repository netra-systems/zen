"""
Health monitor core tests
Tests core health monitoring models and initialization
COMPLIANCE: 450-line max file, 25-line max functions
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

from datetime import datetime

import pytest

from netra_backend.tests.startup.mock_health_monitor import (
    HealthCheckResult,
    HealthStage,
    ServiceConfig,
    ServiceState,
    StageConfig,
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

class HealthStageTests:
    """Test health stage enumeration."""
    
    def test_health_stage_values(self) -> None:
        """Test all health stage enum values."""
        assert HealthStage.INITIALIZATION == "initialization"
        assert HealthStage.STARTUP == "startup"
        assert HealthStage.WARMING == "warming"
        assert HealthStage.OPERATIONAL == "operational"

class ServiceConfigTests:
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

class HealthCheckResultTests:
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

class StageConfigTests:
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

class ServiceStateTests:
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

class StagedHealthMonitorInitTests:
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
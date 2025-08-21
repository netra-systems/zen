"""Tests for system health monitor."""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from netra_backend.app.core.shared_health_types import ComponentHealth, HealthStatus

# Add project root to path
from netra_backend.app.core.system_health_monitor import (
    SystemHealthMonitor,
    system_health_monitor,
)
from netra_backend.app.schemas.core_models import HealthCheckResult

# Add project root to path


class TestSystemHealthMonitor:
    """Test SystemHealthMonitor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = SystemHealthMonitor(check_interval=1)  # Short interval for testing
    
    def test_monitor_initialization(self):
        """Test monitor initialization."""
        assert self.monitor.check_interval == 1
        assert len(self.monitor.component_health) == 0
        assert self.monitor.alert_manager is not None
        assert self.monitor.health_thresholds["healthy"] == 0.8
        assert self.monitor.health_thresholds["degraded"] == 0.5
        assert self.monitor.health_thresholds["unhealthy"] == 0.2
        assert self.monitor._running is False
        assert len(self.monitor.component_checkers) > 0  # Default checkers registered
    
    def test_register_component_checker(self):
        """Test registering component checker."""
        test_checker = Mock()
        self.monitor.register_component_checker("test_component", test_checker)
        
        assert "test_component" in self.monitor.component_checkers
        assert self.monitor.component_checkers["test_component"] == test_checker
    
    def test_register_alert_callback(self):
        """Test registering alert callback."""
        callback = Mock()
        self.monitor.register_alert_callback(callback)
        
        assert callback in self.monitor.alert_manager.alert_callbacks
    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        assert not self.monitor._running
        
        await self.monitor.start_monitoring()
        assert self.monitor._running
        assert self.monitor._monitoring_task is not None
        
        await self.monitor.stop_monitoring()
        assert not self.monitor._running
    async def test_start_monitoring_already_running(self):
        """Test starting monitoring when already running."""
        await self.monitor.start_monitoring()
        task1 = self.monitor._monitoring_task
        
        await self.monitor.start_monitoring()  # Should not create new task
        task2 = self.monitor._monitoring_task
        
        assert task1 == task2
        await self.monitor.stop_monitoring()
    async def test_stop_monitoring_not_running(self):
        """Test stopping monitoring when not running."""
        # Should not raise exception
        await self.monitor.stop_monitoring()
    async def test_execute_health_check_success(self):
        """Test executing successful health check."""
        expected_result = HealthCheckResult(
            component_name="test", success=True, health_score=0.95,
            response_time_ms=50.0, metadata={"test": "data"}
        )
        
        async def mock_checker():
            return expected_result
        
        result = await self.monitor._execute_health_check("test", mock_checker)
        
        assert result == expected_result
    async def test_execute_health_check_sync_function(self):
        """Test executing sync health check function."""
        expected_result = HealthCheckResult(
            component_name="test", success=True, health_score=1.0, response_time_ms=0.0
        )
        
        def sync_checker():
            return expected_result
        
        result = await self.monitor._execute_health_check("test", sync_checker)
        
        assert result == expected_result
    async def test_execute_health_check_legacy_result(self):
        """Test executing health check with legacy result format."""
        legacy_result = {"health_score": 0.8, "metadata": {"key": "value"}}
        
        async def legacy_checker():
            return legacy_result
        
        result = await self.monitor._execute_health_check("test", legacy_checker)
        
        assert isinstance(result, HealthCheckResult)
        assert result.component_name == "test"
        assert result.health_score == 0.8
        assert result.success is True
        assert result.metadata["key"] == "value"
    async def test_execute_health_check_exception(self):
        """Test executing health check that raises exception."""
        async def failing_checker():
            raise Exception("Health check failed")
        
        result = await self.monitor._execute_health_check("test", failing_checker)
        
        assert result.component_name == "test"
        assert result.success is False
        assert result.health_score == 0.0
        assert "Health check failed" in result.error_message
    
    def test_calculate_health_status(self):
        """Test health status calculation."""
        assert self.monitor._calculate_health_status(0.9) == HealthStatus.HEALTHY
        assert self.monitor._calculate_health_status(0.6) == HealthStatus.DEGRADED
        assert self.monitor._calculate_health_status(0.3) == HealthStatus.UNHEALTHY
        assert self.monitor._calculate_health_status(0.1) == HealthStatus.CRITICAL
    async def test_update_component_from_result(self):
        """Test updating component health from result."""
        result = HealthCheckResult(
            component_name="test_component",
            success=True,
            health_score=0.85,
            response_time_ms=100.0,
            metadata={"connections": 5}
        )
        
        await self.monitor._update_component_from_result(result)
        
        assert "test_component" in self.monitor.component_health
        health = self.monitor.component_health["test_component"]
        assert health.name == "test_component"
        assert health.status == HealthStatus.HEALTHY
        assert health.health_score == 0.85
        assert health.error_count == 0
        assert health.metadata["response_time_ms"] == 100.0
        assert health.metadata["connections"] == 5
    async def test_update_component_status_change_alert(self):
        """Test that status change generates alert."""
        # First, set initial health
        initial_result = HealthCheckResult(
            component_name="test", success=True, health_score=0.9, response_time_ms=50.0
        )
        await self.monitor._update_component_from_result(initial_result)
        
        # Mock alert manager
        self.monitor.alert_manager.create_status_change_alert = AsyncMock()
        self.monitor.alert_manager.emit_alert = AsyncMock()
        
        # Update with degraded health
        degraded_result = HealthCheckResult(
            component_name="test", success=True, health_score=0.3, response_time_ms=200.0
        )
        await self.monitor._update_component_from_result(degraded_result)
        
        self.monitor.alert_manager.create_status_change_alert.assert_called_once()
        self.monitor.alert_manager.emit_alert.assert_called_once()
    
    def test_convert_legacy_result_dict(self):
        """Test converting legacy dict result."""
        legacy = {"health_score": 0.7, "metadata": {"key": "value"}}
        
        result = self.monitor._convert_legacy_result("test", legacy)
        
        assert result.component_name == "test"
        assert result.success is True
        assert result.health_score == 0.7
        assert result.metadata["key"] == "value"
    
    def test_convert_legacy_result_number(self):
        """Test converting legacy numeric result."""
        result = self.monitor._convert_legacy_result("test", 0.8)
        
        assert result.health_score == 0.8
        assert result.success is True
    
    def test_convert_legacy_result_boolean(self):
        """Test converting legacy boolean result."""
        true_result = self.monitor._convert_legacy_result("test", True)
        assert true_result.health_score == 1.0
        assert true_result.success is True
        
        false_result = self.monitor._convert_legacy_result("test", False)
        assert false_result.health_score == 0.0
        assert false_result.success is False
    async def test_check_thresholds_response_time(self):
        """Test threshold checking for response time."""
        # Add component with high response time
        health = ComponentHealth(
            name="slow_component", status=HealthStatus.HEALTHY, health_score=0.9,
            last_check=datetime.now(UTC), metadata={"response_time_ms": 6000}
        )
        self.monitor.component_health["slow_component"] = health
        
        self.monitor.alert_manager.create_threshold_alert = AsyncMock()
        self.monitor.alert_manager.emit_alert = AsyncMock()
        
        await self.monitor._check_thresholds()
        
        self.monitor.alert_manager.create_threshold_alert.assert_called()
        call_args = self.monitor.alert_manager.create_threshold_alert.call_args[0]
        assert call_args[0] == "slow_component"
        assert call_args[1] == "response_time"
        assert call_args[2] == 6000
        assert call_args[3] == 5000
    async def test_check_thresholds_error_count(self):
        """Test threshold checking for error count."""
        # Add component with high error count
        health = ComponentHealth(
            name="error_component", status=HealthStatus.DEGRADED, health_score=0.6,
            last_check=datetime.now(UTC), error_count=10
        )
        self.monitor.component_health["error_component"] = health
        
        self.monitor.alert_manager.create_threshold_alert = AsyncMock()
        self.monitor.alert_manager.emit_alert = AsyncMock()
        
        await self.monitor._check_thresholds()
        
        self.monitor.alert_manager.create_threshold_alert.assert_called()
    async def test_evaluate_system_health_critical(self):
        """Test system health evaluation with critical components."""
        # Add healthy and critical components
        self.monitor.component_health["healthy"] = ComponentHealth(
            name="healthy", status=HealthStatus.HEALTHY, health_score=0.9, last_check=datetime.now(UTC)
        )
        self.monitor.component_health["critical"] = ComponentHealth(
            name="critical", status=HealthStatus.CRITICAL, health_score=0.1, last_check=datetime.now(UTC)
        )
        
        self.monitor._trigger_system_wide_alert = AsyncMock()
        
        await self.monitor._evaluate_system_health()
        
        self.monitor._trigger_system_wide_alert.assert_called_once()
        call_args = self.monitor._trigger_system_wide_alert.call_args[0]
        assert call_args[0] == "critical"
        assert "1 critical components" in call_args[1]
    async def test_evaluate_system_health_degraded(self):
        """Test system health evaluation with degraded system."""
        # Add mostly unhealthy components
        for i in range(5):
            self.monitor.component_health[f"unhealthy_{i}"] = ComponentHealth(
                name=f"unhealthy_{i}", status=HealthStatus.UNHEALTHY,
                health_score=0.3, last_check=datetime.now(UTC)
            )
        
        # Add one healthy component (20% healthy)
        self.monitor.component_health["healthy"] = ComponentHealth(
            name="healthy", status=HealthStatus.HEALTHY, health_score=0.9, last_check=datetime.now(UTC)
        )
        
        self.monitor._trigger_system_wide_alert = AsyncMock()
        
        await self.monitor._evaluate_system_health()
        
        self.monitor._trigger_system_wide_alert.assert_called_once()
        call_args = self.monitor._trigger_system_wide_alert.call_args[0]
        assert call_args[0] == "warning"
    async def test_evaluate_system_health_no_components(self):
        """Test system health evaluation with no components."""
        self.monitor._trigger_system_wide_alert = AsyncMock()
        
        await self.monitor._evaluate_system_health()
        
        self.monitor._trigger_system_wide_alert.assert_not_called()
    
    def test_get_system_overview(self):
        """Test getting system overview."""
        # Add components with different statuses
        self.monitor.component_health["healthy"] = ComponentHealth(
            name="healthy", status=HealthStatus.HEALTHY, health_score=0.9, last_check=datetime.now(UTC)
        )
        self.monitor.component_health["degraded"] = ComponentHealth(
            name="degraded", status=HealthStatus.DEGRADED, health_score=0.6, last_check=datetime.now(UTC)
        )
        self.monitor.component_health["critical"] = ComponentHealth(
            name="critical", status=HealthStatus.CRITICAL, health_score=0.1, last_check=datetime.now(UTC)
        )
        
        overview = self.monitor.get_system_overview()
        
        assert overview["overall_status"] == "critical"  # Due to critical component
        assert overview["total_components"] == 3
        assert overview["healthy_components"] == 1
        assert overview["degraded_components"] == 1
        assert overview["critical_components"] == 1
        assert overview["system_health_percentage"] == pytest.approx(33.33, rel=1e-2)
        assert "uptime_seconds" in overview
    
    def test_get_system_overview_no_components(self):
        """Test system overview with no components."""
        overview = self.monitor.get_system_overview()
        
        assert overview["status"] == "no_components"
        assert "components" in overview
    
    def test_determine_system_status(self):
        """Test system status determination."""
        assert self.monitor._determine_system_status(0.9, 0) == "healthy"
        assert self.monitor._determine_system_status(0.7, 0) == "degraded"
        assert self.monitor._determine_system_status(0.4, 0) == "unhealthy"
        assert self.monitor._determine_system_status(0.9, 1) == "critical"  # Critical component present
    async def test_perform_health_checks_integration(self):
        """Test performing health checks integration."""
        # Register mock checker
        mock_checker = AsyncMock(return_value=HealthCheckResult(
            component_name="test", success=True, health_score=0.8, response_time_ms=50.0
        ))
        self.monitor.register_component_checker("test", mock_checker)
        
        await self.monitor._perform_health_checks()
        
        mock_checker.assert_called_once()
        assert "test" in self.monitor.component_health
        assert self.monitor.component_health["test"].health_score == 0.8
    async def test_process_check_results_with_exception(self):
        """Test processing check results with exceptions."""
        results = [
            HealthCheckResult("success", True, 0.9, 10.0),
            Exception("Test exception"),
            HealthCheckResult("another_success", True, 0.8, 20.0)
        ]
        
        await self.monitor._process_check_results(results)
        
        # Should process successful results despite exception
        assert "success" in self.monitor.component_health
        assert "another_success" in self.monitor.component_health
    
    def test_default_checkers_registered(self):
        """Test that default checkers are registered."""
        expected_checkers = ["postgres", "clickhouse", "redis", "websocket", "system_resources"]
        
        for checker in expected_checkers:
            assert checker in self.monitor.component_checkers
    
    def test_global_instance_available(self):
        """Test that global system health monitor instance is available."""
        assert system_health_monitor is not None
        assert isinstance(system_health_monitor, SystemHealthMonitor)
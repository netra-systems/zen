"""Tests for health monitoring types and enums."""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from datetime import datetime, UTC
from dataclasses import asdict

# Add project root to path

from netra_backend.app.core.health_types import (

# Add project root to path
    HealthStatus, ComponentHealth, SystemAlert, HealthCheckResult,
    SystemResourceMetrics, AlertSeverity, RecoveryAction
)


class TestHealthStatus:
    """Test HealthStatus enum."""
    
    def test_health_status_values(self):
        """Test health status enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.CRITICAL.value == "critical"
    
    def test_health_status_ordering(self):
        """Test health status comparison."""
        # Test that we can compare status values
        status_values = [status.value for status in HealthStatus]
        assert "healthy" in status_values
        assert "critical" in status_values


class TestComponentHealth:
    """Test ComponentHealth dataclass."""
    
    def test_component_health_creation(self):
        """Test creating ComponentHealth instance."""
        health = ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            health_score=0.95,
            last_check=datetime.now(UTC),
            error_count=0,
            uptime=100.0,
            metadata={"test": "data"}
        )
        
        assert health.name == "test_component"
        assert health.status == HealthStatus.HEALTHY
        assert health.health_score == 0.95
        assert health.error_count == 0
        assert health.uptime == 100.0
        assert health.metadata["test"] == "data"
    
    def test_component_health_defaults(self):
        """Test ComponentHealth default values."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            health_score=1.0,
            last_check=datetime.now(UTC)
        )
        
        assert health.error_count == 0
        assert health.uptime == 0.0
        assert health.metadata == {}


class TestSystemAlert:
    """Test SystemAlert dataclass."""
    
    def test_system_alert_creation(self):
        """Test creating SystemAlert instance."""
        alert = SystemAlert(
            alert_id="test_alert_123",
            component="test_component",
            severity="warning",
            message="Test alert message",
            timestamp=datetime.now(UTC),
            resolved=False,
            metadata={"source": "test"}
        )
        
        assert alert.alert_id == "test_alert_123"
        assert alert.component == "test_component"
        assert alert.severity == "warning"
        assert alert.message == "Test alert message"
        assert not alert.resolved
        assert alert.metadata["source"] == "test"
    
    def test_system_alert_defaults(self):
        """Test SystemAlert default values."""
        alert = SystemAlert(
            alert_id="test",
            component="test",
            severity="info",
            message="test",
            timestamp=datetime.now(UTC)
        )
        
        assert not alert.resolved
        assert alert.metadata == {}


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""
    
    def test_health_check_result_creation(self):
        """Test creating HealthCheckResult instance."""
        result = HealthCheckResult(
            component_name="postgres",
            success=True,
            health_score=0.98,
            response_time_ms=45.5,
            error_message="",
            metadata={"connections": 10}
        )
        
        assert result.component_name == "postgres"
        assert result.success is True
        assert result.health_score == 0.98
        assert result.response_time_ms == 45.5
        assert result.error_message == ""
        assert result.metadata["connections"] == 10
    
    def test_health_check_result_failure(self):
        """Test failed health check result."""
        result = HealthCheckResult(
            component_name="redis",
            success=False,
            health_score=0.0,
            response_time_ms=0.0,
            error_message="Connection timeout",
            metadata={"retry_count": 3}
        )
        
        assert result.success is False
        assert result.health_score == 0.0
        assert result.error_message == "Connection timeout"
    
    def test_health_check_result_defaults(self):
        """Test HealthCheckResult default values."""
        result = HealthCheckResult(
            component_name="test",
            success=True,
            health_score=1.0,
            response_time_ms=10.0
        )
        
        assert result.error_message == ""
        assert result.metadata == {}


class TestSystemResourceMetrics:
    """Test SystemResourceMetrics dataclass."""
    
    def test_system_resource_metrics_creation(self):
        """Test creating SystemResourceMetrics instance."""
        metrics = SystemResourceMetrics(
            cpu_usage_percent=25.5,
            memory_usage_percent=60.8,
            disk_usage_percent=45.2,
            network_connections=150
        )
        
        assert metrics.cpu_usage_percent == 25.5
        assert metrics.memory_usage_percent == 60.8
        assert metrics.disk_usage_percent == 45.2
        assert metrics.network_connections == 150
        assert isinstance(metrics.timestamp, datetime)
    
    def test_system_resource_metrics_timestamp_default(self):
        """Test default timestamp generation."""
        metrics = SystemResourceMetrics(
            cpu_usage_percent=0.0,
            memory_usage_percent=0.0,
            disk_usage_percent=0.0,
            network_connections=0
        )
        
        # Timestamp should be recent
        time_diff = datetime.now(UTC) - metrics.timestamp
        assert time_diff.total_seconds() < 1.0


class TestAlertSeverity:
    """Test AlertSeverity enum."""
    
    def test_alert_severity_values(self):
        """Test alert severity enum values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestRecoveryAction:
    """Test RecoveryAction enum."""
    
    def test_recovery_action_values(self):
        """Test recovery action enum values."""
        assert RecoveryAction.RESTART_SERVICE.value == "restart_service"
        assert RecoveryAction.CLEAR_CACHE.value == "clear_cache"
        assert RecoveryAction.SCALE_RESOURCES.value == "scale_resources"
        assert RecoveryAction.NOTIFY_ADMIN.value == "notify_admin"
        assert RecoveryAction.GRACEFUL_SHUTDOWN.value == "graceful_shutdown"
    
    def test_all_recovery_actions_available(self):
        """Test that all expected recovery actions are available."""
        expected_actions = {
            "restart_service", "clear_cache", "scale_resources",
            "notify_admin", "graceful_shutdown"
        }
        actual_actions = {action.value for action in RecoveryAction}
        assert actual_actions == expected_actions
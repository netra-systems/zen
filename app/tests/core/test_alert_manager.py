"""Tests for alert manager functionality."""

import pytest
import time
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta, UTC

from app.core.alert_manager import AlertManager
from app.core.health_types import (
    SystemAlert, AlertSeverity, HealthStatus, ComponentHealth, RecoveryAction
)


class TestAlertManager:
    """Test AlertManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.alert_manager = AlertManager(max_alert_history=100)
    
    def test_alert_manager_initialization(self):
        """Test AlertManager initialization."""
        assert len(self.alert_manager.alerts) == 0
        assert self.alert_manager.max_alert_history == 100
        assert len(self.alert_manager.alert_callbacks) == 0
        assert "notify_admin" in self.alert_manager.recovery_actions
        assert "clear_cache" in self.alert_manager.recovery_actions
    
    def test_register_alert_callback(self):
        """Test registering alert callback."""
        callback = Mock()
        self.alert_manager.register_alert_callback(callback)
        
        assert callback in self.alert_manager.alert_callbacks
    
    def test_register_recovery_action(self):
        """Test registering recovery action."""
        action_handler = AsyncMock()
        self.alert_manager.register_recovery_action(RecoveryAction.RESTART_SERVICE, action_handler)
        
        assert self.alert_manager.recovery_actions[RecoveryAction.RESTART_SERVICE.value] == action_handler
    async def test_emit_alert(self):
        """Test emitting an alert."""
        callback = AsyncMock()
        self.alert_manager.register_alert_callback(callback)
        
        alert = SystemAlert(
            alert_id="test_alert",
            component="test_component",
            severity="warning",
            message="Test alert",
            timestamp=datetime.now(UTC)
        )
        
        await self.alert_manager.emit_alert(alert)
        
        assert alert in self.alert_manager.alerts
        callback.assert_called_once_with(alert)
    async def test_emit_alert_with_sync_callback(self):
        """Test emitting alert with synchronous callback."""
        callback = Mock()
        self.alert_manager.register_alert_callback(callback)
        
        alert = SystemAlert(
            alert_id="test_alert",
            component="test",
            severity="info",
            message="Test",
            timestamp=datetime.now(UTC)
        )
        
        await self.alert_manager.emit_alert(alert)
        
        callback.assert_called_once_with(alert)
    async def test_emit_alert_callback_error(self):
        """Test alert emission with callback error."""
        failing_callback = Mock(side_effect=Exception("Callback failed"))
        working_callback = Mock()
        
        self.alert_manager.register_alert_callback(failing_callback)
        self.alert_manager.register_alert_callback(working_callback)
        
        alert = SystemAlert(
            alert_id="test_alert",
            component="test",
            severity="error",
            message="Test",
            timestamp=datetime.now(UTC)
        )
        
        # Should not raise exception even if callback fails
        await self.alert_manager.emit_alert(alert)
        
        working_callback.assert_called_once_with(alert)
    async def test_create_status_change_alert(self):
        """Test creating status change alert."""
        previous_health = ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            health_score=0.9,
            last_check=datetime.now(UTC),
            error_count=0
        )
        
        current_health = ComponentHealth(
            name="test_component",
            status=HealthStatus.CRITICAL,
            health_score=0.1,
            last_check=datetime.now(UTC),
            error_count=5
        )
        
        alert = await self.alert_manager.create_status_change_alert(previous_health, current_health)
        
        assert alert.component == "test_component"
        assert alert.severity == "critical"
        assert "degraded from healthy to critical" in alert.message
        assert alert.metadata["previous_status"] == "healthy"
        assert alert.metadata["current_status"] == "critical"
    async def test_create_recovery_alert(self):
        """Test creating recovery alert."""
        previous_health = ComponentHealth(
            name="test_component",
            status=HealthStatus.CRITICAL,
            health_score=0.1,
            last_check=datetime.now(UTC)
        )
        
        current_health = ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            health_score=0.95,
            last_check=datetime.now(UTC)
        )
        
        alert = await self.alert_manager.create_status_change_alert(previous_health, current_health)
        
        assert "recovered to healthy" in alert.message
        assert alert.severity == "info"
    async def test_create_threshold_alert(self):
        """Test creating threshold alert."""
        alert = await self.alert_manager.create_threshold_alert(
            "database", "response_time", 8000.0, 5000.0
        )
        
        assert alert.component == "database"
        assert alert.severity == "warning"  # ratio 1.6 should be warning
        assert "exceeded threshold" in alert.message
        assert alert.metadata["metric"] == "response_time"
        assert alert.metadata["value"] == 8000.0
        assert alert.metadata["threshold"] == 5000.0
    async def test_create_threshold_alert_critical(self):
        """Test creating critical threshold alert."""
        alert = await self.alert_manager.create_threshold_alert(
            "memory", "usage_percent", 95.0, 40.0  # ratio > 2.0
        )
        
        assert alert.severity == "critical"
    
    def test_get_recent_alerts(self):
        """Test getting recent alerts."""
        # Add old alert
        old_alert = SystemAlert(
            alert_id="old_alert",
            component="test",
            severity="info",
            message="Old alert",
            timestamp=datetime.now(UTC) - timedelta(hours=25)
        )
        self.alert_manager.alerts.append(old_alert)
        
        # Add recent alert
        recent_alert = SystemAlert(
            alert_id="recent_alert",
            component="test",
            severity="info",
            message="Recent alert",
            timestamp=datetime.now(UTC) - timedelta(hours=1)
        )
        self.alert_manager.alerts.append(recent_alert)
        
        recent_alerts = self.alert_manager.get_recent_alerts(hours=24)
        
        assert len(recent_alerts) == 1
        assert recent_alerts[0] == recent_alert
    
    def test_get_active_alerts(self):
        """Test getting active (unresolved) alerts."""
        resolved_alert = SystemAlert(
            alert_id="resolved",
            component="test",
            severity="info",
            message="Resolved",
            timestamp=datetime.now(UTC),
            resolved=True
        )
        
        active_alert = SystemAlert(
            alert_id="active",
            component="test",
            severity="warning",
            message="Active",
            timestamp=datetime.now(UTC),
            resolved=False
        )
        
        self.alert_manager.alerts.extend([resolved_alert, active_alert])
        
        active_alerts = self.alert_manager.get_active_alerts()
        
        assert len(active_alerts) == 1
        assert active_alerts[0] == active_alert
    
    def test_resolve_alert(self):
        """Test resolving an alert."""
        alert = SystemAlert(
            alert_id="test_alert",
            component="test",
            severity="warning",
            message="Test",
            timestamp=datetime.now(UTC),
            resolved=False
        )
        self.alert_manager.alerts.append(alert)
        
        result = self.alert_manager.resolve_alert("test_alert")
        
        assert result is True
        assert alert.resolved is True
    
    def test_resolve_nonexistent_alert(self):
        """Test resolving non-existent alert."""
        result = self.alert_manager.resolve_alert("nonexistent")
        
        assert result is False
    async def test_alert_history_management(self):
        """Test alert history size management."""
        # Set small history limit
        self.alert_manager.max_alert_history = 3
        
        # Add more alerts than limit
        for i in range(5):
            alert = SystemAlert(
                alert_id=f"alert_{i}",
                component="test",
                severity="info",
                message=f"Alert {i}",
                timestamp=datetime.now(UTC)
            )
            await self.alert_manager.emit_alert(alert)
        
        # Should only keep the last max_alert_history alerts
        assert len(self.alert_manager.alerts) == 3
        assert self.alert_manager.alerts[0].alert_id == "alert_2"
        assert self.alert_manager.alerts[-1].alert_id == "alert_4"
    async def test_recovery_action_execution(self):
        """Test automatic recovery action execution."""
        recovery_handler = AsyncMock()
        self.alert_manager.register_recovery_action(RecoveryAction.CLEAR_CACHE, recovery_handler)
        
        # Create critical alert that should trigger recovery
        alert = SystemAlert(
            alert_id="critical_alert",
            component="memory",
            severity="critical",
            message="Memory usage critical",
            timestamp=datetime.now(UTC)
        )
        
        await self.alert_manager.emit_alert(alert)
        
        # Recovery action should be called
        recovery_handler.assert_called_once_with(alert)
    async def test_recovery_action_error_handling(self):
        """Test recovery action error handling."""
        failing_handler = AsyncMock(side_effect=Exception("Recovery failed"))
        self.alert_manager.register_recovery_action(RecoveryAction.RESTART_SERVICE, failing_handler)
        
        alert = SystemAlert(
            alert_id="test_alert",
            component="database",
            severity="error",
            message="Database error",
            timestamp=datetime.now(UTC)
        )
        
        # Should not raise exception even if recovery fails
        await self.alert_manager.emit_alert(alert)
        
        failing_handler.assert_called_once()
    
    def test_determine_threshold_severity(self):
        """Test threshold severity determination."""
        # Test different ratio ranges
        assert self.alert_manager._determine_threshold_severity(150, 100) == "warning"  # 1.5 ratio
        assert self.alert_manager._determine_threshold_severity(180, 100) == "error"     # 1.8 ratio
        assert self.alert_manager._determine_threshold_severity(250, 100) == "critical"  # 2.5 ratio
    
    def test_determine_recovery_action(self):
        """Test recovery action determination."""
        memory_alert = SystemAlert(
            alert_id="mem_alert", component="memory", severity="error",
            message="Memory high", timestamp=datetime.now(UTC)
        )
        assert self.alert_manager._determine_recovery_action(memory_alert) == "clear_cache"
        
        db_alert = SystemAlert(
            alert_id="db_alert", component="database", severity="error",
            message="DB error", timestamp=datetime.now(UTC)
        )
        assert self.alert_manager._determine_recovery_action(db_alert) == "restart_service"
        
        critical_alert = SystemAlert(
            alert_id="crit_alert", component="system", severity="critical",
            message="System critical", timestamp=datetime.now(UTC)
        )
        assert self.alert_manager._determine_recovery_action(critical_alert) == "notify_admin"
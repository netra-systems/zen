"""Alerting and real-time functionality tests for Quality Monitoring Service"""

import asyncio
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch
import pytest

from netra_backend.app.services.quality_monitoring_service import (

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

    QualityMonitoringService,
    AlertSeverity,
    MetricType
)
from netra_backend.tests.helpers.quality_monitoring_fixtures import (
    real_quality_monitoring_service,
    sample_quality_metrics,
    sample_quality_alert,
    poor_quality_metrics
)
from netra_backend.app.services.quality_gate_service import ContentType
from netra_backend.tests.helpers.quality_monitoring_helpers import (
    record_test_quality_event,
    assert_event_in_buffer,
    assert_event_properties,
    create_test_alert,
    assert_quality_alert_properties,
    assert_quality_alert_values,
    assert_quality_alert_status,
    setup_monitoring_mocks,
    start_and_stop_monitoring,
    assert_monitoring_methods_called
)


class TestAlerting:
    """Test alerting functionality"""
    async def test_alert_management_structure(self):
        """Test alert manager structure"""
        service = QualityMonitoringService()
        
        # Check alert manager exists and has expected structure
        assert service.alert_manager is not None
        assert hasattr(service.alert_manager, 'active_alerts')
        assert hasattr(service.alert_manager, 'alert_history')
        assert isinstance(service.alert_manager.active_alerts, dict)
    async def test_immediate_alert_check(self, poor_quality_metrics):
        """Test immediate alert checking on poor quality"""
        service = QualityMonitoringService()
        
        # Record poor quality event - should trigger immediate alert check
        await service.record_quality_event(
            "failing_agent",
            ContentType.OPTIMIZATION,
            poor_quality_metrics
        )
        
        # Verify the event was recorded
        buffer = service.metrics_collector.get_buffer()
        assert "failing_agent" in buffer
        assert len(buffer["failing_agent"]) == 1


class TestRealTimeMonitoring:
    """Test real-time monitoring functionality"""
    async def test_record_quality_event_real(self, real_quality_monitoring_service, sample_quality_metrics):
        """Test recording quality events with real service"""
        await record_test_quality_event(
            real_quality_monitoring_service, 
            "test_agent", 
            sample_quality_metrics
        )
        
        assert_event_in_buffer(real_quality_monitoring_service, "test_agent", 1)
        buffer = real_quality_monitoring_service.metrics_collector.get_buffer()
        event = buffer["test_agent"][0]
        assert_event_properties(event, "test_agent", 0.75)
    async def test_start_stop_monitoring_real(self, real_quality_monitoring_service):
        """Test monitoring lifecycle"""
        await real_quality_monitoring_service.start_monitoring(interval_seconds=0.001)
        assert real_quality_monitoring_service.monitoring_active is True
        assert real_quality_monitoring_service.monitoring_task is not None
        
        await asyncio.sleep(0.005)
        await real_quality_monitoring_service.stop_monitoring()
        assert real_quality_monitoring_service.monitoring_active is False
    async def test_get_dashboard_data_real(self, real_quality_monitoring_service, sample_quality_metrics):
        """Test dashboard data generation"""
        await record_test_quality_event(
            real_quality_monitoring_service, 
            "dashboard_agent", 
            sample_quality_metrics
        )
        
        alert = create_test_alert("test_alert", AlertSeverity.WARNING, "dashboard_agent")
        real_quality_monitoring_service.alert_manager.active_alerts[alert.id] = alert
        
        dashboard_data = await real_quality_monitoring_service.get_dashboard_data()
        
        from netra_backend.tests.helpers.quality_monitoring_helpers import assert_dashboard_data_structure
        assert_dashboard_data_structure(dashboard_data)


class TestAlertManagement:
    """Test alert management functionality"""
    async def test_acknowledge_resolve_alerts_real(self, real_quality_monitoring_service):
        """Test alert acknowledgment and resolution"""
        alert = create_test_alert("ack_alert", AlertSeverity.WARNING, "test_agent")
        real_quality_monitoring_service.alert_manager.active_alerts[alert.id] = alert
        
        result = await real_quality_monitoring_service.acknowledge_alert(alert.id)
        assert result is True
        assert real_quality_monitoring_service.alert_manager.active_alerts[alert.id].acknowledged is True
        
        result = await real_quality_monitoring_service.resolve_alert(alert.id)
        assert result is True
        assert real_quality_monitoring_service.alert_manager.active_alerts[alert.id].resolved is True
    async def test_acknowledge_nonexistent_alert(self, real_quality_monitoring_service):
        """Test acknowledging non-existent alert"""
        result = await real_quality_monitoring_service.acknowledge_alert("fake_id")
        assert result is False
    
    def test_create_alert_if_needed_critical(self):
        """Test alert creation for critical issues"""
        service = QualityMonitoringService()
        alert = service.alert_manager._create_alert_if_needed(
            MetricType.QUALITY_SCORE,
            0.25,
            "critical_agent",
            "Critical quality issue"
        )
        
        assert alert is not None
        assert_quality_alert_properties(alert, alert.id, AlertSeverity.CRITICAL, "critical_agent")
        assert_quality_alert_values(alert, 0.25, alert.threshold)
    
    def test_create_alert_if_needed_good_quality(self):
        """Test no alert creation for good quality"""
        service = QualityMonitoringService()
        alert = service.alert_manager._create_alert_if_needed(
            MetricType.QUALITY_SCORE,
            0.8,
            "good_agent",
            "Good quality"
        )
        
        assert alert is None


class TestMonitoringWithMocks:
    """Test monitoring functionality with mocks"""
    async def test_monitoring_with_no_data(self):
        """Test monitoring loop with no data"""
        service = QualityMonitoringService()
        service.redis_manager = AsyncMock()
        service.clickhouse_manager = AsyncMock()
        
        # Start and quickly stop monitoring
        await service.start_monitoring(interval_seconds=0.001)
        await asyncio.sleep(0.005)
        await service.stop_monitoring()
        
        # Verify monitoring stopped cleanly
        assert service.monitoring_active is False


class TestDataClasses:
    """Test the data classes used by QualityMonitoringService"""
    
    def test_quality_alert_creation(self):
        """Test QualityAlert dataclass"""
        from netra_backend.app.services.quality_monitoring_service import QualityAlert
        
        alert = QualityAlert(
            id="test_alert",
            timestamp=datetime.now(UTC),
            severity=AlertSeverity.ERROR,
            metric_type=MetricType.QUALITY_SCORE,
            agent="test_agent",
            message="Test message",
            current_value=0.3,
            threshold=0.5,
            details={"context": "test"},
            acknowledged=True,
            resolved=False
        )
        
        assert_quality_alert_properties(alert, "test_alert", AlertSeverity.ERROR, "test_agent")
        assert_quality_alert_values(alert, 0.3, 0.5)
        assert_quality_alert_status(alert, acknowledged=True, resolved=False)
        
    def test_quality_trend_creation(self):
        """Test QualityTrend dataclass"""
        from netra_backend.app.services.quality_monitoring_service import QualityTrend
        
        trend = QualityTrend(
            metric_type=MetricType.QUALITY_SCORE,
            period="hour",
            trend_direction="improving",
            change_percentage=15.5,
            current_average=0.75,
            previous_average=0.65,
            forecast_next_period=0.80,
            confidence=0.85
        )
        
        assert trend.metric_type == MetricType.QUALITY_SCORE
        assert trend.period == "hour"
        assert trend.trend_direction == "improving"
        assert trend.change_percentage == 15.5
        assert trend.confidence == 0.85
        
    def test_agent_quality_profile_creation(self):
        """Test AgentQualityProfile dataclass"""
        from netra_backend.app.services.quality_monitoring_service import AgentQualityProfile
        from netra_backend.app.services.quality_gate_service import QualityLevel
        
        profile = AgentQualityProfile(
            agent_name="test_agent",
            total_requests=100,
            average_quality_score=0.78,
            quality_distribution={QualityLevel.GOOD: 70, QualityLevel.ACCEPTABLE: 30},
            slop_detection_count=5,
            retry_count=12,
            fallback_count=3,
            average_response_time=1.25,
            last_updated=datetime.now(UTC),
            issues=["Low specificity"],
            recommendations=["Add more metrics"]
        )
        
        assert profile.agent_name == "test_agent"
        assert profile.total_requests == 100
        assert profile.average_quality_score == 0.78
        assert profile.slop_detection_count == 5
        assert len(profile.issues) == 1
        assert len(profile.recommendations) == 1
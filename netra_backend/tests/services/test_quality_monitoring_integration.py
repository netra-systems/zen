"""Integration and edge case tests for Quality Monitoring Service"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from netra_backend.app.services.quality_gate_service import (
    ContentType,
    QualityLevel,
    QualityMetrics,
)

# Add project root to path
from netra_backend.app.services.quality_monitoring_service import (
    AlertSeverity,
    MetricType,
    # Add project root to path
    QualityMonitoringService,
)
from .quality_monitoring_fixtures import (
    minimal_quality_metrics,
    service_with_mocks,
)
from .quality_monitoring_helpers import (
    assert_alert_history_max_length,
    assert_buffer_max_length,
    create_alert_history_overflow,
    create_buffer_overflow_events,
    create_test_alert,
)


class TestIntegrationWithOtherServices:
    """Integration tests with other services"""
    async def test_service_component_integration(self):
        """Test service components work together"""
        service = QualityMonitoringService()
        
        # Verify components can communicate
        assert service.alert_manager is not None
        assert service.metrics_collector is not None
        assert service.trend_analyzer is not None
        
        # Test basic integration flow
        from netra_backend.app.services.quality_gate_service import (
            ContentType,
            QualityLevel,
            QualityMetrics,
        )
        metrics = QualityMetrics(overall_score=0.8, quality_level=QualityLevel.GOOD)
        
        await service.record_quality_event("integration_agent", ContentType.GENERAL, metrics)
        
        # Verify event was processed by metrics collector
        buffer = service.metrics_collector.get_buffer()
        assert "integration_agent" in buffer
    async def test_monitoring_cycle_integration(self):
        """Test full monitoring cycle"""
        service = QualityMonitoringService()
        
        # Start monitoring briefly
        await service.start_monitoring(interval_seconds=0.01)
        
        # Add some data
        from netra_backend.app.services.quality_gate_service import (
            ContentType,
            QualityLevel,
            QualityMetrics,
        )
        metrics = QualityMetrics(overall_score=0.6, quality_level=QualityLevel.ACCEPTABLE)
        
        await service.record_quality_event("cycle_agent", ContentType.OPTIMIZATION, metrics)
        
        # Allow one monitoring cycle
        await asyncio.sleep(0.02)
        
        # Stop monitoring
        await service.stop_monitoring()
        
        assert service.monitoring_active is False


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling"""
    async def test_empty_metrics_buffer(self, service_with_mocks):
        """Test behavior with empty metrics buffer"""
        dashboard_data = await service_with_mocks.get_dashboard_data()
        
        assert dashboard_data["overall_stats"]["total_events"] == 0
        assert dashboard_data["overall_stats"]["average_quality"] == 0.0
        assert len(dashboard_data["agent_profiles"]) == 0
    async def test_get_agent_report_nonexistent(self, service_with_mocks):
        """Test getting report for non-existent agent"""
        report = await service_with_mocks.get_agent_report("fake_agent")
        
        assert "error" in report
        assert "No data for agent fake_agent" in report["error"]
    async def test_record_event_with_minimal_metrics(self, service_with_mocks, minimal_quality_metrics):
        """Test recording event with minimal metrics"""
        await service_with_mocks.record_quality_event(
            "minimal_agent",
            ContentType.GENERAL,
            minimal_quality_metrics
        )
        
        buffer = service_with_mocks.metrics_collector.get_buffer()
        assert "minimal_agent" in buffer
        event = buffer["minimal_agent"][0]
        assert event["quality_score"] == 0.5


class TestBufferAndHistoryLimits:
    """Test buffer and history size enforcement"""
    
    def test_buffer_max_length_enforcement(self, service_with_mocks):
        """Test that buffer respects max length"""
        agent_name = "buffer_test_agent"
        create_buffer_overflow_events(service_with_mocks, agent_name, 1050)
        assert_buffer_max_length(service_with_mocks, agent_name, 1000)
    
    def test_alert_history_max_length_enforcement(self, service_with_mocks):
        """Test that alert history respects max length"""
        create_alert_history_overflow(service_with_mocks, 550)
        assert_alert_history_max_length(service_with_mocks, 500)


class TestComplexScenarios:
    """Test complex real-world scenarios"""
    async def test_high_volume_event_processing(self):
        """Test processing high volume of events"""
        service = QualityMonitoringService()
        service.redis_manager = AsyncMock()
        service.clickhouse_manager = AsyncMock()
        
        metrics = QualityMetrics(
            overall_score=0.8,
            quality_level=QualityLevel.GOOD
        )
        
        # Process many events rapidly
        tasks = []
        for i in range(100):
            task = service.record_quality_event(
                f"agent_{i % 5}",  # 5 different agents
                ContentType.OPTIMIZATION,
                metrics
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify all events were buffered
        buffer = service.metrics_collector.get_buffer()
        total_events = sum(len(agent_buffer) for agent_buffer in buffer.values())
        assert total_events == 100
    async def test_concurrent_alert_handling(self):
        """Test handling multiple concurrent alerts"""
        service = QualityMonitoringService()
        
        # Create multiple alerts simultaneously
        alerts = []
        for i in range(10):
            alert = create_test_alert(f"concurrent_alert_{i}")
            alerts.append(alert)
            service.alert_manager.active_alerts[alert.id] = alert
        
        # Acknowledge all alerts concurrently
        tasks = []
        for alert in alerts:
            task = service.acknowledge_alert(alert.id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Verify all acknowledgments succeeded
        assert all(result is True for result in results)
        
        # Verify all alerts are acknowledged
        for alert in alerts:
            assert service.alert_manager.active_alerts[alert.id].acknowledged is True
    async def test_service_resilience_during_failures(self):
        """Test service resilience during component failures"""
        service = QualityMonitoringService()
        
        # Mock Redis failure
        service.redis_manager = AsyncMock()
        service.redis_manager.store_quality_event.side_effect = Exception("Redis connection failed")
        
        # Mock ClickHouse success
        service.clickhouse_manager = AsyncMock()
        
        metrics = QualityMetrics(
            overall_score=0.7,
            quality_level=QualityLevel.GOOD
        )
        
        # Should not raise exception despite Redis failure
        try:
            await service.record_quality_event(
                "resilient_agent",
                ContentType.GENERAL,
                metrics
            )
            # Event should still be in local buffer
            buffer = service.metrics_collector.get_buffer()
            assert "resilient_agent" in buffer
        except Exception as e:
            pytest.fail(f"Service should be resilient to component failures: {e}")


class TestServiceShutdownAndCleanup:
    """Test proper service shutdown and cleanup"""
    async def test_graceful_shutdown_with_active_monitoring(self):
        """Test graceful shutdown while monitoring is active"""
        service = QualityMonitoringService()
        service.redis_manager = AsyncMock()
        service.clickhouse_manager = AsyncMock()
        
        # Start monitoring
        await service.start_monitoring(interval_seconds=0.01)
        assert service.monitoring_active is True
        
        # Add some data
        metrics = QualityMetrics(
            overall_score=0.8,
            quality_level=QualityLevel.GOOD
        )
        
        await service.record_quality_event("shutdown_test", ContentType.GENERAL, metrics)
        
        # Stop monitoring gracefully
        await service.stop_monitoring()
        
        # Verify clean shutdown
        assert service.monitoring_active is False
        
        # Verify data is preserved
        buffer = service.metrics_collector.get_buffer()
        assert "shutdown_test" in buffer
    async def test_alert_history_management(self):
        """Test alert history is properly managed"""
        service = QualityMonitoringService()
        
        # Add alerts to history
        old_alert = create_test_alert("old_alert")
        service.alert_manager.alert_history.append(old_alert)
        
        recent_alert = create_test_alert("recent_alert")  
        service.alert_manager.alert_history.append(recent_alert)
        
        # Verify alerts are in history
        alert_ids = [alert.id for alert in service.alert_manager.alert_history]
        assert "old_alert" in alert_ids
        assert "recent_alert" in alert_ids
        
        # Test getting recent alerts
        recent = service.alert_manager.get_recent_alerts(limit=5)
        assert len(recent) <= 5
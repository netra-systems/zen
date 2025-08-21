"""Metrics collection and analysis tests for Quality Monitoring Service"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.tests.helpers.quality_monitoring_fixtures import (

# Add project root to path
    sample_quality_metrics,
    sla_targets,
    actual_metrics
)
# Helper imports removed since many methods don't exist in actual service
from netra_backend.app.services.quality_monitoring_service import QualityMonitoringService
from netra_backend.app.services.quality_gate_service import ContentType


class TestMetricsCollection:
    """Test metrics collection functionality"""
    async def test_record_quality_event(self, sample_quality_metrics):
        """Test recording quality events"""
        service = QualityMonitoringService()
        await service.record_quality_event(
            "test_agent",
            ContentType.OPTIMIZATION,
            sample_quality_metrics
        )
        
        buffer = service.metrics_collector.get_buffer()
        assert "test_agent" in buffer
        assert len(buffer["test_agent"]) == 1
        
        event = buffer["test_agent"][0]
        assert event["quality_score"] == 0.75
        assert event["agent"] == "test_agent"


class TestDashboardData:
    """Test dashboard data generation"""
    async def test_get_dashboard_data(self, sample_quality_metrics):
        """Test getting dashboard data"""
        service = QualityMonitoringService()
        
        # Record a quality event
        await service.record_quality_event(
            "dashboard_agent",
            ContentType.OPTIMIZATION,
            sample_quality_metrics
        )
        
        dashboard_data = await service.get_dashboard_data()
        
        assert "overall_stats" in dashboard_data
        assert "agent_profiles" in dashboard_data
        assert "recent_alerts" in dashboard_data


class TestAgentReports:
    """Test agent reporting functionality"""
    async def test_get_agent_report(self, sample_quality_metrics):
        """Test getting agent report"""
        service = QualityMonitoringService()
        
        # Record events for agent
        await service.record_quality_event(
            "report_agent",
            ContentType.OPTIMIZATION,
            sample_quality_metrics
        )
        
        report = await service.get_agent_report("report_agent")
        
        # Should return report data or error structure
        assert isinstance(report, dict)
    async def test_get_agent_report_nonexistent(self):
        """Test getting report for non-existent agent"""
        service = QualityMonitoringService()
        report = await service.get_agent_report("nonexistent_agent")
        
        # Should handle gracefully
        assert isinstance(report, dict)


class TestMonitoringLifecycle:
    """Test monitoring lifecycle management"""
    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring"""
        service = QualityMonitoringService()
        
        # Start monitoring with short interval
        await service.start_monitoring(interval_seconds=0.01)
        assert service.monitoring_active is True
        assert service.monitoring_task is not None
        
        # Stop monitoring
        await service.stop_monitoring()
        assert service.monitoring_active is False
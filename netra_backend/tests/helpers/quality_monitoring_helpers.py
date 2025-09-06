from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
"""Helper functions for quality monitoring tests"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.services.quality_gate_service import ContentType
from netra_backend.app.services.quality_monitoring_service import (
    AlertSeverity,
    MetricType,
    QualityAlert,
)

def assert_service_initialization(service):
    """Assert service is properly initialized"""
    assert service.redis_manager is not None
    assert service.clickhouse_manager is not None
    assert service.db_session is not None

def assert_service_collections_initialized(service):
    """Assert service collections are initialized"""
    assert service.alert_manager is not None
    assert service.metrics_collector is not None
    assert service.trend_analyzer is not None

def assert_service_monitoring_state(service, active = False):
    """Assert service monitoring state"""
    assert service.monitoring_active == active
    if not active:
        assert service.monitoring_task is None
    assert isinstance(service.subscribers, set)

def assert_quality_alert_properties(alert, expected_id, expected_severity, expected_agent):
    """Assert quality alert basic properties"""
    assert alert.id == expected_id
    assert alert.severity == expected_severity
    assert alert.agent == expected_agent

def assert_quality_alert_values(alert, expected_current, expected_threshold):
    """Assert quality alert values"""
    assert alert.current_value == expected_current
    assert alert.threshold == expected_threshold

def assert_quality_alert_status(alert, acknowledged = False, resolved = False):
    """Assert quality alert status"""
    assert alert.acknowledged == acknowledged
    assert alert.resolved == resolved

def assert_metrics_response_properties(metrics, expected_confidence):
    """Assert response metrics properties"""
    assert metrics is not None
    assert metrics["confidence"] == expected_confidence
    assert "timestamp" in metrics

def assert_metrics_additional_properties(metrics, latency = None, tokens = None):
    """Assert additional metrics properties"""
    if latency:
        assert metrics["latency"] == latency
    if tokens:
        assert metrics["tokens"] == tokens

def assert_system_metrics_properties(metrics, cpu_usage, memory_usage):
    """Assert system metrics properties"""
    assert metrics["cpu_usage"] == cpu_usage
    assert metrics["memory_usage"] == memory_usage
    assert "timestamp" in metrics

def assert_error_metrics_properties(metrics, error_type, severity):
    """Assert error metrics properties"""
    assert metrics["error_type"] == error_type
    assert metrics["severity"] == severity
    assert "timestamp" in metrics

def assert_threshold_validation_passed(result):
    """Assert threshold validation passed"""
    assert result["passed"] is True

def assert_threshold_validation_failed(result):
    """Assert threshold validation failed"""
    assert result["passed"] is False
    assert "below threshold" in result["message"]

def assert_batch_metrics_count(batch_metrics, expected_count):
    """Assert batch metrics count"""
    assert len(batch_metrics) == expected_count

def assert_statistics_keys(stats):
    """Assert statistics contain required keys"""
    required_keys = ["mean", "median", "std", "min", "max"]
    for key in required_keys:
        assert key in stats

def assert_trend_properties(trend, direction, slope_sign):
    """Assert trend analysis properties"""
    assert trend["direction"] == direction
    if slope_sign == "negative":
        assert trend["slope"] < 0
    elif slope_sign == "positive":
        assert trend["slope"] > 0
    assert "forecast" in trend

def assert_report_structure(report):
    """Assert quality report structure"""
    required_keys = ["summary", "metrics", "recommendations"]
    for key in required_keys:
        assert key in report

def assert_dashboard_data_structure(dashboard_data):
    """Assert dashboard data structure"""
    required_keys = ["overall_stats", "agent_profiles", "recent_alerts", 
                        "quality_distribution", "timestamp"]
    for key in required_keys:
        assert key in dashboard_data

def assert_sla_compliance_structure(report):
    """Assert SLA compliance report structure"""
    assert report["compliant"] is True
    required_metrics = ["availability", "response_time", "error_rate"]
    for metric in required_metrics:
        assert report[metric]["status"] == "met"

def create_test_alert(alert_id, severity = AlertSeverity.WARNING, agent = "test_agent"):
    """Create test alert with common defaults"""
    return QualityAlert(
        id = alert_id,
        timestamp = datetime.now(UTC),
        severity = severity,
        metric_type = MetricType.QUALITY_SCORE,
        agent = agent,
        message = "Test alert",
        current_value = 0.4,
        threshold = 0.5,
)

async def record_test_quality_event(service, agent_name = "test_agent", metrics = None):
    """Record a test quality event"""
    if metrics is None:
        from netra_backend.app.services.quality_gate_service import (
            QualityLevel,
            QualityMetrics,
        )
        metrics == QualityMetrics(overall_score = 0.75, quality_level = QualityLevel.GOOD)
    
    await service.record_quality_event(
        agent_name = agent_name,
        content_type = ContentType.OPTIMIZATION,
        metrics = metrics,
        user_id = "user123",
        thread_id = "thread456",
        run_id = "run789",
)

def assert_event_in_buffer(service, agent_name, expected_count = 1):
    """Assert event was added to service buffer"""
    buffer = service.metrics_collector.get_buffer()
    assert agent_name in buffer
    assert len(buffer[agent_name]) == expected_count

def assert_event_properties(event, agent_name, quality_score, user_id = "user123"):
    """Assert event properties"""
    assert event["agent"] == agent_name
    assert event["quality_score"] == quality_score
    assert event["user_id"] == user_id

async def setup_monitoring_mocks(service):
    """Setup monitoring method mocks"""
    service._collect_metrics = AsyncMock()
    service._analyze_trends = AsyncMock(return_value = [])
    service._check_thresholds = AsyncMock(return_value = [])
    service._update_agent_profiles = AsyncMock()
    service._broadcast_updates = AsyncMock()
    service._persist_metrics = AsyncMock()

async def start_and_stop_monitoring(service, interval = 0.001, sleep_duration = 0.005):
    """Start monitoring, wait briefly, then stop"""
    await service.start_monitoring(interval_seconds = interval)
    await asyncio.sleep(sleep_duration)
    await service.stop_monitoring()

def assert_monitoring_methods_called(service):
    """Assert monitoring methods were called"""
    assert service._collect_metrics.called
    assert service._analyze_trends.called

def create_buffer_overflow_events(service, agent_name, count = 1050):
    """Create events that exceed buffer capacity"""
    for i in range(count):
        event = {"quality_score": 0.5, "timestamp": datetime.now(UTC).isoformat()}
        service.metrics_collector.metrics_buffer[agent_name].append(event)

def create_alert_history_overflow(service, count = 550):
    """Create alerts that exceed history capacity"""
    for i in range(count):
        alert = create_test_alert(f"alert_{i}")
        service.alert_manager.alert_history.append(alert)

def assert_buffer_max_length(service, agent_name, max_length = 1000):
    """Assert buffer respects max length"""
    assert len(service.metrics_collector.metrics_buffer[agent_name]) == max_length

def assert_alert_history_max_length(service, max_length = 500):
    """Assert alert history respects max length"""
    assert len(service.alert_manager.alert_history) == max_length
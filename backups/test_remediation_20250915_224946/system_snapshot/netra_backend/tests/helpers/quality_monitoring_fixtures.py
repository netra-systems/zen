from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
"""Fixtures for quality monitoring tests"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from netra_backend.app.services.quality_gate_service import (
    ContentType,
    QualityLevel,
    QualityMetrics,
)
from netra_backend.app.services.quality_monitoring_service import (
    AgentQualityProfile,
    AlertSeverity,
    MetricType,
    QualityAlert,
    QualityMonitoringService,
    QualityTrend,
)

@pytest.fixture
def mock_redis_manager():
    """Mock Redis manager"""
    redis_manager = AsyncMock()
    redis_manager.store_quality_event = AsyncMock()
    redis_manager.get_recent_quality_metrics = AsyncMock(return_value = [])
    redis_manager.store_agent_profile = AsyncMock()
    return redis_manager

@pytest.fixture
def mock_clickhouse_manager():
    """Mock ClickHouse manager"""
    clickhouse_manager = AsyncMock()
    clickhouse_manager.insert_quality_event = AsyncMock()
    clickhouse_manager.batch_insert_quality_events = AsyncMock()
    return clickhouse_manager

@pytest.fixture
def mock_db_session():
    """Mock database session"""
    return AsyncMock()

@pytest.fixture
def quality_monitoring_service(mock_redis_manager, mock_clickhouse_manager, mock_db_session):
    """Create service instance with mocked dependencies"""
    return QualityMonitoringService(
        redis_manager = mock_redis_manager,
        clickhouse_manager = mock_clickhouse_manager,
        db_session = mock_db_session,
)

@pytest.fixture
def real_quality_monitoring_service():
    """Create real service for testing actual methods"""
    return QualityMonitoringService()

@pytest.fixture
def service_with_mocks():
    """Service with minimal mocking for edge case testing"""
    service = QualityMonitoringService()
    service.redis_manager = AsyncMock()
    service.clickhouse_manager = AsyncMock()
    return service

@pytest.fixture
def sample_quality_metrics():
    """Sample quality metrics for testing"""
    return QualityMetrics(
        overall_score = 0.75,
        quality_level = QualityLevel.GOOD,
        specificity_score = 0.8,
        actionability_score = 0.7,
        quantification_score = 0.75,
        word_count = 150,
        generic_phrase_count = 1,
        circular_reasoning_detected = False,
        hallucination_risk = 0.1,
        issues = [],
)

@pytest.fixture
def poor_quality_metrics():
    """Poor quality metrics for testing alerts"""
    return QualityMetrics(
        overall_score = 0.25,
        quality_level = QualityLevel.POOR,
        specificity_score = 0.3,
        actionability_score = 0.2,
        quantification_score = 0.25,
        word_count = 50,
        generic_phrase_count = 5,
        circular_reasoning_detected = True,
        hallucination_risk = 0.8,
        issues = ["Low quality", "Generic content"],
)

@pytest.fixture
def minimal_quality_metrics():
    """Minimal quality metrics for testing"""
    return QualityMetrics(
        overall_score = 0.5,
        quality_level = QualityLevel.ACCEPTABLE,
)

@pytest.fixture
def sample_quality_alert():
    """Sample quality alert for testing"""
    return QualityAlert(
        id = "test_alert",
        timestamp = datetime.now(UTC),
        severity = AlertSeverity.WARNING,
        metric_type = MetricType.QUALITY_SCORE,
        agent = "test_agent",
        message = "Test alert",
        current_value = 0.4,
        threshold = 0.5,
)

@pytest.fixture
def test_quality_thresholds():
    """Test quality thresholds"""
    return {
        "min_confidence": 0.8,
        "max_latency": 2.0,
        "max_error_rate": 0.05,
}

@pytest.fixture
def custom_config():
    """Custom configuration for service"""
    return {
        "alert_threshold": 0.95,
        "monitoring_interval": 30,
        "retention_days": 30,
}

@pytest.fixture
def sample_response_data():
    """Sample response data for metrics collection"""
    return {
        "content": "Test response",
        "confidence": 0.95,
        "latency": 1.2,
        "tokens": 150,
}

@pytest.fixture
def batch_responses():
    """Batch response data for testing"""
    return [
        {"id": 1, "confidence": 0.9},
        {"id": 2, "confidence": 0.85},
        {"id": 3, "confidence": 0.95},
]

@pytest.fixture
def error_data():
    """Sample error data for metrics"""
    return {
        "type": "ValidationError",
        "message": "Invalid input",
        "code": "E001",
        "severity": "high",
}

@pytest.fixture
def historical_data():
    """Historical data for trend analysis"""
    return [0.85, 0.9, 0.88, 0.92, 0.87]

@pytest.fixture
def sla_targets():
    """SLA targets for compliance testing"""
    return {
        "availability": 99.9,
        "response_time": 2.0,
        "error_rate": 0.01,
}

@pytest.fixture
def actual_metrics():
    """Actual metrics for SLA testing"""
    return {
        "availability": 99.95,
        "response_time": 1.8,
        "error_rate": 0.008,
}

@pytest.fixture
def anomaly_values():
    """Values with anomalies for detection testing"""
    return [0.9, 0.88, 0.91, 0.89, 0.3, 0.92, 0.87, 1.5]

@pytest.fixture
def response_times():
    """Sample response times for monitoring"""
    return [1.2, 1.5, 1.1, 2.3, 1.4, 1.3]
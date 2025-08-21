"""Basic tests for Quality Monitoring Service"""

import sys
from unittest.mock import MagicMock, Mock, patch
import pytest

# Mock ClickHouseManager before importing the service
sys.modules['app.db.clickhouse'] = MagicMock()
sys.modules['app.db.clickhouse'].ClickHouseManager = MagicMock

from netra_backend.app.services.quality_monitoring_service import QualityMonitoringService
from tests.helpers.quality_monitoring_fixtures import (
    mock_redis_manager,
    mock_clickhouse_manager, 
    mock_db_session,
    quality_monitoring_service
)
from tests.helpers.quality_monitoring_helpers import (
    assert_service_initialization,
    assert_service_collections_initialized,
    assert_service_monitoring_state
)


class TestQualityMonitoringServiceBasic:
    """Test basic functionality of QualityMonitoringService"""
    async def test_service_initialization(self, quality_monitoring_service):
        """Test service initialization with dependencies"""
        assert_service_initialization(quality_monitoring_service)
        assert_service_collections_initialized(quality_monitoring_service)
        assert_service_monitoring_state(quality_monitoring_service, active=False)
        
    def test_initialization_with_dependencies(self, mock_redis_manager, mock_clickhouse_manager, mock_db_session):
        """Test service initializes with custom dependencies"""
        service = QualityMonitoringService(
            redis_manager=mock_redis_manager,
            clickhouse_manager=mock_clickhouse_manager,
            db_session=mock_db_session
        )
        assert service.redis_manager is mock_redis_manager
        assert service.clickhouse_manager is mock_clickhouse_manager
        assert service.db_session is mock_db_session
        
    def test_initialization_components(self):
        """Test service initializes with required components"""
        service = QualityMonitoringService()
        assert service.alert_manager is not None
        assert service.metrics_collector is not None
        assert service.trend_analyzer is not None


class TestQualityThresholds:
    """Test quality threshold management"""
    
    def test_alert_thresholds_exist(self):
        """Test that alert thresholds are defined"""
        service = QualityMonitoringService()
        from app.services.quality_monitoring.models import MetricType, AlertSeverity
        thresholds = service.alert_manager.ALERT_THRESHOLDS
        
        # Test specific threshold exists
        assert MetricType.QUALITY_SCORE in thresholds
        quality_thresholds = thresholds[MetricType.QUALITY_SCORE]
        assert AlertSeverity.WARNING in quality_thresholds
        assert AlertSeverity.ERROR in quality_thresholds
        assert AlertSeverity.CRITICAL in quality_thresholds


class TestServiceSubscription:
    """Test subscription management"""
    async def test_subscribe_and_unsubscribe(self):
        """Test subscription lifecycle"""
        service = QualityMonitoringService()
        subscriber_id = "test_subscriber"
        
        await service.subscribe_to_updates(subscriber_id)
        assert subscriber_id in service.subscribers
        
        await service.unsubscribe_from_updates(subscriber_id)
        assert subscriber_id not in service.subscribers


class TestServiceConstants:
    """Test service constants and configurations"""
    
    def test_alert_thresholds_structure(self):
        """Test alert thresholds are properly defined"""
        from app.services.quality_monitoring.models import MetricType, AlertSeverity
        service = QualityMonitoringService()
        thresholds = service.alert_manager.ALERT_THRESHOLDS
        
        required_metrics = [
            MetricType.QUALITY_SCORE,
            MetricType.SLOP_DETECTION_RATE,
            MetricType.RETRY_RATE,
            MetricType.FALLBACK_RATE,
            MetricType.ERROR_RATE
        ]
        
        for metric_type in required_metrics:
            assert metric_type in thresholds
            self._assert_severity_thresholds_exist(thresholds, metric_type)
    
    def _assert_severity_thresholds_exist(self, thresholds, metric_type):
        """Assert all severity thresholds exist"""
        from app.services.quality_monitoring.models import AlertSeverity
        assert AlertSeverity.WARNING in thresholds[metric_type]
        assert AlertSeverity.ERROR in thresholds[metric_type]
        assert AlertSeverity.CRITICAL in thresholds[metric_type]
        
    def test_alert_threshold_values(self):
        """Test alert threshold values are reasonable"""
        from app.services.quality_monitoring.models import MetricType, AlertSeverity
        service = QualityMonitoringService()
        thresholds = service.alert_manager.ALERT_THRESHOLDS
        
        quality_thresholds = thresholds[MetricType.QUALITY_SCORE]
        assert quality_thresholds[AlertSeverity.WARNING] > quality_thresholds[AlertSeverity.ERROR]
        assert quality_thresholds[AlertSeverity.ERROR] > quality_thresholds[AlertSeverity.CRITICAL]
        
        self._assert_all_thresholds_valid_range(thresholds)
    
    def _assert_all_thresholds_valid_range(self, thresholds):
        """Assert all thresholds are in valid range"""
        for metric_type, severity_thresholds in thresholds.items():
            for severity, threshold in severity_thresholds.items():
                assert 0 <= threshold <= 1


class TestEnumValues:
    """Test enum values used by service"""
    
    def test_alert_severity_enum_values(self):
        """Test AlertSeverity enum values"""
        from app.services.quality_monitoring.models import AlertSeverity
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"
    
    def test_metric_type_enum_values(self):
        """Test MetricType enum values"""
        from app.services.quality_monitoring.models import MetricType
        assert MetricType.QUALITY_SCORE.value == "quality_score"
        assert MetricType.SLOP_DETECTION_RATE.value == "slop_detection_rate"
        assert MetricType.RETRY_RATE.value == "retry_rate"
        assert MetricType.FALLBACK_RATE.value == "fallback_rate"
        assert MetricType.USER_SATISFACTION.value == "user_satisfaction"
        assert MetricType.RESPONSE_TIME.value == "response_time"
        assert MetricType.TOKEN_EFFICIENCY.value == "token_efficiency"
        assert MetricType.ERROR_RATE.value == "error_rate"
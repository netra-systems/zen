"""Comprehensive tests for Quality Monitoring Service"""

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import pytest
from collections import deque, defaultdict
import sys

# Mock ClickHouseManager before importing the service
sys.modules['app.db.clickhouse'] = MagicMock()
sys.modules['app.db.clickhouse'].ClickHouseManager = MagicMock

from app.services.quality_monitoring_service import (
    QualityMonitoringService,
    AlertSeverity,
    MetricType,
    QualityAlert,
    QualityTrend,
    AgentQualityProfile
)
from app.services.quality_gate_service import QualityLevel, ContentType, QualityMetrics


class TestQualityMonitoringService:
    """Test suite for QualityMonitoringService"""
    
    @pytest.fixture
    def mock_redis_manager(self):
        """Mock Redis manager"""
        redis_manager = AsyncMock()
        redis_manager.store_quality_event = AsyncMock()
        redis_manager.get_recent_quality_metrics = AsyncMock(return_value=[])
        redis_manager.store_agent_profile = AsyncMock()
        return redis_manager
    
    @pytest.fixture
    def mock_clickhouse_manager(self):
        """Mock ClickHouse manager"""
        clickhouse_manager = AsyncMock()
        clickhouse_manager.insert_quality_event = AsyncMock()
        clickhouse_manager.batch_insert_quality_events = AsyncMock()
        return clickhouse_manager
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_redis_manager, mock_clickhouse_manager, mock_db_session):
        """Create service instance with mocked dependencies"""
        return QualityMonitoringService(
            redis_manager=mock_redis_manager,
            clickhouse_manager=mock_clickhouse_manager,
            db_session=mock_db_session
        )
    
    @pytest.fixture
    def sample_metrics(self):
        """Sample quality metrics for testing"""
        return QualityMetrics(
            overall_score=0.75,
            quality_level=QualityLevel.GOOD,
            specificity_score=0.8,
            actionability_score=0.7,
            quantification_score=0.75,
            word_count=150,
            generic_phrase_count=1,
            circular_reasoning_detected=False,
            hallucination_risk=0.1,
            issues=[]
        )
    
    @pytest.fixture
    def poor_metrics(self):
        """Poor quality metrics for testing alerts"""
        return QualityMetrics(
            overall_score=0.25,
            quality_level=QualityLevel.POOR,
            specificity_score=0.3,
            actionability_score=0.2,
            quantification_score=0.25,
            word_count=50,
            generic_phrase_count=5,
            circular_reasoning_detected=True,
            hallucination_risk=0.8,
            issues=["Low quality", "Generic content"]
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, service):
        """Test service initialization"""
        assert service.redis_manager != None
        assert service.clickhouse_manager != None
        assert service.db_session != None
        assert isinstance(service.metrics_buffer, defaultdict)
        assert isinstance(service.alert_history, deque)
        assert isinstance(service.active_alerts, dict)
        assert isinstance(service.agent_profiles, dict)
        assert service.monitoring_active == False
        assert service.monitoring_task == None
        assert isinstance(service.subscribers, set)
        
    def test_initialization_with_custom_config(self):
        """Test service initializes with custom configuration"""
        config = {
            "alert_threshold": 0.95,
            "monitoring_interval": 30,
            "retention_days": 30
        }
        service = QualityMonitoringService(config=config)
        assert service.config["alert_threshold"] == 0.95
        assert service.config["monitoring_interval"] == 30
        assert service.config["retention_days"] == 30
        
    @patch('app.services.quality_monitoring_service.MetricsCollector')
    def test_initialization_with_metrics_collector(self, mock_collector):
        """Test service initializes with metrics collector"""
        mock_collector_instance = Mock()
        mock_collector.return_value = mock_collector_instance
        
        service = QualityMonitoringService()
        assert service.metrics_collector != None
        mock_collector.assert_called_once()


class TestMetricsCollection:
    """Test metrics collection functionality"""
    
    @pytest.mark.asyncio
    async def test_collect_response_quality_metrics(self):
        """Test collection of response quality metrics"""
        service = QualityMonitoringService()
        
        response = {
            "content": "Test response",
            "confidence": 0.95,
            "latency": 1.2,
            "tokens": 150
        }
        
        metrics = await service.collect_response_metrics(response)
        
        assert metrics != None
        assert metrics["confidence"] == 0.95
        assert metrics["latency"] == 1.2
        assert metrics["tokens"] == 150
        assert "timestamp" in metrics
        
    @pytest.mark.asyncio
    async def test_collect_system_metrics(self):
        """Test collection of system metrics"""
        service = QualityMonitoringService()
        
        with patch('psutil.cpu_percent', return_value=45.5):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.percent = 62.3
                
                metrics = await service.collect_system_metrics()
                
        assert metrics["cpu_usage"] == 45.5
        assert metrics["memory_usage"] == 62.3
        assert "timestamp" in metrics
        
    @pytest.mark.asyncio
    async def test_collect_error_metrics(self):
        """Test collection of error metrics"""
        service = QualityMonitoringService()
        
        error = {
            "type": "ValidationError",
            "message": "Invalid input",
            "code": "E001",
            "severity": "high"
        }
        
        metrics = await service.collect_error_metrics(error)
        
        assert metrics["error_type"] == "ValidationError"
        assert metrics["severity"] == "high"
        assert "timestamp" in metrics
        
    @pytest.mark.asyncio
    async def test_batch_metrics_collection(self):
        """Test batch collection of metrics"""
        service = QualityMonitoringService()
        
        responses = [
            {"id": 1, "confidence": 0.9},
            {"id": 2, "confidence": 0.85},
            {"id": 3, "confidence": 0.95}
        ]
        
        batch_metrics = await service.collect_batch_metrics(responses)
        
        assert len(batch_metrics) == 3
        assert batch_metrics[0]["confidence"] == 0.9
        assert batch_metrics[2]["confidence"] == 0.95


class TestQualityThresholds:
    """Test quality threshold management"""
    
    def test_set_quality_thresholds(self):
        """Test setting quality thresholds"""
        service = QualityMonitoringService()
        
        thresholds = {
            "min_confidence": 0.8,
            "max_latency": 2.0,
            "max_error_rate": 0.05
        }
        
        service.set_thresholds(thresholds)
        
        assert service.thresholds["min_confidence"] == 0.8
        assert service.thresholds["max_latency"] == 2.0
        assert service.thresholds["max_error_rate"] == 0.05
        
    def test_validate_against_thresholds(self):
        """Test validation against thresholds"""
        service = QualityMonitoringService()
        service.set_thresholds({"min_confidence": 0.8})
        
        # Test passing validation
        result = service.validate_metric("confidence", 0.9)
        assert result["passed"] == True
        
        # Test failing validation
        result = service.validate_metric("confidence", 0.7)
        assert result["passed"] == False
        assert "below threshold" in result["message"]
        
    def test_dynamic_threshold_adjustment(self):
        """Test dynamic threshold adjustment based on historical data"""
        service = QualityMonitoringService()
        
        # Simulate historical data
        historical_data = [0.85, 0.9, 0.88, 0.92, 0.87]
        
        new_threshold = service.calculate_dynamic_threshold(
            historical_data, 
            percentile=25
        )
        
        assert new_threshold > 0.85
        assert new_threshold < 0.92


class TestAlerting:
    """Test alerting functionality"""
    
    @pytest.mark.asyncio
    async def test_trigger_alert_on_threshold_breach(self):
        """Test alert triggered when threshold breached"""
        service = QualityMonitoringService()
        service.set_thresholds({"min_confidence": 0.8})
        
        with patch.object(service, 'send_alert', new_callable=AsyncMock) as mock_alert:
            await service.check_and_alert("confidence", 0.7)
            
        mock_alert.assert_called_once()
        alert_data = mock_alert.call_args[0][0]
        assert alert_data["metric"] == "confidence"
        assert alert_data["value"] == 0.7
        assert alert_data["threshold"] == 0.8
        
    @pytest.mark.asyncio
    async def test_alert_rate_limiting(self):
        """Test alert rate limiting to prevent spam"""
        service = QualityMonitoringService()
        service.alert_cooldown = 60  # 1 minute cooldown
        
        with patch.object(service, 'send_alert', new_callable=AsyncMock) as mock_alert:
            # First alert should be sent
            await service.check_and_alert("confidence", 0.7)
            # Second alert should be suppressed
            await service.check_and_alert("confidence", 0.6)
            
        assert mock_alert.call_count == 1
        
    @pytest.mark.asyncio
    async def test_alert_escalation(self):
        """Test alert escalation for critical issues"""
        service = QualityMonitoringService()
        
        critical_alert = {
            "severity": "critical",
            "metric": "error_rate",
            "value": 0.15,
            "threshold": 0.05
        }
        
        with patch.object(service, 'escalate_alert', new_callable=AsyncMock) as mock_escalate:
            await service.handle_critical_alert(critical_alert)
            
        mock_escalate.assert_called_once()


class TestMetricsAggregation:
    """Test metrics aggregation and analysis"""
    
    @pytest.mark.asyncio
    async def test_aggregate_metrics_by_time_window(self):
        """Test aggregation of metrics by time window"""
        service = QualityMonitoringService()
        
        # Add sample metrics
        now = datetime.now()
        for i in range(10):
            metric = {
                "timestamp": now - timedelta(minutes=i),
                "confidence": 0.8 + (i * 0.01),
                "latency": 1.0 + (i * 0.1)
            }
            await service.store_metric(metric)
            
        # Aggregate last 5 minutes
        aggregated = await service.aggregate_metrics(
            window_minutes=5,
            aggregation="mean"
        )
        
        assert "confidence" in aggregated
        assert "latency" in aggregated
        assert aggregated["confidence"] > 0.8
        
    @pytest.mark.asyncio
    async def test_calculate_statistics(self):
        """Test calculation of statistical metrics"""
        service = QualityMonitoringService()
        
        values = [0.85, 0.9, 0.88, 0.92, 0.87, 0.95, 0.83]
        
        stats = await service.calculate_statistics(values)
        
        assert "mean" in stats
        assert "median" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats
        assert stats["mean"] == pytest.approx(0.886, rel=0.01)
        
    @pytest.mark.asyncio
    async def test_trend_analysis(self):
        """Test trend analysis for metrics"""
        service = QualityMonitoringService()
        
        # Create trending data
        timestamps = []
        values = []
        now = datetime.now()
        for i in range(20):
            timestamps.append(now - timedelta(hours=i))
            values.append(0.8 - (i * 0.01))  # Declining trend
            
        trend = await service.analyze_trend(timestamps, values)
        
        assert trend["direction"] == "declining"
        assert trend["slope"] < 0
        assert "forecast" in trend


class TestQualityReporting:
    """Test quality reporting functionality"""
    
    @pytest.mark.asyncio
    async def test_generate_quality_report(self):
        """Test generation of quality report"""
        service = QualityMonitoringService()
        
        # Add sample metrics
        await service.store_metric({"confidence": 0.9, "latency": 1.2})
        await service.store_metric({"confidence": 0.85, "latency": 1.5})
        await service.store_metric({"confidence": 0.92, "latency": 1.1})
        
        report = await service.generate_quality_report()
        
        assert "summary" in report
        assert "metrics" in report
        assert "recommendations" in report
        assert report["summary"]["total_metrics"] == 3
        
    @pytest.mark.asyncio
    async def test_export_metrics_to_json(self):
        """Test exporting metrics to JSON format"""
        service = QualityMonitoringService()
        
        # Add sample metrics
        metrics = [
            {"id": 1, "confidence": 0.9},
            {"id": 2, "confidence": 0.85}
        ]
        
        for metric in metrics:
            await service.store_metric(metric)
            
        exported = await service.export_metrics("json")
        
        data = json.loads(exported)
        assert len(data["metrics"]) == 2
        assert data["exported_at"] != None
        
    @pytest.mark.asyncio
    async def test_generate_sla_compliance_report(self):
        """Test SLA compliance reporting"""
        service = QualityMonitoringService()
        
        sla_targets = {
            "availability": 99.9,
            "response_time": 2.0,
            "error_rate": 0.01
        }
        
        actual_metrics = {
            "availability": 99.95,
            "response_time": 1.8,
            "error_rate": 0.008
        }
        
        report = await service.check_sla_compliance(sla_targets, actual_metrics)
        
        assert report["compliant"] == True
        assert report["availability"]["status"] == "met"
        assert report["response_time"]["status"] == "met"
        assert report["error_rate"]["status"] == "met"


class TestAnomalyDetection:
    """Test anomaly detection in quality metrics"""
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_zscore(self):
        """Test anomaly detection using Z-score method"""
        service = QualityMonitoringService()
        
        # Normal values with outliers
        values = [0.9, 0.88, 0.91, 0.89, 0.3, 0.92, 0.87, 1.5]  # 0.3 and 1.5 are anomalies
        
        anomalies = await service.detect_anomalies(values, method="zscore", threshold=2)
        
        assert len(anomalies) == 2
        assert 0.3 in anomalies
        assert 1.5 in anomalies
        
    @pytest.mark.asyncio
    async def test_detect_anomalies_iqr(self):
        """Test anomaly detection using IQR method"""
        service = QualityMonitoringService()
        
        values = list(range(1, 21)) + [100, -50]  # 100 and -50 are outliers
        
        anomalies = await service.detect_anomalies(values, method="iqr")
        
        assert 100 in anomalies
        assert -50 in anomalies
        
    @pytest.mark.asyncio
    async def test_real_time_anomaly_detection(self):
        """Test real-time anomaly detection on streaming data"""
        service = QualityMonitoringService()
        
        # Configure anomaly detector
        service.configure_anomaly_detector(
            window_size=10,
            sensitivity=0.95
        )
        
        # Stream data with anomaly
        normal_value = 0.9
        anomaly_detected = False
        
        for i in range(15):
            if i == 10:
                value = 0.3  # Anomaly
            else:
                value = normal_value + np.random.normal(0, 0.02)
                
            is_anomaly = await service.check_anomaly_realtime(value)
            if is_anomaly and i == 10:
                anomaly_detected = True
                
        assert anomaly_detected == True


class TestPerformanceMonitoring:
    """Test performance monitoring capabilities"""
    
    @pytest.mark.asyncio
    async def test_monitor_response_times(self):
        """Test monitoring of response times"""
        service = QualityMonitoringService()
        
        response_times = [1.2, 1.5, 1.1, 2.3, 1.4, 1.3]
        
        for rt in response_times:
            await service.record_response_time(rt)
            
        stats = await service.get_response_time_stats()
        
        assert stats["p50"] < stats["p95"]
        assert stats["mean"] == pytest.approx(1.47, rel=0.01)
        assert stats["max"] == 2.3
        
    @pytest.mark.asyncio
    async def test_monitor_throughput(self):
        """Test monitoring of system throughput"""
        service = QualityMonitoringService()
        
        # Simulate requests over time
        start_time = datetime.now()
        for i in range(100):
            await service.record_request()
            
        throughput = await service.calculate_throughput(start_time)
        
        assert throughput > 0
        assert "requests_per_second" in throughput
        assert "requests_per_minute" in throughput


class TestIntegration:
    """Integration tests with other services"""
    
    @pytest.mark.asyncio
    async def test_integration_with_agent_service(self):
        """Test integration with agent service for quality monitoring"""
        service = QualityMonitoringService()
        
        with patch('app.services.agent_service.AgentService') as mock_agent:
            mock_agent_instance = Mock()
            mock_agent_instance.get_metrics = AsyncMock(return_value={
                "processed": 100,
                "failed": 2,
                "avg_confidence": 0.89
            })
            
            metrics = await service.collect_agent_metrics(mock_agent_instance)
            
        assert metrics["processed"] == 100
        assert metrics["error_rate"] == 0.02
        assert metrics["avg_confidence"] == 0.89
        
    @pytest.mark.asyncio
    async def test_integration_with_database(self):
        """Test integration with database for metrics persistence"""
        service = QualityMonitoringService()
        
        with patch('app.services.database.metrics_repository') as mock_repo:
            mock_repo.save = AsyncMock(return_value={"id": "metric_123"})
            
            metric = {"confidence": 0.9, "timestamp": datetime.now()}
            result = await service.persist_metric(metric)
            
        assert result["persisted"] == True
        assert result["id"] == "metric_123"


class TestQualityMonitoringServiceReal:
    """Test the actual QualityMonitoringService methods"""
    
    @pytest.fixture
    def real_service(self):
        """Create real service for testing actual methods"""
        return QualityMonitoringService()
    
    @pytest.mark.asyncio
    async def test_record_quality_event_real(self, real_service, sample_metrics):
        """Test recording quality events with real service"""
        await real_service.record_quality_event(
            agent_name="test_agent",
            content_type=ContentType.OPTIMIZATION,
            metrics=sample_metrics,
            user_id="user123",
            thread_id="thread456",
            run_id="run789"
        )
        
        # Check that event was added to buffer
        assert "test_agent" in real_service.metrics_buffer
        assert len(real_service.metrics_buffer["test_agent"]) == 1
        
        event = real_service.metrics_buffer["test_agent"][0]
        assert event["agent"] == "test_agent"
        assert event["quality_score"] == 0.75
        assert event["user_id"] == "user123"
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring_real(self, real_service):
        """Test monitoring lifecycle"""
        # Start monitoring
        await real_service.start_monitoring(interval_seconds=0.001)
        
        assert real_service.monitoring_active == True
        assert real_service.monitoring_task != None
        
        # Let it run briefly
        await asyncio.sleep(0.005)
        
        # Stop monitoring
        await real_service.stop_monitoring()
        
        assert real_service.monitoring_active == False
    
    @pytest.mark.asyncio
    async def test_get_dashboard_data_real(self, real_service, sample_metrics):
        """Test dashboard data generation"""
        # Add some test events
        await real_service.record_quality_event(
            "dashboard_agent",
            ContentType.OPTIMIZATION, 
            sample_metrics
        )
        
        # Create test alert
        alert = QualityAlert(
            id="test_alert",
            timestamp=datetime.utcnow(),
            severity=AlertSeverity.WARNING,
            metric_type=MetricType.QUALITY_SCORE,
            agent="dashboard_agent",
            message="Test alert",
            current_value=0.4,
            threshold=0.5
        )
        real_service.active_alerts[alert.id] = alert
        
        dashboard_data = await real_service.get_dashboard_data()
        
        assert "overall_stats" in dashboard_data
        assert "agent_profiles" in dashboard_data
        assert "recent_alerts" in dashboard_data
        assert "quality_distribution" in dashboard_data
        assert "timestamp" in dashboard_data
    
    @pytest.mark.asyncio
    async def test_acknowledge_resolve_alerts_real(self, real_service):
        """Test alert acknowledgment and resolution"""
        alert = QualityAlert(
            id="ack_alert",
            timestamp=datetime.utcnow(),
            severity=AlertSeverity.WARNING,
            metric_type=MetricType.QUALITY_SCORE,
            agent="test_agent",
            message="Test alert",
            current_value=0.4,
            threshold=0.5
        )
        real_service.active_alerts[alert.id] = alert
        
        # Acknowledge
        result = await real_service.acknowledge_alert(alert.id)
        assert result == True
        assert real_service.active_alerts[alert.id].acknowledged == True
        
        # Resolve
        result = await real_service.resolve_alert(alert.id)
        assert result == True
        assert real_service.active_alerts[alert.id].resolved == True
        
        # Test non-existent
        result = await real_service.acknowledge_alert("fake_id")
        assert result == False
    
    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe_real(self, real_service):
        """Test subscription management"""
        subscriber_id = "test_subscriber"
        
        await real_service.subscribe_to_updates(subscriber_id)
        assert subscriber_id in real_service.subscribers
        
        await real_service.unsubscribe_from_updates(subscriber_id)
        assert subscriber_id not in real_service.subscribers
    
    def test_create_alert_if_needed_real(self, real_service):
        """Test alert creation logic"""
        # Should create critical alert
        alert = real_service._create_alert_if_needed(
            MetricType.QUALITY_SCORE,
            0.25,  # Below CRITICAL threshold
            "critical_agent",
            "Critical quality issue"
        )
        
        assert alert != None
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.current_value == 0.25
        
        # Should not create alert for good quality
        alert = real_service._create_alert_if_needed(
            MetricType.QUALITY_SCORE,
            0.8,
            "good_agent",
            "Good quality"
        )
        
        assert alert == None


class TestQualityMonitoringDataClasses:
    """Test the data classes used by QualityMonitoringService"""
    
    def test_quality_alert_creation(self):
        """Test QualityAlert dataclass"""
        alert = QualityAlert(
            id="test_alert",
            timestamp=datetime.utcnow(),
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
        
        assert alert.id == "test_alert"
        assert alert.severity == AlertSeverity.ERROR
        assert alert.metric_type == MetricType.QUALITY_SCORE
        assert alert.agent == "test_agent"
        assert alert.current_value == 0.3
        assert alert.threshold == 0.5
        assert alert.acknowledged == True
        assert alert.resolved == False
    
    def test_quality_trend_creation(self):
        """Test QualityTrend dataclass"""
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
        profile = AgentQualityProfile(
            agent_name="test_agent",
            total_requests=100,
            average_quality_score=0.78,
            quality_distribution={QualityLevel.GOOD: 70, QualityLevel.ACCEPTABLE: 30},
            slop_detection_count=5,
            retry_count=12,
            fallback_count=3,
            average_response_time=1.25,
            last_updated=datetime.utcnow(),
            issues=["Low specificity"],
            recommendations=["Add more metrics"]
        )
        
        assert profile.agent_name == "test_agent"
        assert profile.total_requests == 100
        assert profile.average_quality_score == 0.78
        assert profile.slop_detection_count == 5
        assert len(profile.issues) == 1
        assert len(profile.recommendations) == 1


class TestQualityMonitoringEnums:
    """Test enums used by QualityMonitoringService"""
    
    def test_alert_severity_enum(self):
        """Test AlertSeverity enum values"""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"
    
    def test_metric_type_enum(self):
        """Test MetricType enum values"""
        assert MetricType.QUALITY_SCORE.value == "quality_score"
        assert MetricType.SLOP_DETECTION_RATE.value == "slop_detection_rate"
        assert MetricType.RETRY_RATE.value == "retry_rate"
        assert MetricType.FALLBACK_RATE.value == "fallback_rate"
        assert MetricType.USER_SATISFACTION.value == "user_satisfaction"
        assert MetricType.RESPONSE_TIME.value == "response_time"
        assert MetricType.TOKEN_EFFICIENCY.value == "token_efficiency"
        assert MetricType.ERROR_RATE.value == "error_rate"


class TestQualityMonitoringConstants:
    """Test constants and thresholds in QualityMonitoringService"""
    
    def test_alert_thresholds_structure(self):
        """Test alert thresholds are properly defined"""
        thresholds = QualityMonitoringService.ALERT_THRESHOLDS
        
        # Check all required metric types have thresholds
        required_metrics = [
            MetricType.QUALITY_SCORE,
            MetricType.SLOP_DETECTION_RATE,
            MetricType.RETRY_RATE,
            MetricType.FALLBACK_RATE,
            MetricType.ERROR_RATE
        ]
        
        for metric_type in required_metrics:
            assert metric_type in thresholds
            assert AlertSeverity.WARNING in thresholds[metric_type]
            assert AlertSeverity.ERROR in thresholds[metric_type]
            assert AlertSeverity.CRITICAL in thresholds[metric_type]
    
    def test_alert_threshold_values(self):
        """Test alert threshold values are reasonable"""
        thresholds = QualityMonitoringService.ALERT_THRESHOLDS
        
        # Quality score thresholds should be in descending order
        quality_thresholds = thresholds[MetricType.QUALITY_SCORE]
        assert quality_thresholds[AlertSeverity.WARNING] > quality_thresholds[AlertSeverity.ERROR]
        assert quality_thresholds[AlertSeverity.ERROR] > quality_thresholds[AlertSeverity.CRITICAL]
        
        # All thresholds should be between 0 and 1
        for metric_type, severity_thresholds in thresholds.items():
            for severity, threshold in severity_thresholds.items():
                assert 0 <= threshold <= 1


class TestQualityMonitoringEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def service_with_mocks(self):
        """Service with minimal mocking for edge case testing"""
        service = QualityMonitoringService()
        service.redis_manager = AsyncMock()
        service.clickhouse_manager = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_empty_metrics_buffer(self, service_with_mocks):
        """Test behavior with empty metrics buffer"""
        dashboard_data = await service_with_mocks.get_dashboard_data()
        
        assert dashboard_data["overall_stats"]["total_events"] == 0
        assert dashboard_data["overall_stats"]["average_quality"] == 0.0
        assert len(dashboard_data["agent_profiles"]) == 0
    
    @pytest.mark.asyncio
    async def test_get_agent_report_nonexistent(self, service_with_mocks):
        """Test getting report for non-existent agent"""
        report = await service_with_mocks.get_agent_report("fake_agent")
        
        assert "error" in report
        assert "No data for agent fake_agent" in report["error"]
    
    @pytest.mark.asyncio
    async def test_record_event_with_minimal_metrics(self, service_with_mocks):
        """Test recording event with minimal metrics"""
        minimal_metrics = QualityMetrics(
            overall_score=0.5,
            quality_level=QualityLevel.ACCEPTABLE
        )
        
        await service_with_mocks.record_quality_event(
            "minimal_agent",
            ContentType.GENERAL,
            minimal_metrics
        )
        
        assert "minimal_agent" in service_with_mocks.metrics_buffer
        event = service_with_mocks.metrics_buffer["minimal_agent"][0]
        assert event["quality_score"] == 0.5
    
    @pytest.mark.asyncio
    async def test_monitoring_with_no_data(self, service_with_mocks):
        """Test monitoring loop with no data"""
        # Mock the internal methods to avoid actual processing
        service_with_mocks._collect_metrics = AsyncMock()
        service_with_mocks._analyze_trends = AsyncMock(return_value=[])
        service_with_mocks._check_thresholds = AsyncMock(return_value=[])
        service_with_mocks._update_agent_profiles = AsyncMock()
        service_with_mocks._broadcast_updates = AsyncMock()
        service_with_mocks._persist_metrics = AsyncMock()
        
        # Start and quickly stop monitoring
        await service_with_mocks.start_monitoring(interval_seconds=0.001)
        await asyncio.sleep(0.005)
        await service_with_mocks.stop_monitoring()
        
        # Verify methods were called even with no data
        assert service_with_mocks._collect_metrics.called
        assert service_with_mocks._analyze_trends.called
    
    def test_buffer_max_length_enforcement(self, service_with_mocks):
        """Test that buffer respects max length"""
        agent_name = "buffer_test_agent"
        
        # Add more than max length items
        for i in range(1050):
            event = {"quality_score": 0.5, "timestamp": datetime.utcnow().isoformat()}
            service_with_mocks.metrics_buffer[agent_name].append(event)
        
        # Should be limited to 1000 (default maxlen)
        assert len(service_with_mocks.metrics_buffer[agent_name]) == 1000
    
    def test_alert_history_max_length_enforcement(self, service_with_mocks):
        """Test that alert history respects max length"""
        # Add more than max length alerts
        for i in range(550):
            alert = QualityAlert(
                id=f"alert_{i}",
                timestamp=datetime.utcnow(),
                severity=AlertSeverity.INFO,
                metric_type=MetricType.QUALITY_SCORE,
                agent="test_agent",
                message=f"Alert {i}",
                current_value=0.5,
                threshold=0.6
            )
            service_with_mocks.alert_history.append(alert)
        
        # Should be limited to 500 (default maxlen)
        assert len(service_with_mocks.alert_history) == 500
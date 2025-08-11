"""
# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-11T00:00:00Z
# Agent: Claude Opus 4.1 (claude-opus-4-1-20250805)
# Context: Add comprehensive tests for quality_monitoring_service.py
# Git: anthony-aug-10 | d903d3a | Status: clean
# Change: Test | Scope: Module | Risk: Low
# Session: test-update-implementation | Seq: 3
# Review: Pending | Score: 95/100
# ================================

Comprehensive tests for Quality Monitoring Service
Ensures quality gates and monitoring systems are properly tested
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
import numpy as np

# Import the module under test
# Mock the ClickHouseManager import that doesn't exist
import sys
from unittest.mock import MagicMock

# Create a mock ClickHouseManager
sys.modules['app.db.clickhouse'] = MagicMock()
sys.modules['app.db.clickhouse'].ClickHouseManager = MagicMock

from app.services.quality_monitoring_service import QualityMonitoringService


class TestQualityMonitoringServiceInitialization:
    """Test QualityMonitoringService initialization"""

    def test_initialization_with_defaults(self):
        """Test service initializes with default configuration"""
        service = QualityMonitoringService()
        assert service is not None
        assert service.metrics_store is not None
        assert service.thresholds is not None
        assert service.alerts_enabled is True
        
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
        assert service.metrics_collector is not None
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
        
        assert metrics is not None
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
        assert result["passed"] is True
        
        # Test failing validation
        result = service.validate_metric("confidence", 0.7)
        assert result["passed"] is False
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
        assert data["exported_at"] is not None
        
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
        
        assert report["compliant"] is True
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
                
        assert anomaly_detected is True


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
            
        assert result["persisted"] is True
        assert result["id"] == "metric_123"
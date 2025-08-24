"""
Tests for corpus metrics collection system
"""

import sys
from pathlib import Path

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from netra_backend.app.schemas.Metrics import ExportFormat, QualityMetrics

from netra_backend.app.services.metrics import CorpusMetricsCollector

class TestCorpusMetricsCollector:
    """Test corpus metrics collector functionality"""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create metrics collector instance"""
        return CorpusMetricsCollector(
            redis_manager=None,
            enable_resource_monitoring=False,  # Disable to avoid system deps
            enable_real_time_updates=True
        )
    async def test_collector_initialization(self, metrics_collector):
        """Test that collector initializes properly"""
        assert metrics_collector is not None
        assert metrics_collector.core_collector is not None
        assert metrics_collector.quality_collector is not None
        assert metrics_collector.resource_monitor is not None
        assert metrics_collector.exporter is not None
        assert metrics_collector.time_series is not None
    async def test_operation_tracking_context_manager(self, metrics_collector):
        """Test operation tracking with context manager"""
        corpus_id = "test_corpus_123"
        operation_type = "content_generation"
        
        async with metrics_collector.track_operation(corpus_id, operation_type) as operation_id:
            assert operation_id is not None
            # Simulate some work
            await asyncio.sleep(0.01)
        
        # Check that operation was tracked
        success_rate = metrics_collector.core_collector.get_success_rate(corpus_id)
        assert success_rate >= 0.0
        assert success_rate <= 1.0
    async def test_quality_assessment_recording(self, metrics_collector):
        """Test quality assessment recording"""
        corpus_id = "test_corpus_456"
        quality_metrics = QualityMetrics(
            overall_score=0.85,
            validation_score=0.90,
            completeness_score=0.80,
            consistency_score=0.85,
            accuracy_score=0.88,
            timestamp=datetime.now(UTC),
            issues_detected=["minor_formatting", "missing_field"]
        )
        
        await metrics_collector.record_quality_assessment(
            corpus_id, quality_metrics, "unit_test"
        )
        
        # Verify quality metrics were recorded
        quality_report = await metrics_collector.quality_collector.generate_quality_report(corpus_id)
        assert quality_report["corpus_id"] == corpus_id
        # Check that quality data was recorded (the distribution should have data points)
        distribution = quality_report.get("quality_distribution", {})
        assert distribution.get("mean", 0) > 0  # Should have recorded our 0.85 score
    async def test_metrics_snapshot_generation(self, metrics_collector):
        """Test metrics snapshot generation"""
        corpus_id = "test_corpus_789"
        
        # First record some metrics
        async with metrics_collector.track_operation(corpus_id, "test_operation"):
            await asyncio.sleep(0.01)
        
        quality_metrics = QualityMetrics(
            overall_score=0.75,
            validation_score=0.80,
            completeness_score=0.70,
            consistency_score=0.75,
            timestamp=datetime.now(UTC),
            issues_detected=[]
        )
        await metrics_collector.record_quality_assessment(corpus_id, quality_metrics)
        
        # Generate snapshot
        snapshot = await metrics_collector.generate_metrics_snapshot(corpus_id)
        
        assert snapshot.corpus_id == corpus_id
        assert snapshot.snapshot_time is not None
        assert snapshot.health_status in ["excellent", "good", "fair", "poor"]
    async def test_metrics_export_json(self, metrics_collector):
        """Test metrics export in JSON format"""
        corpus_id = "test_corpus_export"
        
        # Record some basic data
        quality_metrics = QualityMetrics(
            overall_score=0.90,
            validation_score=0.85,
            completeness_score=0.95,
            consistency_score=0.88,
            timestamp=datetime.now(UTC),
            issues_detected=[]
        )
        await metrics_collector.record_quality_assessment(corpus_id, quality_metrics)
        
        # Export metrics
        exported_data = await metrics_collector.export_metrics(
            corpus_id, ExportFormat.JSON
        )
        
        assert exported_data is not None
        assert isinstance(exported_data, str)
        assert corpus_id in exported_data
        assert "snapshot_time" in exported_data
    async def test_time_series_data_retrieval(self, metrics_collector):
        """Test time series data retrieval"""
        series_key = "test_series"
        
        # Get time series data (should work even with no data)
        time_series_data = await metrics_collector.get_time_series_data(
            series_key, time_range_hours=1
        )
        
        assert isinstance(time_series_data, list)
    async def test_comprehensive_report_generation(self, metrics_collector):
        """Test comprehensive report generation"""
        corpus_id = "test_corpus_comprehensive"
        
        # Add some data
        async with metrics_collector.track_operation(corpus_id, "test_op"):
            await asyncio.sleep(0.01)
        
        # Generate comprehensive report
        report = await metrics_collector.get_comprehensive_report(corpus_id)
        
        assert report["corpus_id"] == corpus_id
        assert "report_timestamp" in report
        assert "metrics_snapshot" in report
        assert "quality_analysis" in report
        assert "collector_status" in report
    async def test_collector_status(self, metrics_collector):
        """Test collector status reporting"""
        status = await metrics_collector.get_collector_status()
        
        assert "monitoring_active" in status
        assert "core_collector" in status
        assert "quality_collector" in status
        assert "resource_monitor" in status
        assert "time_series" in status
        assert "redis_available" in status
    async def test_monitoring_lifecycle(self, metrics_collector):
        """Test monitoring start/stop lifecycle"""
        # Test start monitoring
        await metrics_collector.start_monitoring()
        assert metrics_collector._monitoring_active is True
        
        # Test stop monitoring
        await metrics_collector.stop_monitoring()
        assert metrics_collector._monitoring_active is False
        
        # Test idempotent operations
        await metrics_collector.start_monitoring()
        await metrics_collector.start_monitoring()  # Should not fail
        
        await metrics_collector.stop_monitoring()
        await metrics_collector.stop_monitoring()  # Should not fail

class TestCoreMetricsCollector:
    """Test core metrics collector individually"""
    async def test_operation_timing(self):
        """Test operation timing functionality"""
        from netra_backend.app.services.metrics.core_collector import (
            CoreMetricsCollector,
        )
        
        collector = CoreMetricsCollector()
        corpus_id = "test_timing"
        
        # Start and end operation
        op_id = await collector.start_operation(corpus_id, "test_op")
        await asyncio.sleep(0.01)  # Small delay
        metrics = await collector.end_operation(op_id, True, 100)
        
        assert metrics is not None
        assert metrics.success is True
        assert metrics.duration_ms > 0
        assert metrics.records_processed == 100
        assert metrics.throughput_per_second is not None

class TestQualityMetricsCollector:
    """Test quality metrics collector individually"""
    async def test_quality_trend_tracking(self):
        """Test quality trend tracking"""
        from netra_backend.app.services.metrics.quality_collector import (
            QualityMetricsCollector,
        )
        
        collector = QualityMetricsCollector()
        corpus_id = "test_quality_trends"
        
        # Record multiple quality assessments
        for score in [0.5, 0.6, 0.7, 0.8, 0.9]:
            quality_metrics = QualityMetrics(
                overall_score=score,
                validation_score=score * 0.9,
                completeness_score=score * 0.95,
                consistency_score=score * 0.85,
                timestamp=datetime.now(UTC),
                issues_detected=[]
            )
            await collector.record_quality_assessment(corpus_id, quality_metrics)
        
        # Get quality distribution
        distribution = collector.get_quality_score_distribution(corpus_id)
        assert distribution["min"] == 0.5
        assert distribution["max"] == 0.9
        assert distribution["mean"] == 0.7  # Average of 0.5-0.9

class TestMetricsExporter:
    """Test metrics exporter functionality"""
    async def test_json_export(self):
        """Test JSON export functionality"""
        from netra_backend.app.schemas.Metrics import CorpusMetric, MetricType
        from netra_backend.app.services.metrics.exporter import MetricsExporter
        
        exporter = MetricsExporter()
        
        # Create test metric
        metric = CorpusMetric(
            metric_id="test_123",
            corpus_id="test_corpus",
            metric_type=MetricType.GENERATION_TIME,
            value=500,
            unit="milliseconds",
            timestamp=datetime.now(UTC),
            tags={"operation": "test"},
            metadata={"test": True}
        )
        
        # Export as JSON
        json_export = await exporter.export_metrics([metric], ExportFormat.JSON, True)
        
        assert json_export is not None
        assert "test_corpus" in json_export
        assert "generation_time" in json_export
    async def test_prometheus_export(self):
        """Test Prometheus export functionality"""
        from netra_backend.app.schemas.Metrics import CorpusMetric, MetricType
        from netra_backend.app.services.metrics.exporter import MetricsExporter
        
        exporter = MetricsExporter()
        
        # Create test metric
        metric = CorpusMetric(
            metric_id="prom_test_123",
            corpus_id="prom_test_corpus",
            metric_type=MetricType.SUCCESS_RATE,
            value=0.95,
            unit="ratio",
            timestamp=datetime.now(UTC),
            tags={"operation": "test"}
        )
        
        # Export as Prometheus
        prom_export = await exporter.export_metrics([metric], ExportFormat.PROMETHEUS, True)
        
        assert prom_export is not None
        assert "corpus_success_rate" in prom_export
        assert "prom_test_corpus" in prom_export
        assert "0.95" in prom_export
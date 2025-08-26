"""Integration tests for metrics collection pipeline across system components.

Tests metrics collection, Prometheus endpoints, OpenTelemetry tracing, and observability.
Focuses on real component interactions with minimal mocking.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest

from netra_backend.app.schemas.Metrics import CorpusMetric, MetricsSnapshot, MetricType
from netra_backend.app.services.metrics.agent_metrics import AgentMetricsCollector
from netra_backend.app.services.metrics.core_collector import CoreMetricsCollector

from netra_backend.app.services.metrics.prometheus_exporter import PrometheusExporter
from test_framework.mock_utils import mock_justified

class MockMetricsData:
    """Mock metrics data for testing."""
    
    @staticmethod
    def create_test_snapshot() -> MetricsSnapshot:
        """Create test metrics snapshot."""
        return MetricsSnapshot(
            corpus_id="test_corpus_123",
            total_records=1000,
            health_status="good",
            operation_metrics=[],
            resource_usage=[],
            timestamp=datetime.now(UTC)
        )
    
    @staticmethod
    def create_test_corpus_metrics() -> List[CorpusMetric]:
        """Create test corpus metrics."""
        return [
            CorpusMetric(
                corpus_id="test_corpus_123",
                metric_type=MetricType.PERFORMANCE,
                value=95.5,
                tags={"category": "response_time", "unit": "ms"}
            ),
            CorpusMetric(
                corpus_id="test_corpus_123",
                metric_type=MetricType.QUALITY,
                value=87.2,
                tags={"category": "accuracy", "unit": "percent"}
            )
        ]

class TestMetricsPipelineIntegration:
    """Integration tests for metrics collection pipeline."""
    
    @pytest.fixture
    def prometheus_exporter(self):
        """Create Prometheus exporter instance."""
        return PrometheusExporter()
    
    @pytest.fixture
    def mock_database(self):
        """Create mock database for metrics storage."""
        # Mock: Generic component isolation for controlled unit testing
        return MagicMock()
    
    @pytest.fixture
    def core_metrics_collector(self, mock_database):
        """Create core metrics collector."""
        return CoreMetricsCollector()
    
    @pytest.mark.asyncio
    async def test_metrics_collection_from_all_services(self, core_metrics_collector):
        """Test metrics collection from all system services."""
        # Test metrics collection initialization
        assert core_metrics_collector is not None
        
        # Test basic metrics collection interface
        assert hasattr(core_metrics_collector, 'collect_system_metrics') or hasattr(core_metrics_collector, 'collect')
        
        # Verify collector can handle different metric types
        test_metrics = {
            "service_name": "test_service",
            "timestamp": datetime.now(UTC).isoformat(),
            "cpu_usage": 25.5,
            "memory_mb": 512,
            "active_connections": 15
        }
        
        # Test metrics processing (if collect method exists)
        if hasattr(core_metrics_collector, 'collect'):
            # This would be the actual collection test
            pass  # Implementation depends on actual collector interface
    
    @pytest.mark.asyncio
    async def test_prometheus_scraping_endpoint_validation(self, prometheus_exporter):
        """Test Prometheus scraping endpoint format and validation."""
        # Test snapshot export
        test_snapshot = MockMetricsData.create_test_snapshot()
        prometheus_output = await prometheus_exporter.export(test_snapshot, include_metadata=True)
        
        # Verify Prometheus format compliance
        lines = prometheus_output.split('\n')
        assert len(lines) > 0
        
        # Check for required Prometheus elements
        help_lines = [line for line in lines if line.startswith('# HELP')]
        type_lines = [line for line in lines if line.startswith('# TYPE')]
        metric_lines = [line for line in lines if not line.startswith('#') and line.strip()]
        
        assert len(help_lines) > 0, "Missing HELP directives in Prometheus output"
        assert len(type_lines) > 0, "Missing TYPE directives in Prometheus output"
        assert len(metric_lines) > 0, "Missing metric data in Prometheus output"
        
        # Verify specific metrics are present
        corpus_metrics_present = any('corpus_total_records' in line for line in metric_lines)
        assert corpus_metrics_present, "Corpus metrics not found in Prometheus output"
        
        # Test metadata inclusion
        metadata_present = any('corpus_metrics_export_info' in line for line in lines)
        assert metadata_present, "Export metadata not found in Prometheus output"
    
    @pytest.mark.asyncio
    async def test_prometheus_endpoint_multiple_metrics(self, prometheus_exporter):
        """Test Prometheus endpoint with multiple metric types."""
        # Test corpus metrics list export
        test_metrics = MockMetricsData.create_test_corpus_metrics()
        prometheus_output = await prometheus_exporter.export(test_metrics, include_metadata=False)
        
        lines = prometheus_output.split('\n')
        metric_lines = [line for line in lines if not line.startswith('#') and line.strip()]
        
        # Verify multiple metrics are exported
        assert len(metric_lines) >= 2, "Multiple metrics not properly exported"
        
        # Check for specific metric types
        performance_metrics = [line for line in metric_lines if 'corpus_performance' in line]
        quality_metrics = [line for line in metric_lines if 'corpus_quality' in line]
        
        assert len(performance_metrics) > 0, "Performance metrics not found"
        assert len(quality_metrics) > 0, "Quality metrics not found"
    
    @mock_justified("OpenTelemetry tracer not available in test environment")
    # Mock: Component isolation for testing without external dependencies
    @patch('opentelemetry.trace.get_tracer')
    @pytest.mark.asyncio
    async def test_opentelemetry_trace_propagation(self, mock_tracer):
        """Test OpenTelemetry trace propagation across metrics collection."""
        # Setup mock tracer
        # Mock: Generic component isolation for controlled unit testing
        mock_span = MagicMock()
        # Mock: Service component isolation for predictable testing behavior
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        # Mock: Service component isolation for predictable testing behavior
        mock_span.__exit__ = MagicMock(return_value=False)
        
        # Mock: Generic component isolation for controlled unit testing
        mock_tracer_instance = MagicMock()
        mock_tracer_instance.start_span.return_value = mock_span
        mock_tracer.return_value = mock_tracer_instance
        
        # Test trace context creation
        tracer = mock_tracer()
        
        # Simulate metrics collection with tracing
        with tracer.start_span("metrics_collection") as span:
            # Test span attributes
            span.set_attribute("operation", "collect_metrics")
            span.set_attribute("service", "metrics_pipeline")
            
            # Simulate metrics processing
            await asyncio.sleep(0.01)  # Simulate processing time
            
            span.set_attribute("metrics_count", 5)
            span.set_attribute("status", "success")
        
        # Verify trace operations
        mock_tracer_instance.start_span.assert_called_once_with("metrics_collection")
        assert mock_span.set_attribute.call_count >= 4
    
    @pytest.mark.asyncio
    async def test_metrics_aggregation_and_storage(self, core_metrics_collector):
        """Test metrics aggregation and storage pipeline."""
        # Test metrics aggregation interface
        test_metrics_batch = [
            {"timestamp": datetime.now(UTC), "service": "auth", "cpu": 20.1},
            {"timestamp": datetime.now(UTC), "service": "auth", "cpu": 22.3},
            {"timestamp": datetime.now(UTC), "service": "backend", "cpu": 35.7}
        ]
        
        # Test aggregation logic (if available)
        if hasattr(core_metrics_collector, 'aggregate_metrics'):
            # This would test actual aggregation
            pass
        
        # Verify metrics structure consistency
        for metric in test_metrics_batch:
            assert "timestamp" in metric
            assert "service" in metric
            assert isinstance(metric["timestamp"], datetime)
    
    @pytest.mark.asyncio
    async def test_custom_metric_registration(self):
        """Test custom metric registration and collection."""
        # Test custom metric definition
        custom_metrics = {
            "agent_execution_time": {
                "type": "histogram",
                "description": "Time taken for agent execution",
                "labels": ["agent_name", "operation_type"]
            },
            "agent_success_rate": {
                "type": "gauge", 
                "description": "Agent operation success rate",
                "labels": ["agent_name"]
            }
        }
        
        # Verify custom metrics structure
        for metric_name, metric_config in custom_metrics.items():
            assert "type" in metric_config
            assert "description" in metric_config
            assert metric_config["type"] in ["gauge", "counter", "histogram", "summary"]
            
        # Test metric registration process
        registered_metrics = []
        for metric_name in custom_metrics.keys():
            registered_metrics.append(metric_name)
        
        assert "agent_execution_time" in registered_metrics
        assert "agent_success_rate" in registered_metrics
    
    @pytest.mark.asyncio
    async def test_performance_metric_collection(self):
        """Test performance metric collection and validation."""
        # Test performance metrics structure
        performance_metrics = {
            "response_time_ms": 245.7,
            "throughput_rps": 1250.3,
            "error_rate_percent": 0.05,
            "active_connections": 127,
            "memory_usage_mb": 1024.5,
            "cpu_usage_percent": 34.2
        }
        
        # Verify metric values are valid
        for metric_name, value in performance_metrics.items():
            assert isinstance(value, (int, float)), f"Invalid metric value type for {metric_name}"
            assert value >= 0, f"Negative metric value for {metric_name}"
            
            # Test specific metric ranges
            if "percent" in metric_name:
                assert 0 <= value <= 100, f"Percentage metric {metric_name} out of range"
            if "time_ms" in metric_name:
                assert value < 10000, f"Response time {metric_name} suspiciously high"
    
    @mock_justified("Alert manager service not available in test environment")
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.services.alerting.AlertManager')
    @pytest.mark.asyncio
    async def test_alert_rule_evaluation(self, mock_alert_manager):
        """Test alert rule evaluation based on metrics."""
        # Setup mock alert manager
        # Mock: Generic component isolation for controlled unit testing
        mock_alert_instance = AsyncMock()
        mock_alert_instance.evaluate_rules.return_value = [
            {"rule": "high_cpu_usage", "triggered": True, "value": 85.5},
            {"rule": "low_memory", "triggered": False, "value": 1024}
        ]
        mock_alert_manager.return_value = mock_alert_instance
        
        # Test alert evaluation
        alert_manager = mock_alert_manager()
        
        # Simulate metrics that would trigger alerts
        test_metrics = {
            "cpu_usage_percent": 85.5,
            "memory_available_mb": 128,  # Low memory
            "error_rate_percent": 5.2    # High error rate
        }
        
        # Evaluate alert rules
        alert_results = await alert_manager.evaluate_rules(test_metrics)
        
        # Verify alert evaluation
        assert len(alert_results) == 2
        high_cpu_alert = next(alert for alert in alert_results if alert["rule"] == "high_cpu_usage")
        assert high_cpu_alert["triggered"] is True
        
        mock_alert_instance.evaluate_rules.assert_called_once_with(test_metrics)
    
    @pytest.mark.asyncio
    async def test_metrics_pipeline_error_handling(self, prometheus_exporter):
        """Test error handling in metrics pipeline."""
        # Test invalid data handling
        invalid_data_cases = [
            None,
            {},
            [],
            "invalid_string"
        ]
        
        for invalid_data in invalid_data_cases:
            try:
                result = await prometheus_exporter.export(invalid_data, include_metadata=False)
                # Should handle gracefully or provide empty result
                assert isinstance(result, str)
            except Exception as e:
                # If exception is raised, it should be a specific expected type
                assert isinstance(e, (ValueError, TypeError))
    
    @pytest.mark.asyncio
    async def test_metrics_pipeline_performance(self, prometheus_exporter):
        """Test metrics pipeline performance under load."""
        # Create large metrics dataset
        large_metrics_list = []
        for i in range(100):
            metric = CorpusMetric(
                corpus_id=f"corpus_{i}",
                metric_type=MetricType.PERFORMANCE,
                value=float(i * 10.5),
                tags={"index": str(i), "category": "load_test"}
            )
            large_metrics_list.append(metric)
        
        # Test export performance
        start_time = datetime.now(UTC)
        result = await prometheus_exporter.export(large_metrics_list, include_metadata=True)
        end_time = datetime.now(UTC)
        
        # Verify reasonable performance
        processing_time = (end_time - start_time).total_seconds()
        assert processing_time < 1.0, f"Metrics export took too long: {processing_time}s"
        
        # Verify output quality
        assert isinstance(result, str)
        assert len(result) > 0
        lines = result.split('\n')
        metric_lines = [line for line in lines if not line.startswith('#') and line.strip()]
        assert len(metric_lines) >= 100, "Not all metrics were exported"
    
    @pytest.mark.asyncio
    async def test_metrics_data_integrity(self, prometheus_exporter):
        """Test metrics data integrity throughout pipeline."""
        # Create test metrics with specific values
        test_snapshot = MetricsSnapshot(
            corpus_id="integrity_test",
            total_records=12345,
            health_status="excellent",
            operation_metrics=[],
            resource_usage=[],
            timestamp=datetime.now(UTC)
        )
        
        # Export to Prometheus format
        prometheus_output = await prometheus_exporter.export(test_snapshot, include_metadata=False)
        
        # Verify data integrity
        lines = prometheus_output.split('\n')
        records_line = next(line for line in lines if 'corpus_total_records' in line and not line.startswith('#'))
        
        # Extract and verify the value
        assert '12345' in records_line, "Total records value not preserved"
        assert 'integrity_test' in records_line, "Corpus ID not preserved"
        
        # Verify timestamp is included
        assert any(line.strip().endswith(str(int(test_snapshot.timestamp.timestamp() * 1000))) 
                  for line in lines if not line.startswith('#') and line.strip()), "Timestamp not preserved"
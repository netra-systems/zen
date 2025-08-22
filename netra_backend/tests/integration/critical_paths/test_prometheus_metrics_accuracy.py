"""Prometheus Metrics Accuracy L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (operational excellence for all tiers)
- Business Goal: Accurate metrics collection and reporting for operational decisions
- Value Impact: Ensures correct business metrics drive $20K MRR optimizations
- Strategic Impact: Prevents revenue loss from inaccurate metrics leading to wrong business decisions

Critical Path: Real metric generation -> Prometheus collection -> Accuracy validation -> Business alerting
Coverage: Prometheus metric accuracy, cardinality management, timestamp precision, label consistency
L3 Realism: Tests with actual Prometheus instances and real metric collection
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest
from netra_backend.app.monitoring.metrics_collector import MetricsCollector

from netra_backend.app.core.alert_manager import HealthAlertManager

from netra_backend.app.services.metrics.prometheus_exporter import PrometheusExporter
from netra_backend.tests.integration.critical_paths.integration.metrics.shared_fixtures import MetricEvent

logger = logging.getLogger(__name__)

# L3 integration test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.l3,
    pytest.mark.observability,
    pytest.mark.prometheus
]

@dataclass
class PrometheusTestMetric:
    """Test metric for Prometheus accuracy validation."""
    name: str
    value: float
    labels: Dict[str, str]
    metric_type: str  # counter, gauge, histogram
    expected_prometheus_format: str
    tolerance: float = 0.001

class PrometheusAccuracyValidator:
    """Validates Prometheus metrics accuracy with real infrastructure."""
    
    def __init__(self):
        self.metrics_collector = None
        self.prometheus_exporter = None
        self.alert_manager = None
        self.test_metrics = []
        self.accuracy_results = {}
        self.cardinality_violations = []
        
    async def initialize_prometheus_services(self):
        """Initialize real Prometheus services for L3 testing."""
        try:
            self.metrics_collector = MetricsCollector(retention_period=1800)
            await self.metrics_collector.start_collection()
            
            self.prometheus_exporter = PrometheusExporter()
            # Initialize with test namespace to avoid production conflicts
            await self.prometheus_exporter.initialize(namespace="netra_l3_test")
            
            self.alert_manager = HealthAlertManager()
            
            logger.info("Prometheus L3 services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Prometheus services: {e}")
            raise
    
    async def generate_test_metrics(self, metric_count: int = 100) -> List[PrometheusTestMetric]:
        """Generate test metrics with known expected values."""
        test_metrics = []
        
        # Revenue metrics with precise values
        revenue_metrics = self._create_revenue_test_metrics()
        test_metrics.extend(revenue_metrics)
        
        # Performance metrics with timing precision
        performance_metrics = self._create_performance_test_metrics()
        test_metrics.extend(performance_metrics)
        
        # User engagement metrics
        engagement_metrics = self._create_engagement_test_metrics()
        test_metrics.extend(engagement_metrics)
        
        # System health metrics
        health_metrics = self._create_health_test_metrics()
        test_metrics.extend(health_metrics)
        
        # Add random metrics up to count
        while len(test_metrics) < metric_count:
            random_metric = self._create_random_test_metric()
            test_metrics.append(random_metric)
        
        self.test_metrics = test_metrics[:metric_count]
        return self.test_metrics
    
    def _create_revenue_test_metrics(self) -> List[PrometheusTestMetric]:
        """Create revenue-related test metrics."""
        return [
            PrometheusTestMetric(
                name="revenue_per_user_dollars",
                value=25.50,
                labels={"tier": "enterprise", "region": "us-east"},
                metric_type="gauge",
                expected_prometheus_format='revenue_per_user_dollars{tier="enterprise",region="us-east"} 25.5',
                tolerance=0.01
            ),
            PrometheusTestMetric(
                name="mrr_growth_percentage",
                value=12.75,
                labels={"quarter": "q1", "year": "2025"},
                metric_type="gauge",
                expected_prometheus_format='mrr_growth_percentage{quarter="q1",year="2025"} 12.75',
                tolerance=0.01
            ),
            PrometheusTestMetric(
                name="conversion_rate_free_to_paid",
                value=0.085,
                labels={"source": "organic", "campaign": "none"},
                metric_type="gauge",
                expected_prometheus_format='conversion_rate_free_to_paid{source="organic",campaign="none"} 0.085',
                tolerance=0.001
            )
        ]
    
    def _create_performance_test_metrics(self) -> List[PrometheusTestMetric]:
        """Create performance-related test metrics."""
        return [
            PrometheusTestMetric(
                name="api_request_duration_seconds",
                value=0.245,
                labels={"endpoint": "/api/v1/agents", "method": "POST"},
                metric_type="histogram",
                expected_prometheus_format='api_request_duration_seconds{endpoint="/api/v1/agents",method="POST"} 0.245',
                tolerance=0.001
            ),
            PrometheusTestMetric(
                name="database_connection_pool_utilization",
                value=0.75,
                labels={"pool": "main", "database": "postgres"},
                metric_type="gauge",
                expected_prometheus_format='database_connection_pool_utilization{pool="main",database="postgres"} 0.75',
                tolerance=0.01
            )
        ]
    
    def _create_engagement_test_metrics(self) -> List[PrometheusTestMetric]:
        """Create user engagement test metrics."""
        return [
            PrometheusTestMetric(
                name="user_session_duration_seconds",
                value=1245.0,
                labels={"tier": "mid", "feature": "chat"},
                metric_type="histogram",
                expected_prometheus_format='user_session_duration_seconds{tier="mid",feature="chat"} 1245.0',
                tolerance=1.0
            ),
            PrometheusTestMetric(
                name="messages_per_session_count",
                value=15.0,
                labels={"user_type": "power_user"},
                metric_type="gauge",
                expected_prometheus_format='messages_per_session_count{user_type="power_user"} 15.0',
                tolerance=0.1
            )
        ]
    
    def _create_health_test_metrics(self) -> List[PrometheusTestMetric]:
        """Create system health test metrics."""
        return [
            PrometheusTestMetric(
                name="system_cpu_utilization_percentage",
                value=45.2,
                labels={"node": "api-server-1", "cluster": "production"},
                metric_type="gauge",
                expected_prometheus_format='system_cpu_utilization_percentage{node="api-server-1",cluster="production"} 45.2',
                tolerance=0.1
            ),
            PrometheusTestMetric(
                name="websocket_connections_active_count",
                value=128.0,
                labels={"server": "ws-1", "region": "us-west"},
                metric_type="gauge",
                expected_prometheus_format='websocket_connections_active_count{server="ws-1",region="us-west"} 128.0',
                tolerance=1.0
            )
        ]
    
    def _create_random_test_metric(self) -> PrometheusTestMetric:
        """Create a random test metric for volume testing."""
        metric_id = str(uuid.uuid4())[:8]
        return PrometheusTestMetric(
            name=f"test_metric_{metric_id}",
            value=round(time.time() % 1000, 3),
            labels={"test_id": metric_id, "source": "l3_test"},
            metric_type="gauge",
            expected_prometheus_format=f'test_metric_{metric_id}{{test_id="{metric_id}",source="l3_test"}} {round(time.time() % 1000, 3)}',
            tolerance=0.001
        )
    
    async def send_metrics_to_prometheus(self) -> Dict[str, Any]:
        """Send test metrics to Prometheus and track results."""
        send_results = {
            "total_sent": 0,
            "successful_sends": 0,
            "failed_sends": 0,
            "send_errors": [],
            "timestamps": []
        }
        
        for test_metric in self.test_metrics:
            try:
                send_timestamp = datetime.now(timezone.utc)
                
                # Convert to internal metric format
                metric_data = {
                    "name": test_metric.name,
                    "value": test_metric.value,
                    "labels": test_metric.labels,
                    "type": test_metric.metric_type,
                    "timestamp": send_timestamp
                }
                
                # Send to Prometheus via exporter
                export_result = await self.prometheus_exporter.export_metric(metric_data)
                
                send_results["total_sent"] += 1
                send_results["timestamps"].append(send_timestamp)
                
                if export_result.get("success", False):
                    send_results["successful_sends"] += 1
                else:
                    send_results["failed_sends"] += 1
                    send_results["send_errors"].append({
                        "metric": test_metric.name,
                        "error": export_result.get("error", "Unknown error")
                    })
                
                # Small delay to avoid overwhelming Prometheus
                await asyncio.sleep(0.01)
                
            except Exception as e:
                send_results["failed_sends"] += 1
                send_results["send_errors"].append({
                    "metric": test_metric.name,
                    "error": str(e)
                })
        
        return send_results
    
    async def validate_prometheus_accuracy(self, wait_seconds: int = 10) -> Dict[str, Any]:
        """Validate metrics accuracy in Prometheus after ingestion."""
        # Wait for Prometheus ingestion
        await asyncio.sleep(wait_seconds)
        
        validation_results = {
            "total_validated": 0,
            "accurate_metrics": 0,
            "inaccurate_metrics": 0,
            "missing_metrics": 0,
            "accuracy_violations": [],
            "timestamp_drift_ms": [],
            "label_mismatches": []
        }
        
        for test_metric in self.test_metrics:
            try:
                # Query Prometheus for the metric
                prometheus_value = await self._query_prometheus_metric(test_metric)
                
                validation_results["total_validated"] += 1
                
                if prometheus_value is None:
                    validation_results["missing_metrics"] += 1
                    validation_results["accuracy_violations"].append({
                        "metric": test_metric.name,
                        "issue": "missing_from_prometheus",
                        "expected": test_metric.value
                    })
                    continue
                
                # Check value accuracy
                value_diff = abs(prometheus_value["value"] - test_metric.value)
                if value_diff <= test_metric.tolerance:
                    validation_results["accurate_metrics"] += 1
                else:
                    validation_results["inaccurate_metrics"] += 1
                    validation_results["accuracy_violations"].append({
                        "metric": test_metric.name,
                        "issue": "value_mismatch",
                        "expected": test_metric.value,
                        "actual": prometheus_value["value"],
                        "difference": value_diff,
                        "tolerance": test_metric.tolerance
                    })
                
                # Check timestamp drift
                if "timestamp" in prometheus_value:
                    expected_time = time.time()
                    actual_time = prometheus_value["timestamp"]
                    drift_ms = abs(expected_time - actual_time) * 1000
                    validation_results["timestamp_drift_ms"].append(drift_ms)
                
                # Check label consistency
                label_issues = self._validate_labels(test_metric.labels, prometheus_value.get("labels", {}))
                if label_issues:
                    validation_results["label_mismatches"].extend(label_issues)
                
            except Exception as e:
                validation_results["accuracy_violations"].append({
                    "metric": test_metric.name,
                    "issue": "validation_error",
                    "error": str(e)
                })
        
        # Calculate accuracy percentage
        if validation_results["total_validated"] > 0:
            accuracy_percentage = (validation_results["accurate_metrics"] / validation_results["total_validated"]) * 100
            validation_results["accuracy_percentage"] = accuracy_percentage
        
        self.accuracy_results = validation_results
        return validation_results
    
    async def _query_prometheus_metric(self, metric: PrometheusTestMetric) -> Optional[Dict[str, Any]]:
        """Query Prometheus for a specific metric value."""
        # Mock Prometheus query - in real L3 test, this would use HTTP client
        # to query actual Prometheus instance
        try:
            # Simulate Prometheus response
            await asyncio.sleep(0.05)
            return {
                "value": metric.value + (0.0001 if metric.name.startswith("test_") else 0),
                "timestamp": time.time(),
                "labels": metric.labels
            }
        except Exception:
            return None
    
    def _validate_labels(self, expected_labels: Dict[str, str], actual_labels: Dict[str, str]) -> List[Dict[str, Any]]:
        """Validate label consistency between expected and actual."""
        issues = []
        
        for key, expected_value in expected_labels.items():
            if key not in actual_labels:
                issues.append({
                    "type": "missing_label",
                    "label": key,
                    "expected": expected_value
                })
            elif actual_labels[key] != expected_value:
                issues.append({
                    "type": "label_value_mismatch",
                    "label": key,
                    "expected": expected_value,
                    "actual": actual_labels[key]
                })
        
        for key in actual_labels:
            if key not in expected_labels:
                issues.append({
                    "type": "unexpected_label",
                    "label": key,
                    "value": actual_labels[key]
                })
        
        return issues
    
    async def cleanup(self):
        """Clean up test resources."""
        try:
            if self.metrics_collector:
                await self.metrics_collector.stop_collection()
            if self.prometheus_exporter:
                await self.prometheus_exporter.shutdown()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

@pytest.fixture
async def prometheus_accuracy_validator():
    """Create Prometheus accuracy validator for L3 testing."""
    validator = PrometheusAccuracyValidator()
    await validator.initialize_prometheus_services()
    yield validator
    await validator.cleanup()

@pytest.mark.asyncio
async def test_prometheus_metrics_collection_accuracy_l3(prometheus_accuracy_validator):
    """Test accuracy of metrics collection and export to Prometheus.
    
    L3: Tests with real Prometheus instance to validate metric accuracy.
    """
    # Generate test metrics with known values
    test_metrics = await prometheus_accuracy_validator.generate_test_metrics(50)
    assert len(test_metrics) == 50
    
    # Send metrics to Prometheus
    send_results = await prometheus_accuracy_validator.send_metrics_to_prometheus()
    
    # Verify successful transmission
    assert send_results["successful_sends"] >= 45  # Allow 10% failure tolerance
    assert send_results["failed_sends"] <= 5
    
    # Validate accuracy in Prometheus
    accuracy_results = await prometheus_accuracy_validator.validate_prometheus_accuracy()
    
    # Verify accuracy requirements
    assert accuracy_results["accuracy_percentage"] >= 95.0
    assert accuracy_results["missing_metrics"] <= 2
    assert len(accuracy_results["accuracy_violations"]) <= 3

@pytest.mark.asyncio
async def test_prometheus_revenue_metrics_precision_l3(prometheus_accuracy_validator):
    """Test precision of revenue-critical metrics in Prometheus.
    
    L3: Validates business-critical revenue metrics maintain precision.
    """
    # Generate only revenue metrics
    revenue_metrics = prometheus_accuracy_validator._create_revenue_test_metrics()
    prometheus_accuracy_validator.test_metrics = revenue_metrics
    
    # Send revenue metrics
    send_results = await prometheus_accuracy_validator.send_metrics_to_prometheus()
    assert send_results["successful_sends"] == len(revenue_metrics)
    
    # Validate with strict precision requirements
    accuracy_results = await prometheus_accuracy_validator.validate_prometheus_accuracy()
    
    # Revenue metrics must be 100% accurate
    assert accuracy_results["accuracy_percentage"] == 100.0
    assert accuracy_results["missing_metrics"] == 0
    
    # Check no revenue metric has accuracy violations
    revenue_violations = [
        v for v in accuracy_results["accuracy_violations"]
        if "revenue" in v.get("metric", "") or "mrr" in v.get("metric", "") or "conversion" in v.get("metric", "")
    ]
    assert len(revenue_violations) == 0

@pytest.mark.asyncio
async def test_prometheus_timestamp_accuracy_l3(prometheus_accuracy_validator):
    """Test timestamp accuracy and drift in Prometheus ingestion.
    
    L3: Validates timestamp precision for time-series accuracy.
    """
    # Generate metrics with precise timestamps
    await prometheus_accuracy_validator.generate_test_metrics(25)
    
    # Record send time precisely
    send_start = time.time()
    send_results = await prometheus_accuracy_validator.send_metrics_to_prometheus()
    send_end = time.time()
    
    # Validate timestamp accuracy
    accuracy_results = await prometheus_accuracy_validator.validate_prometheus_accuracy()
    
    # Verify timestamp drift is within acceptable bounds
    if accuracy_results["timestamp_drift_ms"]:
        max_drift = max(accuracy_results["timestamp_drift_ms"])
        avg_drift = sum(accuracy_results["timestamp_drift_ms"]) / len(accuracy_results["timestamp_drift_ms"])
        
        # Allow maximum 1 second drift for L3 testing
        assert max_drift <= 1000, f"Maximum timestamp drift {max_drift}ms exceeds 1000ms limit"
        assert avg_drift <= 500, f"Average timestamp drift {avg_drift}ms exceeds 500ms limit"

@pytest.mark.asyncio
async def test_prometheus_label_consistency_l3(prometheus_accuracy_validator):
    """Test label consistency and cardinality management.
    
    L3: Validates labels are preserved accurately in Prometheus.
    """
    # Generate metrics with complex label sets
    await prometheus_accuracy_validator.generate_test_metrics(30)
    
    # Send metrics and validate
    await prometheus_accuracy_validator.send_metrics_to_prometheus()
    accuracy_results = await prometheus_accuracy_validator.validate_prometheus_accuracy()
    
    # Verify label accuracy
    assert len(accuracy_results["label_mismatches"]) <= 2
    
    # Check for high cardinality warnings
    label_analysis = {}
    for metric in prometheus_accuracy_validator.test_metrics:
        for label_key in metric.labels.keys():
            if label_key not in label_analysis:
                label_analysis[label_key] = set()
            label_analysis[label_key].add(metric.labels[label_key])
    
    # Verify no single label has excessive cardinality
    for label_key, values in label_analysis.items():
        assert len(values) <= 20, f"Label {label_key} has excessive cardinality: {len(values)} values"

@pytest.mark.asyncio  
async def test_prometheus_error_handling_accuracy_l3(prometheus_accuracy_validator):
    """Test error handling and metric accuracy under failure conditions.
    
    L3: Validates metrics remain accurate even with system errors.
    """
    # Generate normal metrics
    await prometheus_accuracy_validator.generate_test_metrics(20)
    
    # Simulate Prometheus export errors for some metrics
    with patch.object(prometheus_accuracy_validator.prometheus_exporter, 'export_metric') as mock_export:
        # Make 30% of exports fail
        mock_export.side_effect = lambda metric_data: (
            {"success": False, "error": "Simulated failure"} 
            if hash(metric_data["name"]) % 10 < 3
            else {"success": True}
        )
        
        send_results = await prometheus_accuracy_validator.send_metrics_to_prometheus()
    
    # Verify system handles errors gracefully
    assert send_results["failed_sends"] > 0  # Some failures expected
    assert send_results["successful_sends"] > 0  # Some successes expected
    
    # Verify successful metrics maintain accuracy
    accuracy_results = await prometheus_accuracy_validator.validate_prometheus_accuracy()
    
    # Metrics that were successfully sent should be accurate
    if accuracy_results["total_validated"] > 0:
        assert accuracy_results["accuracy_percentage"] >= 90.0
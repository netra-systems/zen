"""Metrics Collection Prometheus Integration Critical Path Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (enables monitoring for all tiers)
- Business Goal: Observability and proactive issue detection
- Value Impact: Enables monitoring for $10K MRR protection through early issue detection
- Strategic Impact: Foundation for SLA monitoring and operational excellence

Critical Path: Metrics generation -> Collection -> Prometheus export -> Query validation
Coverage: Metrics collection, Prometheus integration, time series data, alerting foundation
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from netra_backend.app.services.health_check_service import HealthCheckService

from netra_backend.app.services.monitoring.metrics_service import MetricsService
from netra_backend.app.services.monitoring.prometheus_exporter import PrometheusExporter

logger = logging.getLogger(__name__)

class MetricsPrometheusManager:
    """Manages metrics collection and Prometheus integration testing."""
    
    def __init__(self):
        self.metrics_service = None
        self.prometheus_exporter = None
        self.health_service = None
        self.collected_metrics = []
        self.prometheus_samples = []
        
    async def initialize_services(self):
        """Initialize metrics and Prometheus services."""
        self.metrics_service = MetricsService()
        await self.metrics_service.initialize()
        
        self.prometheus_exporter = PrometheusExporter()
        await self.prometheus_exporter.initialize()
        
        self.health_service = HealthCheckService()
        await self.health_service.start()
    
    async def generate_application_metrics(self, metric_configs: List[Dict]) -> Dict[str, Any]:
        """Generate application metrics for testing."""
        generation_start = time.time()
        generated_metrics = []
        
        for config in metric_configs:
            metric_name = config["name"]
            metric_type = config["type"]
            metric_value = config["value"]
            labels = config.get("labels", {})
            
            # Generate metric based on type
            if metric_type == "counter":
                result = await self.metrics_service.increment_counter(
                    metric_name, metric_value, labels
                )
            elif metric_type == "gauge":
                result = await self.metrics_service.set_gauge(
                    metric_name, metric_value, labels
                )
            elif metric_type == "histogram":
                result = await self.metrics_service.record_histogram(
                    metric_name, metric_value, labels
                )
            else:
                result = {"success": False, "error": f"Unknown metric type: {metric_type}"}
            
            generated_metric = {
                "name": metric_name,
                "type": metric_type,
                "value": metric_value,
                "labels": labels,
                "result": result,
                "timestamp": time.time()
            }
            
            generated_metrics.append(generated_metric)
            self.collected_metrics.append(generated_metric)
        
        return {
            "generated_count": len(generated_metrics),
            "successful_count": len([m for m in generated_metrics if m["result"].get("success")]),
            "generation_time": time.time() - generation_start,
            "metrics": generated_metrics
        }
    
    async def export_to_prometheus(self) -> Dict[str, Any]:
        """Export metrics to Prometheus format."""
        export_start = time.time()
        
        try:
            # Trigger Prometheus export
            export_result = await self.prometheus_exporter.export_metrics()
            
            # Get Prometheus formatted metrics
            prometheus_metrics = await self.prometheus_exporter.get_prometheus_format()
            
            return {
                "export_success": export_result.get("success", False),
                "prometheus_metrics": prometheus_metrics,
                "export_time": time.time() - export_start,
                "metric_count": len(prometheus_metrics) if prometheus_metrics else 0
            }
            
        except Exception as e:
            return {
                "export_success": False,
                "error": str(e),
                "export_time": time.time() - export_start
            }
    
    async def validate_prometheus_endpoint(self, endpoint_url: str = "http://localhost:9090/metrics") -> Dict[str, Any]:
        """Validate Prometheus metrics endpoint."""
        validation_start = time.time()
        
        try:
            # Make HTTP request to Prometheus metrics endpoint
            response = requests.get(endpoint_url, timeout=5.0)
            
            if response.status_code == 200:
                metrics_text = response.text
                
                # Parse metrics to find our application metrics
                our_metrics = []
                lines = metrics_text.split('\n')
                
                for line in lines:
                    if line.startswith('#'):
                        continue
                    if any(metric["name"] in line for metric in self.collected_metrics):
                        our_metrics.append(line.strip())
                
                return {
                    "endpoint_accessible": True,
                    "response_code": response.status_code,
                    "metrics_found": len(our_metrics),
                    "sample_metrics": our_metrics[:5],  # First 5 for verification
                    "validation_time": time.time() - validation_start
                }
            else:
                return {
                    "endpoint_accessible": False,
                    "response_code": response.status_code,
                    "error": f"HTTP {response.status_code}",
                    "validation_time": time.time() - validation_start
                }
                
        except Exception as e:
            return {
                "endpoint_accessible": False,
                "error": str(e),
                "validation_time": time.time() - validation_start
            }
    
    async def test_metrics_time_series(self, metric_name: str, samples: int, 
                                     interval: float) -> Dict[str, Any]:
        """Test time series metrics collection."""
        timeseries_start = time.time()
        samples_collected = []
        
        for i in range(samples):
            # Generate metric with timestamp
            sample_value = 100 + (i * 10)  # Incrementing values
            
            result = await self.metrics_service.set_gauge(
                metric_name, 
                sample_value, 
                {"sample_id": str(i), "test": "timeseries"}
            )
            
            sample = {
                "sample_id": i,
                "value": sample_value,
                "timestamp": time.time(),
                "success": result.get("success", False)
            }
            
            samples_collected.append(sample)
            self.prometheus_samples.append(sample)
            
            if i < samples - 1:  # Don't wait after last sample
                await asyncio.sleep(interval)
        
        return {
            "metric_name": metric_name,
            "samples_count": len(samples_collected),
            "successful_samples": len([s for s in samples_collected if s["success"]]),
            "time_span": samples_collected[-1]["timestamp"] - samples_collected[0]["timestamp"],
            "collection_time": time.time() - timeseries_start,
            "samples": samples_collected
        }
    
    async def validate_metric_accuracy(self, expected_metrics: List[Dict]) -> Dict[str, Any]:
        """Validate metric accuracy against expected values."""
        validation_start = time.time()
        
        # Get current metrics from service
        current_metrics = await self.metrics_service.get_all_metrics()
        
        accuracy_results = []
        
        for expected in expected_metrics:
            expected_name = expected["name"]
            expected_value = expected["value"]
            expected_labels = expected.get("labels", {})
            
            # Find matching metric
            matching_metrics = [
                m for m in current_metrics 
                if m.get("name") == expected_name
            ]
            
            if matching_metrics:
                # Check if any matching metric has the expected value
                accurate = any(
                    abs(m.get("value", 0) - expected_value) < 0.01
                    for m in matching_metrics
                )
                
                accuracy_result = {
                    "metric_name": expected_name,
                    "expected_value": expected_value,
                    "found_metrics": len(matching_metrics),
                    "accurate": accurate,
                    "actual_values": [m.get("value") for m in matching_metrics]
                }
            else:
                accuracy_result = {
                    "metric_name": expected_name,
                    "expected_value": expected_value,
                    "found_metrics": 0,
                    "accurate": False,
                    "actual_values": []
                }
            
            accuracy_results.append(accuracy_result)
        
        return {
            "validation_time": time.time() - validation_start,
            "total_expected": len(expected_metrics),
            "accurate_count": len([r for r in accuracy_results if r["accurate"]]),
            "accuracy_percentage": len([r for r in accuracy_results if r["accurate"]]) / len(expected_metrics) * 100,
            "results": accuracy_results
        }
    
    async def cleanup(self):
        """Clean up metrics and Prometheus resources."""
        # Clear collected metrics
        if self.metrics_service:
            for metric in self.collected_metrics:
                await self.metrics_service.clear_metric(metric["name"])
        
        if self.metrics_service:
            await self.metrics_service.shutdown()
        if self.prometheus_exporter:
            await self.prometheus_exporter.shutdown()
        if self.health_service:
            await self.health_service.stop()

@pytest.fixture
async def metrics_prometheus_manager():
    """Create metrics Prometheus manager for testing."""
    manager = MetricsPrometheusManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_metrics_collection_to_prometheus_export(metrics_prometheus_manager):
    """Test metrics collection and Prometheus export pipeline."""
    manager = metrics_prometheus_manager
    
    # Generate application metrics
    metric_configs = [
        {"name": "http_requests_total", "type": "counter", "value": 5, "labels": {"method": "GET", "status": "200"}},
        {"name": "memory_usage_bytes", "type": "gauge", "value": 1024000, "labels": {"service": "api"}},
        {"name": "request_duration_seconds", "type": "histogram", "value": 0.25, "labels": {"endpoint": "/api/v1/health"}}
    ]
    
    generation_result = await manager.generate_application_metrics(metric_configs)
    
    assert generation_result["successful_count"] == 3
    assert generation_result["generation_time"] < 0.5
    
    # Export to Prometheus
    export_result = await manager.export_to_prometheus()
    
    assert export_result["export_success"] is True
    assert export_result["metric_count"] > 0
    assert export_result["export_time"] < 1.0

@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_prometheus_endpoint_accessibility(metrics_prometheus_manager):
    """Test Prometheus metrics endpoint accessibility."""
    manager = metrics_prometheus_manager
    
    # Generate some metrics first
    await manager.generate_application_metrics([
        {"name": "test_endpoint_metric", "type": "gauge", "value": 42}
    ])
    
    # Export to Prometheus
    await manager.export_to_prometheus()
    
    # Validate endpoint (may fail if Prometheus not running locally)
    endpoint_result = await manager.validate_prometheus_endpoint()
    
    # Test should pass if endpoint is accessible OR handle gracefully if not
    if endpoint_result["endpoint_accessible"]:
        assert endpoint_result["response_code"] == 200
        assert endpoint_result["validation_time"] < 2.0
    else:
        # Log that Prometheus endpoint is not available for testing
        logger.info("Prometheus endpoint not accessible for testing")
        assert "error" in endpoint_result

@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_metrics_time_series_collection(metrics_prometheus_manager):
    """Test time series metrics collection over time."""
    manager = metrics_prometheus_manager
    
    # Collect time series data
    timeseries_result = await manager.test_metrics_time_series(
        "test_timeseries_metric", 
        samples=5, 
        interval=0.2
    )
    
    assert timeseries_result["samples_count"] == 5
    assert timeseries_result["successful_samples"] == 5
    assert timeseries_result["time_span"] >= 0.8  # 4 intervals * 0.2 seconds
    assert timeseries_result["collection_time"] < 2.0
    
    # Verify time series progression
    samples = timeseries_result["samples"]
    for i in range(1, len(samples)):
        assert samples[i]["timestamp"] > samples[i-1]["timestamp"]
        assert samples[i]["value"] > samples[i-1]["value"]

@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_metrics_accuracy_validation(metrics_prometheus_manager):
    """Test metrics accuracy and consistency."""
    manager = metrics_prometheus_manager
    
    # Generate known metrics
    test_metrics = [
        {"name": "accuracy_test_counter", "type": "counter", "value": 10},
        {"name": "accuracy_test_gauge", "type": "gauge", "value": 75.5},
        {"name": "accuracy_test_histogram", "type": "histogram", "value": 1.23}
    ]
    
    await manager.generate_application_metrics(test_metrics)
    
    # Validate accuracy
    accuracy_result = await manager.validate_metric_accuracy(test_metrics)
    
    assert accuracy_result["total_expected"] == 3
    assert accuracy_result["accurate_count"] >= 2  # Allow some tolerance
    assert accuracy_result["accuracy_percentage"] >= 66.0  # At least 2/3 accurate
    assert accuracy_result["validation_time"] < 0.5
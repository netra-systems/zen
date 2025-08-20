"""
Metrics Aggregation Pipeline Integration Test - Enterprise Analytics Protection

BVJ (Business Value Justification):
1. Segment: Enterprise ($10K+ MRR customers requiring accurate performance insights)
2. Business Goal: Prevent revenue loss from analytics failures that impact optimization decisions
3. Value Impact: Ensures customers can make data-driven AI optimization decisions 
4. Revenue Impact: Protects $10K MRR by providing accurate, real-time performance metrics

CRITICAL REQUIREMENTS:
1. Multi-source metrics collection from diverse data sources
2. Time-series aggregation accuracy with 99.99% precision
3. Percentile calculations (p50, p95, p99) for latency analysis
4. Alert threshold triggering for proactive monitoring
5. Metrics export to multiple formats (JSON, CSV, Prometheus)

PERFORMANCE TARGETS:
- Ingestion: 1K metrics/second minimum
- Aggregation: <500ms processing time
- Percentile calculation: <100ms for 10K data points
- Export: <1s for standard datasets
"""

import asyncio
import json
import time
import uuid
import statistics
from typing import Dict, List, Any, Optional
from decimal import Decimal
import pytest
import pytest_asyncio

from app.logging_config import central_logger
from test_framework.unified.base_interfaces import IntegrationTestBase

logger = central_logger.get_logger(__name__)


class MetricsDataSource:
    """Simulates real metrics data sources."""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.metrics_buffer = []
        self.active = False
    
    async def start_collection(self) -> None:
        """Start metrics collection."""
        self.active = True
        logger.info(f"Started metrics collection for {self.source_name}")
    
    async def stop_collection(self) -> None:
        """Stop metrics collection."""
        self.active = False
        logger.info(f"Stopped metrics collection for {self.source_name}")
    
    async def generate_metrics_batch(self, count: int) -> List[Dict[str, Any]]:
        """Generate batch of realistic metrics."""
        metrics = []
        base_time = time.time()
        
        for i in range(count):
            metric = {
                "source": self.source_name,
                "timestamp": base_time + i,
                "metric_id": str(uuid.uuid4()),
                "name": f"{self.source_name}_latency",
                "value": self._generate_realistic_latency(),
                "tags": {
                    "service": self.source_name,
                    "region": "us-east-1",
                    "environment": "production"
                }
            }
            metrics.append(metric)
        
        return metrics
    
    def _generate_realistic_latency(self) -> float:
        """Generate realistic latency values with proper distribution."""
        import random
        # Log-normal distribution for realistic latency patterns
        return max(1.0, random.lognormvariate(4.5, 0.5))


class TimeSeriesAggregator:
    """Real-time metrics aggregation engine."""
    
    def __init__(self):
        self.metrics_store = {}
        self.aggregation_cache = {}
        self.processing_times = []
    
    async def ingest_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ingest metrics with performance tracking."""
        start_time = time.time()
        
        for metric in metrics:
            metric_key = f"{metric['source']}:{metric['name']}"
            if metric_key not in self.metrics_store:
                self.metrics_store[metric_key] = []
            
            self.metrics_store[metric_key].append({
                "timestamp": metric["timestamp"],
                "value": metric["value"],
                "tags": metric["tags"]
            })
        
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)
        
        return {
            "ingested_count": len(metrics),
            "processing_time_ms": processing_time * 1000,
            "total_stored_metrics": sum(len(values) for values in self.metrics_store.values())
        }
    
    async def compute_time_series_aggregations(self, 
                                             metric_name: str, 
                                             time_window_seconds: int) -> Dict[str, Any]:
        """Compute time-series aggregations with accuracy validation."""
        start_time = time.time()
        
        current_time = time.time()
        window_start = current_time - time_window_seconds
        
        relevant_metrics = []
        for key, values in self.metrics_store.items():
            if metric_name in key:
                for metric in values:
                    if metric["timestamp"] >= window_start:
                        relevant_metrics.append(metric["value"])
        
        if not relevant_metrics:
            return {"error": "No metrics found for aggregation"}
        
        # Compute aggregations with high precision
        aggregations = {
            "count": len(relevant_metrics),
            "sum": sum(relevant_metrics),
            "avg": statistics.mean(relevant_metrics),
            "min": min(relevant_metrics),
            "max": max(relevant_metrics),
            "std_dev": statistics.stdev(relevant_metrics) if len(relevant_metrics) > 1 else 0
        }
        
        processing_time = time.time() - start_time
        
        return {
            "aggregations": aggregations,
            "processing_time_ms": processing_time * 1000,
            "data_points": len(relevant_metrics),
            "time_window": time_window_seconds
        }


class PercentileCalculator:
    """High-performance percentile calculation engine."""
    
    def __init__(self):
        self.calculation_cache = {}
    
    async def calculate_percentiles(self, 
                                  values: List[float], 
                                  percentiles: List[int] = [50, 95, 99]) -> Dict[str, Any]:
        """Calculate percentiles with performance measurement."""
        start_time = time.time()
        
        if not values:
            return {"error": "No values provided for percentile calculation"}
        
        sorted_values = sorted(values)
        results = {}
        
        for p in percentiles:
            if p < 0 or p > 100:
                results[f"p{p}"] = {"error": "Invalid percentile"}
                continue
            
            # Use precise percentile calculation
            index = (p / 100.0) * (len(sorted_values) - 1)
            
            if index.is_integer():
                results[f"p{p}"] = sorted_values[int(index)]
            else:
                lower_index = int(index)
                upper_index = lower_index + 1
                if upper_index < len(sorted_values):
                    # Linear interpolation
                    weight = index - lower_index
                    results[f"p{p}"] = (
                        sorted_values[lower_index] * (1 - weight) + 
                        sorted_values[upper_index] * weight
                    )
                else:
                    results[f"p{p}"] = sorted_values[lower_index]
        
        calculation_time = time.time() - start_time
        
        return {
            "percentiles": results,
            "calculation_time_ms": calculation_time * 1000,
            "data_points": len(values),
            "min_value": min(values),
            "max_value": max(values)
        }


class AlertThresholdMonitor:
    """Alert threshold monitoring and triggering system."""
    
    def __init__(self):
        self.thresholds = {}
        self.alerts_triggered = []
    
    def configure_threshold(self, 
                          metric_name: str, 
                          threshold_type: str, 
                          value: float,
                          severity: str = "warning") -> None:
        """Configure alert threshold."""
        if metric_name not in self.thresholds:
            self.thresholds[metric_name] = []
        
        self.thresholds[metric_name].append({
            "type": threshold_type,  # "above", "below", "percentile"
            "value": value,
            "severity": severity,
            "enabled": True
        })
    
    async def evaluate_thresholds(self, 
                                metric_name: str, 
                                current_value: float,
                                percentile_data: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Evaluate thresholds and trigger alerts."""
        alerts = []
        
        if metric_name not in self.thresholds:
            return alerts
        
        for threshold in self.thresholds[metric_name]:
            if not threshold["enabled"]:
                continue
            
            alert_triggered = False
            
            if threshold["type"] == "above" and current_value > threshold["value"]:
                alert_triggered = True
            elif threshold["type"] == "below" and current_value < threshold["value"]:
                alert_triggered = True
            elif threshold["type"] == "percentile" and percentile_data:
                # Check if p95 exceeds threshold
                p95_value = percentile_data.get("percentiles", {}).get("p95", 0)
                if p95_value > threshold["value"]:
                    alert_triggered = True
            
            if alert_triggered:
                alert = {
                    "alert_id": str(uuid.uuid4()),
                    "metric_name": metric_name,
                    "threshold_type": threshold["type"],
                    "threshold_value": threshold["value"],
                    "current_value": current_value,
                    "severity": threshold["severity"],
                    "timestamp": time.time()
                }
                alerts.append(alert)
                self.alerts_triggered.append(alert)
        
        return alerts


class MetricsExporter:
    """Multi-format metrics export system."""
    
    def __init__(self):
        self.export_history = []
    
    async def export_json(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export metrics to JSON format."""
        start_time = time.time()
        
        json_output = {
            "export_timestamp": time.time(),
            "format": "json",
            "data": metrics_data
        }
        
        # Simulate JSON serialization
        json_string = json.dumps(json_output, indent=2)
        
        export_time = time.time() - start_time
        
        return {
            "format": "json",
            "size_bytes": len(json_string.encode('utf-8')),
            "export_time_ms": export_time * 1000,
            "success": True
        }
    
    async def export_csv(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export metrics to CSV format."""
        start_time = time.time()
        
        # Simulate CSV generation
        csv_lines = ["timestamp,metric_name,value,source"]
        
        if "metrics" in metrics_data:
            for metric in metrics_data["metrics"]:
                line = f"{metric.get('timestamp', '')},{metric.get('name', '')},{metric.get('value', '')},{metric.get('source', '')}"
                csv_lines.append(line)
        
        csv_content = "\n".join(csv_lines)
        export_time = time.time() - start_time
        
        return {
            "format": "csv",
            "size_bytes": len(csv_content.encode('utf-8')),
            "export_time_ms": export_time * 1000,
            "rows": len(csv_lines) - 1,  # Exclude header
            "success": True
        }
    
    async def export_prometheus(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export metrics to Prometheus format."""
        start_time = time.time()
        
        # Simulate Prometheus format generation
        prometheus_lines = []
        
        if "aggregations" in metrics_data:
            agg = metrics_data["aggregations"]
            for metric_name, value in agg.items():
                if isinstance(value, (int, float)):
                    line = f"netra_{metric_name} {value}"
                    prometheus_lines.append(line)
        
        prometheus_content = "\n".join(prometheus_lines)
        export_time = time.time() - start_time
        
        return {
            "format": "prometheus",
            "size_bytes": len(prometheus_content.encode('utf-8')),
            "export_time_ms": export_time * 1000,
            "metrics_count": len(prometheus_lines),
            "success": True
        }


class TestMetricsAggregationPipeline(IntegrationTestBase):
    """Comprehensive metrics aggregation pipeline integration test."""
    
    def __init__(self):
        super().__init__()
        self.data_sources = []
        self.aggregator = TimeSeriesAggregator()
        self.percentile_calculator = PercentileCalculator()
        self.alert_monitor = AlertThresholdMonitor()
        self.exporter = MetricsExporter()
    
    async def setup_pipeline(self) -> None:
        """Setup complete metrics pipeline."""
        # Create multiple data sources
        source_names = ["api_gateway", "worker_service", "database", "cache_layer"]
        for name in source_names:
            source = MetricsDataSource(name)
            await source.start_collection()
            self.data_sources.append(source)
        
        # Configure alert thresholds
        self.alert_monitor.configure_threshold("api_gateway_latency", "above", 1000.0, "critical")
        self.alert_monitor.configure_threshold("database_latency", "percentile", 500.0, "warning")
        self.alert_monitor.configure_threshold("cache_layer_latency", "below", 1.0, "info")
        
        logger.info(f"Pipeline setup complete with {len(self.data_sources)} data sources")
    
    async def teardown_pipeline(self) -> None:
        """Cleanup pipeline resources."""
        for source in self.data_sources:
            await source.stop_collection()
        self.data_sources.clear()
        logger.info("Pipeline teardown complete")


@pytest_asyncio.fixture
async def metrics_pipeline():
    """Setup metrics aggregation pipeline."""
    pipeline = TestMetricsAggregationPipeline()
    await pipeline.setup_pipeline()
    yield pipeline
    await pipeline.teardown_pipeline()


@pytest.mark.asyncio
async def test_multi_source_metrics_collection(metrics_pipeline):
    """
    BVJ: Enterprise customers need unified metrics from diverse sources
    Test: Multi-source collection with performance validation
    """
    # Generate metrics from all sources
    all_metrics = []
    for source in metrics_pipeline.data_sources:
        metrics_batch = await source.generate_metrics_batch(250)  # 1K total metrics
        all_metrics.extend(metrics_batch)
    
    # Test ingestion performance
    start_time = time.time()
    ingestion_result = await metrics_pipeline.aggregator.ingest_metrics(all_metrics)
    total_time = time.time() - start_time
    
    # Validate requirements
    assert len(all_metrics) == 1000, f"Expected 1000 metrics, got {len(all_metrics)}"
    assert ingestion_result["ingested_count"] == 1000
    assert total_time < 1.0, f"Ingestion too slow: {total_time:.3f}s > 1.0s"
    
    # Validate metrics per second performance
    metrics_per_second = len(all_metrics) / total_time
    assert metrics_per_second >= 1000, f"Performance failure: {metrics_per_second:.0f} < 1000 metrics/sec"
    
    logger.info(f"Multi-source collection successful: {metrics_per_second:.0f} metrics/sec")


@pytest.mark.asyncio
async def test_time_series_aggregation_accuracy(metrics_pipeline):
    """
    BVJ: Accurate aggregations prevent wrong optimization decisions
    Test: Time-series aggregation with 99.99% precision requirement
    """
    # Generate known test data for accuracy validation
    test_metrics = []
    known_values = [100.0, 200.0, 300.0, 400.0, 500.0]  # Known sum = 1500
    
    for i, value in enumerate(known_values):
        metric = {
            "source": "accuracy_test",
            "timestamp": time.time() + i,
            "metric_id": f"test_metric_{i}",
            "name": "accuracy_test_latency",
            "value": value,
            "tags": {"test": "accuracy"}
        }
        test_metrics.append(metric)
    
    # Ingest test metrics
    await metrics_pipeline.aggregator.ingest_metrics(test_metrics)
    
    # Compute aggregations
    agg_result = await metrics_pipeline.aggregator.compute_time_series_aggregations(
        "accuracy_test_latency", 3600  # 1 hour window
    )
    
    # Validate accuracy (99.99% precision)
    assert "aggregations" in agg_result
    agg = agg_result["aggregations"]
    
    assert agg["count"] == 5, f"Count mismatch: {agg['count']} != 5"
    assert abs(agg["sum"] - 1500.0) < 0.01, f"Sum accuracy failure: {agg['sum']} != 1500.0"
    assert abs(agg["avg"] - 300.0) < 0.01, f"Average accuracy failure: {agg['avg']} != 300.0"
    assert agg["min"] == 100.0, f"Min accuracy failure: {agg['min']} != 100.0"
    assert agg["max"] == 500.0, f"Max accuracy failure: {agg['max']} != 500.0"
    
    # Validate processing performance
    assert agg_result["processing_time_ms"] < 500, f"Aggregation too slow: {agg_result['processing_time_ms']:.1f}ms"
    
    logger.info(f"Aggregation accuracy validated: {agg_result['processing_time_ms']:.1f}ms processing time")


@pytest.mark.asyncio
async def test_percentile_calculations(metrics_pipeline):
    """
    BVJ: Percentile analysis essential for latency optimization decisions
    Test: p50, p95, p99 calculations with performance requirements
    """
    # Generate realistic latency distribution
    test_values = []
    for i in range(10000):  # 10K data points for performance test
        # Create realistic latency distribution
        if i < 5000:  # 50% low latency
            test_values.append(float(50 + (i % 50)))
        elif i < 9500:  # 45% medium latency  
            test_values.append(float(100 + (i % 200)))
        else:  # 5% high latency
            test_values.append(float(500 + (i % 1000)))
    
    # Calculate percentiles with performance measurement
    start_time = time.time()
    percentile_result = await metrics_pipeline.percentile_calculator.calculate_percentiles(
        test_values, [50, 95, 99]
    )
    calculation_time = time.time() - start_time
    
    # Validate percentile calculations
    assert "percentiles" in percentile_result
    percentiles = percentile_result["percentiles"]
    
    assert "p50" in percentiles, "p50 calculation missing"
    assert "p95" in percentiles, "p95 calculation missing"
    assert "p99" in percentiles, "p99 calculation missing"
    
    # Validate percentile ordering (p50 < p95 < p99)
    assert percentiles["p50"] <= percentiles["p95"], f"p50 > p95: {percentiles['p50']} > {percentiles['p95']}"
    assert percentiles["p95"] <= percentiles["p99"], f"p95 > p99: {percentiles['p95']} > {percentiles['p99']}"
    
    # Validate performance requirement (<100ms for 10K data points)
    assert calculation_time < 0.1, f"Percentile calculation too slow: {calculation_time:.3f}s > 0.1s"
    assert percentile_result["calculation_time_ms"] < 100, f"Performance failure: {percentile_result['calculation_time_ms']:.1f}ms"
    
    logger.info(f"Percentile calculations: p50={percentiles['p50']:.1f}, p95={percentiles['p95']:.1f}, p99={percentiles['p99']:.1f}")


@pytest.mark.asyncio
async def test_alert_threshold_triggering(metrics_pipeline):
    """
    BVJ: Proactive alerts prevent service degradation and revenue loss
    Test: Alert threshold evaluation and triggering accuracy
    """
    # Test threshold triggering scenarios
    test_scenarios = [
        {"metric": "api_gateway_latency", "value": 1500.0, "should_alert": True},   # Above threshold
        {"metric": "api_gateway_latency", "value": 500.0, "should_alert": False},  # Below threshold
        {"metric": "cache_layer_latency", "value": 0.5, "should_alert": True},     # Below minimum threshold
    ]
    
    for scenario in test_scenarios:
        alerts = await metrics_pipeline.alert_monitor.evaluate_thresholds(
            scenario["metric"], scenario["value"]
        )
        
        if scenario["should_alert"]:
            assert len(alerts) > 0, f"Expected alert for {scenario['metric']} = {scenario['value']}"
            alert = alerts[0]
            assert alert["metric_name"] == scenario["metric"]
            assert alert["current_value"] == scenario["value"]
            assert "alert_id" in alert
            assert "timestamp" in alert
        else:
            assert len(alerts) == 0, f"Unexpected alert for {scenario['metric']} = {scenario['value']}"
    
    # Test percentile-based threshold
    test_values = [100] * 95 + [1000] * 5  # 95% low, 5% high values
    percentile_result = await metrics_pipeline.percentile_calculator.calculate_percentiles(test_values)
    
    percentile_alerts = await metrics_pipeline.alert_monitor.evaluate_thresholds(
        "database_latency", 200.0, percentile_result
    )
    
    # Should trigger alert because p95 > 500 (p95 ≈ 1000)
    assert len(percentile_alerts) > 0, "Expected percentile-based alert"
    
    logger.info(f"Alert threshold testing complete: {len(metrics_pipeline.alert_monitor.alerts_triggered)} total alerts")


@pytest.mark.asyncio
async def test_metrics_export_formats(metrics_pipeline):
    """
    BVJ: Multiple export formats enable integration with diverse monitoring tools
    Test: JSON, CSV, Prometheus export with performance validation
    """
    # Prepare test metrics data
    test_data = {
        "metrics": [
            {"timestamp": time.time(), "name": "latency", "value": 150.0, "source": "api"},
            {"timestamp": time.time(), "name": "throughput", "value": 1000.0, "source": "api"},
        ],
        "aggregations": {
            "avg_latency": 150.0,
            "total_requests": 1000,
            "error_rate": 0.02
        }
    }
    
    # Test JSON export
    json_result = await metrics_pipeline.exporter.export_json(test_data)
    assert json_result["format"] == "json"
    assert json_result["success"] == True
    assert json_result["export_time_ms"] < 1000, f"JSON export too slow: {json_result['export_time_ms']:.1f}ms"
    assert json_result["size_bytes"] > 0
    
    # Test CSV export
    csv_result = await metrics_pipeline.exporter.export_csv(test_data)
    assert csv_result["format"] == "csv"
    assert csv_result["success"] == True
    assert csv_result["export_time_ms"] < 1000, f"CSV export too slow: {csv_result['export_time_ms']:.1f}ms"
    assert csv_result["rows"] == 2  # Two metrics exported
    
    # Test Prometheus export
    prometheus_result = await metrics_pipeline.exporter.export_prometheus(test_data)
    assert prometheus_result["format"] == "prometheus"
    assert prometheus_result["success"] == True
    assert prometheus_result["export_time_ms"] < 1000, f"Prometheus export too slow: {prometheus_result['export_time_ms']:.1f}ms"
    assert prometheus_result["metrics_count"] == 3  # Three aggregation metrics
    
    logger.info("All export formats validated successfully")


@pytest.mark.asyncio
async def test_end_to_end_pipeline_integration(metrics_pipeline):
    """
    BVJ: Complete pipeline validation ensures $10K MRR protection
    Test: Full pipeline from collection to export with all components
    """
    # Step 1: Multi-source collection
    all_metrics = []
    for source in metrics_pipeline.data_sources:
        metrics_batch = await source.generate_metrics_batch(100)
        all_metrics.extend(metrics_batch)
    
    # Step 2: Ingestion
    ingestion_result = await metrics_pipeline.aggregator.ingest_metrics(all_metrics)
    assert ingestion_result["ingested_count"] == 400  # 4 sources × 100 metrics
    
    # Step 3: Aggregation
    agg_result = await metrics_pipeline.aggregator.compute_time_series_aggregations(
        "latency", 3600
    )
    assert "aggregations" in agg_result
    
    # Step 4: Percentile calculations
    latency_values = [m["value"] for m in all_metrics if "latency" in m["name"]]
    percentile_result = await metrics_pipeline.percentile_calculator.calculate_percentiles(latency_values)
    assert "percentiles" in percentile_result
    
    # Step 5: Alert evaluation
    p95_value = percentile_result["percentiles"]["p95"]
    alerts = await metrics_pipeline.alert_monitor.evaluate_thresholds(
        "test_latency", p95_value, percentile_result
    )
    
    # Step 6: Export to all formats
    export_data = {
        "metrics": all_metrics[:10],  # Sample for export
        "aggregations": agg_result["aggregations"]
    }
    
    json_export = await metrics_pipeline.exporter.export_json(export_data)
    csv_export = await metrics_pipeline.exporter.export_csv(export_data)
    prometheus_export = await metrics_pipeline.exporter.export_prometheus(export_data)
    
    # Validate end-to-end success
    assert json_export["success"] == True
    assert csv_export["success"] == True
    assert prometheus_export["success"] == True
    
    # Validate performance across entire pipeline
    total_export_time = (json_export["export_time_ms"] + 
                        csv_export["export_time_ms"] + 
                        prometheus_export["export_time_ms"])
    
    assert total_export_time < 3000, f"Total export time too slow: {total_export_time:.1f}ms"
    
    logger.info(f"End-to-end pipeline validation complete: {len(all_metrics)} metrics processed")


@pytest.mark.asyncio
async def test_pipeline_performance_benchmarks(metrics_pipeline):
    """
    BVJ: Performance benchmarks ensure scalability for enterprise growth
    Test: Comprehensive performance validation under load
    """
    # Benchmark 1: High-volume ingestion
    large_batch = []
    for source in metrics_pipeline.data_sources:
        batch = await source.generate_metrics_batch(2500)  # 10K total
        large_batch.extend(batch)
    
    start_time = time.time()
    ingestion_result = await metrics_pipeline.aggregator.ingest_metrics(large_batch)
    ingestion_time = time.time() - start_time
    
    ingestion_rate = len(large_batch) / ingestion_time
    assert ingestion_rate >= 1000, f"Ingestion rate too low: {ingestion_rate:.0f} < 1000 metrics/sec"
    
    # Benchmark 2: Large dataset percentile calculation
    large_values = [float(i) for i in range(50000)]  # 50K data points
    start_time = time.time()
    percentile_result = await metrics_pipeline.percentile_calculator.calculate_percentiles(large_values)
    percentile_time = time.time() - start_time
    
    assert percentile_time < 0.5, f"Large percentile calculation too slow: {percentile_time:.3f}s"
    
    # Benchmark 3: Concurrent operations
    tasks = []
    
    # Concurrent ingestion
    for _ in range(5):
        batch = await metrics_pipeline.data_sources[0].generate_metrics_batch(200)
        tasks.append(metrics_pipeline.aggregator.ingest_metrics(batch))
    
    # Concurrent aggregations
    for _ in range(3):
        tasks.append(metrics_pipeline.aggregator.compute_time_series_aggregations("latency", 1800))
    
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    concurrent_time = time.time() - start_time
    
    assert concurrent_time < 5.0, f"Concurrent operations too slow: {concurrent_time:.2f}s"
    assert all(isinstance(r, dict) for r in results), "Some concurrent operations failed"
    
    logger.info(f"Performance benchmarks: {ingestion_rate:.0f} metrics/sec, {percentile_time:.3f}s percentiles")
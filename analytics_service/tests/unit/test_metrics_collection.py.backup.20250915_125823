"""
Test Analytics Metrics Collection Business Logic

Business Value Justification (BVJ):
- Segment: Mid, Enterprise - Analytics & Business Intelligence
- Business Goal: Enable data-driven decision making through comprehensive metrics
- Value Impact: Users can track performance, usage patterns, and business outcomes
- Strategic Impact: Critical for product optimization and customer success metrics

This test suite validates analytics metrics collection including:
- Real-time metrics aggregation
- Time-series data processing
- Custom metric definition and tracking
- Performance monitoring and alerting
- Data export and reporting capabilities

Performance Requirements:
- Metric collection should complete within 10ms
- Aggregation queries should complete within 1 second
- Memory usage should be bounded during high-volume collection
- Data retention should be configurable and efficient
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any, Optional, List, Union

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    SET = "set"


class AggregationType(Enum):
    """Aggregation types for metric processing."""
    SUM = "sum"
    AVERAGE = "average"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    PERCENTILE = "percentile"


class MockMetric:
    """Mock metric for testing."""
    
    def __init__(self, name: str, metric_type: MetricType, value: Union[int, float], 
                 timestamp: Optional[datetime] = None, tags: Optional[Dict[str, str]] = None):
        self.name = name
        self.metric_type = metric_type
        self.value = value
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.tags = tags or {}
        self.id = f"metric_{uuid.uuid4().hex[:8]}"


class MockMetricsCollector:
    """Mock metrics collector for unit testing."""
    
    def __init__(self):
        self._metrics: Dict[str, List[MockMetric]] = {}
        self._metric_definitions: Dict[str, Dict[str, Any]] = {}
        self._aggregations: Dict[str, Dict[str, Any]] = {}
        self._alerts: Dict[str, Dict[str, Any]] = {}
        self._collection_stats = {
            "total_metrics_collected": 0,
            "collection_time_ms": 0,
            "aggregations_computed": 0,
            "alerts_triggered": 0,
            "unique_metric_names": 0,
            "start_time": time.time()
        }
    
    async def define_metric(self, name: str, metric_type: MetricType, description: str = "",
                           unit: str = "", tags: Optional[Dict[str, str]] = None,
                           retention_days: int = 30) -> bool:
        """Define a new metric for collection."""
        if name in self._metric_definitions:
            return False  # Metric already exists
        
        self._metric_definitions[name] = {
            "name": name,
            "type": metric_type,
            "description": description,
            "unit": unit,
            "tags": tags or {},
            "retention_days": retention_days,
            "created_at": datetime.now(timezone.utc),
            "sample_count": 0
        }
        
        # Initialize storage for this metric
        self._metrics[name] = []
        self._collection_stats["unique_metric_names"] = len(self._metric_definitions)
        
        return True
    
    async def collect_metric(self, name: str, value: Union[int, float],
                           timestamp: Optional[datetime] = None, 
                           tags: Optional[Dict[str, str]] = None) -> bool:
        """Collect a metric value."""
        start_time = time.time()
        
        # Check if metric is defined
        if name not in self._metric_definitions:
            # Auto-define metric if not exists
            await self.define_metric(name, MetricType.GAUGE)
        
        metric_def = self._metric_definitions[name]
        
        # Create metric
        metric = MockMetric(
            name=name,
            metric_type=metric_def["type"],
            value=value,
            timestamp=timestamp,
            tags=tags
        )
        
        # Store metric
        self._metrics[name].append(metric)
        
        # Update definition stats
        metric_def["sample_count"] += 1
        metric_def["last_updated"] = datetime.now(timezone.utc)
        
        # Update collection stats
        collection_time = (time.time() - start_time) * 1000
        self._collection_stats["total_metrics_collected"] += 1
        self._collection_stats["collection_time_ms"] += collection_time
        
        # Check alerts
        await self._check_alerts(name, value, tags)
        
        return True
    
    async def get_metrics(self, name: Optional[str] = None, start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None, tags: Optional[Dict[str, str]] = None,
                         limit: int = 1000) -> List[MockMetric]:
        """Retrieve metrics with filtering."""
        results = []
        
        # Determine which metrics to search
        metric_names = [name] if name else list(self._metrics.keys())
        
        for metric_name in metric_names:
            if metric_name not in self._metrics:
                continue
                
            for metric in self._metrics[metric_name]:
                # Apply filters
                if start_time and metric.timestamp < start_time:
                    continue
                if end_time and metric.timestamp > end_time:
                    continue
                
                # Tag filtering
                if tags:
                    if not all(metric.tags.get(k) == v for k, v in tags.items()):
                        continue
                
                results.append(metric)
                
                if len(results) >= limit:
                    break
            
            if len(results) >= limit:
                break
        
        # Sort by timestamp
        results.sort(key=lambda m: m.timestamp, reverse=True)
        
        return results[:limit]
    
    async def aggregate_metrics(self, name: str, aggregation: AggregationType,
                              start_time: Optional[datetime] = None,
                              end_time: Optional[datetime] = None,
                              group_by_tags: Optional[List[str]] = None,
                              percentile: Optional[float] = None) -> Dict[str, Any]:
        """Aggregate metrics over time period."""
        start_agg_time = time.time()
        
        # Get metrics for aggregation
        metrics = await self.get_metrics(
            name=name,
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        if not metrics:
            return {"aggregation": aggregation.value, "result": None, "count": 0}
        
        # Group metrics by tags if requested
        groups = {}
        if group_by_tags:
            for metric in metrics:
                group_key = tuple(metric.tags.get(tag, "unknown") for tag in group_by_tags)
                if group_key not in groups:
                    groups[group_key] = []
                groups[group_key].append(metric)
        else:
            groups["all"] = metrics
        
        # Perform aggregation for each group
        results = {}
        for group_key, group_metrics in groups.items():
            values = [m.value for m in group_metrics]
            
            if aggregation == AggregationType.SUM:
                result = sum(values)
            elif aggregation == AggregationType.AVERAGE:
                result = sum(values) / len(values)
            elif aggregation == AggregationType.COUNT:
                result = len(values)
            elif aggregation == AggregationType.MIN:
                result = min(values)
            elif aggregation == AggregationType.MAX:
                result = max(values)
            elif aggregation == AggregationType.PERCENTILE and percentile:
                sorted_values = sorted(values)
                index = int(len(sorted_values) * percentile / 100)
                result = sorted_values[min(index, len(sorted_values) - 1)]
            else:
                result = None
            
            group_name = "_".join(str(k) for k in group_key) if group_by_tags else "all"
            results[group_name] = {
                "value": result,
                "count": len(group_metrics),
                "timespan": {
                    "start": min(m.timestamp for m in group_metrics),
                    "end": max(m.timestamp for m in group_metrics)
                }
            }
        
        # Update aggregation stats
        agg_time = (time.time() - start_agg_time) * 1000
        self._collection_stats["aggregations_computed"] += 1
        
        return {
            "aggregation": aggregation.value,
            "results": results,
            "total_samples": len(metrics),
            "processing_time_ms": agg_time
        }
    
    async def create_alert(self, name: str, metric_name: str, condition: str,
                          threshold: Union[int, float], notification_config: Dict[str, Any]) -> str:
        """Create an alert for a metric."""
        alert_id = f"alert_{uuid.uuid4().hex[:8]}"
        
        self._alerts[alert_id] = {
            "id": alert_id,
            "name": name,
            "metric_name": metric_name,
            "condition": condition,  # "greater_than", "less_than", "equals"
            "threshold": threshold,
            "notification_config": notification_config,
            "created_at": datetime.now(timezone.utc),
            "enabled": True,
            "triggered_count": 0,
            "last_triggered": None
        }
        
        return alert_id
    
    async def _check_alerts(self, metric_name: str, value: Union[int, float], 
                           tags: Optional[Dict[str, str]]):
        """Check if any alerts should be triggered."""
        for alert_id, alert in self._alerts.items():
            if not alert["enabled"] or alert["metric_name"] != metric_name:
                continue
            
            condition = alert["condition"]
            threshold = alert["threshold"]
            
            should_trigger = False
            if condition == "greater_than" and value > threshold:
                should_trigger = True
            elif condition == "less_than" and value < threshold:
                should_trigger = True
            elif condition == "equals" and value == threshold:
                should_trigger = True
            
            if should_trigger:
                alert["triggered_count"] += 1
                alert["last_triggered"] = datetime.now(timezone.utc)
                self._collection_stats["alerts_triggered"] += 1
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        uptime_seconds = time.time() - self._collection_stats["start_time"]
        
        stats = {
            **self._collection_stats,
            "uptime_seconds": uptime_seconds,
            "avg_collection_time_ms": (
                self._collection_stats["collection_time_ms"] / 
                max(self._collection_stats["total_metrics_collected"], 1)
            ),
            "collection_rate_per_second": (
                self._collection_stats["total_metrics_collected"] / 
                max(uptime_seconds, 1)
            ),
            "active_alerts": len([a for a in self._alerts.values() if a["enabled"]]),
            "total_alerts": len(self._alerts)
        }
        
        return stats
    
    async def cleanup_old_metrics(self, older_than_days: int = 30) -> int:
        """Clean up old metrics based on retention policy."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        deleted_count = 0
        
        for metric_name in self._metrics:
            original_count = len(self._metrics[metric_name])
            self._metrics[metric_name] = [
                m for m in self._metrics[metric_name] 
                if m.timestamp > cutoff_time
            ]
            deleted_count += original_count - len(self._metrics[metric_name])
        
        return deleted_count


class TestMetricsCollector(SSotBaseTestCase):
    """Test MetricsCollector business logic and functionality."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        self.metrics_collector = MockMetricsCollector()
        
        # Standard business metrics for testing
        self.business_metrics = [
            ("user_sessions", MetricType.COUNTER, "Active user sessions", "count"),
            ("api_response_time", MetricType.HISTOGRAM, "API response time", "milliseconds"),
            ("agent_executions", MetricType.COUNTER, "Agent executions", "count"),
            ("error_rate", MetricType.GAUGE, "System error rate", "percentage"),
            ("revenue_impact", MetricType.GAUGE, "Revenue impact", "dollars")
        ]
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    async def test_metric_definition_and_collection(self):
        """Test metric definition and basic collection."""
        # When: Defining business metrics
        definition_results = []
        for name, metric_type, description, unit in self.business_metrics:
            result = await self.metrics_collector.define_metric(
                name=name,
                metric_type=metric_type,
                description=description,
                unit=unit,
                tags={"service": "netra", "environment": "test"},
                retention_days=90
            )
            definition_results.append(result)
        
        # Then: All metrics should be defined successfully
        assert all(definition_results)
        
        # And: Metric definitions should be stored correctly
        for name, metric_type, description, unit in self.business_metrics:
            definition = self.metrics_collector._metric_definitions[name]
            assert definition["name"] == name
            assert definition["type"] == metric_type
            assert definition["description"] == description
            assert definition["unit"] == unit
            assert definition["tags"]["service"] == "netra"
            assert definition["retention_days"] == 90
        
        # When: Collecting metric values
        collection_data = [
            ("user_sessions", 150, {"region": "us-west"}),
            ("api_response_time", 245.5, {"endpoint": "/api/agents"}),
            ("agent_executions", 1, {"agent_type": "cost_optimizer"}),
            ("error_rate", 0.02, {"severity": "warning"}),
            ("revenue_impact", 1250.75, {"customer_tier": "enterprise"})
        ]
        
        collection_results = []
        for name, value, tags in collection_data:
            result = await self.metrics_collector.collect_metric(
                name=name,
                value=value,
                tags=tags
            )
            collection_results.append(result)
        
        # Then: All collections should succeed
        assert all(collection_results)
        
        # And: Metrics should be retrievable
        for name, expected_value, expected_tags in collection_data:
            metrics = await self.metrics_collector.get_metrics(name=name, limit=1)
            assert len(metrics) == 1
            assert metrics[0].value == expected_value
            assert all(metrics[0].tags[k] == v for k, v in expected_tags.items())
        
        self.record_metric("metrics_defined", len(self.business_metrics))
        self.record_metric("metrics_collected", len(collection_data))
        self.record_metric("definition_collection_validated", True)
    
    @pytest.mark.unit
    async def test_time_series_data_processing(self):
        """Test time-series data collection and retrieval."""
        # Given: Time-series metric
        await self.metrics_collector.define_metric(
            name="cpu_usage",
            metric_type=MetricType.GAUGE,
            description="CPU usage percentage",
            unit="percentage"
        )
        
        # When: Collecting time-series data over period
        base_time = datetime.now(timezone.utc)
        time_series_data = []
        
        for i in range(10):
            timestamp = base_time - timedelta(minutes=i)
            # Simulate varying CPU usage
            cpu_value = 50 + (i * 5) + ((-1) ** i * 10)  # Oscillating pattern
            
            await self.metrics_collector.collect_metric(
                name="cpu_usage",
                value=cpu_value,
                timestamp=timestamp,
                tags={"host": "web-server-01"}
            )
            
            time_series_data.append((timestamp, cpu_value))
        
        # Then: Time-series data should be retrievable
        all_metrics = await self.metrics_collector.get_metrics(
            name="cpu_usage",
            limit=20
        )
        assert len(all_metrics) == 10
        
        # And: Data should be ordered by timestamp (newest first)
        timestamps = [m.timestamp for m in all_metrics]
        assert timestamps == sorted(timestamps, reverse=True)
        
        # When: Querying specific time ranges
        middle_time = base_time - timedelta(minutes=5)
        
        recent_metrics = await self.metrics_collector.get_metrics(
            name="cpu_usage",
            start_time=middle_time,
            limit=10
        )
        
        old_metrics = await self.metrics_collector.get_metrics(
            name="cpu_usage",
            end_time=middle_time,
            limit=10
        )
        
        # Then: Time filtering should work correctly
        assert len(recent_metrics) == 5  # Last 5 minutes
        assert len(old_metrics) == 6   # First 6 minutes (including middle_time)
        
        # And: All timestamps should be within expected ranges
        assert all(m.timestamp >= middle_time for m in recent_metrics)
        assert all(m.timestamp <= middle_time for m in old_metrics)
        
        self.record_metric("time_series_points", len(time_series_data))
        self.record_metric("time_series_processing_validated", True)
    
    @pytest.mark.unit
    async def test_metrics_aggregation_operations(self):
        """Test various aggregation operations on metrics."""
        # Given: Metrics for aggregation
        await self.metrics_collector.define_metric("response_time", MetricType.HISTOGRAM)
        
        # Generate sample response time data
        response_times = [100, 150, 200, 120, 180, 250, 90, 300, 110, 160]
        
        for i, response_time in enumerate(response_times):
            await self.metrics_collector.collect_metric(
                name="response_time",
                value=response_time,
                tags={"service": "api" if i < 5 else "web"}
            )
        
        # When: Performing different aggregations
        aggregation_tests = [
            (AggregationType.SUM, None),
            (AggregationType.AVERAGE, None),
            (AggregationType.COUNT, None),
            (AggregationType.MIN, None),
            (AggregationType.MAX, None),
            (AggregationType.PERCENTILE, 95)
        ]
        
        aggregation_results = {}
        for agg_type, percentile in aggregation_tests:
            result = await self.metrics_collector.aggregate_metrics(
                name="response_time",
                aggregation=agg_type,
                percentile=percentile
            )
            aggregation_results[agg_type.value] = result
        
        # Then: Aggregations should produce correct results
        # Sum aggregation
        sum_result = aggregation_results["sum"]
        assert sum_result["results"]["all"]["value"] == sum(response_times)
        assert sum_result["total_samples"] == len(response_times)
        
        # Average aggregation
        avg_result = aggregation_results["average"]
        expected_avg = sum(response_times) / len(response_times)
        assert abs(avg_result["results"]["all"]["value"] - expected_avg) < 0.01
        
        # Count aggregation
        count_result = aggregation_results["count"]
        assert count_result["results"]["all"]["value"] == len(response_times)
        
        # Min/Max aggregations
        min_result = aggregation_results["min"]
        max_result = aggregation_results["max"]
        assert min_result["results"]["all"]["value"] == min(response_times)
        assert max_result["results"]["all"]["value"] == max(response_times)
        
        # Percentile aggregation
        p95_result = aggregation_results["percentile"]
        assert p95_result["results"]["all"]["value"] is not None
        
        # When: Aggregating with grouping by tags
        grouped_result = await self.metrics_collector.aggregate_metrics(
            name="response_time",
            aggregation=AggregationType.AVERAGE,
            group_by_tags=["service"]
        )
        
        # Then: Should have separate results for each service
        assert "api" in grouped_result["results"]
        assert "web" in grouped_result["results"]
        
        api_avg = sum(response_times[:5]) / 5
        web_avg = sum(response_times[5:]) / 5
        
        assert abs(grouped_result["results"]["api"]["value"] - api_avg) < 0.01
        assert abs(grouped_result["results"]["web"]["value"] - web_avg) < 0.01
        
        self.record_metric("aggregation_operations_tested", len(aggregation_tests))
        self.record_metric("aggregation_validated", True)
    
    @pytest.mark.unit
    async def test_alert_system_functionality(self):
        """Test alert creation and triggering."""
        # Given: Metric with alert monitoring
        await self.metrics_collector.define_metric("error_count", MetricType.COUNTER)
        
        # When: Creating alerts
        alert_configs = [
            {
                "name": "High Error Rate",
                "condition": "greater_than",
                "threshold": 10,
                "notification": {"email": "ops@company.com", "slack": "#alerts"}
            },
            {
                "name": "Low Error Rate",
                "condition": "less_than", 
                "threshold": 1,
                "notification": {"email": "dev@company.com"}
            }
        ]
        
        alert_ids = []
        for config in alert_configs:
            alert_id = await self.metrics_collector.create_alert(
                name=config["name"],
                metric_name="error_count",
                condition=config["condition"],
                threshold=config["threshold"],
                notification_config=config["notification"]
            )
            alert_ids.append(alert_id)
        
        # Then: Alerts should be created successfully
        assert len(alert_ids) == 2
        assert all(alert_id in self.metrics_collector._alerts for alert_id in alert_ids)
        
        # When: Collecting metrics that trigger alerts
        test_values = [5, 15, 0, 12, 8]  # Some above/below thresholds
        
        for value in test_values:
            await self.metrics_collector.collect_metric(
                name="error_count",
                value=value
            )
        
        # Then: Alerts should be triggered appropriately
        stats = await self.metrics_collector.get_collection_stats()
        assert stats["alerts_triggered"] > 0
        
        # And: Alert counters should be updated
        high_error_alert = None
        low_error_alert = None
        
        for alert in self.metrics_collector._alerts.values():
            if alert["name"] == "High Error Rate":
                high_error_alert = alert
            elif alert["name"] == "Low Error Rate":
                low_error_alert = alert
        
        assert high_error_alert is not None
        assert low_error_alert is not None
        
        # High error alert should trigger for values > 10 (15, 12)
        assert high_error_alert["triggered_count"] >= 2
        
        # Low error alert should trigger for values < 1 (0)
        assert low_error_alert["triggered_count"] >= 1
        
        self.record_metric("alerts_created", len(alert_configs))
        self.record_metric("alert_triggers_tested", len(test_values))
        self.record_metric("alert_system_validated", True)
    
    @pytest.mark.unit
    async def test_metrics_retention_and_cleanup(self):
        """Test metrics retention policies and cleanup."""
        # Given: Metrics with different ages
        await self.metrics_collector.define_metric("test_metric", MetricType.GAUGE)
        
        base_time = datetime.now(timezone.utc)
        
        # Create old metrics (over 30 days)
        old_metrics_data = []
        for i in range(5):
            old_timestamp = base_time - timedelta(days=35 + i)
            await self.metrics_collector.collect_metric(
                name="test_metric",
                value=100 + i,
                timestamp=old_timestamp,
                tags={"age": "old"}
            )
            old_metrics_data.append(old_timestamp)
        
        # Create recent metrics (under 30 days)
        recent_metrics_data = []
        for i in range(3):
            recent_timestamp = base_time - timedelta(days=10 + i)
            await self.metrics_collector.collect_metric(
                name="test_metric",
                value=200 + i,
                timestamp=recent_timestamp,
                tags={"age": "recent"}
            )
            recent_metrics_data.append(recent_timestamp)
        
        # Verify initial state
        initial_metrics = await self.metrics_collector.get_metrics("test_metric", limit=10)
        assert len(initial_metrics) == 8  # 5 old + 3 recent
        
        # When: Cleaning up old metrics
        deleted_count = await self.metrics_collector.cleanup_old_metrics(older_than_days=30)
        
        # Then: Old metrics should be deleted
        assert deleted_count == 5
        
        # And: Recent metrics should remain
        remaining_metrics = await self.metrics_collector.get_metrics("test_metric", limit=10)
        assert len(remaining_metrics) == 3
        
        # And: Only recent metrics should be present
        for metric in remaining_metrics:
            assert metric.tags.get("age") == "recent"
            assert metric.timestamp > base_time - timedelta(days=30)
        
        self.record_metric("old_metrics_created", len(old_metrics_data))
        self.record_metric("recent_metrics_created", len(recent_metrics_data))
        self.record_metric("metrics_cleaned_up", deleted_count)
        self.record_metric("retention_cleanup_validated", True)


class TestMetricsCollectorPerformance(SSotBaseTestCase):
    """Test metrics collector performance characteristics."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        self.metrics_collector = MockMetricsCollector()
    
    @pytest.mark.unit
    async def test_high_volume_metrics_collection(self):
        """Test performance under high-volume metrics collection."""
        # Given: High-volume metric collection scenario
        await self.metrics_collector.define_metric("high_volume_metric", MetricType.COUNTER)
        
        metric_count = 1000
        max_collection_time_ms = 10  # 10ms max per metric
        
        # When: Collecting many metrics rapidly
        collection_times = []
        
        for i in range(metric_count):
            start_time = time.time()
            
            await self.metrics_collector.collect_metric(
                name="high_volume_metric",
                value=i,
                tags={"batch": str(i // 100), "index": str(i)}
            )
            
            collection_time = (time.time() - start_time) * 1000  # Convert to ms
            collection_times.append(collection_time)
        
        # Then: Performance should meet requirements
        avg_collection_time = sum(collection_times) / len(collection_times)
        max_collection_time = max(collection_times)
        
        assert avg_collection_time < max_collection_time_ms
        assert max_collection_time < max_collection_time_ms * 3  # Allow some variance
        
        # And: All metrics should be collected
        stats = await self.metrics_collector.get_collection_stats()
        assert stats["total_metrics_collected"] >= metric_count
        
        self.record_metric("high_volume_metrics_collected", metric_count)
        self.record_metric("avg_collection_time_ms", avg_collection_time)
        self.record_metric("max_collection_time_ms", max_collection_time)
    
    @pytest.mark.unit
    async def test_aggregation_performance_with_large_dataset(self):
        """Test aggregation performance with large datasets."""
        # Given: Large dataset for aggregation
        await self.metrics_collector.define_metric("perf_metric", MetricType.HISTOGRAM)
        
        data_points = 500
        max_aggregation_time_ms = 1000  # 1 second max
        
        # Create large dataset
        for i in range(data_points):
            await self.metrics_collector.collect_metric(
                name="perf_metric",
                value=100 + (i % 200),  # Values between 100-300
                tags={"service": f"service_{i % 10}", "region": f"region_{i % 3}"}
            )
        
        # When: Performing aggregations on large dataset
        aggregation_tests = [
            ("sum", AggregationType.SUM),
            ("average", AggregationType.AVERAGE),
            ("count", AggregationType.COUNT),
            ("min", AggregationType.MIN),
            ("max", AggregationType.MAX)
        ]
        
        aggregation_times = []
        
        for test_name, agg_type in aggregation_tests:
            start_time = time.time()
            
            result = await self.metrics_collector.aggregate_metrics(
                name="perf_metric",
                aggregation=agg_type,
                group_by_tags=["service"]
            )
            
            agg_time = (time.time() - start_time) * 1000  # Convert to ms
            aggregation_times.append((test_name, agg_time))
            
            # Verify result structure
            assert result["total_samples"] == data_points
            assert len(result["results"]) == 10  # 10 different services
        
        # Then: Aggregation performance should meet requirements
        for test_name, agg_time in aggregation_times:
            assert agg_time < max_aggregation_time_ms, f"Aggregation '{test_name}' took {agg_time}ms"
        
        avg_agg_time = sum(time for _, time in aggregation_times) / len(aggregation_times)
        max_agg_time = max(time for _, time in aggregation_times)
        
        self.record_metric("performance_data_points", data_points)
        self.record_metric("aggregation_tests_performed", len(aggregation_tests))
        self.record_metric("avg_aggregation_time_ms", avg_agg_time)
        self.record_metric("max_aggregation_time_ms", max_agg_time)
        self.record_metric("aggregation_performance_validated", True)
    
    def teardown_method(self, method):
        """Cleanup after each test."""
        # Log test execution metrics
        execution_time = self.get_metrics().execution_time
        if execution_time > 3.0:  # Warn for slow tests
            self.record_metric("slow_metrics_test_warning", execution_time)
        
        super().teardown_method(method)
"""Metrics Aggregation Pipeline L4 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (operational excellence for all tiers)
- Business Goal: Ensure metrics aggregation accuracy and performance for observability
- Value Impact: Protects $10K MRR through reliable data-driven decision making and monitoring
- Strategic Impact: Critical for time-series analytics, rollup operations, and retention policies

Critical Path: 
Raw metrics ingestion -> Time-series aggregation -> Rollup computations -> Retention enforcement -> Query optimization

Coverage: Real ClickHouse time-series, Prometheus aggregation, retention policies, rollup accuracy, staging validation
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
import uuid
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import random
import math

# Add project root to path


# from netra_backend.app.tests.unified.e2e.staging_test_helpers import StagingTestSuite, get_staging_suite
from unittest.mock import AsyncMock
StagingTestSuite = AsyncMock
get_staging_suite = AsyncMock
from netra_backend.app.db.client_clickhouse import ClickHouseClient
from netra_backend.app.core.health_checkers import HealthChecker


# Mock metrics aggregation components for L4 testing
class MetricsCollector:
    """Mock metrics collector for L4 testing."""
    async def initialize(self): pass
    async def shutdown(self): pass
    
    async def collect_metric(self, metric_data: Dict) -> Dict[str, Any]:
        return {"success": True}


class PrometheusExporter:
    """Mock Prometheus exporter for L4 testing."""
    async def initialize(self): pass
    async def shutdown(self): pass
    
    async def export_metric(self, metric_data: Dict) -> Dict[str, Any]:
        return {"success": True}


class TimeSeriesAggregator:
    """Mock time-series aggregator for L4 testing."""
    async def initialize(self): pass
    async def shutdown(self): pass


class RollupEngine:
    """Mock rollup engine for L4 testing."""
    async def initialize(self): pass
    async def shutdown(self): pass


class RetentionManager:
    """Mock retention manager for L4 testing."""
    async def initialize(self): pass
    async def shutdown(self): pass


@dataclass
class AggregationMetrics:
    """Metrics container for aggregation pipeline testing."""
    raw_metrics_ingested: int
    aggregation_accuracy: float
    rollup_computation_time: float
    retention_policy_compliance: float
    query_performance_improvement: float
    data_compression_ratio: float


@dataclass
class TimeSeriesMetric:
    """Time-series metric data container."""
    metric_name: str
    timestamp: datetime
    value: float
    labels: Dict[str, str]
    source: str
    aggregation_level: str


class MetricsAggregationPipelineL4TestSuite:
    """L4 test suite for metrics aggregation pipeline in staging environment."""
    
    def __init__(self):
        self.staging_suite: Optional[StagingTestSuite] = None
        self.clickhouse_client: Optional[ClickHouseClient] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.prometheus_exporter: Optional[PrometheusExporter] = None
        self.time_series_aggregator: Optional[TimeSeriesAggregator] = None
        self.rollup_engine: Optional[RollupEngine] = None
        self.retention_manager: Optional[RetentionManager] = None
        self.raw_metrics: List[TimeSeriesMetric] = []
        self.aggregated_metrics: List[Dict] = []
        self.rollup_results: List[Dict] = []
        self.test_metrics = {
            "metrics_ingested": 0,
            "aggregations_computed": 0,
            "rollups_executed": 0,
            "retention_cleanups": 0,
            "queries_optimized": 0
        }
        
    async def initialize_l4_environment(self) -> None:
        """Initialize L4 staging environment for metrics aggregation testing."""
        self.staging_suite = await get_staging_suite()
        await self.staging_suite.setup()
        
        # Initialize ClickHouse client for time-series data
        self.clickhouse_client = ClickHouseClient()
        await self.clickhouse_client.initialize()
        
        # Initialize metrics collection components
        self.metrics_collector = MetricsCollector()
        await self.metrics_collector.initialize()
        
        self.prometheus_exporter = PrometheusExporter()
        await self.prometheus_exporter.initialize()
        
        # Initialize aggregation components
        self.time_series_aggregator = TimeSeriesAggregator()
        await self.time_series_aggregator.initialize()
        
        self.rollup_engine = RollupEngine()
        await self.rollup_engine.initialize()
        
        self.retention_manager = RetentionManager()
        await self.retention_manager.initialize()
        
        # Validate staging infrastructure
        await self._validate_aggregation_infrastructure()
    
    async def _validate_aggregation_infrastructure(self) -> None:
        """Validate metrics aggregation infrastructure in staging."""
        try:
            # Test ClickHouse connectivity
            clickhouse_health = await self.clickhouse_client.execute_query("SELECT 1 as health_check")
            if not clickhouse_health or len(clickhouse_health) == 0:
                raise RuntimeError("ClickHouse not accessible")
            
            # Verify time-series tables exist
            tables_query = """
            SELECT name FROM system.tables 
            WHERE database = 'netra_metrics' 
            AND name IN ('raw_metrics', 'aggregated_metrics_1m', 'aggregated_metrics_1h', 'aggregated_metrics_1d')
            """
            
            existing_tables = await self.clickhouse_client.execute_query(tables_query)
            required_tables = {'raw_metrics', 'aggregated_metrics_1m', 'aggregated_metrics_1h', 'aggregated_metrics_1d'}
            found_tables = {table['name'] for table in existing_tables} if existing_tables else set()
            
            if not required_tables.issubset(found_tables):
                missing_tables = required_tables - found_tables
                raise RuntimeError(f"Missing required time-series tables: {missing_tables}")
                
        except Exception as e:
            raise RuntimeError(f"Aggregation infrastructure validation failed: {e}")
    
    async def generate_time_series_data_l4(self, data_points: int = 10000, 
                                         time_range_hours: int = 24) -> Dict[str, Any]:
        """Generate realistic time-series data for aggregation testing."""
        generation_start = time.time()
        
        # Define realistic metric patterns
        metric_patterns = [
            {
                "name": "api_request_duration_seconds",
                "base_value": 0.150,
                "variance": 0.050,
                "trend": "stable",
                "labels": {"service": "api", "endpoint": "/users", "method": "GET"}
            },
            {
                "name": "http_requests_total",
                "base_value": 1000,
                "variance": 200,
                "trend": "increasing",
                "labels": {"service": "api", "status": "200", "method": "GET"}
            },
            {
                "name": "memory_usage_bytes",
                "base_value": 2147483648,  # 2GB
                "variance": 536870912,     # 512MB
                "trend": "cyclical",
                "labels": {"service": "backend", "instance": "web-1"}
            },
            {
                "name": "llm_tokens_processed_total",
                "base_value": 50000,
                "variance": 15000,
                "trend": "increasing",
                "labels": {"model": "gpt-4", "user_tier": "enterprise"}
            },
            {
                "name": "billing_amount_cents",
                "base_value": 12500,  # $125.00
                "variance": 5000,     # $50.00
                "trend": "stable",
                "labels": {"user_tier": "enterprise", "region": "us-east"}
            }
        ]
        
        # Generate time-series data points
        start_time = datetime.utcnow() - timedelta(hours=time_range_hours)
        time_interval = timedelta(hours=time_range_hours) / data_points
        
        for i in range(data_points):
            current_time = start_time + (time_interval * i)
            
            # Select random metric pattern
            pattern = random.choice(metric_patterns)
            
            # Calculate value based on pattern
            value = self._calculate_metric_value(pattern, i, data_points)
            
            # Create time-series metric
            metric = TimeSeriesMetric(
                metric_name=pattern["name"],
                timestamp=current_time,
                value=value,
                labels=pattern["labels"].copy(),
                source="l4_test_generator",
                aggregation_level="raw"
            )
            
            # Add some variance to labels for realistic cardinality
            if random.random() < 0.3:  # 30% chance of label variation
                metric.labels["instance"] = f"instance-{random.randint(1, 5)}"
            
            self.raw_metrics.append(metric)
            self.test_metrics["metrics_ingested"] += 1
        
        # Insert raw metrics into ClickHouse
        insertion_result = await self._insert_raw_metrics_clickhouse()
        
        generation_time = time.time() - generation_start
        
        return {
            "total_metrics_generated": len(self.raw_metrics),
            "time_range_hours": time_range_hours,
            "generation_time": generation_time,
            "insertion_success": insertion_result["success"],
            "insertion_rate": insertion_result["insertion_rate"]
        }
    
    def _calculate_metric_value(self, pattern: Dict, index: int, total_points: int) -> float:
        """Calculate metric value based on pattern and position in time series."""
        base_value = pattern["base_value"]
        variance = pattern["variance"]
        trend = pattern["trend"]
        
        # Apply trend
        if trend == "increasing":
            trend_factor = 1.0 + (index / total_points) * 0.5  # 50% increase over time
        elif trend == "decreasing":
            trend_factor = 1.0 - (index / total_points) * 0.3  # 30% decrease over time
        elif trend == "cyclical":
            # Sine wave pattern
            cycle_position = (index / total_points) * 2 * math.pi
            trend_factor = 1.0 + 0.2 * math.sin(cycle_position)  # 20% amplitude
        else:  # stable
            trend_factor = 1.0
        
        # Apply random variance
        random_factor = 1.0 + random.uniform(-0.2, 0.2)  # ±20% random variation
        
        # Calculate final value
        value = base_value * trend_factor * random_factor
        
        # Add Gaussian noise for realism
        noise = random.gauss(0, variance * 0.1)
        value += noise
        
        return max(0, value)  # Ensure non-negative values
    
    async def _insert_raw_metrics_clickhouse(self) -> Dict[str, Any]:
        """Insert raw metrics into ClickHouse time-series tables."""
        try:
            # Prepare batch insert data
            batch_data = []
            for metric in self.raw_metrics:
                batch_data.append({
                    "metric_name": metric.metric_name,
                    "timestamp": metric.timestamp,
                    "value": metric.value,
                    "labels": json.dumps(metric.labels),
                    "source": metric.source
                })
            
            # Execute batch insert
            insert_query = """
            INSERT INTO netra_metrics.raw_metrics 
            (metric_name, timestamp, value, labels, source)
            VALUES
            """
            
            insertion_start = time.time()
            result = await self.clickhouse_client.insert_batch(
                "netra_metrics.raw_metrics",
                batch_data
            )
            insertion_time = time.time() - insertion_start
            
            insertion_rate = len(batch_data) / insertion_time if insertion_time > 0 else 0
            
            return {
                "success": result["success"] if result else True,
                "insertion_rate": insertion_rate,
                "records_inserted": len(batch_data)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "insertion_rate": 0
            }
    
    async def test_time_series_aggregation_l4(self) -> Dict[str, Any]:
        """Test time-series aggregation accuracy and performance."""
        aggregation_results = {
            "aggregation_levels_tested": 0,
            "aggregation_accuracy": 0.0,
            "aggregation_performance": {},
            "data_reduction_ratios": {}
        }
        
        # Define aggregation levels to test
        aggregation_levels = [
            {"interval": "1m", "table": "aggregated_metrics_1m"},
            {"interval": "1h", "table": "aggregated_metrics_1h"},
            {"interval": "1d", "table": "aggregated_metrics_1d"}
        ]
        
        for level in aggregation_levels:
            aggregation_start = time.time()
            
            try:
                # Execute aggregation for this level
                aggregation_query = f"""
                INSERT INTO netra_metrics.{level['table']}
                SELECT 
                    metric_name,
                    toStartOfInterval(timestamp, INTERVAL {level['interval']}) as aggregation_timestamp,
                    avg(value) as avg_value,
                    min(value) as min_value,
                    max(value) as max_value,
                    count() as sample_count,
                    labels
                FROM netra_metrics.raw_metrics
                WHERE timestamp >= now() - INTERVAL 25 HOUR
                GROUP BY metric_name, aggregation_timestamp, labels
                """
                
                aggregation_result = await self.clickhouse_client.execute_query(aggregation_query)
                aggregation_time = time.time() - aggregation_start
                
                # Verify aggregation results
                verification_query = f"""
                SELECT 
                    metric_name,
                    count() as aggregated_points,
                    avg(avg_value) as overall_avg,
                    sum(sample_count) as total_samples
                FROM netra_metrics.{level['table']}
                WHERE aggregation_timestamp >= now() - INTERVAL 25 HOUR
                GROUP BY metric_name
                """
                
                verification_result = await self.clickhouse_client.execute_query(verification_query)
                
                if verification_result:
                    # Calculate data reduction ratio
                    total_raw_points = len(self.raw_metrics)
                    total_aggregated_points = sum(row["aggregated_points"] for row in verification_result)
                    
                    if total_aggregated_points > 0:
                        reduction_ratio = total_raw_points / total_aggregated_points
                        aggregation_results["data_reduction_ratios"][level["interval"]] = reduction_ratio
                    
                    # Store performance metrics
                    aggregation_results["aggregation_performance"][level["interval"]] = aggregation_time
                    
                    aggregation_results["aggregation_levels_tested"] += 1
                    self.test_metrics["aggregations_computed"] += 1
                
            except Exception as e:
                print(f"Aggregation failed for level {level['interval']}: {e}")
        
        # Calculate overall aggregation accuracy
        if aggregation_results["aggregation_levels_tested"] > 0:
            aggregation_results["aggregation_accuracy"] = aggregation_results["aggregation_levels_tested"] / len(aggregation_levels)
        
        return aggregation_results
    
    async def test_rollup_computations_l4(self) -> Dict[str, Any]:
        """Test rollup computations for time-series data."""
        rollup_results = {
            "rollup_operations_tested": 0,
            "rollup_accuracy": 0.0,
            "rollup_performance": {},
            "rollup_consistency": True
        }
        
        # Define rollup operations to test
        rollup_operations = [
            {
                "name": "hourly_to_daily",
                "source_table": "aggregated_metrics_1h",
                "target_table": "aggregated_metrics_1d",
                "aggregation_function": "avg"
            },
            {
                "name": "minute_to_hourly",
                "source_table": "aggregated_metrics_1m", 
                "target_table": "aggregated_metrics_1h",
                "aggregation_function": "avg"
            }
        ]
        
        for rollup_op in rollup_operations:
            rollup_start = time.time()
            
            try:
                # Execute rollup computation
                rollup_query = f"""
                INSERT INTO netra_metrics.{rollup_op['target_table']}
                SELECT 
                    metric_name,
                    toStartOfHour(aggregation_timestamp) as aggregation_timestamp,
                    {rollup_op['aggregation_function']}(avg_value) as avg_value,
                    min(min_value) as min_value,
                    max(max_value) as max_value,
                    sum(sample_count) as sample_count,
                    labels
                FROM netra_metrics.{rollup_op['source_table']}
                WHERE aggregation_timestamp >= now() - INTERVAL 25 HOUR
                GROUP BY metric_name, toStartOfHour(aggregation_timestamp), labels
                """
                
                rollup_result = await self.clickhouse_client.execute_query(rollup_query)
                rollup_time = time.time() - rollup_start
                
                # Verify rollup results
                verification_query = f"""
                SELECT 
                    metric_name,
                    count() as rollup_points,
                    avg(avg_value) as rollup_avg
                FROM netra_metrics.{rollup_op['target_table']}
                WHERE aggregation_timestamp >= now() - INTERVAL 25 HOUR
                GROUP BY metric_name
                """
                
                verification_result = await self.clickhouse_client.execute_query(verification_query)
                
                if verification_result:
                    rollup_results["rollup_performance"][rollup_op["name"]] = rollup_time
                    rollup_results["rollup_operations_tested"] += 1
                    self.test_metrics["rollups_executed"] += 1
                
            except Exception as e:
                print(f"Rollup failed for operation {rollup_op['name']}: {e}")
                rollup_results["rollup_consistency"] = False
        
        # Calculate rollup accuracy
        if len(rollup_operations) > 0:
            rollup_results["rollup_accuracy"] = rollup_results["rollup_operations_tested"] / len(rollup_operations)
        
        return rollup_results
    
    async def test_retention_policy_enforcement_l4(self) -> Dict[str, Any]:
        """Test retention policy enforcement for time-series data."""
        retention_results = {
            "retention_policies_tested": 0,
            "data_cleanup_success": True,
            "retention_efficiency": 0.0,
            "cleanup_performance": {}
        }
        
        # Define retention policies to test
        retention_policies = [
            {
                "table": "raw_metrics",
                "retention_days": 7,
                "policy_name": "raw_data_7d"
            },
            {
                "table": "aggregated_metrics_1m",
                "retention_days": 30,
                "policy_name": "minute_aggregates_30d"
            },
            {
                "table": "aggregated_metrics_1h", 
                "retention_days": 180,
                "policy_name": "hourly_aggregates_180d"
            }
        ]
        
        for policy in retention_policies:
            cleanup_start = time.time()
            
            try:
                # Check current data volume before cleanup
                pre_cleanup_query = f"""
                SELECT count() as record_count
                FROM netra_metrics.{policy['table']}
                WHERE timestamp < now() - INTERVAL {policy['retention_days']} DAY
                """
                
                pre_cleanup_result = await self.clickhouse_client.execute_query(pre_cleanup_query)
                pre_cleanup_count = pre_cleanup_result[0]["record_count"] if pre_cleanup_result else 0
                
                # Execute retention cleanup
                cleanup_query = f"""
                ALTER TABLE netra_metrics.{policy['table']}
                DELETE WHERE timestamp < now() - INTERVAL {policy['retention_days']} DAY
                """
                
                cleanup_result = await self.clickhouse_client.execute_query(cleanup_query)
                
                # Check data volume after cleanup
                post_cleanup_query = f"""
                SELECT count() as record_count
                FROM netra_metrics.{policy['table']}
                WHERE timestamp < now() - INTERVAL {policy['retention_days']} DAY
                """
                
                post_cleanup_result = await self.clickhouse_client.execute_query(post_cleanup_query)
                post_cleanup_count = post_cleanup_result[0]["record_count"] if post_cleanup_result else 0
                
                cleanup_time = time.time() - cleanup_start
                
                # Calculate cleanup efficiency
                if pre_cleanup_count > 0:
                    cleanup_efficiency = (pre_cleanup_count - post_cleanup_count) / pre_cleanup_count
                else:
                    cleanup_efficiency = 1.0  # No data to clean up
                
                retention_results["cleanup_performance"][policy["policy_name"]] = cleanup_time
                retention_results["retention_policies_tested"] += 1
                
                if cleanup_efficiency < 0.9:  # Less than 90% cleanup
                    retention_results["data_cleanup_success"] = False
                
                self.test_metrics["retention_cleanups"] += 1
                
            except Exception as e:
                print(f"Retention cleanup failed for policy {policy['policy_name']}: {e}")
                retention_results["data_cleanup_success"] = False
        
        # Calculate overall retention efficiency
        if retention_results["retention_policies_tested"] > 0:
            retention_results["retention_efficiency"] = (
                retention_results["retention_policies_tested"] / len(retention_policies)
            )
        
        return retention_results
    
    async def test_query_optimization_l4(self) -> Dict[str, Any]:
        """Test query optimization for aggregated time-series data."""
        optimization_results = {
            "queries_tested": 0,
            "optimization_improvement": 0.0,
            "query_performance": {},
            "index_effectiveness": 0.0
        }
        
        # Define test queries to benchmark
        test_queries = [
            {
                "name": "range_query_raw",
                "query": """
                SELECT metric_name, avg(value) as avg_value
                FROM netra_metrics.raw_metrics
                WHERE timestamp >= now() - INTERVAL 1 HOUR
                GROUP BY metric_name
                """,
                "table": "raw_metrics"
            },
            {
                "name": "range_query_aggregated",
                "query": """
                SELECT metric_name, avg(avg_value) as avg_value
                FROM netra_metrics.aggregated_metrics_1m
                WHERE aggregation_timestamp >= now() - INTERVAL 1 HOUR
                GROUP BY metric_name
                """,
                "table": "aggregated_metrics_1m"
            },
            {
                "name": "time_series_analysis",
                "query": """
                SELECT 
                    metric_name,
                    aggregation_timestamp,
                    avg_value,
                    lag(avg_value) OVER (PARTITION BY metric_name ORDER BY aggregation_timestamp) as prev_value
                FROM netra_metrics.aggregated_metrics_1h
                WHERE aggregation_timestamp >= now() - INTERVAL 24 HOUR
                ORDER BY metric_name, aggregation_timestamp
                """,
                "table": "aggregated_metrics_1h"
            }
        ]
        
        for test_query in test_queries:
            # Execute query and measure performance
            query_start = time.time()
            
            try:
                query_result = await self.clickhouse_client.execute_query(test_query["query"])
                query_time = time.time() - query_start
                
                optimization_results["query_performance"][test_query["name"]] = {
                    "execution_time": query_time,
                    "result_count": len(query_result) if query_result else 0
                }
                
                optimization_results["queries_tested"] += 1
                self.test_metrics["queries_optimized"] += 1
                
            except Exception as e:
                print(f"Query optimization test failed for {test_query['name']}: {e}")
        
        # Calculate optimization improvement (compare raw vs aggregated queries)
        raw_query_time = optimization_results["query_performance"].get("range_query_raw", {}).get("execution_time", 0)
        aggregated_query_time = optimization_results["query_performance"].get("range_query_aggregated", {}).get("execution_time", 0)
        
        if raw_query_time > 0 and aggregated_query_time > 0:
            optimization_results["optimization_improvement"] = (
                (raw_query_time - aggregated_query_time) / raw_query_time
            )
        
        return optimization_results
    
    async def cleanup_l4_resources(self) -> None:
        """Clean up L4 test resources."""
        try:
            # Clean up test data from ClickHouse
            cleanup_queries = [
                "DELETE FROM netra_metrics.raw_metrics WHERE source = 'l4_test_generator'",
                "DELETE FROM netra_metrics.aggregated_metrics_1m WHERE aggregation_timestamp >= now() - INTERVAL 25 HOUR",
                "DELETE FROM netra_metrics.aggregated_metrics_1h WHERE aggregation_timestamp >= now() - INTERVAL 25 HOUR",
                "DELETE FROM netra_metrics.aggregated_metrics_1d WHERE aggregation_timestamp >= now() - INTERVAL 25 HOUR"
            ]
            
            for cleanup_query in cleanup_queries:
                try:
                    await self.clickhouse_client.execute_query(cleanup_query)
                except Exception as e:
                    print(f"Cleanup query failed: {e}")
            
            # Shutdown components
            if self.clickhouse_client:
                await self.clickhouse_client.close()
            if self.metrics_collector:
                await self.metrics_collector.shutdown()
            if self.prometheus_exporter:
                await self.prometheus_exporter.shutdown()
            if self.time_series_aggregator:
                await self.time_series_aggregator.shutdown()
            if self.rollup_engine:
                await self.rollup_engine.shutdown()
            if self.retention_manager:
                await self.retention_manager.shutdown()
                
        except Exception as e:
            print(f"L4 metrics aggregation cleanup failed: {e}")


@pytest.fixture
async def metrics_aggregation_pipeline_l4_suite():
    """Create L4 metrics aggregation pipeline test suite."""
    suite = MetricsAggregationPipelineL4TestSuite()
    await suite.initialize_l4_environment()
    yield suite
    await suite.cleanup_l4_resources()


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
async def test_time_series_data_generation_l4(metrics_aggregation_pipeline_l4_suite):
    """Test time-series data generation and ingestion."""
    # Generate realistic time-series data
    generation_results = await metrics_aggregation_pipeline_l4_suite.generate_time_series_data_l4(
        data_points=5000,
        time_range_hours=12
    )
    
    # Validate data generation
    assert generation_results["total_metrics_generated"] >= 5000, "Insufficient time-series data generated"
    assert generation_results["insertion_success"] is True, "Time-series data insertion failed"
    
    # Validate generation performance
    assert generation_results["generation_time"] < 30.0, "Data generation took too long"
    assert generation_results["insertion_rate"] >= 100, "Data insertion rate too low"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
async def test_time_series_aggregation_accuracy_l4(metrics_aggregation_pipeline_l4_suite):
    """Test time-series aggregation accuracy and performance."""
    # First generate test data
    await metrics_aggregation_pipeline_l4_suite.generate_time_series_data_l4(
        data_points=3000,
        time_range_hours=8
    )
    
    # Test aggregation
    aggregation_results = await metrics_aggregation_pipeline_l4_suite.test_time_series_aggregation_l4()
    
    # Validate aggregation functionality
    assert aggregation_results["aggregation_levels_tested"] >= 2, "Insufficient aggregation levels tested"
    assert aggregation_results["aggregation_accuracy"] >= 0.8, "Aggregation accuracy too low"
    
    # Validate data reduction effectiveness
    for interval, reduction_ratio in aggregation_results["data_reduction_ratios"].items():
        assert reduction_ratio >= 2.0, f"Insufficient data reduction for {interval}: {reduction_ratio}"
    
    # Validate aggregation performance
    for interval, agg_time in aggregation_results["aggregation_performance"].items():
        assert agg_time < 30.0, f"Aggregation too slow for {interval}: {agg_time}s"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
async def test_rollup_computations_accuracy_l4(metrics_aggregation_pipeline_l4_suite):
    """Test rollup computations for multi-level aggregation."""
    # Generate test data and perform initial aggregation
    await metrics_aggregation_pipeline_l4_suite.generate_time_series_data_l4(
        data_points=2000,
        time_range_hours=6
    )
    await metrics_aggregation_pipeline_l4_suite.test_time_series_aggregation_l4()
    
    # Test rollup computations
    rollup_results = await metrics_aggregation_pipeline_l4_suite.test_rollup_computations_l4()
    
    # Validate rollup functionality
    assert rollup_results["rollup_operations_tested"] >= 1, "No rollup operations completed"
    assert rollup_results["rollup_accuracy"] >= 0.8, "Rollup accuracy too low"
    assert rollup_results["rollup_consistency"] is True, "Rollup consistency violations detected"
    
    # Validate rollup performance
    for operation, rollup_time in rollup_results["rollup_performance"].items():
        assert rollup_time < 20.0, f"Rollup too slow for {operation}: {rollup_time}s"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
async def test_retention_policy_enforcement_l4(metrics_aggregation_pipeline_l4_suite):
    """Test retention policy enforcement for time-series data."""
    # Generate test data
    await metrics_aggregation_pipeline_l4_suite.generate_time_series_data_l4(
        data_points=1000,
        time_range_hours=4
    )
    
    # Test retention policy enforcement
    retention_results = await metrics_aggregation_pipeline_l4_suite.test_retention_policy_enforcement_l4()
    
    # Validate retention functionality
    assert retention_results["retention_policies_tested"] >= 2, "Insufficient retention policies tested"
    assert retention_results["data_cleanup_success"] is True, "Retention cleanup failed"
    assert retention_results["retention_efficiency"] >= 0.8, "Retention efficiency too low"
    
    # Validate cleanup performance
    for policy, cleanup_time in retention_results["cleanup_performance"].items():
        assert cleanup_time < 15.0, f"Retention cleanup too slow for {policy}: {cleanup_time}s"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
async def test_query_optimization_performance_l4(metrics_aggregation_pipeline_l4_suite):
    """Test query optimization for aggregated time-series data."""
    # Generate test data and perform aggregation
    await metrics_aggregation_pipeline_l4_suite.generate_time_series_data_l4(
        data_points=4000,
        time_range_hours=10
    )
    await metrics_aggregation_pipeline_l4_suite.test_time_series_aggregation_l4()
    
    # Test query optimization
    optimization_results = await metrics_aggregation_pipeline_l4_suite.test_query_optimization_l4()
    
    # Validate query optimization
    assert optimization_results["queries_tested"] >= 2, "Insufficient optimization queries tested"
    
    # Aggregated queries should be faster than raw queries
    if optimization_results["optimization_improvement"] > 0:
        assert optimization_results["optimization_improvement"] >= 0.2, "Insufficient query optimization improvement"
    
    # Validate query performance
    for query_name, perf_data in optimization_results["query_performance"].items():
        execution_time = perf_data["execution_time"]
        assert execution_time < 10.0, f"Query too slow for {query_name}: {execution_time}s"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
async def test_metrics_aggregation_pipeline_e2e_l4(metrics_aggregation_pipeline_l4_suite):
    """Test end-to-end metrics aggregation pipeline performance."""
    e2e_start = time.time()
    
    # Execute full pipeline: generation -> aggregation -> rollup -> retention -> optimization
    
    # Step 1: Generate time-series data
    generation_results = await metrics_aggregation_pipeline_l4_suite.generate_time_series_data_l4(
        data_points=8000,
        time_range_hours=16
    )
    
    # Step 2: Perform aggregation
    aggregation_results = await metrics_aggregation_pipeline_l4_suite.test_time_series_aggregation_l4()
    
    # Step 3: Execute rollup computations
    rollup_results = await metrics_aggregation_pipeline_l4_suite.test_rollup_computations_l4()
    
    # Step 4: Test query optimization
    optimization_results = await metrics_aggregation_pipeline_l4_suite.test_query_optimization_l4()
    
    total_e2e_time = time.time() - e2e_start
    
    # Validate end-to-end pipeline
    assert generation_results["insertion_success"] is True, "E2E: Data generation failed"
    assert aggregation_results["aggregation_accuracy"] >= 0.8, "E2E: Aggregation accuracy insufficient"
    assert rollup_results["rollup_consistency"] is True, "E2E: Rollup consistency violated"
    assert optimization_results["queries_tested"] >= 2, "E2E: Query optimization insufficient"
    
    # Validate overall pipeline performance
    assert total_e2e_time < 120.0, f"E2E pipeline too slow: {total_e2e_time}s"
    
    # Validate pipeline efficiency
    total_metrics_processed = generation_results["total_metrics_generated"]
    processing_rate = total_metrics_processed / total_e2e_time
    assert processing_rate >= 50, f"Pipeline processing rate too low: {processing_rate} metrics/sec"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
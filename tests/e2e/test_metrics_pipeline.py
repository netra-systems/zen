"""
Real-Time Metrics Aggregation Pipeline E2E Test

BVJ (Business Value Justification):
1. Segment: Enterprise ($35K+ MRR accounts depend on real-time analytics)
2. Business Goal: Prevent revenue loss from analytics system failures
3. Value Impact: Ensures customers can monitor AI optimization ROI in real-time
4. Revenue Impact: Analytics failures = customer churn = $35K+ MRR loss

CRITICAL PATH PROTECTION:
Events  ->  ClickHouse  ->  Aggregation  ->  Dashboard
- High-volume event ingestion (10K events/second)
- Real-time aggregation accuracy (<2 second latency)
- Dashboard update reliability
- Data retention policy enforcement

REQUIREMENTS:
- File: <300 lines total
- Functions: <8 lines each
- Performance: 10K events/second ingestion
- Latency: <2 seconds dashboard updates
- Accuracy: 100% aggregation correctness
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

import pytest
import pytest_asyncio

from tests.e2e.metrics_pipeline_helpers import (
    AggregationValidator,
    DashboardLatencyMeasurer,
    HighVolumeEventGenerator,
    MetricsPipelineTestHarness,
    RetentionPolicyTester,
)


@pytest_asyncio.fixture
async def metrics_harness():
    """Setup metrics pipeline test harness."""
    harness = MetricsPipelineTestHarness()
    await harness.setup_pipeline_environment()
    yield harness
    await harness.teardown_pipeline_environment()


@pytest_asyncio.fixture
async def event_generator():
    """Setup high-volume event generator."""
    generator = HighVolumeEventGenerator()
    await generator.initialize_generator()
    yield generator
    await generator.cleanup_generator()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_high_volume_event_ingestion_performance(metrics_harness, event_generator):
    """
    BVJ: Enterprise customers require 10K events/second for real-time monitoring
    Tests: Event ingestion at scale with performance validation
    """
    # Generate 10K events for performance testing
    events = await event_generator.generate_high_volume_events(count=10000)
    
    # Measure ingestion performance
    start_time = time.time()
    ingestion_results = await metrics_harness.ingest_events_batch(events)
    ingestion_duration = time.time() - start_time
    
    # Validate performance requirements
    events_per_second = len(events) / ingestion_duration
    assert events_per_second >= 10000, f"Performance failure: {events_per_second:.0f} events/sec < 10K"
    assert ingestion_results["success_count"] == len(events)
    assert ingestion_results["error_count"] == 0


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_real_time_aggregation_accuracy(metrics_harness, event_generator):
    """
    BVJ: Incorrect aggregation = wrong optimization decisions = customer churn
    Tests: Aggregation calculations with 100% accuracy requirement
    """
    # Generate test events with known values
    test_events = await event_generator.generate_known_value_events()
    
    # Ingest events and trigger aggregation
    await metrics_harness.ingest_events_batch(test_events)
    await metrics_harness.trigger_real_time_aggregation()
    
    # Validate aggregation accuracy
    validator = AggregationValidator()
    accuracy_results = await validator.validate_aggregation_accuracy(test_events)
    
    assert accuracy_results["accuracy_percentage"] == 100.0
    assert accuracy_results["calculation_errors"] == []
    assert accuracy_results["missing_aggregations"] == []


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_dashboard_update_latency(metrics_harness, event_generator):
    """
    BVJ: Dashboard delays > 2 seconds impact user experience and decision speed
    Tests: End-to-end latency from event to dashboard update
    """
    # Generate real-time events
    events = await event_generator.generate_real_time_events(count=100)
    
    # Measure end-to-end latency
    latency_measurer = DashboardLatencyMeasurer()
    
    start_time = time.time()
    await metrics_harness.ingest_events_batch(events)
    dashboard_update_time = await latency_measurer.measure_dashboard_update_latency()
    
    # Validate latency requirements
    assert dashboard_update_time < 2.0, f"Latency failure: {dashboard_update_time:.2f}s > 2s"
    
    # Verify dashboard data accuracy
    dashboard_data = await latency_measurer.get_dashboard_data()
    assert dashboard_data["event_count"] == len(events)
    assert dashboard_data["data_freshness"] < 2.0


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_historical_data_query_performance(metrics_harness, event_generator):
    """
    BVJ: Slow historical queries impact enterprise reporting capabilities
    Tests: Large dataset query performance and accuracy
    """
    # Generate historical data (30 days worth)
    historical_events = await event_generator.generate_historical_events(days=30)
    await metrics_harness.ingest_events_batch(historical_events)
    
    # Test historical query performance
    start_time = time.time()
    query_results = await metrics_harness.query_historical_metrics(days=30)
    query_duration = time.time() - start_time
    
    # Validate query performance
    assert query_duration < 5.0, f"Query too slow: {query_duration:.2f}s > 5s"
    assert query_results["total_events"] == len(historical_events)
    assert query_results["aggregation_accuracy"] > 99.9


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_data_retention_policy_enforcement(metrics_harness, event_generator):
    """
    BVJ: Proper data retention prevents storage costs and compliance issues
    Tests: Automated data cleanup and retention policy compliance
    """
    # Create test data with different ages
    retention_tester = RetentionPolicyTester()
    aged_events = await retention_tester.create_aged_test_data()
    
    await metrics_harness.ingest_events_batch(aged_events)
    
    # Execute retention policy
    retention_results = await retention_tester.execute_retention_policy()
    
    # Validate retention policy enforcement
    assert retention_results["expired_data_removed"] > 0
    assert retention_results["active_data_preserved"] > 0
    assert retention_results["policy_compliance"] == True


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_concurrent_pipeline_operations(metrics_harness, event_generator):
    """
    BVJ: Enterprise workloads require concurrent operation support
    Tests: Multiple simultaneous pipeline operations without conflicts
    """
    # Create concurrent operation tasks
    tasks = []
    
    # Task 1: High-volume ingestion
    events_batch_1 = await event_generator.generate_high_volume_events(count=5000)
    tasks.append(metrics_harness.ingest_events_batch(events_batch_1))
    
    # Task 2: Real-time queries
    tasks.append(metrics_harness.execute_real_time_queries())
    
    # Task 3: Historical aggregation
    tasks.append(metrics_harness.run_historical_aggregation())
    
    # Execute all tasks concurrently
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    execution_time = time.time() - start_time
    
    # Validate concurrent execution
    for result in results:
        assert not isinstance(result, Exception), f"Concurrent operation failed: {result}"
    
    assert execution_time < 10.0, f"Concurrent execution too slow: {execution_time:.2f}s"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_error_recovery_and_resilience(metrics_harness, event_generator):
    """
    BVJ: System failures cannot disrupt revenue-critical analytics
    Tests: Error recovery and system resilience under failure conditions
    """
    # Generate test events
    events = await event_generator.generate_standard_events(count=1000)
    
    # Simulate system failures during ingestion
    failure_results = await metrics_harness.test_failure_recovery(events)
    
    # Validate error recovery
    assert failure_results["recovery_successful"] == True
    assert failure_results["data_loss"] == 0
    assert failure_results["recovery_time"] < 30.0


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_end_to_end_pipeline_integration(metrics_harness, event_generator):
    """
    BVJ: Complete pipeline validation ensures $35K+ MRR protection
    Tests: Full pipeline from event generation to dashboard display
    """
    # Execute complete pipeline test
    pipeline_test_events = await event_generator.generate_integration_test_events()
    
    # Run end-to-end pipeline
    e2e_results = await metrics_harness.execute_full_pipeline_test(pipeline_test_events)
    
    # Validate complete pipeline
    assert e2e_results["ingestion_success"] == True
    assert e2e_results["aggregation_accuracy"] == 100.0
    assert e2e_results["dashboard_latency"] < 2.0
    assert e2e_results["data_consistency"] == True
    assert e2e_results["retention_compliance"] == True


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_pipeline_performance_benchmarking(metrics_harness, event_generator):
    """
    BVJ: Performance benchmarks ensure scalability for enterprise growth
    Tests: Comprehensive performance metrics collection
    """
    # Run performance benchmark suite
    benchmark_results = await metrics_harness.run_performance_benchmarks()
    
    # Validate performance benchmarks
    assert benchmark_results["ingestion_rate"] >= 10000  # events/second
    assert benchmark_results["query_latency"] < 2.0     # seconds
    assert benchmark_results["aggregation_speed"] >= 5000  # calculations/second
    assert benchmark_results["memory_efficiency"] < 80  # percent usage
    assert benchmark_results["cpu_efficiency"] < 70     # percent usage
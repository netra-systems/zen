"""Tests for Performance Metrics System

Comprehensive tests for:
- EnhancedExecutionTimingCollector
- TimingBreakdown calculations
- Performance analysis
- Metrics aggregation
- Resource monitoring

Business Value: Ensures reliable performance monitoring for optimization.
"""

import pytest
import time
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
# Removed non-existent AuthManager import
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.performance_metrics import (
    EnhancedExecutionTimingCollector,
    PhaseTimer,
    TimingBreakdown,
    PerformanceMetric,
    MetricType,
    PerformanceAnalyzer
)
from netra_backend.app.monitoring.metrics_aggregator import (
    MetricsAggregator,
    AggregationWindow,
    ResourceMetrics,
    AggregatedMetrics,
    get_global_aggregator
)
from netra_backend.app.agents.supervisor.comprehensive_observability import (
    SupervisorObservability
)
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus


class TestPhaseTimer:
    """Test PhaseTimer functionality."""
    
    def test_phase_timer_initialization(self):
        """Test phase timer initialization."""
        timer = PhaseTimer(phase_name="test_phase")
        
        assert timer.phase_name == "test_phase"
        assert timer.start_time is not None
        assert timer.end_time is None
        assert timer.duration_ms is None
        assert timer.is_running is True
    
    def test_phase_timer_stop(self):
        """Test stopping a phase timer."""
        timer = PhaseTimer(phase_name="test_phase")
        time.sleep(0.01)  # Small delay
        duration = timer.stop()
        
        assert timer.end_time is not None
        assert timer.duration_ms is not None
        assert timer.duration_ms > 0
        assert timer.duration_ms == duration
        assert timer.is_running is False
    
    def test_phase_timer_metadata(self):
        """Test phase timer with metadata."""
        metadata = {"operation": "test", "count": 5}
        timer = PhaseTimer(phase_name="test_phase", metadata=metadata)
        
        assert timer.metadata == metadata


class TestEnhancedExecutionTimingCollector:
    """Test EnhancedExecutionTimingCollector functionality."""
    
    def test_collector_initialization(self):
        """Test timing collector initialization."""
        execution_id = uuid4()
        collector = EnhancedExecutionTimingCollector(
            execution_id=execution_id,
            agent_name="test_agent"
        )
        
        assert collector.execution_id == execution_id
        assert collector.agent_name == "test_agent"
        assert len(collector.phases) == 0
        assert len(collector.metrics) == 0
    
    def test_start_stop_phase(self):
        """Test starting and stopping phases."""
        execution_id = uuid4()
        collector = EnhancedExecutionTimingCollector(execution_id, "test_agent")
        
        # Start phase
        timer = collector.start_phase("initialization")
        assert "initialization" in collector.phases
        assert timer.is_running
        
        time.sleep(0.01)
        
        # Stop phase
        duration = collector.stop_phase("initialization")
        assert duration is not None
        assert duration > 0
        assert not collector.phases["initialization"].is_running
    
    def test_nested_phases(self):
        """Test nested phase tracking."""
        execution_id = uuid4()
        collector = EnhancedExecutionTimingCollector(execution_id, "test_agent")
        
        # Start multiple phases
        collector.start_phase("initialization")
        time.sleep(0.01)
        collector.start_phase("tool_execution")
        time.sleep(0.01)
        collector.start_phase("llm_processing")
        time.sleep(0.01)
        
        # Stop in different order
        llm_duration = collector.stop_phase("llm_processing")
        tool_duration = collector.stop_phase("tool_execution")
        init_duration = collector.stop_phase("initialization")
        
        assert all([llm_duration, tool_duration, init_duration])
        assert init_duration > tool_duration  # Init ran longer
    
    def test_record_first_token(self):
        """Test TTFT recording."""
        execution_id = uuid4()
        collector = EnhancedExecutionTimingCollector(execution_id, "test_agent")
        
        time.sleep(0.05)  # Simulate some processing
        ttft = collector.record_first_token()
        
        assert ttft > 0
        assert collector.first_token_time is not None
        
        # Check metric was recorded
        ttft_metrics = [m for m in collector.metrics if m.metric_type == MetricType.TTFT]
        assert len(ttft_metrics) == 1
        assert ttft_metrics[0].value == ttft
    
    def test_parallel_task_tracking(self):
        """Test parallel task execution tracking."""
        execution_id = uuid4()
        collector = EnhancedExecutionTimingCollector(execution_id, "test_agent")
        
        # Start parallel tasks
        task1 = collector.start_parallel_task("api_call_1")
        task2 = collector.start_parallel_task("api_call_2")
        task3 = collector.start_parallel_task("api_call_3")
        
        time.sleep(0.01)
        
        # Stop tasks
        duration1 = collector.stop_parallel_task("api_call_1")
        duration2 = collector.stop_parallel_task("api_call_2")
        duration3 = collector.stop_parallel_task("api_call_3")
        
        assert all([duration1, duration2, duration3])
        assert len(collector.parallel_tasks) == 3
    
    def test_get_breakdown(self):
        """Test timing breakdown calculation."""
        execution_id = uuid4()
        collector = EnhancedExecutionTimingCollector(execution_id, "test_agent")
        
        # Record various phases
        collector.start_phase("initialization")
        time.sleep(0.01)
        collector.stop_phase("initialization")
        
        collector.start_phase("tool_execution")
        time.sleep(0.02)
        collector.stop_phase("tool_execution")
        
        collector.start_phase("llm_processing")
        time.sleep(0.015)
        collector.stop_phase("llm_processing")
        
        # Get breakdown
        breakdown = collector.get_breakdown()
        
        assert breakdown.initialization_ms > 0
        assert breakdown.tool_execution_ms > 0
        assert breakdown.llm_processing_ms > 0
        assert breakdown.total_ms > 0
        
        # Check efficiency calculation
        efficiency = breakdown.calculate_efficiency()
        assert 0 <= efficiency <= 100
    
    def test_add_custom_metrics(self):
        """Test adding custom performance metrics."""
        execution_id = uuid4()
        collector = EnhancedExecutionTimingCollector(execution_id, "test_agent")
        
        # Add custom metrics
        collector.add_metric(MetricType.DATABASE_QUERY, 150.5, {"query": "SELECT *"})
        collector.add_metric(MetricType.EXTERNAL_API, 2500.0, {"endpoint": "/api/v1"})
        
        assert len(collector.metrics) == 2
        
        db_metric = collector.metrics[0]
        assert db_metric.metric_type == MetricType.DATABASE_QUERY
        assert db_metric.value == 150.5
        assert db_metric.metadata["query"] == "SELECT *"
    
    def test_get_summary(self):
        """Test execution summary generation."""
        execution_id = uuid4()
        collector = EnhancedExecutionTimingCollector(execution_id, "test_agent")
        
        # Record some activity
        collector.start_phase("initialization")
        time.sleep(0.01)
        collector.stop_phase("initialization")
        collector.record_first_token()
        
        summary = collector.get_summary()
        
        assert summary["execution_id"] == str(execution_id)
        assert summary["agent_name"] == "test_agent"
        assert summary["total_duration_ms"] > 0
        assert summary["time_to_first_token_ms"] is not None
        assert "breakdown" in summary
        assert summary["phase_count"] == 1
        assert summary["metric_count"] == 2  # init phase + TTFT


class TestPerformanceAnalyzer:
    """Test PerformanceAnalyzer functionality."""
    
    def test_analyze_timing_breakdown(self):
        """Test timing breakdown analysis."""
        analyzer = PerformanceAnalyzer()
        
        # Create breakdown with bottlenecks
        breakdown = TimingBreakdown(
            initialization_ms=100,
            tool_execution_ms=200,
            llm_processing_ms=3000,  # Bottleneck
            websocket_notification_ms=50,
            database_query_ms=150,
            external_api_ms=100,
            queue_wait_ms=1500,  # High wait time
            total_ms=5100
        )
        
        analysis = analyzer.analyze_timing_breakdown(breakdown)
        
        assert len(analysis["bottlenecks"]) > 0
        assert any(b["phase"] == "llm_processing" for b in analysis["bottlenecks"])
        assert len(analysis["recommendations"]) > 0
        assert analysis["efficiency_score"] > 0
    
    def test_detect_anomalies(self):
        """Test anomaly detection in metrics."""
        analyzer = PerformanceAnalyzer()
        
        # Create metrics with an anomaly
        metrics = [
            PerformanceMetric(MetricType.DATABASE_QUERY, 100),
            PerformanceMetric(MetricType.DATABASE_QUERY, 110),
            PerformanceMetric(MetricType.DATABASE_QUERY, 95),
            PerformanceMetric(MetricType.DATABASE_QUERY, 105),
            PerformanceMetric(MetricType.DATABASE_QUERY, 500),  # Anomaly
        ]
        
        anomalies = analyzer.detect_anomalies(metrics)
        
        # Should detect the 500ms query as anomaly
        assert len(anomalies) > 0
        assert any(a["value"] == 500 for a in anomalies)
    
    def test_calculate_slo_compliance(self):
        """Test SLO compliance calculation."""
        analyzer = PerformanceAnalyzer()
        
        # Create metrics
        metrics = [
            PerformanceMetric(MetricType.TTFT, 800),
            PerformanceMetric(MetricType.TTFT, 1200),
            PerformanceMetric(MetricType.TTFT, 900),
            PerformanceMetric(MetricType.TTFT, 1500),
            PerformanceMetric(MetricType.DATABASE_QUERY, 50),
            PerformanceMetric(MetricType.DATABASE_QUERY, 150),
            PerformanceMetric(MetricType.DATABASE_QUERY, 80),
        ]
        
        # Define SLOs
        slo_thresholds = {
            "time_to_first_token": 1000,  # 1 second
            "database_query": 100  # 100ms
        }
        
        compliance = analyzer.calculate_slo_compliance(metrics, slo_thresholds)
        
        assert "time_to_first_token" in compliance
        assert "database_query" in compliance
        assert 0 <= compliance["time_to_first_token"] <= 100
        assert 0 <= compliance["database_query"] <= 100


class TestMetricsAggregator:
    """Test MetricsAggregator functionality."""
    
    def test_aggregator_initialization(self):
        """Test metrics aggregator initialization."""
        aggregator = MetricsAggregator(retention_hours=24)
        
        assert aggregator.retention_hours == 24
        assert len(aggregator.metric_windows) > 0
        assert len(aggregator.resource_history) == 0
    
    def test_add_and_aggregate_metrics(self):
        """Test adding metrics and aggregation."""
        aggregator = MetricsAggregator()
        
        # Add multiple metrics
        for i in range(10):
            metric = PerformanceMetric(
                metric_type=MetricType.DATABASE_QUERY,
                value=100 + i * 10
            )
            aggregator.add_metric(metric)
        
        # Get aggregated metrics
        agg = aggregator.get_aggregated_metrics(
            MetricType.DATABASE_QUERY,
            AggregationWindow.MINUTE
        )
        
        assert agg is not None
        assert agg.count == 10
        assert agg.mean == 145.0
        assert agg.min_value == 100
        assert agg.max_value == 190
    
    def test_percentile_calculation(self):
        """Test percentile calculations."""
        aggregator = MetricsAggregator()
        
        # Add metrics with known distribution
        values = list(range(1, 101))  # 1 to 100
        for v in values:
            metric = PerformanceMetric(MetricType.LLM_PROCESSING, v)
            aggregator.add_metric(metric)
        
        agg = aggregator.get_aggregated_metrics(
            MetricType.LLM_PROCESSING,
            AggregationWindow.MINUTE
        )
        
        assert agg.p50 == pytest.approx(50, abs=1)
        assert agg.p95 == pytest.approx(95, abs=1)
        assert agg.p99 == pytest.approx(99, abs=1)
    
    def test_timing_breakdown_aggregation(self):
        """Test aggregating timing breakdowns."""
        aggregator = MetricsAggregator()
        
        # Add multiple timing breakdowns
        for i in range(5):
            breakdown = TimingBreakdown(
                initialization_ms=100 + i * 10,
                tool_execution_ms=200 + i * 20,
                llm_processing_ms=1000 + i * 50,
                total_ms=1300 + i * 80
            )
            aggregator.add_timing_breakdown(breakdown)
        
        # Check that metrics were created
        init_agg = aggregator.get_aggregated_metrics(
            MetricType.INITIALIZATION,
            AggregationWindow.MINUTE
        )
        assert init_agg is not None
        assert init_agg.count == 5
    
    def test_resource_metrics(self):
        """Test resource metrics tracking."""
        aggregator = MetricsAggregator()
        
        # Add resource metrics
        for i in range(10):
            metrics = ResourceMetrics(
                cpu_percent=50 + i,
                memory_mb=1000 + i * 100,
                thread_count=10 + i
            )
            aggregator.add_resource_metrics(metrics)
        
        summary = aggregator.get_performance_summary()
        resource_summary = summary["resource_utilization"]
        
        assert "cpu" in resource_summary
        assert "memory" in resource_summary
        assert "threads" in resource_summary
    
    def test_bottleneck_detection(self):
        """Test bottleneck detection."""
        aggregator = MetricsAggregator()
        
        # Add metrics with some outliers
        for i in range(20):
            value = 100 if i < 18 else 5000  # Last 2 are bottlenecks
            metric = PerformanceMetric(MetricType.DATABASE_QUERY, value)
            aggregator.add_metric(metric)
        
        bottlenecks = aggregator.get_bottlenecks(threshold_percentile=95)
        
        # Should detect database queries as bottleneck
        assert len(bottlenecks) > 0
    
    def test_trend_detection(self):
        """Test performance trend detection."""
        aggregator = MetricsAggregator()
        
        # Add improving trend
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)
        for i in range(20):
            metric = PerformanceMetric(
                metric_type=MetricType.TTFT,
                value=1000 - i * 20,  # Decreasing (improving)
                timestamp=base_time + timedelta(minutes=i*5)
            )
            aggregator.add_metric(metric)
        
        summary = aggregator.get_performance_summary()
        trends = summary["trends"]
        
        assert MetricType.TTFT.value in trends
        # Trend detection depends on time windows, so just check it exists
    
    def test_export_metrics(self):
        """Test metrics export."""
        aggregator = MetricsAggregator()
        
        # Add metrics
        for i in range(5):
            metric = PerformanceMetric(
                metric_type=MetricType.TOOL_EXECUTION,
                value=100 + i,
                agent_name="test_agent",
                correlation_id=f"exec_{i}"
            )
            aggregator.add_metric(metric)
        
        exported = aggregator.export_metrics(AggregationWindow.MINUTE)
        
        assert len(exported) >= 5
        assert all("type" in m for m in exported)
        assert all("value" in m for m in exported)
        assert all("timestamp" in m for m in exported)


class TestSupervisorObservabilityIntegration:
    """Test SupervisorObservability with performance metrics."""
    
    def test_workflow_trace_with_timing(self):
        """Test workflow trace with timing collection."""
        from netra_backend.app.agents.state import DeepAgentState
        
        observability = SupervisorObservability()
        
        # Create execution context with required state
        state = DeepAgentState()
        context = ExecutionContext(
            run_id=str(uuid4()),
            agent_name="test_agent",
            state=state,
            user_id="user123"
        )
        
        # Start workflow
        observability.start_workflow_trace(context)
        
        # Simulate phases
        observability.start_phase(context.run_id, "tool_execution")
        time.sleep(0.01)
        observability.stop_phase(context.run_id, "tool_execution")
        
        observability.start_phase(context.run_id, "llm_processing")
        time.sleep(0.02)
        observability.record_first_token(context.run_id)
        observability.stop_phase(context.run_id, "llm_processing")
        
        # Complete workflow
        result = ExecutionResult(status=ExecutionStatus.COMPLETED, request_id=context.request_id, data={"test": "data"})
        observability.complete_workflow_trace(context, result)
        
        # Check metrics
        metrics = observability.get_metrics_snapshot()
        assert metrics["metrics"]["total_workflows"] == 1
        assert metrics["metrics"]["successful_workflows"] == 1
    
    def test_performance_summary(self):
        """Test comprehensive performance summary."""
        observability = SupervisorObservability()
        
        # Add some metrics
        trace_id = str(uuid4())
        observability.add_performance_metric(
            trace_id,
            MetricType.DATABASE_QUERY,
            150.5,
            {"query": "test"}
        )
        
        # Record resource metrics
        observability.record_resource_metrics(
            cpu_percent=45.5,
            memory_mb=2048,
            thread_count=25
        )
        
        # Get summary
        summary = observability.get_performance_summary()
        
        assert "metrics" in summary
        assert "performance" in summary
        assert "bottlenecks" in summary
    
    def test_get_timing_breakdown(self):
        """Test getting timing breakdown for specific execution."""
        from netra_backend.app.agents.state import DeepAgentState
        
        observability = SupervisorObservability()
        
        state = DeepAgentState()
        context = ExecutionContext(
            run_id=str(uuid4()),
            agent_name="test_agent",
            state=state,
            user_id="user123"
        )
        
        observability.start_workflow_trace(context)
        
        # Add some phases
        observability.start_phase(context.run_id, "initialization")
        time.sleep(0.01)
        observability.stop_phase(context.run_id, "initialization")
        
        # Get breakdown
        breakdown = observability.get_timing_breakdown(context.run_id)
        
        assert breakdown is not None
        assert breakdown.initialization_ms > 0


class TestGlobalAggregator:
    """Test global aggregator singleton."""
    
    def test_global_aggregator_singleton(self):
        """Test that global aggregator is a singleton."""
        agg1 = get_global_aggregator()
        agg2 = get_global_aggregator()
        
        assert agg1 is agg2
    
    def test_global_aggregator_functionality(self):
        """Test global aggregator works correctly."""
        aggregator = get_global_aggregator()
        
        # Add a metric
        metric = PerformanceMetric(
            metric_type=MetricType.WEBSOCKET_LATENCY,
            value=25.5
        )
        aggregator.add_metric(metric)
        
        # Verify it was added
        agg = aggregator.get_aggregated_metrics(
            MetricType.WEBSOCKET_LATENCY,
            AggregationWindow.MINUTE
        )
        
        assert agg is not None
        assert agg.count >= 1  # May have other tests' data


@pytest.mark.asyncio
class TestAsyncPerformanceTracking:
    """Test performance tracking in async contexts."""
    
    async def test_async_phase_tracking(self):
        """Test phase tracking in async code."""
        execution_id = uuid4()
        collector = EnhancedExecutionTimingCollector(execution_id, "async_agent")
        
        # Start phase
        collector.start_phase("async_operation")
        
        # Simulate async work
        await asyncio.sleep(0.01)
        
        # Stop phase
        duration = collector.stop_phase("async_operation")
        
        assert duration > 10  # At least 10ms
    
    async def test_concurrent_phase_tracking(self):
        """Test tracking concurrent async operations."""
        execution_id = uuid4()
        collector = EnhancedExecutionTimingCollector(execution_id, "async_agent")
        
        async def async_task(task_name: str, delay: float):
            timer = collector.start_parallel_task(task_name)
            await asyncio.sleep(delay)
            return collector.stop_parallel_task(task_name)
        
        # Run tasks concurrently
        results = await asyncio.gather(
            async_task("task1", 0.01),
            async_task("task2", 0.02),
            async_task("task3", 0.015)
        )
        
        assert all(r > 0 for r in results)
        assert results[1] > results[0]  # task2 took longer
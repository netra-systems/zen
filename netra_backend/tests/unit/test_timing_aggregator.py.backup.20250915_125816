"""
Unit Tests for Timing Aggregator

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable performance optimization and SLA monitoring
- Value Impact: Timing data enables 20-30% performance improvements and optimization decisions  
- Strategic Impact: Platform performance directly impacts user satisfaction and operational costs

These tests validate the business logic of timing aggregation without external dependencies.
Testing bottleneck identification, optimization recommendations, and report generation ensures
effective performance analysis capabilities.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.base.timing_aggregator import (
    TimingAggregator,
    OptimizationPriority,
    Bottleneck,
    OptimizationReport,
    TrendData
)
from netra_backend.app.agents.base.timing_collector import (
    ExecutionTimingTree,
    TimingEntry,
    TimingCategory,
    AggregateStats
)


class TestTimingAggregator(SSotBaseTestCase):
    """Test timing aggregation and optimization analysis."""

    def setup_method(self, method=None):
        """Setup test method with timing aggregator and test data."""
        super().setup_method(method)
        self.aggregator = TimingAggregator()
        
        # Create sample timing data for tests
        self.sample_tree = self._create_sample_timing_tree()

    def _create_sample_timing_tree(self) -> ExecutionTimingTree:
        """Create a sample timing tree for testing."""
        tree = ExecutionTimingTree(
            agent_name="test_optimization_agent",
            correlation_id="test-123",
            root_id="root-1"
        )
        
        # Add root entry
        root_entry = TimingEntry(
            entry_id="root-1",
            operation="agent_execution",
            category=TimingCategory.ORCHESTRATION,
            duration_ms=1000.0
        )
        root_entry.end_time = root_entry.start_time + 1.0
        tree.entries["root-1"] = root_entry
        
        # Add LLM entry (slow operation)
        llm_entry = TimingEntry(
            entry_id="llm-1",
            operation="llm_query",
            category=TimingCategory.LLM,
            duration_ms=800.0,
            parent_id="root-1"
        )
        llm_entry.end_time = llm_entry.start_time + 0.8
        tree.entries["llm-1"] = llm_entry
        
        # Add database entry (fast operation)
        db_entry = TimingEntry(
            entry_id="db-1", 
            operation="user_lookup",
            category=TimingCategory.DATABASE,
            duration_ms=50.0,
            parent_id="root-1"
        )
        db_entry.end_time = db_entry.start_time + 0.05
        tree.entries["db-1"] = db_entry
        
        return tree

    def _create_slow_timing_tree(self) -> ExecutionTimingTree:
        """Create a timing tree with slow operations for bottleneck testing."""
        tree = ExecutionTimingTree(
            agent_name="slow_agent",
            correlation_id="slow-456",
            root_id="slow-root"
        )
        
        # Very slow LLM operation
        slow_entry = TimingEntry(
            entry_id="slow-llm",
            operation="complex_llm_analysis",
            category=TimingCategory.LLM,
            duration_ms=6000.0  # 6 seconds - critical bottleneck
        )
        slow_entry.end_time = slow_entry.start_time + 6.0
        tree.entries["slow-llm"] = slow_entry
        
        return tree

    @pytest.mark.unit
    def test_add_timing_tree(self):
        """Test adding timing trees to aggregator.
        
        BVJ: Tree collection enables comprehensive performance analysis.
        """
        initial_count = len(self.aggregator.timing_trees)
        
        self.aggregator.add_timing_tree(self.sample_tree)
        
        assert len(self.aggregator.timing_trees) == initial_count + 1
        assert self.sample_tree in self.aggregator.timing_trees
        
        self.record_metric("timing_tree_added", True)

    @pytest.mark.unit
    def test_aggregate_by_category(self):
        """Test aggregation of timing data by category.
        
        BVJ: Category aggregation enables targeted optimization efforts.
        """
        self.aggregator.add_timing_tree(self.sample_tree)
        
        category_stats = self.aggregator.aggregate_by_category()
        
        # Verify expected categories are present
        assert TimingCategory.LLM.value in category_stats
        assert TimingCategory.DATABASE.value in category_stats
        assert TimingCategory.ORCHESTRATION.value in category_stats
        
        # Verify LLM stats (should have the 800ms operation)
        llm_stats = category_stats[TimingCategory.LLM.value]
        assert isinstance(llm_stats, AggregateStats)
        assert llm_stats.count > 0
        assert llm_stats.total_time_ms >= 800.0
        
        self.record_metric("category_aggregation_correct", True)

    @pytest.mark.unit
    def test_aggregate_by_agent(self):
        """Test aggregation of timing data by agent.
        
        BVJ: Agent-specific aggregation enables agent performance comparison.
        """
        self.aggregator.add_timing_tree(self.sample_tree)
        
        agent_stats = self.aggregator.aggregate_by_agent()
        
        # Verify agent is present in stats
        agent_name = self.sample_tree.agent_name
        assert agent_name in agent_stats
        
        # Verify agent stats
        agent_stat = agent_stats[agent_name]
        assert isinstance(agent_stat, AggregateStats)
        assert agent_stat.count > 0
        assert agent_stat.total_time_ms >= 1000.0  # Root entry duration
        
        self.record_metric("agent_aggregation_correct", True)

    @pytest.mark.unit
    def test_identify_bottlenecks_default_threshold(self):
        """Test bottleneck identification with default threshold.
        
        BVJ: Bottleneck identification enables focused optimization efforts.
        """
        # Add tree with operations above default threshold (500ms)
        self.aggregator.add_timing_tree(self.sample_tree)
        
        bottlenecks = self.aggregator.identify_bottlenecks()
        
        # Should identify the LLM operation (800ms) as a bottleneck
        assert len(bottlenecks) > 0
        
        # Find the LLM bottleneck
        llm_bottleneck = next(
            (b for b in bottlenecks if b.category == TimingCategory.LLM),
            None
        )
        assert llm_bottleneck is not None
        assert llm_bottleneck.avg_duration_ms >= 800.0
        assert llm_bottleneck.operation == "llm_query"
        
        self.record_metric("bottlenecks_identified", True)

    @pytest.mark.unit
    def test_identify_bottlenecks_custom_threshold(self):
        """Test bottleneck identification with custom threshold.
        
        BVJ: Configurable thresholds enable environment-specific optimization.
        """
        self.aggregator.add_timing_tree(self.sample_tree)
        
        # Use higher threshold - should filter out smaller operations
        bottlenecks = self.aggregator.identify_bottlenecks(threshold_ms=900.0)
        
        # Should not identify the 800ms LLM operation
        llm_bottlenecks = [b for b in bottlenecks if b.category == TimingCategory.LLM]
        assert len(llm_bottlenecks) == 0
        
        self.record_metric("custom_threshold_applied", True)

    @pytest.mark.unit
    def test_identify_bottlenecks_priority_assignment(self):
        """Test that bottlenecks are assigned correct priority levels.
        
        BVJ: Priority assignment enables proper resource allocation for optimization.
        """
        # Add tree with very slow operation
        slow_tree = self._create_slow_timing_tree()
        self.aggregator.add_timing_tree(slow_tree)
        
        bottlenecks = self.aggregator.identify_bottlenecks()
        
        # Find the critical bottleneck (6000ms)
        critical_bottleneck = next(
            (b for b in bottlenecks if b.avg_duration_ms >= 6000),
            None
        )
        
        assert critical_bottleneck is not None
        assert critical_bottleneck.priority == OptimizationPriority.CRITICAL
        assert critical_bottleneck.total_impact_ms >= 6000.0
        
        self.record_metric("priority_assignment_correct", True)

    @pytest.mark.unit
    def test_bottleneck_sorting_by_impact(self):
        """Test that bottlenecks are sorted by total impact.
        
        BVJ: Impact-based sorting prioritizes highest-value optimizations.
        """
        # Add multiple trees to create different impact levels
        self.aggregator.add_timing_tree(self.sample_tree)
        slow_tree = self._create_slow_timing_tree() 
        self.aggregator.add_timing_tree(slow_tree)
        
        bottlenecks = self.aggregator.identify_bottlenecks()
        
        # Verify sorting by total impact (descending)
        if len(bottlenecks) > 1:
            for i in range(len(bottlenecks) - 1):
                assert bottlenecks[i].total_impact_ms >= bottlenecks[i + 1].total_impact_ms
        
        self.record_metric("bottlenecks_sorted_by_impact", True)

    @pytest.mark.unit
    def test_generate_optimization_report(self):
        """Test generation of comprehensive optimization report.
        
        BVJ: Optimization reports enable data-driven performance improvements.
        """
        self.aggregator.add_timing_tree(self.sample_tree)
        
        report = self.aggregator.generate_optimization_report()
        
        # Verify report structure
        assert isinstance(report, OptimizationReport)
        assert report.total_executions == 1
        assert report.total_duration_ms > 0
        assert report.avg_duration_ms > 0
        assert len(report.bottlenecks) >= 0
        assert len(report.category_breakdown) > 0
        assert len(report.agent_breakdown) > 0
        assert report.optimization_potential_ms >= 0
        assert len(report.recommendations) >= 0
        assert isinstance(report.generated_at, datetime)
        
        self.record_metric("optimization_report_generated", True)

    @pytest.mark.unit
    def test_calculate_optimization_potential(self):
        """Test calculation of optimization potential from bottlenecks.
        
        BVJ: Optimization potential estimates business value of performance work.
        """
        slow_tree = self._create_slow_timing_tree()
        self.aggregator.add_timing_tree(slow_tree)
        
        bottlenecks = self.aggregator.identify_bottlenecks()
        potential = self.aggregator._calculate_optimization_potential(bottlenecks)
        
        # Should have positive optimization potential
        assert potential > 0
        
        # For critical bottlenecks, should estimate 50% improvement
        critical_bottlenecks = [b for b in bottlenecks if b.priority == OptimizationPriority.CRITICAL]
        if critical_bottlenecks:
            expected_min = critical_bottlenecks[0].total_impact_ms * 0.4  # At least 40%
            assert potential >= expected_min
        
        self.record_metric("optimization_potential_calculated", True)

    @pytest.mark.unit
    def test_generate_recommendations(self):
        """Test generation of optimization recommendations.
        
        BVJ: Actionable recommendations enable targeted performance improvements.
        """
        slow_tree = self._create_slow_timing_tree()
        self.aggregator.add_timing_tree(slow_tree)
        
        bottlenecks = self.aggregator.identify_bottlenecks()
        category_breakdown = self.aggregator.aggregate_by_category()
        
        recommendations = self.aggregator._generate_recommendations(bottlenecks, category_breakdown)
        
        # Should generate actionable recommendations
        assert len(recommendations) > 0
        
        # Recommendations should be strings with actionable content
        for rec in recommendations:
            assert isinstance(rec, str)
            assert len(rec) > 10  # Should be substantial recommendations
        
        self.record_metric("recommendations_generated", True)

    @pytest.mark.unit
    def test_get_critical_paths(self):
        """Test getting critical paths from timing trees.
        
        BVJ: Critical path analysis identifies execution bottlenecks.
        """
        # Mock the get_critical_path method on the tree
        self.sample_tree.get_critical_path = Mock(return_value=[
            self.sample_tree.entries["root-1"],
            self.sample_tree.entries["llm-1"]
        ])
        
        self.aggregator.add_timing_tree(self.sample_tree)
        
        critical_paths = self.aggregator.get_critical_paths()
        
        assert len(critical_paths) > 0
        assert isinstance(critical_paths[0], list)
        
        self.record_metric("critical_paths_retrieved", True)

    @pytest.mark.unit
    def test_export_report_json(self):
        """Test exporting optimization report as JSON.
        
        BVJ: JSON export enables integration with monitoring and alerting systems.
        """
        self.aggregator.add_timing_tree(self.sample_tree)
        report = self.aggregator.generate_optimization_report()
        
        json_str = self.aggregator.export_report_json(report)
        
        # Verify valid JSON
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)  # Should not raise exception
        
        # Verify key sections are present
        assert "generated_at" in parsed
        assert "summary" in parsed
        assert "bottlenecks" in parsed
        assert "category_breakdown" in parsed
        assert "agent_breakdown" in parsed
        assert "recommendations" in parsed
        
        # Verify summary section
        summary = parsed["summary"]
        assert "total_executions" in summary
        assert "total_duration_ms" in summary
        assert "avg_duration_ms" in summary
        assert "optimization_potential_ms" in summary
        
        self.record_metric("json_export_successful", True)

    @pytest.mark.unit
    def test_determine_priority_thresholds(self):
        """Test priority determination based on duration thresholds.
        
        BVJ: Accurate priority assignment ensures proper resource allocation.
        """
        aggregator = TimingAggregator()
        
        # Test different priority levels
        assert aggregator._determine_priority(6000.0) == OptimizationPriority.CRITICAL
        assert aggregator._determine_priority(3000.0) == OptimizationPriority.HIGH
        assert aggregator._determine_priority(1500.0) == OptimizationPriority.MEDIUM
        assert aggregator._determine_priority(750.0) == OptimizationPriority.LOW
        assert aggregator._determine_priority(300.0) == OptimizationPriority.LOW
        
        self.record_metric("priority_thresholds_correct", True)

    @pytest.mark.unit
    def test_get_recommendation_by_category_and_duration(self):
        """Test getting category-specific recommendations based on duration.
        
        BVJ: Targeted recommendations improve optimization effectiveness.
        """
        aggregator = TimingAggregator()
        
        # Test LLM recommendations
        llm_rec_cache = aggregator._get_recommendation(TimingCategory.LLM, 6000.0)
        assert "cache" in llm_rec_cache.lower() or "caching" in llm_rec_cache.lower()
        
        llm_rec_batch = aggregator._get_recommendation(TimingCategory.LLM, 3000.0)
        assert "batch" in llm_rec_batch.lower()
        
        # Test Database recommendations
        db_rec = aggregator._get_recommendation(TimingCategory.DATABASE, 4000.0)
        assert isinstance(db_rec, str)
        assert len(db_rec) > 10
        
        self.record_metric("category_recommendations_targeted", True)

    @pytest.mark.unit
    def test_bottleneck_impact_percentage_calculation(self):
        """Test calculation of bottleneck impact percentage.
        
        BVJ: Impact percentage enables prioritization of optimization efforts.
        """
        # Create multiple trees to test percentage calculation
        self.aggregator.add_timing_tree(self.sample_tree)
        slow_tree = self._create_slow_timing_tree()
        self.aggregator.add_timing_tree(slow_tree)
        
        bottlenecks = self.aggregator.identify_bottlenecks()
        
        # Verify impact percentages are calculated
        for bottleneck in bottlenecks:
            assert hasattr(bottleneck, '_impact_percentage')
            assert bottleneck.impact_percentage >= 0
            assert bottleneck.impact_percentage <= 100
        
        self.record_metric("impact_percentage_calculated", True)

    @pytest.mark.unit
    def test_empty_aggregator_handling(self):
        """Test handling of empty aggregator (no timing trees).
        
        BVJ: Graceful handling of edge cases prevents system failures.
        """
        empty_aggregator = TimingAggregator()
        
        # Should handle empty state gracefully
        category_stats = empty_aggregator.aggregate_by_category()
        assert isinstance(category_stats, dict)
        assert len(category_stats) == 0
        
        agent_stats = empty_aggregator.aggregate_by_agent()
        assert isinstance(agent_stats, dict)
        assert len(agent_stats) == 0
        
        bottlenecks = empty_aggregator.identify_bottlenecks()
        assert isinstance(bottlenecks, list)
        assert len(bottlenecks) == 0
        
        report = empty_aggregator.generate_optimization_report()
        assert report.total_executions == 0
        assert report.total_duration_ms == 0
        assert report.avg_duration_ms == 0
        
        self.record_metric("empty_state_handled_gracefully", True)

    def test_execution_timing_under_threshold(self):
        """Verify test execution performance meets requirements.
        
        BVJ: Fast unit tests enable rapid development cycles.
        """
        # Unit tests must execute under 100ms
        self.assert_execution_time_under(0.1)
        
        # Verify business metrics were recorded
        self.assert_metrics_recorded(
            "timing_tree_added",
            "category_aggregation_correct",
            "agent_aggregation_correct", 
            "bottlenecks_identified",
            "custom_threshold_applied",
            "priority_assignment_correct",
            "bottlenecks_sorted_by_impact",
            "optimization_report_generated",
            "optimization_potential_calculated",
            "recommendations_generated",
            "critical_paths_retrieved",
            "json_export_successful",
            "priority_thresholds_correct",
            "category_recommendations_targeted",
            "impact_percentage_calculated",
            "empty_state_handled_gracefully"
        )
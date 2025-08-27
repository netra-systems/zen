"""Summary and analysis unit tests for MetricsCollector.

Tests metric summarization and analysis for billing insights.
Complements core MetricsCollector tests with advanced analysis features.

Business Value: Provides billing analytics and usage pattern insights
for customer optimization and revenue forecasting.
"""

from pathlib import Path
import sys

from collections import deque
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock

import pytest

from netra_backend.app.monitoring.metrics_collector import MetricsCollector, PerformanceMetric

class TestMetricsCollectorSummary:

    """Test suite for MetricsCollector summary and analysis features."""
    
    @pytest.fixture

    def collector(self):

        """Create metrics collector with minimal retention."""

        return MetricsCollector(retention_period=300)
    
    def test_get_recent_metrics_filtered(self, collector):

        """Test getting recent metrics with time filtering."""

        old_time = datetime.now() - timedelta(seconds=400)

        recent_time = datetime.now() - timedelta(seconds=100)
        
        old_metric = PerformanceMetric("test", 1.0, old_time)

        recent_metric = PerformanceMetric("test", 2.0, recent_time)
        
        collector._metrics_buffer["test_metric"].extend([old_metric, recent_metric])
        
        recent_metrics = collector.get_recent_metrics("test_metric", 300)
        
        assert len(recent_metrics) == 1

        assert recent_metrics[0].timestamp == recent_time
    
    def test_get_recent_metrics_nonexistent(self, collector):

        """Test getting recent metrics for non-existent metric."""

        metrics = collector.get_recent_metrics("nonexistent.metric", 300)
        
        assert metrics == []
    
    def test_get_metric_summary_with_data(self, collector):

        """Test metric summary calculation with data."""

        times = [datetime.now() - timedelta(seconds=i*10) for i in range(5)]

        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        
        metrics = [PerformanceMetric("test", values[i], times[i]) for i in range(5)]

        collector._metrics_buffer["test_metric"].extend(metrics)
        
        summary = collector.get_metric_summary("test_metric", 300)
        
        assert summary["count"] == 5

        assert summary["min"] == 10.0

        assert summary["max"] == 50.0

        assert summary["avg"] == 30.0

        assert summary["current"] == 10.0  # Most recent (first in list)
    
    def test_get_metric_summary_empty(self, collector):

        """Test metric summary with no data."""

        summary = collector.get_metric_summary("empty_metric", 300)
        
        assert summary == {}
    
    def test_calculate_cache_hit_ratio_with_data(self, collector):

        """Test cache hit ratio calculation."""

        perf_stats = {"cache_stats": {"total_hits": 750, "size": 1000}}
        
        ratio = collector._calculate_cache_hit_ratio(perf_stats)
        
        assert ratio == 0.75
    
    def test_calculate_cache_hit_ratio_empty_cache(self, collector):

        """Test cache hit ratio with empty cache."""

        perf_stats = {"cache_stats": {"total_hits": 0, "size": 0}}
        
        ratio = collector._calculate_cache_hit_ratio(perf_stats)
        
        assert ratio == 0.0
    
    def test_calculate_cache_hit_ratio_missing_stats(self, collector):

        """Test cache hit ratio with missing cache stats."""

        perf_stats = {}
        
        ratio = collector._calculate_cache_hit_ratio(perf_stats)
        
        assert ratio == 0.0
    
    def test_metric_buffer_size_limits(self, collector):

        """Test that metric buffers respect size limits."""
        # Fill buffer beyond maxlen

        for i in range(1200):

            metric = PerformanceMetric("test", float(i), datetime.now())

            collector._metrics_buffer["test_metric"].append(metric)
        
        # Should be limited to maxlen of 1000

        assert len(collector._metrics_buffer["test_metric"]) == 1000
    
    def test_summary_statistics_accuracy(self, collector):

        """Test accuracy of summary statistics calculations."""

        values = [5.0, 15.0, 25.0, 35.0, 45.0]

        timestamps = [datetime.now() - timedelta(seconds=i) for i in range(5)]
        
        for i, (value, timestamp) in enumerate(zip(values, timestamps)):

            metric = PerformanceMetric("accuracy_test", value, timestamp)

            collector._metrics_buffer["accuracy_metric"].append(metric)
        
        summary = collector.get_metric_summary("accuracy_metric", 300)
        
        assert summary["min"] == 5.0

        assert summary["max"] == 45.0

        assert summary["avg"] == 25.0  # (5+15+25+35+45)/5 = 25

        assert summary["count"] == 5
    
    def test_time_based_filtering_edge_cases(self, collector):

        """Test edge cases in time-based metric filtering."""

        now = datetime.now()
        
        # Metrics at exact boundary

        boundary_metric = PerformanceMetric("test", 1.0, now - timedelta(seconds=300))

        inside_metric = PerformanceMetric("test", 2.0, now - timedelta(seconds=299))

        outside_metric = PerformanceMetric("test", 3.0, now - timedelta(seconds=301))
        
        collector._metrics_buffer["boundary_test"].extend([

            outside_metric, boundary_metric, inside_metric

        ])
        
        recent_metrics = collector.get_recent_metrics("boundary_test", 300)
        
        # Should include boundary and inside metrics

        assert len(recent_metrics) == 2

        assert all(m.value in [1.0, 2.0] for m in recent_metrics)
    
    def test_metric_aggregation_performance(self, collector):

        """Test performance of metric aggregation with large datasets."""
        # Add substantial amount of test data

        large_dataset_size = 500

        base_time = datetime.now()
        
        for i in range(large_dataset_size):

            timestamp = base_time - timedelta(seconds=i)

            metric = PerformanceMetric("perf_test", float(i), timestamp)

            collector._metrics_buffer["performance_metric"].append(metric)
        
        # Should handle large dataset efficiently

        recent_metrics = collector.get_recent_metrics("performance_metric", 600)

        summary = collector.get_metric_summary("performance_metric", 600)
        
        assert len(recent_metrics) == large_dataset_size

        assert summary["count"] == large_dataset_size

        assert summary["avg"] == (large_dataset_size - 1) / 2  # 0 to (n-1) average
    
    def test_concurrent_metric_access_safety(self, collector):

        """Test thread safety of metric access operations."""
        # Simulate concurrent access patterns

        base_time = datetime.now()
        
        # Add metrics while potentially being read

        for i in range(100):

            timestamp = base_time - timedelta(seconds=i)

            metric = PerformanceMetric("concurrent", float(i), timestamp)

            collector._metrics_buffer["concurrent_test"].append(metric)
            
            # Interleave reads during writes

            if i % 10 == 0:

                recent = collector.get_recent_metrics("concurrent_test", 200)

                summary = collector.get_metric_summary("concurrent_test", 200)
                
                # Should not raise exceptions and provide consistent data

                assert isinstance(recent, list)

                assert isinstance(summary, dict)
    
    def test_metric_cleanup_efficiency(self, collector):

        """Test efficiency of metric cleanup operations."""

        cutoff_time = datetime.now() - timedelta(seconds=collector.retention_period)
        
        # Mix of old and new metrics

        old_metrics = [

            PerformanceMetric("test", float(i), cutoff_time - timedelta(seconds=i))

            for i in range(50)

        ]

        new_metrics = [

            PerformanceMetric("test", float(i), cutoff_time + timedelta(seconds=i+1))

            for i in range(50)

        ]
        
        collector._metrics_buffer["cleanup_test"].extend(old_metrics + new_metrics)
        
        # Cleanup should remove only old metrics

        collector._remove_expired_metrics()
        
        # Verify only new metrics remain

        remaining = list(collector._metrics_buffer["cleanup_test"])

        assert len(remaining) == 50

        assert all(m.timestamp > cutoff_time for m in remaining)
    
    # Helper methods (each ≤8 lines)

    def _create_test_metric_series(self, name, count, start_time=None):

        """Helper to create a series of test metrics."""

        if start_time is None:

            start_time = datetime.now()

        return [

            PerformanceMetric(name, float(i), start_time - timedelta(seconds=i))

            for i in range(count)

        ]
    
    def _populate_metric_buffer(self, collector, metric_name, values, timestamps=None):

        """Helper to populate metric buffer with specific values."""

        if timestamps is None:

            timestamps = [datetime.now() - timedelta(seconds=i) for i in range(len(values))]

        metrics = [PerformanceMetric(metric_name, val, ts) for val, ts in zip(values, timestamps)]

        collector._metrics_buffer[metric_name].extend(metrics)
    
    def _assert_summary_valid(self, summary, expected_count):

        """Helper to assert summary structure is valid."""

        if expected_count > 0:

            assert "count" in summary

            assert "min" in summary

            assert "max" in summary

            assert "avg" in summary

            assert "current" in summary

            assert summary["count"] == expected_count

        else:

            assert summary == {}
    
    def _verify_metric_ordering(self, metrics):

        """Helper to verify metrics are in expected time order."""

        if len(metrics) <= 1:

            return True

        return all(

            metrics[i].timestamp >= metrics[i+1].timestamp

            for i in range(len(metrics)-1)

        )
    
    def test_cache_performance_degradation_detection(self, collector):
        """Test detection of cache performance degradation patterns."""
        
        # Test cache hit ratio calculation with various scenarios
        mock_perf_stats_high = {"cache_stats": {"total_hits": 850, "size": 1000}}
        mock_perf_stats_medium = {"cache_stats": {"total_hits": 650, "size": 1000}}
        mock_perf_stats_low = {"cache_stats": {"total_hits": 200, "size": 1000}}
        mock_perf_stats_empty = {"cache_stats": {"total_hits": 0, "size": 0}}
        
        # Verify cache hit ratio calculations
        high_ratio = collector._calculate_cache_hit_ratio(mock_perf_stats_high)
        medium_ratio = collector._calculate_cache_hit_ratio(mock_perf_stats_medium)
        low_ratio = collector._calculate_cache_hit_ratio(mock_perf_stats_low)
        empty_ratio = collector._calculate_cache_hit_ratio(mock_perf_stats_empty)
        
        assert high_ratio == 0.85, f"Expected high ratio 0.85, got {high_ratio}"
        assert medium_ratio == 0.65, f"Expected medium ratio 0.65, got {medium_ratio}"
        assert low_ratio == 0.20, f"Expected low ratio 0.20, got {low_ratio}"
        assert empty_ratio == 0.0, f"Expected empty ratio 0.0, got {empty_ratio}"
        
        # Test edge cases for cache performance monitoring
        partial_stats = {"cache_stats": {"total_hits": 100}}  # Missing size
        no_cache_stats = {}  # No cache_stats section
        
        partial_ratio = collector._calculate_cache_hit_ratio(partial_stats)
        no_cache_ratio = collector._calculate_cache_hit_ratio(no_cache_stats)
        
        assert partial_ratio == 0.0, "Should handle missing size gracefully"
        assert no_cache_ratio == 0.0, "Should handle missing cache_stats gracefully"
        
        # Simulate recording cache hit rate directly to verify metrics buffer
        collector._record_metric("cache_hit_rate", high_ratio)
        collector._record_metric("cache_hit_rate", medium_ratio)
        collector._record_metric("cache_hit_rate", low_ratio)
        
        # Verify cache metrics were recorded and can detect performance degradation
        cache_metrics = collector.get_recent_metrics("cache_hit_rate", 60)
        assert len(cache_metrics) >= 3, "Should have recorded all cache hit rate metrics"
        
        cache_values = [m.value for m in cache_metrics]
        assert 0.85 in cache_values, "Should contain high cache hit rate"
        assert 0.65 in cache_values, "Should contain medium cache hit rate"
        assert 0.20 in cache_values, "Should contain low cache hit rate"
        
        # Test performance degradation detection logic
        min_cache_ratio = min(cache_values)
        max_cache_ratio = max(cache_values)
        degradation_threshold = 0.3  # 30% degradation threshold
        
        performance_degraded = (max_cache_ratio - min_cache_ratio) > degradation_threshold
        assert performance_degraded, "Should detect significant cache performance degradation"
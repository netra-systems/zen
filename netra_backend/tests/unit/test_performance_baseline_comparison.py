"""Test Suite: Performance Baseline Comparison (Iteration 97)

Production-critical tests for performance regression detection via baseline comparison.
Ensures system performance remains within acceptable thresholds.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from netra_backend.app.monitoring.performance_monitor import PerformanceBaselineMonitor
from netra_backend.app.monitoring.metrics_collector import MetricsCollector


class TestPerformanceBaselineComparison:
    """Performance baseline comparison tests."""

    @pytest.mark.asyncio
    async def test_api_response_time_regression_detection(self):
        """Test detection of API response time regressions against baseline."""
        monitor = PerformanceBaselineMonitor()
        
        # Establish baseline performance metrics
        baseline_metrics = {
            'api_response_time_p95': 150.0,  # 150ms
            'api_response_time_p99': 300.0,  # 300ms
            'throughput_rps': 500,  # 500 requests/second
            'error_rate': 0.001,  # 0.1%
            'cpu_utilization': 0.65,  # 65%
            'memory_utilization': 0.75  # 75%
        }
        
        # Current metrics showing regression
        current_metrics = {
            'api_response_time_p95': 450.0,  # 3x slower - regression!
            'api_response_time_p99': 800.0,  # 2.7x slower - regression!
            'throughput_rps': 350,  # 30% lower - regression!
            'error_rate': 0.005,  # 5x higher error rate
            'cpu_utilization': 0.85,  # Higher CPU usage
            'memory_utilization': 0.90  # Higher memory usage
        }
        
        with patch.object(monitor, '_load_baseline_metrics', return_value=baseline_metrics):
            with patch.object(monitor, '_trigger_performance_alert', AsyncMock()) as mock_alert:
                result = await monitor.detect_performance_regression(current_metrics)
                
                assert result.regression_detected is True
                assert result.severity == 'critical'
                assert 'api_response_time_p95' in result.regressed_metrics
                assert 'throughput_rps' in result.regressed_metrics
                assert result.performance_degradation_percentage > 100.0  # >100% degradation
                mock_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_query_performance_monitoring(self):
        """Test database query performance monitoring and threshold enforcement."""
        monitor = PerformanceBaselineMonitor()
        
        # Database performance baselines
        db_baselines = {
            'avg_query_time_ms': 25.0,
            'slow_query_threshold_ms': 100.0,
            'connection_pool_utilization': 0.60,
            'deadlock_rate': 0.0001,
            'cache_hit_ratio': 0.95
        }
        
        # Current performance showing degradation
        current_db_metrics = {
            'avg_query_time_ms': 85.0,  # 3.4x slower
            'slow_query_count': 15,  # Too many slow queries
            'connection_pool_utilization': 0.95,  # Nearly exhausted
            'deadlock_rate': 0.002,  # 20x more deadlocks
            'cache_hit_ratio': 0.80  # Lower cache efficiency
        }
        
        with patch.object(monitor, '_get_db_performance_baseline', return_value=db_baselines):
            with patch.object(monitor, '_optimize_database_performance', AsyncMock()) as mock_optimize:
                result = await monitor.monitor_database_performance(current_db_metrics)
                
                assert result.performance_degradation_detected is True
                assert result.optimization_triggered is True
                assert result.critical_thresholds_exceeded is True
                assert current_db_metrics['avg_query_time_ms'] > db_baselines['slow_query_threshold_ms'] * 0.85
                mock_optimize.assert_called_once()
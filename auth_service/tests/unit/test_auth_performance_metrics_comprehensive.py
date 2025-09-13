"""
Auth Performance Metrics Comprehensive Unit Tests

Tests auth service performance monitoring system for real-time metrics collection,
analysis, and alerting for Issue #718.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - critical performance monitoring
- Business Goal: Protect $500K+ ARR through proactive performance monitoring
- Value Impact: Prevents auth performance degradation that impacts user experience
- Strategic Impact: Enables data-driven optimization of auth system performance
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from collections import deque

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

from auth_service.auth_core.performance.metrics import (
    AuthPerformanceMonitor,
    AuthMetric,
    PerformanceStats,
    monitor_auth_performance,
    auth_performance_monitor
)


class TestAuthPerformanceMonitor(SSotBaseTestCase):
    """Comprehensive unit tests for auth performance monitoring."""

    def setUp(self):
        """Set up test environment with SSOT patterns."""
        super().setUp()
        self.monitor = AuthPerformanceMonitor(max_metrics_history=100)

    def test_record_auth_operation_success(self):
        """Test recording successful auth operations."""
        operation = "jwt_validation"
        duration_ms = 150.0
        user_id = "test_user_123"

        initial_count = len(self.monitor.metrics_history)

        self.monitor.record_auth_operation(
            operation=operation,
            duration_ms=duration_ms,
            success=True,
            user_id=user_id,
            cache_hit=False
        )

        # Verify metric was recorded
        self.assertEqual(len(self.monitor.metrics_history), initial_count + 1)
        self.assertEqual(len(self.monitor.current_window_metrics), 1)

        # Verify operation stats tracking
        self.assertIn(operation, self.monitor.operation_stats)
        self.assertIn(duration_ms, self.monitor.operation_stats[operation])

    def test_record_auth_operation_failure(self):
        """Test recording failed auth operations."""
        operation = "user_authentication"
        duration_ms = 500.0
        error_type = "invalid_credentials"

        self.monitor.record_auth_operation(
            operation=operation,
            duration_ms=duration_ms,
            success=False,
            error_type=error_type
        )

        # Verify error was tracked
        self.assertEqual(self.monitor.error_counts[error_type], 1)

        # Verify metric was recorded with failure
        latest_metric = self.monitor.metrics_history[-1]
        self.assertFalse(latest_metric.success)
        self.assertEqual(latest_metric.error_type, error_type)

    def test_record_slow_operation_warning(self):
        """Test that slow operations trigger warnings."""
        operation = "slow_operation"
        slow_duration = self.monitor.target_response_time_ms + 500  # Exceed target

        with patch('auth_service.auth_core.performance.metrics.logger') as mock_logger:
            self.monitor.record_auth_operation(
                operation=operation,
                duration_ms=slow_duration,
                success=True
            )

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            warning_message = mock_logger.warning.call_args[0][0]
            self.assertIn("Slow auth operation", warning_message)
            self.assertIn(operation, warning_message)

    def test_operation_stats_size_limit(self):
        """Test that operation stats respect size limits."""
        operation = "test_operation"

        # Add more than the limit (1000) of measurements
        for i in range(1050):
            self.monitor.operation_stats[operation].append(float(i))

        # Should be trimmed to last 1000
        self.assertEqual(len(self.monitor.operation_stats[operation]), 1000)
        # Should contain the most recent values
        self.assertIn(1049.0, self.monitor.operation_stats[operation])
        self.assertNotIn(0.0, self.monitor.operation_stats[operation])

    def test_get_current_performance_stats_empty(self):
        """Test performance stats calculation with no data."""
        stats = self.monitor.get_current_performance_stats()

        self.assertIsInstance(stats, PerformanceStats)
        self.assertEqual(stats.total_requests, 0)
        self.assertEqual(stats.success_rate, 0)

    def test_get_current_performance_stats_with_data(self):
        """Test performance stats calculation with sample data."""
        # Add sample metrics
        test_metrics = [
            (100.0, True, False),   # Fast success
            (200.0, True, True),    # Medium success with cache hit
            (300.0, True, False),   # Slow success
            (400.0, False, False),  # Failed request
            (150.0, True, True),    # Fast success with cache hit
        ]

        for duration, success, cache_hit in test_metrics:
            self.monitor.record_auth_operation(
                operation="test_op",
                duration_ms=duration,
                success=success,
                cache_hit=cache_hit
            )

        stats = self.monitor.get_current_performance_stats()

        # Verify calculations
        self.assertEqual(stats.total_requests, 5)
        self.assertEqual(stats.success_rate, 0.8)  # 4/5 = 80%
        self.assertEqual(stats.cache_hit_rate, 0.4)  # 2/5 = 40%
        self.assertEqual(stats.error_rate, 0.2)  # 1/5 = 20%
        self.assertEqual(stats.avg_response_time_ms, 230.0)  # (100+200+300+400+150)/5

    def test_percentile_calculations(self):
        """Test that percentile response times are calculated correctly."""
        # Add 100 measurements with known distribution
        durations = [float(i) for i in range(1, 101)]  # 1ms to 100ms

        for duration in durations:
            self.monitor.record_auth_operation(
                operation="percentile_test",
                duration_ms=duration,
                success=True
            )

        stats = self.monitor.get_current_performance_stats()

        # P95 should be around 95ms (95th percentile of 1-100)
        self.assertGreaterEqual(stats.p95_response_time_ms, 94.0)
        self.assertLessEqual(stats.p95_response_time_ms, 96.0)

        # P99 should be around 99ms
        self.assertGreaterEqual(stats.p99_response_time_ms, 98.0)
        self.assertLessEqual(stats.p99_response_time_ms, 100.0)

    def test_requests_per_second_calculation(self):
        """Test requests per second calculation."""
        # Record metrics over a known time period
        start_time = time.time()
        self.monitor.current_window_start = start_time

        # Add 10 requests
        for _ in range(10):
            self.monitor.record_auth_operation("test_op", 100.0, True)

        # Simulate 2 seconds elapsed
        with patch('time.time', return_value=start_time + 2.0):
            stats = self.monitor.get_current_performance_stats()

        # Should be 5 requests per second (10 requests / 2 seconds)
        self.assertAlmostEqual(stats.requests_per_second, 5.0, places=1)

    def test_slow_requests_count(self):
        """Test counting of slow requests."""
        target_time = self.monitor.target_response_time_ms

        # Add mix of fast and slow requests
        durations = [
            target_time - 100,  # Fast
            target_time + 100,  # Slow
            target_time - 50,   # Fast
            target_time + 200,  # Slow
            target_time + 500,  # Very slow
        ]

        for duration in durations:
            self.monitor.record_auth_operation("test_op", duration, True)

        stats = self.monitor.get_current_performance_stats()
        self.assertEqual(stats.slow_requests_count, 3)  # 3 requests over target

    def test_critical_errors_detection(self):
        """Test detection of critical error types."""
        critical_errors = ['jwt_validation_failed', 'database_error', 'redis_error']
        non_critical_errors = ['invalid_input', 'timeout']

        # Add critical errors
        for error_type in critical_errors:
            self.monitor.record_auth_operation(
                operation="test_op",
                duration_ms=100.0,
                success=False,
                error_type=error_type
            )

        # Add non-critical errors
        for error_type in non_critical_errors:
            self.monitor.record_auth_operation(
                operation="test_op",
                duration_ms=100.0,
                success=False,
                error_type=error_type
            )

        stats = self.monitor.get_current_performance_stats()
        self.assertEqual(stats.critical_errors, 3)  # Only critical errors count

    def test_get_operation_performance_success(self):
        """Test getting performance stats for a specific operation."""
        operation = "jwt_validation"
        durations = [100.0, 150.0, 200.0, 250.0, 300.0]

        for duration in durations:
            self.monitor.operation_stats[operation].append(duration)

        perf = self.monitor.get_operation_performance(operation)

        self.assertEqual(perf["operation"], operation)
        self.assertEqual(perf["total_calls"], 5)
        self.assertEqual(perf["avg_duration_ms"], 200.0)  # Average of 100-300
        self.assertEqual(perf["min_duration_ms"], 100.0)
        self.assertEqual(perf["max_duration_ms"], 300.0)
        self.assertEqual(perf["p50_duration_ms"], 200.0)  # Median

    def test_get_operation_performance_no_data(self):
        """Test getting performance for operation with no data."""
        perf = self.monitor.get_operation_performance("nonexistent_operation")

        self.assertIn("error", perf)
        self.assertIn("No data for operation", perf["error"])

    def test_get_performance_alerts(self):
        """Test performance alert generation."""
        # Create conditions that should trigger alerts

        # Add slow operations to trigger response time alert
        for _ in range(5):
            self.monitor.record_auth_operation(
                "slow_op",
                self.monitor.target_response_time_ms + 500,  # Exceed target
                True
            )

        # Add failed operations to trigger success rate alert
        for _ in range(6):
            self.monitor.record_auth_operation("failed_op", 100.0, False)

        # Add operations with low cache hit rate
        for _ in range(10):
            self.monitor.record_auth_operation("no_cache_op", 100.0, True, cache_hit=False)

        # Add critical errors
        for _ in range(2):
            self.monitor.record_auth_operation(
                "critical_op", 100.0, False, error_type="database_error"
            )

        alerts = self.monitor.get_performance_alerts()

        # Should have multiple alerts
        alert_types = [alert["type"] for alert in alerts]

        self.assertIn("slow_response_time", alert_types)
        self.assertIn("low_success_rate", alert_types)
        self.assertIn("low_cache_hit_rate", alert_types)
        self.assertIn("critical_errors", alert_types)

        # Verify alert structure
        for alert in alerts:
            self.assertIn("type", alert)
            self.assertIn("severity", alert)
            self.assertIn("message", alert)
            self.assertIn("current_value", alert)
            self.assertIn("target_value", alert)

    def test_get_performance_report_comprehensive(self):
        """Test comprehensive performance report generation."""
        # Add varied test data
        operations = ["jwt_validation", "user_authentication", "token_refresh"]

        for operation in operations:
            for i in range(10):
                self.monitor.record_auth_operation(
                    operation=operation,
                    duration_ms=100.0 + i * 10,
                    success=i < 8,  # 80% success rate
                    cache_hit=i % 2 == 0  # 50% cache hit rate
                )

        report = self.monitor.get_performance_report()

        # Verify report structure
        self.assertIn("timestamp", report)
        self.assertIn("current_stats", report)
        self.assertIn("targets", report)
        self.assertIn("alerts", report)
        self.assertIn("operation_performance", report)
        self.assertIn("error_breakdown", report)
        self.assertIn("health_score", report)

        # Verify operation performance data
        for operation in operations:
            self.assertIn(operation, report["operation_performance"])

        # Verify health score calculation
        self.assertIsInstance(report["health_score"], float)
        self.assertGreaterEqual(report["health_score"], 0)
        self.assertLessEqual(report["health_score"], 100)

    def test_calculate_health_score(self):
        """Test health score calculation logic."""
        # Test perfect performance
        perfect_stats = PerformanceStats(
            total_requests=100,
            success_rate=1.0,  # 100%
            avg_response_time_ms=100.0,  # Under target
            cache_hit_rate=0.9,  # 90%
            critical_errors=0
        )

        score = self.monitor._calculate_health_score(perfect_stats)
        self.assertEqual(score, 100.0)

        # Test degraded performance
        degraded_stats = PerformanceStats(
            total_requests=100,
            success_rate=0.8,  # 80% (below 95% target)
            avg_response_time_ms=3000.0,  # Above target
            cache_hit_rate=0.5,  # 50% (below 80% target)
            critical_errors=2
        )

        score = self.monitor._calculate_health_score(degraded_stats)
        self.assertLess(score, 50.0)  # Should be significantly reduced

    def test_window_rotation(self):
        """Test monitoring window rotation."""
        # Add metrics to current window
        for i in range(5):
            self.monitor.record_auth_operation("test_op", 100.0, True)

        initial_window_size = len(self.monitor.current_window_metrics)
        self.assertEqual(initial_window_size, 5)

        # Force window rotation
        self.monitor._rotate_window()

        # Current window should be reset
        self.assertEqual(len(self.monitor.current_window_metrics), 0)

        # Window start time should be updated
        self.assertGreater(self.monitor.current_window_start, time.time() - 1)

    def test_hourly_stats_retention(self):
        """Test that hourly stats are properly retained and limited."""
        # Simulate 25 hours of data (should keep only 24 most recent)
        base_time = int(time.time() // 3600)

        for hour_offset in range(25):
            hour_key = base_time + hour_offset
            self.monitor.hourly_stats[hour_key] = PerformanceStats(total_requests=hour_offset)

        # Trigger cleanup
        self.monitor._rotate_window()

        # Should keep only 24 hours
        self.assertLessEqual(len(self.monitor.hourly_stats), 24)

        # Should keep the most recent hours
        max_hour = max(self.monitor.hourly_stats.keys())
        self.assertEqual(max_hour, base_time + 24)

    @pytest.mark.asyncio
    async def test_start_monitoring(self):
        """Test starting background monitoring tasks."""
        with patch.object(self.monitor, '_periodic_reporting') as mock_reporting:
            mock_reporting.return_value = asyncio.Future()
            mock_reporting.return_value.set_result(None)

            await self.monitor.start_monitoring()

            # Should have created the periodic reporting task
            mock_reporting.assert_called_once()

    @pytest.mark.asyncio
    async def test_periodic_reporting(self):
        """Test periodic reporting functionality."""
        # Mock time to control the reporting cycle
        with patch('asyncio.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, Exception("Stop test")]  # Stop after first iteration

            with patch('auth_service.auth_core.performance.metrics.logger') as mock_logger:
                # Add some alerts to trigger logging
                self.monitor.record_auth_operation("slow_op", 5000.0, True)

                try:
                    await self.monitor._periodic_reporting()
                except Exception:
                    pass  # Expected to stop the test

                # Should have logged performance info
                mock_logger.warning.assert_called()


class TestAuthMetric(SSotBaseTestCase):
    """Test the AuthMetric dataclass."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

    def test_auth_metric_creation(self):
        """Test AuthMetric creation with all fields."""
        timestamp = time.time()
        metric = AuthMetric(
            timestamp=timestamp,
            operation="jwt_validation",
            duration_ms=150.0,
            success=True,
            user_id="user_123",
            error_type=None,
            cache_hit=True
        )

        self.assertEqual(metric.timestamp, timestamp)
        self.assertEqual(metric.operation, "jwt_validation")
        self.assertEqual(metric.duration_ms, 150.0)
        self.assertTrue(metric.success)
        self.assertEqual(metric.user_id, "user_123")
        self.assertIsNone(metric.error_type)
        self.assertTrue(metric.cache_hit)

    def test_auth_metric_minimal_creation(self):
        """Test AuthMetric creation with minimal required fields."""
        metric = AuthMetric(
            timestamp=time.time(),
            operation="test_op",
            duration_ms=100.0,
            success=True
        )

        self.assertIsNone(metric.user_id)
        self.assertIsNone(metric.error_type)
        self.assertFalse(metric.cache_hit)


class TestPerformanceStats(SSotBaseTestCase):
    """Test the PerformanceStats dataclass."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

    def test_performance_stats_initialization(self):
        """Test PerformanceStats initialization with defaults."""
        stats = PerformanceStats()

        self.assertEqual(stats.total_requests, 0)
        self.assertEqual(stats.success_rate, 0.0)
        self.assertEqual(stats.avg_response_time_ms, 0.0)
        self.assertEqual(stats.p95_response_time_ms, 0.0)
        self.assertEqual(stats.p99_response_time_ms, 0.0)
        self.assertEqual(stats.cache_hit_rate, 0.0)
        self.assertEqual(stats.error_rate, 0.0)
        self.assertEqual(stats.requests_per_second, 0.0)
        self.assertEqual(stats.slow_requests_count, 0)
        self.assertEqual(stats.critical_errors, 0)

    def test_performance_stats_business_metrics(self):
        """Test PerformanceStats with business-relevant values."""
        stats = PerformanceStats(
            total_requests=1000,
            success_rate=0.99,  # 99% success rate
            avg_response_time_ms=120.0,  # 120ms average
            p95_response_time_ms=200.0,  # 200ms P95
            p99_response_time_ms=500.0,  # 500ms P99
            cache_hit_rate=0.85,  # 85% cache hit rate
            error_rate=0.01,  # 1% error rate
            requests_per_second=50.0,  # 50 RPS
            slow_requests_count=10,
            critical_errors=2
        )

        # Verify business targets are met
        self.assertGreaterEqual(stats.success_rate, 0.95)  # > 95% success
        self.assertLessEqual(stats.avg_response_time_ms, 200.0)  # < 200ms average
        self.assertGreaterEqual(stats.cache_hit_rate, 0.80)  # > 80% cache hit
        self.assertLessEqual(stats.error_rate, 0.05)  # < 5% error rate


class TestMonitorAuthPerformanceDecorator(SSotBaseTestCase):
    """Test the monitor_auth_performance decorator."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

    @pytest.mark.asyncio
    async def test_async_function_monitoring(self):
        """Test monitoring async functions."""
        @monitor_auth_performance("async_test_operation")
        async def async_test_function(user_id="test_user"):
            await asyncio.sleep(0.01)  # Simulate work
            return {"result": "success"}

        initial_count = len(auth_performance_monitor.metrics_history)

        result = await async_test_function()

        self.assertEqual(result, {"result": "success"})
        self.assertEqual(len(auth_performance_monitor.metrics_history), initial_count + 1)

        # Verify metric details
        latest_metric = auth_performance_monitor.metrics_history[-1]
        self.assertEqual(latest_metric.operation, "async_test_operation")
        self.assertTrue(latest_metric.success)
        self.assertGreaterEqual(latest_metric.duration_ms, 10.0)  # Should be at least 10ms

    def test_sync_function_monitoring(self):
        """Test monitoring synchronous functions."""
        @monitor_auth_performance("sync_test_operation")
        def sync_test_function(user_id="test_user"):
            time.sleep(0.01)  # Simulate work
            return {"result": "success"}

        initial_count = len(auth_performance_monitor.metrics_history)

        result = sync_test_function()

        self.assertEqual(result, {"result": "success"})
        self.assertEqual(len(auth_performance_monitor.metrics_history), initial_count + 1)

    @pytest.mark.asyncio
    async def test_function_failure_monitoring(self):
        """Test monitoring functions that raise exceptions."""
        @monitor_auth_performance("failing_operation")
        async def failing_function():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        initial_count = len(auth_performance_monitor.metrics_history)

        with pytest.raises(ValueError):
            await failing_function()

        # Should still record the metric
        self.assertEqual(len(auth_performance_monitor.metrics_history), initial_count + 1)

        # Verify failure was recorded
        latest_metric = auth_performance_monitor.metrics_history[-1]
        self.assertFalse(latest_metric.success)
        self.assertEqual(latest_metric.error_type, "valueerror")

    def test_cache_hit_parameter(self):
        """Test monitoring with cache hit parameter."""
        @monitor_auth_performance("cache_test_operation")
        def cache_test_function(_cache_hit=True):
            return {"cached": True}

        result = cache_test_function()

        # Verify cache hit was recorded
        latest_metric = auth_performance_monitor.metrics_history[-1]
        self.assertTrue(latest_metric.cache_hit)

    def test_user_id_extraction(self):
        """Test user ID extraction from function parameters."""
        @monitor_auth_performance("user_test_operation")
        def user_test_function(user_id, other_param="value"):
            return {"user": user_id}

        result = user_test_function("test_user_456")

        # Verify user ID was captured
        latest_metric = auth_performance_monitor.metrics_history[-1]
        self.assertEqual(latest_metric.user_id, "test_user_456")


class TestGlobalPerformanceMonitor(SSotBaseTestCase):
    """Test the global auth performance monitor instance."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

    def test_global_monitor_instance(self):
        """Test that global monitor instance is properly initialized."""
        self.assertIsInstance(auth_performance_monitor, AuthPerformanceMonitor)
        self.assertEqual(auth_performance_monitor.target_response_time_ms, 2000)
        self.assertEqual(auth_performance_monitor.target_success_rate, 0.95)
        self.assertEqual(auth_performance_monitor.target_cache_hit_rate, 0.80)

    def test_global_monitor_concurrent_access(self):
        """Test that global monitor handles concurrent access safely."""
        import threading

        results = []

        def record_operation(operation_id):
            auth_performance_monitor.record_auth_operation(
                operation=f"concurrent_op_{operation_id}",
                duration_ms=100.0,
                success=True,
                user_id=f"user_{operation_id}"
            )
            results.append(operation_id)

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=record_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all operations were recorded
        self.assertEqual(len(results), 10)

    def test_business_value_monitoring(self):
        """Test monitoring of business-critical auth operations."""
        # Simulate various auth operations that impact business value
        critical_operations = [
            ("user_login", 200.0, True),
            ("jwt_validation", 50.0, True),
            ("token_refresh", 100.0, True),
            ("user_registration", 300.0, True),
            ("oauth_callback", 150.0, True),
        ]

        for operation, duration, success in critical_operations:
            auth_performance_monitor.record_auth_operation(
                operation=operation,
                duration_ms=duration,
                success=success,
                user_id="business_user"
            )

        # Verify all operations were tracked
        stats = auth_performance_monitor.get_current_performance_stats()
        self.assertEqual(stats.total_requests, 5)
        self.assertEqual(stats.success_rate, 1.0)  # 100% success

        # Verify operation-specific tracking
        for operation, _, _ in critical_operations:
            perf = auth_performance_monitor.get_operation_performance(operation)
            self.assertEqual(perf["total_calls"], 1)
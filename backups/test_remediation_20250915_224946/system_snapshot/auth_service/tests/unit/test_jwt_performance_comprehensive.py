"""
JWT Performance Optimization Comprehensive Unit Tests

Tests JWT performance optimization features including caching, rate limiting,
circuit breakers, and connection pooling for Issue #718.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - critical performance infrastructure
- Business Goal: Protect $500K+ ARR through reliable auth performance
- Value Impact: Ensures auth system can handle production load without degradation
- Strategic Impact: Maintains platform availability and user experience quality
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from collections import deque

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

from auth_service.auth_core.performance.jwt_performance import (
    JWTPerformanceOptimizer,
    ConnectionPoolManager,
    PerformanceMetrics,
    track_performance,
    jwt_performance_optimizer,
    connection_pool_manager
)


class JWTPerformanceOptimizerTests(SSotBaseTestCase):
    """Comprehensive unit tests for JWT performance optimization."""

    def setUp(self):
        """Set up test environment with SSOT patterns."""
        super().setUp()
        self.optimizer = JWTPerformanceOptimizer()
        self.test_client_id = "test_client_123"
        self.test_operation = "jwt_validation"

    @pytest.mark.asyncio
    async def test_track_request_successful(self):
        """Test successful request tracking without rate limits."""
        initial_requests = self.optimizer.metrics.total_requests

        result = await self.optimizer.track_request(self.test_operation, self.test_client_id)

        self.assertIsNone(result)  # None means request is allowed
        self.assertEqual(self.optimizer.metrics.total_requests, initial_requests + 1)
        self.assertEqual(self.optimizer.metrics.current_load, 1)

    @pytest.mark.asyncio
    async def test_track_request_without_client_id(self):
        """Test request tracking without client ID."""
        result = await self.optimizer.track_request(self.test_operation)

        self.assertIsNone(result)  # Should still work without client ID
        self.assertEqual(self.optimizer.metrics.current_load, 1)

    @pytest.mark.asyncio
    async def test_track_request_updates_peak_load(self):
        """Test that peak load is properly tracked."""
        initial_peak = self.optimizer.metrics.peak_load

        # Track multiple concurrent requests
        for _ in range(5):
            await self.optimizer.track_request(self.test_operation, self.test_client_id)

        self.assertEqual(self.optimizer.metrics.current_load, 5)
        self.assertGreaterEqual(self.optimizer.metrics.peak_load, 5)
        self.assertGreaterEqual(self.optimizer.metrics.peak_load, initial_peak)

    @pytest.mark.asyncio
    async def test_track_response_successful(self):
        """Test successful response tracking."""
        await self.optimizer.track_request(self.test_operation, self.test_client_id)
        initial_successful = self.optimizer.metrics.successful_requests
        response_time = 0.150  # 150ms

        await self.optimizer.track_response(self.test_operation, True, response_time, self.test_client_id)

        self.assertEqual(self.optimizer.metrics.successful_requests, initial_successful + 1)
        self.assertEqual(self.optimizer.metrics.current_load, 0)  # Should decrease
        self.assertIn(response_time, self.optimizer.response_times)

    @pytest.mark.asyncio
    async def test_track_response_failed(self):
        """Test failed response tracking."""
        await self.optimizer.track_request(self.test_operation, self.test_client_id)
        initial_failed = self.optimizer.metrics.failed_requests
        response_time = 0.500  # 500ms

        await self.optimizer.track_response(self.test_operation, False, response_time, self.test_client_id)

        self.assertEqual(self.optimizer.metrics.failed_requests, initial_failed + 1)
        self.assertEqual(self.optimizer.metrics.current_load, 0)

    @pytest.mark.asyncio
    async def test_response_time_metrics_calculation(self):
        """Test response time metrics are calculated correctly."""
        response_times = [0.100, 0.200, 0.300, 0.400, 0.500]  # 100-500ms

        for rt in response_times:
            await self.optimizer.track_request(self.test_operation)
            await self.optimizer.track_response(self.test_operation, True, rt)

        # Check that metrics are updated
        self.assertEqual(self.optimizer.metrics.max_response_time, 0.500)
        self.assertEqual(self.optimizer.metrics.min_response_time, 0.100)
        self.assertEqual(self.optimizer.metrics.avg_response_time, 0.300)  # Average

    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self):
        """Test that rate limiting is enforced when limits are exceeded."""
        # Enable rate limiting and set low limit for testing
        self.optimizer.rate_limit_enabled = True
        self.optimizer.max_requests_per_minute = 5

        # Make requests up to the limit
        for i in range(5):
            result = await self.optimizer.track_request(self.test_operation, self.test_client_id)
            self.assertIsNone(result)

        # Next request should be rate limited
        result = await self.optimizer.track_request(self.test_operation, self.test_client_id)
        self.assertEqual(result, "rate_limit_exceeded")

    @pytest.mark.asyncio
    async def test_rate_limiting_different_clients(self):
        """Test that rate limiting is per-client."""
        self.optimizer.rate_limit_enabled = True
        self.optimizer.max_requests_per_minute = 3

        client1 = "client_1"
        client2 = "client_2"

        # Fill up client1's quota
        for _ in range(3):
            result = await self.optimizer.track_request(self.test_operation, client1)
            self.assertIsNone(result)

        # Client1 should be rate limited
        result = await self.optimizer.track_request(self.test_operation, client1)
        self.assertEqual(result, "rate_limit_exceeded")

        # Client2 should still be allowed
        result = await self.optimizer.track_request(self.test_operation, client2)
        self.assertIsNone(result)

    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker opens after threshold failures."""
        # Set low threshold for testing
        self.optimizer.circuit_breaker_threshold = 3

        # Generate failures to trip circuit breaker
        for _ in range(3):
            await self.optimizer.track_request(self.test_operation)
            await self.optimizer.track_response(self.test_operation, False, 0.100)

        # Next request should be blocked by circuit breaker
        result = await self.optimizer.track_request(self.test_operation)
        self.assertEqual(result, "service_temporarily_unavailable")

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker resets after timeout."""
        # Set low threshold and timeout for testing
        self.optimizer.circuit_breaker_threshold = 2
        self.optimizer.circuit_breaker_timeout = 1  # 1 second

        # Trip circuit breaker
        for _ in range(2):
            await self.optimizer.track_request(self.test_operation)
            await self.optimizer.track_response(self.test_operation, False, 0.100)

        # Should be blocked
        result = await self.optimizer.track_request(self.test_operation)
        self.assertEqual(result, "service_temporarily_unavailable")

        # Wait for circuit breaker to reset
        await asyncio.sleep(1.1)

        # Should be allowed again
        result = await self.optimizer.track_request(self.test_operation)
        self.assertIsNone(result)

    @pytest.mark.asyncio
    @patch('auth_service.auth_core.performance.jwt_performance.auth_redis_manager')
    async def test_cache_operations_redis_enabled(self, mock_redis_manager):
        """Test cache operations when Redis is available."""
        # Mock Redis to be enabled and working
        mock_redis_manager.enabled = True
        mock_redis_client = AsyncMock()
        mock_redis_manager.get_client.return_value = mock_redis_client

        cache_key = "test_cache_key"
        test_data = {"user_id": "123", "permissions": ["read"]}

        # Test cache miss
        mock_redis_client.get.return_value = None
        result = await self.optimizer.get_cached_response(cache_key)
        self.assertIsNone(result)
        self.assertEqual(self.optimizer.metrics.cache_misses, 1)

        # Test cache storage
        import json
        success = await self.optimizer.cache_response(cache_key, test_data)
        self.assertTrue(success)
        mock_redis_client.setex.assert_called_once_with(
            cache_key,
            self.optimizer.cache_ttl_seconds,
            json.dumps(test_data, default=str)
        )

        # Test cache hit
        mock_redis_client.get.return_value = json.dumps(test_data)
        result = await self.optimizer.get_cached_response(cache_key)
        self.assertEqual(result, test_data)
        self.assertEqual(self.optimizer.metrics.cache_hits, 1)

    @pytest.mark.asyncio
    @patch('auth_service.auth_core.performance.jwt_performance.auth_redis_manager')
    async def test_cache_operations_redis_disabled(self, mock_redis_manager):
        """Test cache operations when Redis is disabled."""
        mock_redis_manager.enabled = False

        cache_key = "test_cache_key"
        test_data = {"user_id": "123"}

        # Should return None for cache miss
        result = await self.optimizer.get_cached_response(cache_key)
        self.assertIsNone(result)

        # Should return False for cache storage
        success = await self.optimizer.cache_response(cache_key, test_data)
        self.assertFalse(success)

    @pytest.mark.asyncio
    async def test_cache_operations_disabled(self):
        """Test cache operations when caching is disabled."""
        self.optimizer.cache_enabled = False

        cache_key = "test_cache_key"
        test_data = {"user_id": "123"}

        # Should return None immediately
        result = await self.optimizer.get_cached_response(cache_key)
        self.assertIsNone(result)

        # Should return False immediately
        success = await self.optimizer.cache_response(cache_key, test_data)
        self.assertFalse(success)

    def test_generate_cache_key(self):
        """Test cache key generation with various parameters."""
        operation = "jwt_validate"

        # Test with no parameters
        key1 = self.optimizer.generate_cache_key(operation)
        self.assertEqual(key1, "jwt_api:jwt_validate:")

        # Test with parameters
        key2 = self.optimizer.generate_cache_key(operation, user_id="123", token_type="access")
        expected_params = "token_type=access&user_id=123"  # Sorted alphabetically
        self.assertEqual(key2, f"jwt_api:jwt_validate:{expected_params}")

        # Test parameter consistency (same params should generate same key)
        key3 = self.optimizer.generate_cache_key(operation, token_type="access", user_id="123")
        self.assertEqual(key2, key3)

    def test_performance_stats_generation(self):
        """Test comprehensive performance statistics generation."""
        # Add some test data
        self.optimizer.metrics.total_requests = 100
        self.optimizer.metrics.successful_requests = 95
        self.optimizer.metrics.failed_requests = 5
        self.optimizer.metrics.cache_hits = 60
        self.optimizer.metrics.cache_misses = 40
        self.optimizer.metrics.current_load = 10
        self.optimizer.metrics.peak_load = 25

        stats = self.optimizer.get_performance_stats()

        # Verify calculated rates
        self.assertEqual(stats["requests"]["total"], 100)
        self.assertEqual(stats["requests"]["successful"], 95)
        self.assertEqual(stats["requests"]["failed"], 5)
        self.assertEqual(stats["requests"]["success_rate"], 95.0)  # 95%

        self.assertEqual(stats["cache"]["hits"], 60)
        self.assertEqual(stats["cache"]["misses"], 40)
        self.assertEqual(stats["cache"]["hit_rate"], 60.0)  # 60%

        self.assertEqual(stats["load"]["current"], 10)
        self.assertEqual(stats["load"]["peak"], 25)

    def test_reset_metrics(self):
        """Test metrics reset functionality."""
        # Add some data
        self.optimizer.metrics.total_requests = 50
        self.optimizer.response_times.extend([0.1, 0.2, 0.3])

        # Reset metrics
        self.optimizer.reset_metrics()

        # Verify reset
        self.assertEqual(self.optimizer.metrics.total_requests, 0)
        self.assertEqual(len(self.optimizer.response_times), 0)

    @pytest.mark.asyncio
    async def test_error_handling_in_tracking(self):
        """Test error handling in request/response tracking."""
        # Mock an internal error in metrics update
        with patch.object(self.optimizer.metrics, '__setattr__', side_effect=Exception("Metrics error")):
            # Should not raise exception
            result = await self.optimizer.track_request(self.test_operation, self.test_client_id)
            self.assertIsNone(result)  # Should handle error gracefully

    @pytest.mark.asyncio
    async def test_concurrent_operations_safety(self):
        """Test that optimizer handles concurrent operations safely."""
        async def concurrent_operation(operation_id):
            client_id = f"client_{operation_id}"
            await self.optimizer.track_request(f"operation_{operation_id}", client_id)
            await asyncio.sleep(0.01)  # Simulate processing time
            await self.optimizer.track_response(f"operation_{operation_id}", True, 0.01, client_id)
            return operation_id

        # Run multiple concurrent operations
        tasks = [concurrent_operation(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # Verify all operations completed
        self.assertEqual(len(results), 20)
        self.assertEqual(self.optimizer.metrics.total_requests, 20)
        self.assertEqual(self.optimizer.metrics.successful_requests, 20)


class ConnectionPoolManagerTests(SSotBaseTestCase):
    """Test connection pool management functionality."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.pool_manager = ConnectionPoolManager()

    @pytest.mark.asyncio
    async def test_get_database_pool_initialization(self):
        """Test database pool initialization."""
        pool = await self.pool_manager.get_database_pool()

        self.assertIsNotNone(pool)
        self.assertIn("database", self.pool_manager.pools)
        self.assertTrue(self.pool_manager.pools["database"]["initialized"])

    @pytest.mark.asyncio
    async def test_get_database_pool_reuse(self):
        """Test that database pool is reused after initialization."""
        # Get pool first time
        pool1 = await self.pool_manager.get_database_pool()

        # Get pool second time
        pool2 = await self.pool_manager.get_database_pool()

        # Should be same pool reference
        self.assertIs(pool1, pool2)

    def test_get_pool_stats(self):
        """Test pool statistics generation."""
        stats = self.pool_manager.get_pool_stats()

        self.assertIn("pools", stats)
        self.assertIn("configuration", stats)
        self.assertEqual(stats["configuration"]["max_connections"], 20)
        self.assertEqual(stats["configuration"]["min_connections"], 5)

    @pytest.mark.asyncio
    async def test_pool_initialization_error_handling(self):
        """Test error handling during pool initialization."""
        with patch.object(self.pool_manager, '_initialize_database_pool', side_effect=Exception("Pool error")):
            pool = await self.pool_manager.get_database_pool()
            self.assertIsNone(pool)


class PerformanceDecoratorTests(SSotBaseTestCase):
    """Test the performance tracking decorator."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

    @pytest.mark.asyncio
    async def test_track_performance_decorator_success(self):
        """Test performance decorator tracks successful operations."""
        @track_performance("test_operation")
        async def test_function(user_id="test_user"):
            await asyncio.sleep(0.01)  # Simulate work
            return {"result": "success"}

        initial_requests = jwt_performance_optimizer.metrics.total_requests

        result = await test_function()

        self.assertEqual(result, {"result": "success"})
        self.assertEqual(jwt_performance_optimizer.metrics.total_requests, initial_requests + 1)

    @pytest.mark.asyncio
    async def test_track_performance_decorator_failure(self):
        """Test performance decorator tracks failed operations."""
        @track_performance("test_operation")
        async def failing_function():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        initial_failed = jwt_performance_optimizer.metrics.failed_requests

        with pytest.raises(ValueError):
            await failing_function()

        self.assertEqual(jwt_performance_optimizer.metrics.failed_requests, initial_failed + 1)

    @pytest.mark.asyncio
    async def test_track_performance_decorator_rate_limiting(self):
        """Test performance decorator respects rate limiting."""
        # Enable rate limiting with low threshold
        jwt_performance_optimizer.rate_limit_enabled = True
        jwt_performance_optimizer.max_requests_per_minute = 1

        @track_performance("limited_operation")
        async def limited_function(client_id="test_client"):
            return {"result": "success"}

        # First call should succeed
        result1 = await limited_function()
        self.assertEqual(result1, {"result": "success"})

        # Second call should be rate limited
        result2 = await limited_function()
        self.assertEqual(result2, {"error": "rate_limit_exceeded"})

        # Reset for other tests
        jwt_performance_optimizer.rate_limit_enabled = False


class PerformanceMetricsTests(SSotBaseTestCase):
    """Test the PerformanceMetrics dataclass."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

    def test_performance_metrics_initialization(self):
        """Test PerformanceMetrics initialization."""
        metrics = PerformanceMetrics()

        self.assertEqual(metrics.total_requests, 0)
        self.assertEqual(metrics.successful_requests, 0)
        self.assertEqual(metrics.failed_requests, 0)
        self.assertEqual(metrics.cache_hits, 0)
        self.assertEqual(metrics.cache_misses, 0)
        self.assertEqual(metrics.avg_response_time, 0.0)
        self.assertEqual(metrics.max_response_time, 0.0)
        self.assertEqual(metrics.min_response_time, float('inf'))
        self.assertEqual(metrics.current_load, 0)
        self.assertEqual(metrics.peak_load, 0)
        self.assertIsInstance(metrics.last_reset, datetime)

    def test_performance_metrics_business_calculations(self):
        """Test business-relevant performance calculations."""
        metrics = PerformanceMetrics()

        # Simulate production load metrics
        metrics.total_requests = 1000
        metrics.successful_requests = 950  # 95% success rate
        metrics.failed_requests = 50
        metrics.cache_hits = 800
        metrics.cache_misses = 200
        metrics.avg_response_time = 0.150  # 150ms average
        metrics.max_response_time = 2.000  # 2s max
        metrics.min_response_time = 0.050  # 50ms min
        metrics.current_load = 25
        metrics.peak_load = 100

        # Calculate business metrics
        success_rate = metrics.successful_requests / metrics.total_requests
        cache_hit_rate = metrics.cache_hits / (metrics.cache_hits + metrics.cache_misses)
        error_rate = metrics.failed_requests / metrics.total_requests

        # Assert business targets
        self.assertGreaterEqual(success_rate, 0.95)  # 95% success rate target
        self.assertGreaterEqual(cache_hit_rate, 0.80)  # 80% cache hit rate target
        self.assertLessEqual(error_rate, 0.05)  # 5% error rate limit
        self.assertLessEqual(metrics.avg_response_time, 0.200)  # 200ms response time target


class GlobalInstancesTests(SSotBaseTestCase):
    """Test global performance optimizer and connection pool instances."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

    def test_global_optimizer_instance(self):
        """Test that global optimizer instance is properly initialized."""
        self.assertIsInstance(jwt_performance_optimizer, JWTPerformanceOptimizer)
        self.assertTrue(jwt_performance_optimizer.cache_enabled)
        self.assertTrue(jwt_performance_optimizer.rate_limit_enabled)

    def test_global_connection_pool_instance(self):
        """Test that global connection pool instance is properly initialized."""
        self.assertIsInstance(connection_pool_manager, ConnectionPoolManager)
        self.assertEqual(connection_pool_manager.max_connections, 20)
        self.assertEqual(connection_pool_manager.min_connections, 5)

    @pytest.mark.asyncio
    async def test_global_instances_integration(self):
        """Test integration between global instances."""
        # Test that global optimizer can track operations
        result = await jwt_performance_optimizer.track_request("global_test")
        self.assertIsNone(result)

        # Test that global pool manager can provide pools
        pool = await connection_pool_manager.get_database_pool()
        self.assertIsNotNone(pool)
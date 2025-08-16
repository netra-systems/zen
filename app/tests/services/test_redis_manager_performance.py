"""
Tests for Redis Manager performance characteristics
Tests high throughput, memory usage, latency, and concurrent safety
"""

import pytest
import asyncio
import time
import tracemalloc

from app.tests.helpers.redis_test_fixtures import performance_redis_manager, RedisConnectionPool
from app.tests.helpers.redis_test_helpers import (
    verify_performance_metrics, verify_memory_usage, verify_latency_metrics,
    verify_metrics_accuracy, calculate_hit_rate, verify_concurrent_safety,
    setup_large_dataset_tasks, measure_operation_latency, setup_batch_operations,
    verify_no_exceptions
)


class TestRedisManagerPerformance:
    """Test Redis manager performance characteristics"""
    async def test_high_throughput_operations(self, performance_redis_manager):
        """Test high throughput Redis operations"""
        num_operations = 1000
        
        async def perform_batch_operations():
            """Execute batch operations for performance testing"""
            tasks = setup_batch_operations(performance_redis_manager, num_operations)
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        start_time = time.time()
        results = await perform_batch_operations()
        end_time = time.time()
        
        execution_time = end_time - start_time
        throughput = len(results) / execution_time
        
        verify_performance_metrics(execution_time, throughput)
        assert verify_no_exceptions(results)
    async def test_memory_usage_under_load(self, performance_redis_manager):
        """Test memory usage under high load"""
        tracemalloc.start()
        
        large_data_size = 100
        large_value = "x" * 1000
        tasks = setup_large_dataset_tasks(performance_redis_manager, large_data_size, large_value)
        
        await asyncio.gather(*tasks)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        verify_memory_usage(peak, 50)
    async def test_operation_latency_measurement(self, performance_redis_manager):
        """Test operation latency measurement"""
        latencies = []
        
        for i in range(50):
            measure_func = measure_operation_latency(
                performance_redis_manager.set, f"latency_key_{i}", f"latency_value_{i}"
            )
            latency = await measure_func()
            latencies.append(latency)
        
        verify_latency_metrics(latencies)
    
    def test_metrics_collection_accuracy(self, performance_redis_manager):
        """Test accuracy of collected metrics"""
        performance_redis_manager.reset_metrics()
        
        asyncio.run(performance_redis_manager.get_with_retry("metric_key_1"))
        asyncio.run(performance_redis_manager.set_with_retry("metric_key_1", "value_1"))
        asyncio.run(performance_redis_manager.get_with_retry("metric_key_1"))
        
        metrics = performance_redis_manager.get_metrics()
        verify_metrics_accuracy(metrics, 3, 1, 1, 0)
        
        expected_hit_rate = calculate_hit_rate(1, 2)
        assert abs(metrics['cache_hit_rate'] - expected_hit_rate) < 0.01
    async def test_concurrent_connection_safety(self, performance_redis_manager):
        """Test thread safety of concurrent connections"""
        connection_pool = RedisConnectionPool(max_connections=3)
        performance_redis_manager.set_connection_pool(connection_pool)
        
        concurrent_operations = 20
        
        async def concurrent_operation(op_id):
            """Perform concurrent Redis operation"""
            try:
                connection = await performance_redis_manager.get_pooled_connection()
                await connection.set(f"concurrent_key_{op_id}", f"concurrent_value_{op_id}")
                result = await connection.get(f"concurrent_key_{op_id}")
                await performance_redis_manager.return_pooled_connection(connection)
                return result
            except Exception as e:
                return e
        
        tasks = [concurrent_operation(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks)
        
        verify_concurrent_safety(results, concurrent_operations, connection_pool.max_connections)
        assert connection_pool.active_connections <= connection_pool.max_connections
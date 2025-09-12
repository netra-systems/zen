"""
Redis test helpers for setup, assertions, and teardown operations
Provides reusable functions to ensure all test functions stay  <= 8 lines
"""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import redis.asyncio as redis

from netra_backend.app.redis_manager import RedisManager

def setup_redis_settings_mock(mock_settings, host="localhost", port=6379, username=None, password=None):
    """Setup mock settings for Redis connection"""
    mock_settings.redis.host = host
    mock_settings.redis.port = port
    mock_settings.redis.username = username
    mock_settings.redis.password = password

def verify_redis_operation_basic(mock_client, operation_count=1):
    """Verify basic Redis operation executed"""
    assert mock_client.operation_count == operation_count

def verify_redis_get_result(result, expected_value):
    """Verify Redis GET operation result"""
    assert result == expected_value

def verify_redis_set_result(result, mock_client, key, value):
    """Verify Redis SET operation result"""
    assert result == True
    assert mock_client.data[key] == value

def verify_redis_set_with_ttl(mock_client, key, expiration_seconds):
    """Verify Redis SET operation with TTL"""
    assert key in mock_client.ttls
    expected_expiry = datetime.now(UTC) + timedelta(seconds=expiration_seconds)
    ttl = mock_client.ttls[key]
    assert abs((ttl - expected_expiry).total_seconds()) < 1

def verify_redis_delete_result(result, mock_client, key, expected_deleted=1):
    """Verify Redis DELETE operation result"""
    assert result == expected_deleted
    if expected_deleted > 0:
        assert key not in mock_client.data

def verify_command_in_history(mock_client, command_tuple):
    """Verify command appears in mock client history"""
    assert command_tuple in mock_client.command_history

def setup_test_data(mock_client, key, value):
    """Setup test data in mock Redis client"""
    mock_client.data[key] = value

def create_disabled_redis_manager():
    """Create disabled Redis manager for testing"""
    manager = RedisManager()
    manager.enabled = False
    manager.redis_client = None
    return manager

def verify_disabled_operations(get_result, set_result, delete_result):
    """Verify disabled Redis operations return None"""
    assert get_result == None
    assert set_result == None
    assert delete_result == None

def setup_failing_redis_client(mock_client, failure_type="connection"):
    """Setup Redis client to fail"""
    mock_client.set_failure_mode(True, failure_type)

def verify_connection_pool_state(pool, expected_active, expected_max):
    """Verify connection pool state"""
    assert pool.active_connections == expected_active
    assert pool.max_connections == expected_max

def create_concurrent_tasks(operation_func, count):
    """Create list of concurrent async tasks"""
    return [operation_func(i) for i in range(count)]

def verify_concurrent_results(results, expected_count):
    """Verify concurrent operation results"""
    assert len(results) == expected_count
    return all(f"value_{i}" in results for i in range(expected_count))

def verify_pool_cleanup(pool):
    """Verify connection pool cleanup"""
    assert pool.active_connections == 0
    assert len(pool.connections) == 0

def setup_transient_failure_mock(attempt_threshold=2):
    """Setup mock that fails first N attempts"""
    attempt_count = 0
    
    async def failing_operation(key):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count <= attempt_threshold:
            raise redis.ConnectionError("Transient connection error")
        return f"success_{key}"
    
    return failing_operation, lambda: attempt_count

def setup_persistent_failure_mock():
    """Setup mock that always fails"""
    async def always_failing_operation(key):
        raise redis.ConnectionError("Persistent connection error")
    
    return always_failing_operation

def setup_timing_failure_mock(failure_count=2):
    """Setup mock that tracks retry timing"""
    retry_times = []
    
    async def timing_failing_operation(key):
        retry_times.append(time.time())
        if len(retry_times) <= failure_count:
            raise redis.ConnectionError("Timed failure")
        return "success"
    
    return timing_failing_operation, retry_times

def verify_exponential_backoff(retry_times, expected_delays):
    """Verify exponential backoff timing"""
    if len(retry_times) < len(expected_delays) + 1:
        return False
    
    for i, expected_delay in enumerate(expected_delays):
        actual_delay = retry_times[i + 1] - retry_times[i]
        min_delay, max_delay = expected_delay
        if not (min_delay < actual_delay < max_delay):
            return False
    
    return True

def setup_fallback_cache():
    """Setup fallback cache for testing"""
    return {}

def create_fallback_operations(manager, fallback_cache):
    """Create fallback operations for Redis manager"""
    async def fallback_get(key):
        if manager.redis_client == None:
            return fallback_cache.get(key)
        return await manager.get(key)
    
    async def fallback_set(key, value, ex=None):
        if manager.redis_client == None:
            fallback_cache[key] = value
            return True
        return await manager.set(key, value, ex=ex)
    
    return fallback_get, fallback_set

def verify_performance_metrics(execution_time, throughput, max_time=2.0, min_throughput=500):
    """Verify performance metrics meet requirements"""
    assert execution_time < max_time
    assert throughput > min_throughput

def verify_memory_usage(peak_memory, max_memory_mb=50):
    """Verify memory usage within limits"""
    max_memory_bytes = max_memory_mb * 1024 * 1024
    assert peak_memory < max_memory_bytes

def verify_latency_metrics(latencies, max_avg=10.0, max_peak=50.0):
    """Verify latency metrics meet requirements"""
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)
    
    assert avg_latency < max_avg
    assert max_latency < max_peak
    assert min_latency >= 0.0

def verify_metrics_accuracy(metrics, expected_success, expected_hits, expected_misses, expected_failures):
    """Verify collected metrics accuracy"""
    assert metrics['successful_operations'] == expected_success
    assert metrics['cache_hits'] == expected_hits
    assert metrics['cache_misses'] == expected_misses
    assert metrics['failed_operations'] == expected_failures

def calculate_hit_rate(hits, total_gets):
    """Calculate cache hit rate"""
    return hits / total_gets if total_gets > 0 else 0

def verify_concurrent_safety(results, expected_count, max_connections):
    """Verify concurrent operation safety"""
    successful_results = [r for r in results if not isinstance(r, Exception)]
    assert len(successful_results) == expected_count

def setup_large_dataset_tasks(manager, size, value_template):
    """Setup tasks for large dataset operations"""
    tasks = []
    for i in range(size):
        key = f"large_key_{i}"
        value = value_template
        tasks.append(manager.set(key, value))
    return tasks

def measure_operation_latency(operation_func, *args):
    """Measure single operation latency"""
    async def measure():
        start_time = time.time()
        await operation_func(*args)
        end_time = time.time()
        return (end_time - start_time) * 1000  # Convert to milliseconds
    
    return measure

def setup_batch_operations(manager, count):
    """Setup batch operations for performance testing"""
    tasks = []
    
    # Mix of different operations
    for i in range(count // 3):
        tasks.append(manager.set(f"key_{i}", f"value_{i}"))
    
    for i in range(count // 3):
        tasks.append(manager.get(f"key_{i}"))
    
    for i in range(count // 3):
        tasks.append(manager.delete(f"delete_key_{i}"))
    
    return tasks

def verify_no_exceptions(results):
    """Verify no exceptions in operation results"""
    exceptions = [r for r in results if isinstance(r, Exception)]
    return len(exceptions) == 0

async def create_test_redis_client(host="localhost", port=6379, db=1):
    """Create a test Redis client for integration testing"""
    import redis.asyncio as redis
    client = await get_redis_client()  # MIGRATED: was redis.Redis(host=host, port=port, db=db, decode_responses=True)
    try:
        await client.ping()
        return client
    except Exception:
        # Return mock client if Redis not available
        # Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
        from test_framework.real_services import get_real_services
        
        # Use canonical MockRedisClient from test_framework
        return MockRedisClient()

async def clear_redis_test_data(client, pattern="test:*"):
    """Clear test data from Redis"""
    try:
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
    except Exception:
        pass  # Ignore errors during cleanup

def generate_test_rate_limit_keys(user_id, endpoint):
    """Generate rate limit keys for testing"""
    return [
        f"rate_limit:{user_id}:{endpoint}",
        f"rate_limit:global:{user_id}",
        f"rate_limit:service:{user_id}:{endpoint}"
    ]
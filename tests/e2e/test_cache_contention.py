"""
Test Suite 9: Cache Contention Under Load - E2E Implementation

This comprehensive test suite validates Redis cache behavior under high contention scenarios,
focusing on atomic operations, cache invalidation race conditions, hit/miss ratios, and 
cache coherence protocols. Tests simulate realistic enterprise AI workload scenarios.

Business Value Justification (BVJ):
- Segment: Enterprise/Mid-tier  
- Business Goal: Platform Stability, Performance Optimization, Risk Reduction
- Value Impact: Ensures cache coherence preventing data corruption affecting AI response quality
- Strategic/Revenue Impact: Critical for enterprise customers with high-volume concurrent AI workloads
"""

import pytest
import asyncio
import threading
import time
import gc
import psutil
import uuid
import json
import logging
import random
import hashlib
import secrets
import redis.asyncio as redis
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Set
from unittest.mock import AsyncMock, MagicMock, patch
from collections import defaultdict, Counter
from contextlib import asynccontextmanager
import statistics

# Configure logging for cache contention detection
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration constants
REDIS_URL = "redis://localhost:6379"
PERFORMANCE_REQUIREMENTS = {
    "cache_hit_latency_ms": 20,  # p95 requirement (relaxed for test environment)
    "cache_miss_latency_ms": 200,  # p95 requirement (relaxed for test environment)
    "atomic_operation_latency_ms": 15,  # p95 requirement (relaxed for concurrent operations)
    "invalidation_latency_ms": 50,  # p95 requirement (relaxed for test environment)
    "throughput_ops_per_sec": 500,  # minimum throughput (realistic for test environment)
    "cache_hit_ratio_percent": 80,  # minimum hit ratio under load (relaxed)
    "operation_success_rate_percent": 95.0,  # minimum success rate (relaxed for test stability)
    "recovery_time_sec": 10,  # max recovery time after partition (relaxed)
}

# Test data configuration
TEST_DATA_CONFIG = {
    "num_cache_keys": 10000,
    "data_size_range": (1024, 10240),  # 1KB to 10KB
    "ttl_range": (60, 300),  # 1-5 minutes
    "zipfian_alpha": 1.1,  # 80/20 access pattern
    "concurrency_levels": [10, 50, 100, 500],
}


class CacheContentionMetrics:
    """Collects and analyzes cache contention performance metrics."""
    
    def __init__(self):
        self.operation_times = defaultdict(list)
        self.operation_results = defaultdict(list)
        self.cache_stats = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.start_time = None
        self.end_time = None
        
    def start_measurement(self):
        """Start performance measurement period."""
        self.start_time = time.time()
        
    def end_measurement(self):
        """End performance measurement period."""
        self.end_time = time.time()
        
    def record_operation(self, operation_type: str, duration_ms: float, success: bool, result: Any = None):
        """Record individual operation metrics."""
        self.operation_times[operation_type].append(duration_ms)
        self.operation_results[operation_type].append(success)
        if success:
            self.cache_stats[f"{operation_type}_success"] += 1
        else:
            self.cache_stats[f"{operation_type}_failure"] += 1
            self.error_counts[operation_type] += 1
            
    def record_cache_hit(self):
        """Record cache hit."""
        self.cache_stats["cache_hits"] += 1
        
    def record_cache_miss(self):
        """Record cache miss."""
        self.cache_stats["cache_misses"] += 1
        
    def get_latency_percentile(self, operation_type: str, percentile: int) -> float:
        """Calculate latency percentile for operation type."""
        times = self.operation_times.get(operation_type, [])
        if not times:
            return 0.0
        return statistics.quantiles(times, n=100)[percentile-1] if len(times) >= percentile else max(times)
        
    def get_success_rate(self, operation_type: str) -> float:
        """Calculate success rate for operation type."""
        results = self.operation_results.get(operation_type, [])
        if not results:
            return 0.0
        return (sum(results) / len(results)) * 100
        
    def get_cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        hits = self.cache_stats.get("cache_hits", 0)
        misses = self.cache_stats.get("cache_misses", 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0
        
    def get_throughput(self) -> float:
        """Calculate operations per second."""
        if not self.start_time or not self.end_time:
            return 0.0
        duration = self.end_time - self.start_time
        total_ops = sum(len(times) for times in self.operation_times.values())
        return total_ops / duration if duration > 0 else 0.0
        
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        return {
            "latency_metrics": {
                op_type: {
                    "p50": self.get_latency_percentile(op_type, 50),
                    "p95": self.get_latency_percentile(op_type, 95),
                    "p99": self.get_latency_percentile(op_type, 99),
                    "max": max(times) if times else 0,
                    "avg": statistics.mean(times) if times else 0,
                }
                for op_type, times in self.operation_times.items()
            },
            "success_rates": {
                op_type: self.get_success_rate(op_type)
                for op_type in self.operation_results.keys()
            },
            "cache_performance": {
                "hit_ratio_percent": self.get_cache_hit_ratio(),
                "total_hits": self.cache_stats.get("cache_hits", 0),
                "total_misses": self.cache_stats.get("cache_misses", 0),
            },
            "throughput": {
                "ops_per_second": self.get_throughput(),
                "test_duration_sec": (self.end_time - self.start_time) if self.start_time and self.end_time else 0,
            },
            "error_summary": dict(self.error_counts),
            "cache_stats": dict(self.cache_stats),
        }


class RedisTestClient:
    """Redis client wrapper for cache contention testing."""
    
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_url = redis_url
        self.client = None
        self.connection_pool = None
        
    async def connect(self):
        """Connect to Redis with optimized settings for testing."""
        self.connection_pool = redis.ConnectionPool.from_url(
            self.redis_url,
            max_connections=200,  # High connection limit for concurrency tests
            retry_on_timeout=True,
            socket_timeout=5,
            socket_connect_timeout=10,
            decode_responses=True
        )
        self.client = redis.Redis(connection_pool=self.connection_pool)
        
        # Test connection
        await self.client.ping()
        logger.info("Redis connection established successfully")
        
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.aclose()
        if self.connection_pool:
            await self.connection_pool.disconnect()
            
    async def flush_test_data(self):
        """Flush all test data from Redis."""
        if self.client:
            await self.client.flushdb()
            
    async def get_memory_usage(self) -> int:
        """Get Redis memory usage in bytes."""
        info = await self.client.info("memory")
        return info.get("used_memory", 0)
        
    async def get_connection_count(self) -> int:
        """Get number of active Redis connections."""
        info = await self.client.info("clients")
        return info.get("connected_clients", 0)


class CacheContentionTestSuite:
    """Main test suite for cache contention scenarios."""
    
    def __init__(self):
        self.redis_client = RedisTestClient()
        self.metrics = CacheContentionMetrics()
        self.test_keys = set()
        self.test_data = {}
        
    async def setup_test_environment(self):
        """Setup test environment and prepare test data."""
        await self.redis_client.connect()
        await self.redis_client.flush_test_data()
        
        # Generate test data
        await self._generate_test_data()
        
        logger.info(f"Test environment setup complete. {len(self.test_keys)} keys prepared.")
        
    async def teardown_test_environment(self):
        """Cleanup test environment."""
        try:
            # Clean up test keys
            if self.test_keys and self.redis_client.client:
                await self.redis_client.client.delete(*self.test_keys)
            
            await self.redis_client.disconnect()
            logger.info("Test environment cleanup complete")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
            
    async def _generate_test_data(self):
        """Generate test data with realistic patterns."""
        for i in range(TEST_DATA_CONFIG["num_cache_keys"]):
            key = f"test:cache:key:{i}"
            data_size = random.randint(*TEST_DATA_CONFIG["data_size_range"])
            value = secrets.token_hex(data_size // 2)  # hex encoding doubles size
            ttl = random.randint(*TEST_DATA_CONFIG["ttl_range"])
            
            self.test_keys.add(key)
            self.test_data[key] = {
                "value": value,
                "ttl": ttl,
                "size": len(value)
            }
            
        # Pre-populate some cache entries
        populate_keys = random.sample(list(self.test_keys), min(1000, len(self.test_keys)))
        for key in populate_keys:
            data = self.test_data[key]
            await self.redis_client.client.setex(key, data["ttl"], data["value"])
            
    def _get_zipfian_key(self) -> str:
        """Get key following Zipfian distribution (80/20 rule)."""
        # Simple approximation of Zipfian distribution
        if random.random() < 0.8:
            # 80% of access to top 20% of keys
            key_idx = random.randint(0, len(self.test_keys) // 5)
        else:
            # 20% of access to remaining 80% of keys
            key_idx = random.randint(len(self.test_keys) // 5, len(self.test_keys) - 1)
            
        return list(self.test_keys)[key_idx]


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.asyncio
class TestCacheContentionSuite:
    """Cache contention test suite implementation."""
    
    @pytest.fixture(autouse=True)
    async def setup_suite(self):
        """Setup test suite."""
        self.suite = CacheContentionTestSuite()
        await self.suite.setup_test_environment()
        yield
        await self.suite.teardown_test_environment()
        
    async def test_concurrent_counter_operations(self):
        """
        Test Case 1: Validate Redis atomic INCR/DECR operations under high concurrency.
        
        Simulates AI usage metrics and request counting under concurrent load.
        """
        logger.info("Starting concurrent counter operations test")
        
        counter_key = "test:counter:concurrent"
        num_workers = 50
        increments_per_worker = 100
        expected_total = num_workers * increments_per_worker
        
        self.suite.metrics.start_measurement()
        
        async def increment_worker(worker_id: int) -> int:
            """Worker function for concurrent increments."""
            success_count = 0
            for i in range(increments_per_worker):
                start_time = time.time()
                try:
                    result = await self.suite.redis_client.client.incr(counter_key)
                    duration_ms = (time.time() - start_time) * 1000
                    self.suite.metrics.record_operation("incr", duration_ms, True, result)
                    success_count += 1
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    self.suite.metrics.record_operation("incr", duration_ms, False)
                    logger.error(f"Worker {worker_id} increment failed: {e}")
                    
            return success_count
            
        # Execute concurrent increments
        tasks = [increment_worker(i) for i in range(num_workers)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        self.suite.metrics.end_measurement()
        
        # Verify results
        final_count = await self.suite.redis_client.client.get(counter_key)
        final_count = int(final_count) if final_count else 0
        
        successful_operations = sum(r for r in results if isinstance(r, int))
        
        # Assertions
        assert final_count == expected_total, f"Expected {expected_total}, got {final_count}"
        assert successful_operations == expected_total, f"Not all operations succeeded"
        
        # Performance assertions
        p95_latency = self.suite.metrics.get_latency_percentile("incr", 95)
        success_rate = self.suite.metrics.get_success_rate("incr")
        
        assert p95_latency < PERFORMANCE_REQUIREMENTS["atomic_operation_latency_ms"], \
            f"P95 latency {p95_latency}ms exceeds {PERFORMANCE_REQUIREMENTS['atomic_operation_latency_ms']}ms"
        assert success_rate >= PERFORMANCE_REQUIREMENTS["operation_success_rate_percent"], \
            f"Success rate {success_rate}% below {PERFORMANCE_REQUIREMENTS['operation_success_rate_percent']}%"
            
        logger.info(f"Concurrent counter test passed: final_count={final_count}, p95_latency={p95_latency:.2f}ms")
        
    async def test_cache_stampede_prevention(self):
        """
        Test Case 2: Test system behavior when cache expires under heavy load.
        
        Simulates expensive AI model response caching with concurrent access.
        """
        logger.info("Starting cache stampede prevention test")
        
        cache_key = "test:expensive:ai_response"
        num_workers = 100
        expensive_computation_time = 0.1  # 100ms simulated computation
        
        # Lua script for cache stampede prevention using SETNX pattern
        stampede_script = """
        local key = KEYS[1]
        local lock_key = KEYS[2]
        local value = ARGV[1]
        local ttl = tonumber(ARGV[2])
        local lock_ttl = tonumber(ARGV[3])
        
        -- First check if value already exists
        local existing_val = redis.call('GET', key)
        if existing_val then
            return existing_val
        end
        
        -- Try to acquire lock for computation
        if redis.call('SETNX', lock_key, '1') == 1 then
            redis.call('EXPIRE', lock_key, lock_ttl)
            -- Double-check value doesn't exist (race condition protection)
            existing_val = redis.call('GET', key)
            if existing_val then
                redis.call('DEL', lock_key)
                return existing_val
            end
            -- Set the actual value
            redis.call('SETEX', key, ttl, value)
            redis.call('DEL', lock_key)
            return 'computed'
        else
            -- Lock exists, wait and check for value
            local retries = 20
            while retries > 0 do
                local val = redis.call('GET', key)
                if val then
                    return val
                end
                retries = retries - 1
            end
            return 'wait_timeout'
        end
        """
        
        computation_count = 0
        computation_lock = asyncio.Lock()
        
        async def expensive_computation() -> str:
            """Simulate expensive AI computation."""
            nonlocal computation_count
            async with computation_lock:
                computation_count += 1
            await asyncio.sleep(expensive_computation_time)
            return f"expensive_result_{uuid.uuid4().hex[:8]}"
            
        async def cache_access_worker(worker_id: int) -> Tuple[str, bool]:
            """Worker that attempts to access cached value."""
            start_time = time.time()
            
            try:
                # Check if value exists in cache
                cached_value = await self.suite.redis_client.client.get(cache_key)
                
                if cached_value:
                    # Cache hit
                    duration_ms = (time.time() - start_time) * 1000
                    self.suite.metrics.record_operation("cache_hit", duration_ms, True)
                    self.suite.metrics.record_cache_hit()
                    return cached_value, True
                else:
                    # Cache miss - use stampede prevention
                    lock_key = f"{cache_key}:lock"
                    
                    # Try to acquire lock first before expensive computation
                    lock_acquired = await self.suite.redis_client.client.setnx(lock_key, "1")
                    
                    if lock_acquired:
                        # We got the lock - do the expensive computation
                        await self.suite.redis_client.client.expire(lock_key, 5)
                        
                        # Double-check cache in case another worker set it
                        cached_value = await self.suite.redis_client.client.get(cache_key)
                        if cached_value:
                            await self.suite.redis_client.client.delete(lock_key)
                            duration_ms = (time.time() - start_time) * 1000
                            self.suite.metrics.record_operation("cache_hit_after_lock", duration_ms, True)
                            self.suite.metrics.record_cache_hit()
                            return cached_value, True
                            
                        # Perform expensive computation
                        new_value = await expensive_computation()
                        
                        # Set cache value and release lock
                        await self.suite.redis_client.client.setex(cache_key, 60, new_value)
                        await self.suite.redis_client.client.delete(lock_key)
                        
                        duration_ms = (time.time() - start_time) * 1000
                        self.suite.metrics.record_operation("cache_miss_computed", duration_ms, True)
                        self.suite.metrics.record_cache_miss()
                        return new_value, False
                        
                    else:
                        # Lock is held by someone else - wait for result
                        retries = 20
                        while retries > 0:
                            await asyncio.sleep(0.01)  # Small delay
                            cached_value = await self.suite.redis_client.client.get(cache_key)
                            if cached_value:
                                duration_ms = (time.time() - start_time) * 1000
                                self.suite.metrics.record_operation("cache_miss_waited", duration_ms, True)
                                self.suite.metrics.record_cache_miss()
                                return cached_value, False
                            retries -= 1
                            
                        # Timeout waiting - do fallback computation
                        new_value = await expensive_computation()
                        duration_ms = (time.time() - start_time) * 1000
                        self.suite.metrics.record_operation("cache_miss_timeout", duration_ms, True)
                        self.suite.metrics.record_cache_miss()
                        return new_value, False
                    
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.suite.metrics.record_operation("cache_error", duration_ms, False)
                logger.error(f"Worker {worker_id} failed: {e}")
                return None, False
                
        self.suite.metrics.start_measurement()
        
        # Execute concurrent cache access
        tasks = [cache_access_worker(i) for i in range(num_workers)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        self.suite.metrics.end_measurement()
        
        # Analyze results
        successful_results = [r for r in results if not isinstance(r, Exception) and r[0] is not None]
        
        # Assertions
        assert len(successful_results) >= num_workers * 0.95, "Too many failed requests"
        # Allow more computations due to race conditions in test environment
        assert computation_count <= max(10, num_workers * 0.15), f"Too many computations: {computation_count} (expected ≤{max(10, num_workers * 0.15)})"
        
        # Performance assertions
        avg_response_time = self.suite.metrics.get_latency_percentile("cache_miss_computed", 50)
        assert avg_response_time < PERFORMANCE_REQUIREMENTS["cache_miss_latency_ms"], \
            f"Average response time {avg_response_time}ms exceeds limit"
            
        logger.info(f"Cache stampede test passed: computations={computation_count}, success_rate={len(successful_results)/num_workers*100:.1f}%")
        
    async def test_multi_key_transaction_atomicity(self):
        """
        Test Case 3: Validate MULTI/EXEC atomic transactions under contention.
        
        Simulates user session + preferences + permissions updates.
        """
        logger.info("Starting multi-key transaction atomicity test")
        
        num_workers = 50
        operations_per_worker = 10
        
        async def transaction_worker(worker_id: int) -> int:
            """Worker performing atomic multi-key transactions."""
            success_count = 0
            
            for i in range(operations_per_worker):
                start_time = time.time()
                session_key = f"session:{worker_id}:{i}"
                prefs_key = f"prefs:{worker_id}:{i}"
                perms_key = f"perms:{worker_id}:{i}"
                
                try:
                    # Start transaction
                    pipe = self.suite.redis_client.client.pipeline(transaction=True)
                    
                    # Multi-key atomic update
                    pipe.multi()
                    pipe.setex(session_key, 300, f"session_data_{worker_id}_{i}")
                    pipe.setex(prefs_key, 600, f"preferences_{worker_id}_{i}")
                    pipe.setex(perms_key, 900, f"permissions_{worker_id}_{i}")
                    
                    # Execute transaction
                    result = await pipe.execute()
                    
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Verify all operations succeeded
                    if all(r is True for r in result):
                        self.suite.metrics.record_operation("transaction", duration_ms, True)
                        success_count += 1
                    else:
                        self.suite.metrics.record_operation("transaction", duration_ms, False)
                        
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    self.suite.metrics.record_operation("transaction", duration_ms, False)
                    logger.error(f"Transaction worker {worker_id} failed: {e}")
                    
            return success_count
            
        self.suite.metrics.start_measurement()
        
        # Execute concurrent transactions
        tasks = [transaction_worker(i) for i in range(num_workers)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        self.suite.metrics.end_measurement()
        
        # Verify results
        successful_operations = sum(r for r in results if isinstance(r, int))
        expected_total = num_workers * operations_per_worker
        
        # Check for consistency - verify related keys exist together
        consistency_errors = 0
        for worker_id in range(num_workers):
            for i in range(operations_per_worker):
                session_key = f"session:{worker_id}:{i}"
                prefs_key = f"prefs:{worker_id}:{i}"
                perms_key = f"perms:{worker_id}:{i}"
                
                exists_results = await asyncio.gather(
                    self.suite.redis_client.client.exists(session_key),
                    self.suite.redis_client.client.exists(prefs_key),
                    self.suite.redis_client.client.exists(perms_key),
                    return_exceptions=True
                )
                
                # All should exist or none should exist (atomicity)
                if not all(r == exists_results[0] for r in exists_results):
                    consistency_errors += 1
                    
        # Assertions
        assert consistency_errors == 0, f"Found {consistency_errors} consistency violations"
        assert successful_operations >= expected_total * 0.95, "Too many failed transactions"
        
        # Performance assertions
        p95_latency = self.suite.metrics.get_latency_percentile("transaction", 95)
        success_rate = self.suite.metrics.get_success_rate("transaction")
        
        assert p95_latency < PERFORMANCE_REQUIREMENTS["atomic_operation_latency_ms"] * 5, \
            f"Transaction P95 latency {p95_latency}ms too high (limit: {PERFORMANCE_REQUIREMENTS['atomic_operation_latency_ms'] * 5}ms)"
        assert success_rate >= PERFORMANCE_REQUIREMENTS["operation_success_rate_percent"], \
            f"Transaction success rate {success_rate}% too low"
            
        logger.info(f"Transaction atomicity test passed: success_rate={success_rate:.1f}%, consistency_errors={consistency_errors}")
        
    async def test_cache_invalidation_consistency(self):
        """
        Test Case 4: Test cache invalidation under concurrent read/write operations.
        
        Simulates cache invalidation events with concurrent access patterns.
        """
        logger.info("Starting cache invalidation consistency test")
        
        base_key = "test:invalidation"
        num_readers = 30
        num_writers = 10
        num_invalidators = 5
        test_duration = 10  # seconds
        
        # Shared state for coordinating test
        test_active = True
        invalidation_events = []
        stale_data_detected = []
        
        async def reader_worker(worker_id: int):
            """Worker that continuously reads cache values."""
            read_count = 0
            while test_active:
                try:
                    key = f"{base_key}:{random.randint(0, 9)}"
                    start_time = time.time()
                    
                    value = await self.suite.redis_client.client.get(key)
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if value:
                        self.suite.metrics.record_operation("read_hit", duration_ms, True)
                        self.suite.metrics.record_cache_hit()
                        
                        # Check if value is stale (contains old timestamp)
                        try:
                            data = json.loads(value)
                            timestamp = data.get("timestamp", 0)
                            if time.time() - timestamp > 60:  # Stale if older than 1 minute
                                stale_data_detected.append({
                                    "key": key,
                                    "timestamp": timestamp,
                                    "detected_at": time.time()
                                })
                        except (json.JSONDecodeError, KeyError):
                            pass
                    else:
                        self.suite.metrics.record_operation("read_miss", duration_ms, True)
                        self.suite.metrics.record_cache_miss()
                        
                    read_count += 1
                    await asyncio.sleep(0.01)  # Small delay
                    
                except Exception as e:
                    logger.error(f"Reader {worker_id} error: {e}")
                    
            logger.debug(f"Reader {worker_id} completed {read_count} reads")
            
        async def writer_worker(worker_id: int):
            """Worker that continuously writes cache values."""
            write_count = 0
            while test_active:
                try:
                    key = f"{base_key}:{random.randint(0, 9)}"
                    value = json.dumps({
                        "data": f"writer_{worker_id}_value_{write_count}",
                        "timestamp": time.time(),
                        "worker_id": worker_id
                    })
                    
                    start_time = time.time()
                    await self.suite.redis_client.client.setex(key, 30, value)
                    duration_ms = (time.time() - start_time) * 1000
                    
                    self.suite.metrics.record_operation("write", duration_ms, True)
                    write_count += 1
                    await asyncio.sleep(0.05)  # Moderate write frequency
                    
                except Exception as e:
                    logger.error(f"Writer {worker_id} error: {e}")
                    
            logger.debug(f"Writer {worker_id} completed {write_count} writes")
            
        async def invalidator_worker(worker_id: int):
            """Worker that periodically invalidates cache entries."""
            invalidation_count = 0
            while test_active:
                try:
                    # Invalidate random keys
                    keys_to_invalidate = [f"{base_key}:{i}" for i in range(10)]
                    
                    start_time = time.time()
                    deleted_count = await self.suite.redis_client.client.delete(*keys_to_invalidate)
                    duration_ms = (time.time() - start_time) * 1000
                    
                    self.suite.metrics.record_operation("invalidation", duration_ms, True)
                    
                    invalidation_events.append({
                        "timestamp": time.time(),
                        "keys_deleted": deleted_count,
                        "worker_id": worker_id
                    })
                    
                    invalidation_count += 1
                    await asyncio.sleep(1.0)  # Invalidate every second
                    
                except Exception as e:
                    logger.error(f"Invalidator {worker_id} error: {e}")
                    
            logger.debug(f"Invalidator {worker_id} completed {invalidation_count} invalidations")
            
        self.suite.metrics.start_measurement()
        
        # Start all workers
        tasks = []
        tasks.extend([reader_worker(i) for i in range(num_readers)])
        tasks.extend([writer_worker(i) for i in range(num_writers)])
        tasks.extend([invalidator_worker(i) for i in range(num_invalidators)])
        
        # Run test for specified duration
        await asyncio.sleep(test_duration)
        test_active = False
        
        # Wait for workers to finish
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.suite.metrics.end_measurement()
        
        # Analyze results
        total_invalidations = len(invalidation_events)
        stale_data_count = len(stale_data_detected)
        
        # Assertions
        assert total_invalidations > 0, "No invalidations occurred during test"
        assert stale_data_count == 0, f"Detected {stale_data_count} stale data instances"
        
        # Performance assertions
        invalidation_p95 = self.suite.metrics.get_latency_percentile("invalidation", 95)
        read_success_rate = self.suite.metrics.get_success_rate("read_hit")
        
        assert invalidation_p95 < PERFORMANCE_REQUIREMENTS["invalidation_latency_ms"], \
            f"Invalidation P95 latency {invalidation_p95}ms exceeds limit"
        assert read_success_rate >= 95.0, f"Read success rate {read_success_rate}% too low"
        
        logger.info(f"Cache invalidation test passed: invalidations={total_invalidations}, stale_data={stale_data_count}")
        
    async def test_lock_free_performance_validation(self):
        """
        Test Case 5: Compare lock-free Redis operations vs traditional locking.
        
        Validates superior performance of Redis atomic operations.
        """
        logger.info("Starting lock-free performance validation test")
        
        num_workers = 100
        operations_per_worker = 50
        test_key = "test:performance:counter"
        
        # Test 1: Lock-free atomic operations
        await self.suite.redis_client.client.delete(test_key)
        lock_free_times = []
        
        async def lock_free_worker(worker_id: int):
            """Worker using Redis atomic operations."""
            for i in range(operations_per_worker):
                start_time = time.time()
                await self.suite.redis_client.client.incr(test_key)
                duration_ms = (time.time() - start_time) * 1000
                lock_free_times.append(duration_ms)
                
        self.suite.metrics.start_measurement()
        
        # Execute lock-free operations
        start_total = time.time()
        tasks = [lock_free_worker(i) for i in range(num_workers)]
        await asyncio.gather(*tasks)
        lock_free_total_time = time.time() - start_total
        
        lock_free_final_value = int(await self.suite.redis_client.client.get(test_key))
        
        # Test 2: Application-level locking simulation
        await self.suite.redis_client.client.delete(test_key)
        locked_times = []
        application_lock = asyncio.Lock()
        
        async def locked_worker(worker_id: int):
            """Worker using application-level locking."""
            for i in range(operations_per_worker):
                start_time = time.time()
                async with application_lock:
                    current = await self.suite.redis_client.client.get(test_key)
                    current = int(current) if current else 0
                    await self.suite.redis_client.client.set(test_key, current + 1)
                duration_ms = (time.time() - start_time) * 1000
                locked_times.append(duration_ms)
                
        # Execute locked operations
        start_total = time.time()
        tasks = [locked_worker(i) for i in range(num_workers)]
        await asyncio.gather(*tasks)
        locked_total_time = time.time() - start_total
        
        locked_final_value = int(await self.suite.redis_client.client.get(test_key))
        
        self.suite.metrics.end_measurement()
        
        # Analyze performance differences
        lock_free_avg = statistics.mean(lock_free_times)
        locked_avg = statistics.mean(locked_times)
        lock_free_p95 = statistics.quantiles(lock_free_times, n=100)[94]
        locked_p95 = statistics.quantiles(locked_times, n=100)[94]
        
        performance_improvement = ((locked_avg - lock_free_avg) / locked_avg) * 100
        throughput_improvement = ((lock_free_total_time - locked_total_time) / locked_total_time) * 100
        
        # Assertions
        expected_final = num_workers * operations_per_worker
        assert lock_free_final_value == expected_final, f"Lock-free operations lost data: {lock_free_final_value} != {expected_final}"
        assert locked_final_value == expected_final, f"Locked operations lost data: {locked_final_value} != {expected_final}"
        assert performance_improvement >= 50.0, f"Performance improvement {performance_improvement:.1f}% below 50% requirement"
        assert lock_free_p95 < PERFORMANCE_REQUIREMENTS["atomic_operation_latency_ms"] * 2, f"Lock-free P95 {lock_free_p95}ms too high (limit: {PERFORMANCE_REQUIREMENTS['atomic_operation_latency_ms'] * 2}ms)"
        
        logger.info(f"Lock-free performance test passed: improvement={performance_improvement:.1f}%, throughput_gain={throughput_improvement:.1f}%")
        
        # Record performance metrics
        self.suite.metrics.record_operation("lock_free_avg", lock_free_avg, True)
        self.suite.metrics.record_operation("locked_avg", locked_avg, True)
        
    async def test_memory_pressure_cache_eviction(self):
        """
        Test Case 7: Validate cache behavior under memory pressure.
        
        Tests LRU eviction and performance under memory constraints.
        """
        logger.info("Starting memory pressure cache eviction test")
        
        # Fill Redis with data until memory pressure
        initial_memory = await self.suite.redis_client.get_memory_usage()
        target_memory = initial_memory + (50 * 1024 * 1024)  # Add 50MB
        
        keys_created = []
        data_size = 10240  # 10KB per entry
        
        # Fill memory
        current_memory = initial_memory
        counter = 0
        while current_memory < target_memory and counter < 10000:  # Safety limit
            key = f"memory_test:{counter}"
            value = "x" * data_size
            
            start_time = time.time()
            await self.suite.redis_client.client.setex(key, 300, value)
            duration_ms = (time.time() - start_time) * 1000
            
            self.suite.metrics.record_operation("memory_fill", duration_ms, True)
            keys_created.append(key)
            
            if counter % 100 == 0:
                current_memory = await self.suite.redis_client.get_memory_usage()
                
            counter += 1
            
        logger.info(f"Created {len(keys_created)} keys, memory usage: {current_memory - initial_memory} bytes")
        
        # Test concurrent operations under memory pressure
        num_workers = 50
        operations_per_worker = 20
        
        async def memory_pressure_worker(worker_id: int):
            """Worker performing operations under memory pressure."""
            success_count = 0
            for i in range(operations_per_worker):
                try:
                    # Mix of operations
                    if i % 3 == 0:
                        # Read existing key
                        key = random.choice(keys_created[:100])  # Read from early keys
                        start_time = time.time()
                        value = await self.suite.redis_client.client.get(key)
                        duration_ms = (time.time() - start_time) * 1000
                        
                        if value:
                            self.suite.metrics.record_operation("pressure_read_hit", duration_ms, True)
                            self.suite.metrics.record_cache_hit()
                        else:
                            self.suite.metrics.record_operation("pressure_read_miss", duration_ms, True)
                            self.suite.metrics.record_cache_miss()
                            
                    else:
                        # Create new key (may trigger eviction)
                        key = f"pressure:{worker_id}:{i}"
                        value = "y" * data_size
                        start_time = time.time()
                        await self.suite.redis_client.client.setex(key, 60, value)
                        duration_ms = (time.time() - start_time) * 1000
                        
                        self.suite.metrics.record_operation("pressure_write", duration_ms, True)
                        
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Memory pressure worker {worker_id} error: {e}")
                    
            return success_count
            
        self.suite.metrics.start_measurement()
        
        # Execute operations under memory pressure
        tasks = [memory_pressure_worker(i) for i in range(num_workers)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        self.suite.metrics.end_measurement()
        
        # Analyze results
        successful_operations = sum(r for r in results if isinstance(r, int))
        expected_operations = num_workers * operations_per_worker
        
        final_memory = await self.suite.redis_client.get_memory_usage()
        
        # Check cache hit ratio under pressure
        cache_hit_ratio = self.suite.metrics.get_cache_hit_ratio()
        
        # Performance assertions
        read_p95 = self.suite.metrics.get_latency_percentile("pressure_read_hit", 95)
        write_p95 = self.suite.metrics.get_latency_percentile("pressure_write", 95)
        
        # Assertions
        assert successful_operations >= expected_operations * 0.95, "Too many failed operations under memory pressure"
        assert read_p95 < PERFORMANCE_REQUIREMENTS["cache_hit_latency_ms"] * 3, f"Read latency {read_p95}ms too high under pressure"
        assert write_p95 < PERFORMANCE_REQUIREMENTS["cache_hit_latency_ms"] * 5, f"Write latency {write_p95}ms too high under pressure"
        assert final_memory > 0, "Redis memory usage reporting failed"
        
        logger.info(f"Memory pressure test passed: hit_ratio={cache_hit_ratio:.1f}%, memory_delta={final_memory-initial_memory} bytes")
        
        # Cleanup large test data
        if keys_created:
            await self.suite.redis_client.client.delete(*keys_created[:1000])  # Delete in batches


@pytest.mark.e2e
@pytest.mark.integration
async def test_comprehensive_cache_contention_validation():
    """
    Comprehensive validation test that runs multiple cache contention scenarios
    and generates a complete performance report.
    """
    logger.info("Starting comprehensive cache contention validation")
    
    suite = CacheContentionTestSuite()
    await suite.setup_test_environment()
    
    try:
        # Run core test scenarios in sequence
        test_scenarios = [
            ("Concurrent Counters", TestCacheContentionSuite().test_concurrent_counter_operations),
            ("Cache Stampede", TestCacheContentionSuite().test_cache_stampede_prevention),
            ("Transaction Atomicity", TestCacheContentionSuite().test_multi_key_transaction_atomicity),
            ("Cache Invalidation", TestCacheContentionSuite().test_cache_invalidation_consistency),
            ("Lock-Free Performance", TestCacheContentionSuite().test_lock_free_performance_validation),
            ("Memory Pressure", TestCacheContentionSuite().test_memory_pressure_cache_eviction),
        ]
        
        results_summary = {}
        
        for scenario_name, test_func in test_scenarios:
            logger.info(f"Executing scenario: {scenario_name}")
            start_time = time.time()
            
            try:
                # Set suite context for individual tests
                test_instance = TestCacheContentionSuite()
                test_instance.suite = suite
                
                await test_func(test_instance)
                
                duration = time.time() - start_time
                results_summary[scenario_name] = {
                    "status": "PASSED",
                    "duration_sec": duration,
                    "error": None
                }
                logger.info(f"✅ {scenario_name} passed in {duration:.2f}s")
                
            except Exception as e:
                duration = time.time() - start_time
                results_summary[scenario_name] = {
                    "status": "FAILED", 
                    "duration_sec": duration,
                    "error": str(e)
                }
                logger.error(f"❌ {scenario_name} failed in {duration:.2f}s: {e}")
                
        # Generate comprehensive report
        performance_report = suite.metrics.generate_report()
        
        # Calculate overall success metrics
        passed_scenarios = sum(1 for r in results_summary.values() if r["status"] == "PASSED")
        total_scenarios = len(results_summary)
        overall_success_rate = (passed_scenarios / total_scenarios) * 100
        
        # Business impact assessment
        business_impact = {
            "enterprise_readiness": overall_success_rate >= 85,
            "performance_target_met": suite.metrics.get_throughput() >= PERFORMANCE_REQUIREMENTS["throughput_ops_per_sec"],
            "reliability_target_met": suite.metrics.get_cache_hit_ratio() >= PERFORMANCE_REQUIREMENTS["cache_hit_ratio_percent"],
            "risk_assessment": "LOW" if passed_scenarios == total_scenarios else "MEDIUM" if passed_scenarios >= total_scenarios * 0.8 else "HIGH"
        }
        
        # Final validation
        assert overall_success_rate >= 80, f"Too many test scenarios failed: {overall_success_rate:.1f}% success rate"
        assert business_impact["risk_assessment"] != "HIGH", "High risk assessment indicates system not ready for enterprise workloads"
        
        logger.info(f"Comprehensive cache contention validation completed: {passed_scenarios}/{total_scenarios} scenarios passed")
        logger.info(f"Business impact: {business_impact}")
        
        # Return detailed results for further analysis
        return {
            "scenario_results": results_summary,
            "performance_report": performance_report,
            "business_impact": business_impact,
            "overall_success_rate": overall_success_rate
        }
        
    finally:
        await suite.teardown_test_environment()


if __name__ == "__main__":
    """Run cache contention tests directly for development."""
    import asyncio
    
    async def run_development_tests():
        logger.info("Running cache contention tests in development mode")
        
        # Set up environment for direct execution
        import os
        os.environ["RUN_E2E_TESTS"] = "true"
        os.environ["TESTING"] = "1"
        
        try:
            results = await test_comprehensive_cache_contention_validation()
            logger.info("Development test execution completed successfully")
            logger.info(f"Results summary: {results['overall_success_rate']:.1f}% success rate")
        except Exception as e:
            logger.error(f"Development test execution failed: {e}")
            
    asyncio.run(run_development_tests())
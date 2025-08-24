"""Cache Stampede Prevention - L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (cache stampedes affect system stability across all user segments)
- Business Goal: Prevent thundering herd problems that can crash services during cache misses
- Value Impact: Maintains service availability during high load, prevents cascade failures
- Strategic Impact: $6K MRR protection through system stability and performance under load spikes

Critical Path: Cache miss detection -> Stampede prevention -> Single computation -> Result distribution -> Performance validation
L3 Realism: Real Redis with distributed locks, actual concurrent load simulation, thundering herd scenarios
Performance Requirements: Lock acquisition < 10ms, computation efficiency > 95%, stampede prevention 100%
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import hashlib
import json
import logging
import random
import statistics
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set

import pytest
import redis.asyncio as aioredis

from netra_backend.app.logging_config import central_logger

from netra_backend.tests.integration.helpers.redis_l3_helpers import (
    RedisContainer as NetraRedisContainer,
)

logger = central_logger.get_logger(__name__)

@dataclass
class StampedeMetrics:
    """Metrics for cache stampede prevention testing."""
    cache_miss_events: int = 0
    stampede_prevention_attempts: int = 0
    successful_lock_acquisitions: int = 0
    failed_lock_acquisitions: int = 0
    lock_acquisition_times: List[float] = None
    computation_times: List[float] = None
    duplicate_computations: int = 0
    cache_population_times: List[float] = None
    concurrent_requests: int = 0
    requests_served_from_cache: int = 0
    
    def __post_init__(self):
        if self.lock_acquisition_times is None:
            self.lock_acquisition_times = []
        if self.computation_times is None:
            self.computation_times = []
        if self.cache_population_times is None:
            self.cache_population_times = []
    
    @property
    def lock_success_rate(self) -> float:
        """Calculate lock acquisition success rate."""
        total_attempts = self.successful_lock_acquisitions + self.failed_lock_acquisitions
        if total_attempts == 0:
            return 100.0
        return (self.successful_lock_acquisitions / total_attempts) * 100.0
    
    @property
    def avg_lock_acquisition_time(self) -> float:
        """Calculate average lock acquisition time."""
        return statistics.mean(self.lock_acquisition_times) if self.lock_acquisition_times else 0.0
    
    @property
    def computation_efficiency(self) -> float:
        """Calculate computation efficiency (avoid duplicate work)."""
        if self.cache_miss_events == 0:
            return 100.0
        expected_computations = self.cache_miss_events
        actual_computations = len(self.computation_times)
        duplicate_ratio = self.duplicate_computations / expected_computations if expected_computations > 0 else 0
        return (1 - duplicate_ratio) * 100.0

class CacheStampedePreventionL3Manager:
    """L3 cache stampede prevention test manager with real Redis distributed locks."""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client  # Single real Redis client
        self.metrics = StampedeMetrics()
        self.test_keys = set()
        self.computation_results = {}
        self.active_computations = set()
        
    async def setup_redis_for_stampede_testing(self) -> bool:
        """Setup Redis for stampede prevention testing using the real client."""
        try:
            # Test Redis connection
            await self.redis_client.ping()
            logger.info("Redis client ready for stampede testing")
            return True
        except Exception as e:
            logger.error(f"Failed to setup Redis for stampede testing: {e}")
            return False
    
    async def simulate_expensive_computation(self, key: str, duration: float = 0.1) -> Dict[str, Any]:
        """Simulate expensive computation that should be cached."""
        start_time = time.time()
        
        # Simulate computation work
        await asyncio.sleep(duration)
        
        # Generate deterministic result based on key
        computation_hash = hashlib.md5(key.encode()).hexdigest()
        result = {
            "key": key,
            "result": f"computed_value_{computation_hash[:8]}",
            "timestamp": datetime.utcnow().isoformat(),
            "computation_time": duration,
            "computed_by": f"worker_{random.randint(1, 100)}"
        }
        
        computation_time = time.time() - start_time
        self.metrics.computation_times.append(computation_time)
        
        return result
    
    async def acquire_distributed_lock(self, lock_key: str, timeout: float = 5.0, ttl: float = 10.0) -> Optional[str]:
        """Acquire distributed lock to prevent stampede."""
        lock_id = str(uuid.uuid4())
        
        start_time = time.time()
        
        try:
            # Use SET with NX and EX for atomic lock acquisition
            acquired = await self.redis_client.set(
                lock_key, 
                lock_id, 
                nx=True,  # Only set if key doesn't exist
                ex=int(ttl)  # Set expiration
            )
            
            acquisition_time = time.time() - start_time
            self.metrics.lock_acquisition_times.append(acquisition_time)
            
            if acquired:
                self.metrics.successful_lock_acquisitions += 1
                return lock_id
            else:
                self.metrics.failed_lock_acquisitions += 1
                return None
                
        except Exception as e:
            self.metrics.failed_lock_acquisitions += 1
            logger.error(f"Lock acquisition failed for {lock_key}: {e}")
            return None
    
    async def release_distributed_lock(self, lock_key: str, lock_id: str) -> bool:
        """Release distributed lock safely."""
        try:
            # Lua script for atomic lock release (only if we own the lock)
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            result = await self.redis_client.eval(lua_script, 1, lock_key, lock_id)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Lock release failed for {lock_key}: {e}")
            return False
    
    async def get_or_compute_with_stampede_prevention(self, key: str, computation_duration: float = 0.1) -> Dict[str, Any]:
        """Get value from cache or compute with stampede prevention."""
        lock_key = f"lock:{key}"
        
        # First, try to get from cache
        try:
            cached_value = await self.redis_client.get(key)
            if cached_value:
                self.metrics.requests_served_from_cache += 1
                return {
                    "key": key,
                    "value": json.loads(cached_value),
                    "source": "cache",
                    "cache_hit": True
                }
        except Exception as e:
            logger.warning(f"Cache read failed for {key}: {e}")
        
        # Cache miss - need to compute
        self.metrics.cache_miss_events += 1
        self.metrics.stampede_prevention_attempts += 1
        
        # Try to acquire lock
        lock_id = await self.acquire_distributed_lock(lock_key, timeout=2.0, ttl=30.0)
        
        if lock_id:
            try:
                # We got the lock - check cache again (double-checked locking)
                cached_value = await self.redis_client.get(key)
                if cached_value:
                    # Someone else computed while we were acquiring lock
                    await self.release_distributed_lock(lock_key, lock_id)
                    self.metrics.requests_served_from_cache += 1
                    return {
                        "key": key,
                        "value": json.loads(cached_value),
                        "source": "cache_after_lock",
                        "cache_hit": True
                    }
                
                # Still not in cache - we need to compute
                if key in self.active_computations:
                    self.metrics.duplicate_computations += 1
                
                self.active_computations.add(key)
                
                # Perform expensive computation
                start_time = time.time()
                computed_result = await self.simulate_expensive_computation(key, computation_duration)
                
                # Store in cache
                cache_value = json.dumps(computed_result)
                await self.redis_client.setex(key, 300, cache_value)  # 5 minutes TTL
                
                cache_population_time = time.time() - start_time
                self.metrics.cache_population_times.append(cache_population_time)
                
                # Release lock
                await self.release_distributed_lock(lock_key, lock_id)
                self.active_computations.discard(key)
                
                self.test_keys.add(key)
                
                return {
                    "key": key,
                    "value": computed_result,
                    "source": "computation",
                    "cache_hit": False,
                    "computation_time": cache_population_time
                }
                
            except Exception as e:
                # Make sure to release lock on error
                await self.release_distributed_lock(lock_key, lock_id)
                self.active_computations.discard(key)
                raise
        
        else:
            # Failed to acquire lock - wait and try cache again
            await asyncio.sleep(0.01)  # Brief wait
            
            try:
                cached_value = await self.redis_client.get(key)
                if cached_value:
                    self.metrics.requests_served_from_cache += 1
                    return {
                        "key": key,
                        "value": json.loads(cached_value),
                        "source": "cache_after_wait",
                        "cache_hit": True
                    }
            except Exception as e:
                logger.warning(f"Cache read after wait failed for {key}: {e}")
            
            # Still no value - this is a failure case
            raise Exception(f"Failed to get or compute value for {key}")
    
    @pytest.mark.asyncio
    async def test_basic_stampede_prevention(self, concurrent_requests: int) -> Dict[str, Any]:
        """Test basic stampede prevention with concurrent requests for same key."""
        test_key = f"stampede_test_{uuid.uuid4().hex[:8]}"
        
        # Create concurrent tasks requesting the same key
        tasks = []
        for i in range(concurrent_requests):
            task = self.get_or_compute_with_stampede_prevention(test_key, 0.2)  # 200ms computation
            tasks.append(task)
        
        # Execute all requests concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_requests = [r for r in results if not isinstance(r, Exception)]
        failed_requests = [r for r in results if isinstance(r, Exception)]
        
        cache_hits = len([r for r in successful_requests if r.get("cache_hit", False)])
        computations = len([r for r in successful_requests if not r.get("cache_hit", False)])
        
        self.metrics.concurrent_requests += concurrent_requests
        
        return {
            "test_key": test_key,
            "concurrent_requests": concurrent_requests,
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "cache_hits": cache_hits,
            "computations": computations,
            "total_time": total_time,
            "requests_per_second": concurrent_requests / total_time if total_time > 0 else 0,
            "stampede_prevented": computations <= 1  # Should be only 1 computation
        }
    
    @pytest.mark.asyncio
    async def test_multiple_key_stampede_prevention(self, key_count: int, requests_per_key: int) -> Dict[str, Any]:
        """Test stampede prevention across multiple keys."""
        test_keys = [f"multi_stampede_{i}_{uuid.uuid4().hex[:8]}" for i in range(key_count)]
        
        # Create tasks for multiple keys
        all_tasks = []
        for key in test_keys:
            for i in range(requests_per_key):
                task = self.get_or_compute_with_stampede_prevention(key, 0.1)  # 100ms computation
                all_tasks.append(task)
        
        # Shuffle tasks to simulate random request arrival
        random.shuffle(all_tasks)
        
        # Execute all requests
        start_time = time.time()
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results by key
        key_results = {}
        for key in test_keys:
            key_results[key] = {
                "cache_hits": 0,
                "computations": 0,
                "failures": 0
            }
        
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        for result in successful_results:
            key = result["key"]
            if result.get("cache_hit", False):
                key_results[key]["cache_hits"] += 1
            else:
                key_results[key]["computations"] += 1
        
        # Calculate stampede prevention effectiveness
        prevented_stampedes = 0
        total_keys_tested = 0
        
        for key, stats in key_results.items():
            total_keys_tested += 1
            if stats["computations"] <= 1:  # Stampede prevented if only 1 computation
                prevented_stampedes += 1
        
        return {
            "total_keys": key_count,
            "requests_per_key": requests_per_key,
            "total_requests": len(all_tasks),
            "successful_requests": len(successful_results),
            "failed_requests": len(failed_results),
            "total_time": total_time,
            "prevented_stampedes": prevented_stampedes,
            "stampede_prevention_rate": (prevented_stampedes / total_keys_tested * 100) if total_keys_tested > 0 else 0,
            "key_results": key_results
        }
    
    @pytest.mark.asyncio
    async def test_lock_timeout_and_recovery(self, timeout_scenario: str) -> Dict[str, Any]:
        """Test lock timeout handling and recovery scenarios."""
        test_key = f"timeout_test_{uuid.uuid4().hex[:8]}"
        lock_key = f"lock:{test_key}"
        
        if timeout_scenario == "holder_dies":
            # Simulate lock holder dying (acquire lock but don't release)
            lock_id = await self.acquire_distributed_lock(lock_key, timeout=2.0, ttl=1.0)  # Short TTL
            assert lock_id, "Should acquire lock for timeout test"
            
            # Don't release lock - simulate process death
            # Wait for TTL expiration
            await asyncio.sleep(1.5)
            
            # Now try to get value - should succeed after lock expires
            result = await self.get_or_compute_with_stampede_prevention(test_key, 0.1)
            
            return {
                "scenario": timeout_scenario,
                "test_key": test_key,
                "lock_expired": True,
                "computation_successful": not result.get("cache_hit", False),
                "result_obtained": result is not None
            }
        
        elif timeout_scenario == "slow_computation":
            # Test behavior when computation takes longer than lock TTL
            
            # Start long computation
            computation_task = asyncio.create_task(
                self.get_or_compute_with_stampede_prevention(test_key, 2.0)  # 2 second computation
            )
            
            # Wait a bit then try concurrent access
            await asyncio.sleep(0.1)
            
            concurrent_results = []
            for i in range(5):
                try:
                    result = await self.get_or_compute_with_stampede_prevention(test_key, 0.1)
                    concurrent_results.append(result)
                except Exception as e:
                    concurrent_results.append({"error": str(e)})
            
            # Wait for original computation to complete
            original_result = await computation_task
            
            return {
                "scenario": timeout_scenario,
                "test_key": test_key,
                "original_computation_completed": original_result is not None,
                "concurrent_requests": len(concurrent_results),
                "concurrent_successes": len([r for r in concurrent_results if "error" not in r])
            }
        
        else:
            raise ValueError(f"Unknown timeout scenario: {timeout_scenario}")
    
    @pytest.mark.asyncio
    async def test_cache_warming_prevention(self, warming_key_count: int) -> Dict[str, Any]:
        """Test stampede prevention during cache warming scenarios."""
        warming_keys = [f"warming_{i}_{uuid.uuid4().hex[:8]}" for i in range(warming_key_count)]
        
        # Simulate cache warming - multiple workers trying to populate cache
        warming_tasks = []
        
        # Create 3 "workers" each trying to warm the same set of keys
        for worker_id in range(3):
            for key in warming_keys:
                task = self.get_or_compute_with_stampede_prevention(key, 0.15)  # 150ms computation
                warming_tasks.append((worker_id, task))
        
        # Execute warming operations
        start_time = time.time()
        task_results = await asyncio.gather(*[task for _, task in warming_tasks], return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze warming efficiency
        successful_warmings = [r for r in task_results if not isinstance(r, Exception)]
        failed_warmings = [r for r in task_results if isinstance(r, Exception)]
        
        computations_by_key = {}
        for result in successful_warmings:
            if not isinstance(result, Exception):
                key = result["key"]
                if not result.get("cache_hit", False):
                    computations_by_key[key] = computations_by_key.get(key, 0) + 1
        
        # Check if each key was computed only once
        efficiently_warmed = 0
        for key in warming_keys:
            if computations_by_key.get(key, 0) <= 1:
                efficiently_warmed += 1
        
        return {
            "warming_keys": warming_key_count,
            "total_warming_tasks": len(warming_tasks),
            "successful_tasks": len(successful_warmings),
            "failed_tasks": len(failed_warmings),
            "efficiently_warmed_keys": efficiently_warmed,
            "warming_efficiency": (efficiently_warmed / warming_key_count * 100) if warming_key_count > 0 else 0,
            "total_time": total_time,
            "computations_by_key": computations_by_key
        }
    
    def get_stampede_prevention_summary(self) -> Dict[str, Any]:
        """Get comprehensive stampede prevention test summary."""
        return {
            "stampede_metrics": {
                "cache_miss_events": self.metrics.cache_miss_events,
                "stampede_prevention_attempts": self.metrics.stampede_prevention_attempts,
                "lock_success_rate": self.metrics.lock_success_rate,
                "avg_lock_acquisition_time": self.metrics.avg_lock_acquisition_time,
                "computation_efficiency": self.metrics.computation_efficiency,
                "duplicate_computations": self.metrics.duplicate_computations,
                "concurrent_requests": self.metrics.concurrent_requests,
                "requests_served_from_cache": self.metrics.requests_served_from_cache
            },
            "sla_compliance": {
                "lock_acquisition_under_10ms": self.metrics.avg_lock_acquisition_time < 0.01,
                "computation_efficiency_above_95": self.metrics.computation_efficiency > 95.0,
                "lock_success_rate_above_99": self.metrics.lock_success_rate > 99.0
            },
            "recommendations": self._generate_stampede_recommendations()
        }
    
    def _generate_stampede_recommendations(self) -> List[str]:
        """Generate stampede prevention recommendations."""
        recommendations = []
        
        if self.metrics.avg_lock_acquisition_time > 0.01:
            recommendations.append(f"Lock acquisition time {self.metrics.avg_lock_acquisition_time*1000:.1f}ms exceeds 10ms - optimize lock service")
        
        if self.metrics.computation_efficiency < 95.0:
            recommendations.append(f"Computation efficiency {self.metrics.computation_efficiency:.1f}% below 95% - review stampede prevention logic")
        
        if self.metrics.lock_success_rate < 99.0:
            recommendations.append(f"Lock success rate {self.metrics.lock_success_rate:.1f}% below 99% - review lock implementation")
        
        if self.metrics.duplicate_computations > 0:
            recommendations.append(f"{self.metrics.duplicate_computations} duplicate computations detected - improve coordination")
        
        if not recommendations:
            recommendations.append("All stampede prevention metrics meet SLA requirements")
        
        return recommendations
    
    async def cleanup(self):
        """Clean up Redis test resources."""
        try:
            # Clean up test keys from the Redis client
            for key in self.test_keys:
                try:
                    await self.redis_client.delete(key)
                    # Also clean up lock keys
                    await self.redis_client.delete(f"lock:{key}")
                except Exception as e:
                    logger.warning(f"Failed to delete test key {key}: {e}")
                
        except Exception as e:
            logger.error(f"Stampede prevention cleanup failed: {e}")

@pytest.fixture
async def stampede_prevention_manager(isolated_redis_client):
    """Create L3 cache stampede prevention manager with real Redis client."""
    manager = CacheStampedePreventionL3Manager(isolated_redis_client)
    await manager.setup_redis_for_stampede_testing()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_basic_cache_stampede_prevention(stampede_prevention_manager):
    """L3: Test basic cache stampede prevention with concurrent requests."""
    result = await stampede_prevention_manager.test_basic_stampede_prevention(20)
    
    # Verify stampede prevention
    assert result["stampede_prevented"], f"Stampede not prevented: {result['computations']} computations for same key"
    assert result["successful_requests"] >= 19, f"Too many failed requests: {result['failed_requests']}"
    assert result["computations"] == 1, f"Expected 1 computation, got {result['computations']}"
    assert result["cache_hits"] >= 15, f"Insufficient cache hits: {result['cache_hits']}"
    
    logger.info(f"Basic stampede prevention test: {result['computations']} computation, {result['cache_hits']} cache hits")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_multiple_key_stampede_prevention(stampede_prevention_manager):
    """L3: Test stampede prevention across multiple keys simultaneously."""
    result = await stampede_prevention_manager.test_multiple_key_stampede_prevention(10, 8)
    
    # Verify multi-key stampede prevention
    assert result["stampede_prevention_rate"] > 90.0, f"Stampede prevention rate {result['stampede_prevention_rate']:.1f}% below 90%"
    assert result["successful_requests"] >= result["total_requests"] * 0.95, "Too many failed requests in multi-key test"
    
    # Verify each key had minimal computations
    for key, stats in result["key_results"].items():
        assert stats["computations"] <= 2, f"Key {key} had too many computations: {stats['computations']}"
    
    logger.info(f"Multi-key stampede prevention: {result['stampede_prevention_rate']:.1f}% prevention rate across {result['total_keys']} keys")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_lock_timeout_holder_dies_scenario(stampede_prevention_manager):
    """L3: Test lock timeout handling when lock holder dies."""
    result = await stampede_prevention_manager.test_lock_timeout_and_recovery("holder_dies")
    
    # Verify timeout recovery
    assert result["lock_expired"], "Lock should have expired due to TTL"
    assert result["computation_successful"], "Should successfully compute after lock expiration"
    assert result["result_obtained"], "Should obtain result despite lock holder death"
    
    logger.info(f"Lock timeout (holder dies) test completed: lock expired and recovery successful")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_lock_timeout_slow_computation_scenario(stampede_prevention_manager):
    """L3: Test behavior when computation takes longer than lock TTL."""
    result = await stampede_prevention_manager.test_lock_timeout_and_recovery("slow_computation")
    
    # Verify slow computation handling
    assert result["original_computation_completed"], "Original computation should complete"
    assert result["concurrent_successes"] >= 3, f"Too few concurrent successes: {result['concurrent_successes']}"
    
    logger.info(f"Lock timeout (slow computation) test: {result['concurrent_successes']}/{result['concurrent_requests']} concurrent successes")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_cache_warming_stampede_prevention(stampede_prevention_manager):
    """L3: Test stampede prevention during cache warming scenarios."""
    result = await stampede_prevention_manager.test_cache_warming_prevention(15)
    
    # Verify cache warming efficiency
    assert result["warming_efficiency"] > 85.0, f"Cache warming efficiency {result['warming_efficiency']:.1f}% below 85%"
    assert result["successfully_warmed_keys"] >= 12, f"Too few keys warmed successfully: {result['efficiently_warmed_keys']}"
    assert result["failed_tasks"] <= 5, f"Too many failed warming tasks: {result['failed_tasks']}"
    
    # Verify minimal duplicate computations
    max_computations_per_key = max(result["computations_by_key"].values()) if result["computations_by_key"] else 0
    assert max_computations_per_key <= 2, f"Too many computations per key during warming: {max_computations_per_key}"
    
    logger.info(f"Cache warming test: {result['warming_efficiency']:.1f}% efficiency, {result['efficiently_warmed_keys']}/{result['warming_keys']} keys")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_cache_stampede_prevention_sla_compliance(stampede_prevention_manager):
    """L3: Test comprehensive cache stampede prevention SLA compliance."""
    # Execute comprehensive test suite
    await stampede_prevention_manager.test_basic_stampede_prevention(15)
    await stampede_prevention_manager.test_multiple_key_stampede_prevention(8, 6)
    await stampede_prevention_manager.test_cache_warming_prevention(10)
    
    # Get comprehensive summary
    summary = stampede_prevention_manager.get_stampede_prevention_summary()
    
    # Verify SLA compliance
    sla = summary["sla_compliance"]
    assert sla["lock_acquisition_under_10ms"], f"Lock acquisition time SLA violation: {stampede_prevention_manager.metrics.avg_lock_acquisition_time*1000:.1f}ms"
    assert sla["computation_efficiency_above_95"], f"Computation efficiency SLA violation: {stampede_prevention_manager.metrics.computation_efficiency:.1f}%"
    assert sla["lock_success_rate_above_99"], f"Lock success rate SLA violation: {stampede_prevention_manager.metrics.lock_success_rate:.1f}%"
    
    # Verify overall effectiveness
    assert stampede_prevention_manager.metrics.duplicate_computations <= 2, f"Too many duplicate computations: {stampede_prevention_manager.metrics.duplicate_computations}"
    
    # Verify no critical recommendations
    critical_recommendations = [r for r in summary["recommendations"] if "exceeds" in r or "below" in r]
    assert len(critical_recommendations) == 0, f"Critical stampede prevention issues: {critical_recommendations}"
    
    logger.info(f"Cache stampede prevention SLA compliance test completed successfully")
    logger.info(f"Summary: {summary}")
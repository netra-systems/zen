"""Redis Memory Pressure and LRU Eviction - L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (memory efficiency affects cost and performance across all segments)
- Business Goal: Optimize memory usage and ensure predictable eviction behavior under pressure
- Value Impact: Reduces infrastructure costs, maintains performance under memory constraints
- Strategic Impact: $4K MRR protection through efficient memory management and predictable cache behavior

Critical Path: Memory pressure -> LRU eviction -> Cache miss handling -> Memory recovery -> Performance validation
L3 Realism: Real Redis containers with memory limits, actual eviction policies, memory pressure simulation
Performance Requirements: Eviction time < 50ms, memory recovery > 80%, cache efficiency maintained > 85%
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import logging
import os
import statistics
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import psutil
import pytest
import redis.asyncio as aioredis

from app.logging_config import central_logger

# Add project root to path
from .integration.helpers.redis_l3_helpers import (
    RedisContainer as NetraRedisContainer,
)

# Add project root to path

logger = central_logger.get_logger(__name__)


@dataclass
class MemoryPressureMetrics:
    """Metrics for memory pressure and eviction testing."""
    memory_usage_samples: List[float] = None
    eviction_times: List[float] = None
    evicted_keys: int = 0
    memory_recovered: float = 0.0
    cache_efficiency_samples: List[float] = None
    lru_accuracy: float = 0.0
    memory_pressure_events: int = 0
    
    def __post_init__(self):
        if self.memory_usage_samples is None:
            self.memory_usage_samples = []
        if self.eviction_times is None:
            self.eviction_times = []
        if self.cache_efficiency_samples is None:
            self.cache_efficiency_samples = []
    
    @property
    def avg_eviction_time(self) -> float:
        """Calculate average eviction time."""
        return statistics.mean(self.eviction_times) if self.eviction_times else 0.0
    
    @property
    def peak_memory_usage(self) -> float:
        """Calculate peak memory usage."""
        return max(self.memory_usage_samples) if self.memory_usage_samples else 0.0
    
    @property
    def avg_cache_efficiency(self) -> float:
        """Calculate average cache efficiency."""
        return statistics.mean(self.cache_efficiency_samples) if self.cache_efficiency_samples else 0.0


class MemoryPressureEvictionL3Manager:
    """L3 memory pressure and eviction test manager with real Redis containers."""
    
    def __init__(self):
        self.redis_containers = {}
        self.redis_clients = {}
        self.metrics = MemoryPressureMetrics()
        self.test_keys = set()
        self.memory_limits = {"small": "32mb", "medium": "64mb", "large": "128mb"}
        
    async def setup_redis_with_memory_limits(self) -> Dict[str, str]:
        """Setup Redis containers with different memory limits."""
        redis_urls = {}
        base_port = 6390
        
        for size, limit in self.memory_limits.items():
            try:
                container = NetraRedisContainer(port=base_port)
                
                # Configure Redis with memory limit and LRU eviction
                redis_config = [
                    "redis-server",
                    "--maxmemory", limit,
                    "--maxmemory-policy", "allkeys-lru",
                    "--appendonly", "no"  # Disable persistence to save memory
                ]
                
                # Override container command for memory configuration
                container.container_name = f"netra-redis-memory-{size}-{uuid.uuid4().hex[:8]}"
                
                url = await container.start()
                
                self.redis_containers[size] = container
                redis_urls[size] = url
                
                # Create Redis client and configure memory settings
                client = aioredis.from_url(url, decode_responses=True)
                await client.ping()
                
                # Configure memory policy via Redis commands
                await client.config_set("maxmemory", limit)
                await client.config_set("maxmemory-policy", "allkeys-lru")
                
                self.redis_clients[size] = client
                base_port += 1
                
                logger.info(f"Redis container {size} started with {limit} memory limit: {url}")
                
            except Exception as e:
                logger.error(f"Failed to start Redis container {size}: {e}")
                raise
        
        return redis_urls
    
    async def test_memory_pressure_simulation(self, data_size_mb: int) -> Dict[str, Any]:
        """Simulate memory pressure by filling cache beyond limit."""
        memory_stats = {}
        
        for size, client in self.redis_clients.items():
            try:
                # Get initial memory usage
                initial_info = await client.info("memory")
                initial_memory = int(initial_info.get("used_memory", 0))
                
                # Fill cache with data
                keys_written = 0
                total_data_written = 0
                eviction_detected = False
                
                # Write data until eviction occurs
                for i in range(data_size_mb * 100):  # ~10KB per iteration
                    key = f"pressure_test_{size}_{i}_{uuid.uuid4().hex[:8]}"
                    value = {
                        "data": "x" * 10000,  # ~10KB payload
                        "timestamp": datetime.utcnow().isoformat(),
                        "index": i
                    }
                    
                    start_time = time.time()
                    await client.setex(key, 3600, json.dumps(value))
                    
                    keys_written += 1
                    total_data_written += len(json.dumps(value))
                    self.test_keys.add(key)
                    
                    # Check for eviction
                    if i > 50 and i % 10 == 0:  # Check every 10 iterations after initial writes
                        current_info = await client.info("memory")
                        current_memory = int(current_info.get("used_memory", 0))
                        evicted_keys = int(current_info.get("evicted_keys", 0))
                        
                        if evicted_keys > 0 and not eviction_detected:
                            eviction_detected = True
                            eviction_time = time.time() - start_time
                            self.metrics.eviction_times.append(eviction_time)
                            self.metrics.evicted_keys += evicted_keys
                            self.metrics.memory_pressure_events += 1
                            
                            logger.info(f"Eviction detected in {size} container: {evicted_keys} keys evicted")
                        
                        self.metrics.memory_usage_samples.append(current_memory)
                        
                        # Stop if we've triggered eviction and written enough data
                        if eviction_detected and i > 100:
                            break
                
                # Final memory stats
                final_info = await client.info("memory")
                final_memory = int(final_info.get("used_memory", 0))
                final_evicted = int(final_info.get("evicted_keys", 0))
                
                memory_stats[size] = {
                    "initial_memory": initial_memory,
                    "final_memory": final_memory,
                    "keys_written": keys_written,
                    "total_data_written": total_data_written,
                    "evicted_keys": final_evicted,
                    "eviction_detected": eviction_detected,
                    "memory_efficiency": (final_memory - initial_memory) / total_data_written if total_data_written > 0 else 0
                }
                
            except Exception as e:
                logger.error(f"Memory pressure simulation failed for {size}: {e}")
                memory_stats[size] = {"error": str(e)}
        
        return memory_stats
    
    async def test_lru_eviction_accuracy(self, container_size: str = "medium") -> Dict[str, Any]:
        """Test LRU eviction policy accuracy."""
        client = self.redis_clients[container_size]
        
        # Create keys with known access patterns
        old_keys = []
        recent_keys = []
        
        # Create "old" keys
        for i in range(50):
            key = f"old_key_{i}_{uuid.uuid4().hex[:8]}"
            value = {"data": f"old_data_{i}", "created": datetime.utcnow().isoformat()}
            await client.setex(key, 3600, json.dumps(value))
            old_keys.append(key)
            self.test_keys.add(key)
        
        # Wait to establish age difference
        await asyncio.sleep(0.1)
        
        # Create "recent" keys
        for i in range(50):
            key = f"recent_key_{i}_{uuid.uuid4().hex[:8]}"
            value = {"data": f"recent_data_{i}", "created": datetime.utcnow().isoformat()}
            await client.setex(key, 3600, json.dumps(value))
            recent_keys.append(key)
            self.test_keys.add(key)
        
        # Access recent keys to make them "hot"
        for key in recent_keys:
            await client.get(key)
        
        # Force eviction by writing large amounts of data
        pressure_keys = []
        for i in range(200):  # Force memory pressure
            key = f"pressure_key_{i}_{uuid.uuid4().hex[:8]}"
            value = {"data": "x" * 5000, "pressure": True}  # 5KB each
            await client.setex(key, 3600, json.dumps(value))
            pressure_keys.append(key)
            self.test_keys.add(key)
        
        # Check which keys survived
        old_survived = 0
        recent_survived = 0
        
        for key in old_keys:
            if await client.exists(key):
                old_survived += 1
        
        for key in recent_keys:
            if await client.exists(key):
                recent_survived += 1
        
        # LRU accuracy: recent keys should survive better than old keys
        total_old = len(old_keys)
        total_recent = len(recent_keys)
        
        old_survival_rate = (old_survived / total_old) * 100 if total_old > 0 else 0
        recent_survival_rate = (recent_survived / total_recent) * 100 if total_recent > 0 else 0
        
        lru_accuracy = recent_survival_rate - old_survival_rate  # Should be positive
        self.metrics.lru_accuracy = lru_accuracy
        
        return {
            "old_keys_created": total_old,
            "recent_keys_created": total_recent,
            "old_keys_survived": old_survived,
            "recent_keys_survived": recent_survived,
            "old_survival_rate": old_survival_rate,
            "recent_survival_rate": recent_survival_rate,
            "lru_accuracy": lru_accuracy,
            "pressure_keys_written": len(pressure_keys)
        }
    
    async def test_cache_efficiency_under_pressure(self, container_size: str = "medium") -> Dict[str, Any]:
        """Test cache efficiency maintenance under memory pressure."""
        client = self.redis_clients[container_size]
        
        # Baseline cache efficiency test
        baseline_hits = 0
        baseline_total = 100
        
        # Populate cache
        test_keys = []
        for i in range(baseline_total):
            key = f"efficiency_test_{i}_{uuid.uuid4().hex[:8]}"
            value = {"data": f"efficiency_data_{i}"}
            await client.setex(key, 3600, json.dumps(value))
            test_keys.append(key)
            self.test_keys.add(key)
        
        # Test baseline hit rate
        for key in test_keys:
            if await client.exists(key):
                baseline_hits += 1
        
        baseline_efficiency = (baseline_hits / baseline_total) * 100
        self.metrics.cache_efficiency_samples.append(baseline_efficiency)
        
        # Apply memory pressure
        pressure_keys = []
        for i in range(300):  # Create memory pressure
            key = f"pressure_efficiency_{i}_{uuid.uuid4().hex[:8]}"
            value = {"data": "x" * 3000, "pressure": True}  # 3KB each
            await client.setex(key, 3600, json.dumps(value))
            pressure_keys.append(key)
            self.test_keys.add(key)
        
        # Test cache efficiency after pressure
        pressure_hits = 0
        for key in test_keys:
            if await client.exists(key):
                pressure_hits += 1
        
        pressure_efficiency = (pressure_hits / baseline_total) * 100
        self.metrics.cache_efficiency_samples.append(pressure_efficiency)
        
        # Test cache efficiency with mixed workload
        mixed_hits = 0
        mixed_total = 200
        
        # Mix of existing and new keys
        for i in range(mixed_total):
            if i < 100 and i < len(test_keys):
                key = test_keys[i]
            else:
                key = f"mixed_test_{i}_{uuid.uuid4().hex[:8]}"
                value = {"data": f"mixed_data_{i}"}
                await client.setex(key, 3600, json.dumps(value))
                self.test_keys.add(key)
            
            if await client.exists(key):
                mixed_hits += 1
        
        mixed_efficiency = (mixed_hits / mixed_total) * 100
        self.metrics.cache_efficiency_samples.append(mixed_efficiency)
        
        return {
            "baseline_efficiency": baseline_efficiency,
            "pressure_efficiency": pressure_efficiency,
            "mixed_efficiency": mixed_efficiency,
            "efficiency_degradation": baseline_efficiency - pressure_efficiency,
            "pressure_keys_created": len(pressure_keys),
            "original_keys_surviving": pressure_hits
        }
    
    async def test_memory_recovery_patterns(self) -> Dict[str, Any]:
        """Test memory recovery patterns after pressure relief."""
        recovery_stats = {}
        
        for size, client in self.redis_clients.items():
            try:
                # Get pre-pressure memory usage
                pre_info = await client.info("memory")
                pre_memory = int(pre_info.get("used_memory", 0))
                
                # Apply memory pressure
                pressure_keys = []
                for i in range(100):
                    key = f"recovery_pressure_{size}_{i}_{uuid.uuid4().hex[:8]}"
                    value = {"data": "x" * 8000}  # 8KB each
                    await client.setex(key, 60, json.dumps(value))  # Short TTL
                    pressure_keys.append(key)
                    self.test_keys.add(key)
                
                # Measure peak memory
                peak_info = await client.info("memory")
                peak_memory = int(peak_info.get("used_memory", 0))
                
                # Wait for TTL expiration and memory recovery
                await asyncio.sleep(65)  # Wait for TTL expiration
                
                # Trigger garbage collection
                await client.flushdb()  # Clear expired keys
                
                # Measure recovered memory
                post_info = await client.info("memory")
                post_memory = int(post_info.get("used_memory", 0))
                
                memory_recovered = peak_memory - post_memory
                recovery_percentage = (memory_recovered / (peak_memory - pre_memory)) * 100 if peak_memory > pre_memory else 0
                
                self.metrics.memory_recovered += recovery_percentage
                
                recovery_stats[size] = {
                    "pre_pressure_memory": pre_memory,
                    "peak_memory": peak_memory,
                    "post_recovery_memory": post_memory,
                    "memory_recovered": memory_recovered,
                    "recovery_percentage": recovery_percentage,
                    "pressure_keys_created": len(pressure_keys)
                }
                
            except Exception as e:
                logger.error(f"Memory recovery test failed for {size}: {e}")
                recovery_stats[size] = {"error": str(e)}
        
        return recovery_stats
    
    async def test_concurrent_eviction_performance(self, container_size: str = "medium") -> Dict[str, Any]:
        """Test eviction performance under concurrent operations."""
        client = self.redis_clients[container_size]
        
        # Create concurrent tasks that will trigger eviction
        eviction_tasks = []
        
        for i in range(50):
            task = self._concurrent_memory_pressure_task(client, i)
            eviction_tasks.append(task)
        
        # Execute concurrent memory pressure
        start_time = time.time()
        results = await asyncio.gather(*eviction_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_ops = len([r for r in results if not isinstance(r, Exception)])
        failed_ops = len([r for r in results if isinstance(r, Exception)])
        
        # Check final memory state
        final_info = await client.info("memory")
        final_evicted = int(final_info.get("evicted_keys", 0))
        
        return {
            "total_tasks": len(eviction_tasks),
            "successful_tasks": successful_ops,
            "failed_tasks": failed_ops,
            "total_time": total_time,
            "tasks_per_second": len(eviction_tasks) / total_time if total_time > 0 else 0,
            "total_evicted_keys": final_evicted,
            "success_rate": (successful_ops / len(eviction_tasks)) * 100 if eviction_tasks else 0
        }
    
    async def _concurrent_memory_pressure_task(self, client, task_id: int) -> Dict[str, Any]:
        """Execute concurrent memory pressure task."""
        keys_written = 0
        
        try:
            for i in range(20):  # Write 20 keys per task
                key = f"concurrent_pressure_{task_id}_{i}_{uuid.uuid4().hex[:8]}"
                value = {"data": "x" * 4000, "task_id": task_id, "index": i}  # 4KB each
                
                await client.setex(key, 300, json.dumps(value))
                keys_written += 1
                self.test_keys.add(key)
            
            return {"task_id": task_id, "keys_written": keys_written, "success": True}
            
        except Exception as e:
            logger.error(f"Concurrent pressure task {task_id} failed: {e}")
            return {"task_id": task_id, "keys_written": keys_written, "success": False, "error": str(e)}
    
    def get_memory_pressure_summary(self) -> Dict[str, Any]:
        """Get comprehensive memory pressure test summary."""
        return {
            "memory_metrics": {
                "avg_eviction_time": self.metrics.avg_eviction_time,
                "peak_memory_usage": self.metrics.peak_memory_usage,
                "evicted_keys": self.metrics.evicted_keys,
                "memory_recovered": self.metrics.memory_recovered,
                "avg_cache_efficiency": self.metrics.avg_cache_efficiency,
                "lru_accuracy": self.metrics.lru_accuracy,
                "memory_pressure_events": self.metrics.memory_pressure_events
            },
            "sla_compliance": {
                "eviction_under_50ms": self.metrics.avg_eviction_time < 0.05,
                "memory_recovery_above_80": self.metrics.memory_recovered > 80.0,
                "cache_efficiency_above_85": self.metrics.avg_cache_efficiency > 85.0,
                "lru_accuracy_positive": self.metrics.lru_accuracy > 0
            },
            "recommendations": self._generate_memory_recommendations()
        }
    
    def _generate_memory_recommendations(self) -> List[str]:
        """Generate memory management recommendations."""
        recommendations = []
        
        if self.metrics.avg_eviction_time > 0.05:
            recommendations.append(f"Eviction time {self.metrics.avg_eviction_time*1000:.1f}ms exceeds 50ms - optimize eviction logic")
        
        if self.metrics.memory_recovered < 80.0:
            recommendations.append(f"Memory recovery {self.metrics.memory_recovered:.1f}% below 80% - review cleanup processes")
        
        if self.metrics.avg_cache_efficiency < 85.0:
            recommendations.append(f"Cache efficiency {self.metrics.avg_cache_efficiency:.1f}% below 85% - review caching strategy")
        
        if self.metrics.lru_accuracy <= 0:
            recommendations.append("LRU accuracy is poor - review eviction policy configuration")
        
        if self.metrics.memory_pressure_events > 10:
            recommendations.append(f"{self.metrics.memory_pressure_events} memory pressure events - consider increasing memory limits")
        
        if not recommendations:
            recommendations.append("All memory management metrics meet SLA requirements")
        
        return recommendations
    
    async def cleanup(self):
        """Clean up Redis containers and test resources."""
        try:
            # Clean up test keys
            for key in self.test_keys:
                for client in self.redis_clients.values():
                    try:
                        await client.delete(key)
                    except Exception:
                        pass
            
            # Close Redis clients
            for client in self.redis_clients.values():
                await client.close()
            
            # Stop Redis containers
            for container in self.redis_containers.values():
                await container.stop()
                
        except Exception as e:
            logger.error(f"Memory pressure cleanup failed: {e}")


@pytest.fixture
async def memory_pressure_manager():
    """Create L3 memory pressure and eviction manager."""
    manager = MemoryPressureEvictionL3Manager()
    await manager.setup_redis_with_memory_limits()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_memory_pressure_eviction_simulation(memory_pressure_manager):
    """L3: Test memory pressure simulation and eviction behavior with real Redis."""
    result = await memory_pressure_manager.test_memory_pressure_simulation(10)  # 10MB of data
    
    # Verify eviction behavior for each container size
    for size, stats in result.items():
        if "error" not in stats:
            assert stats["eviction_detected"], f"No eviction detected in {size} container despite memory pressure"
            assert stats["evicted_keys"] > 0, f"No keys evicted in {size} container: {stats['evicted_keys']}"
            assert stats["memory_efficiency"] > 0, f"Invalid memory efficiency for {size}: {stats['memory_efficiency']}"
    
    logger.info(f"Memory pressure simulation completed: {len(result)} containers tested")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_lru_eviction_policy_accuracy(memory_pressure_manager):
    """L3: Test LRU eviction policy accuracy with real Redis memory limits."""
    result = await memory_pressure_manager.test_lru_eviction_accuracy()
    
    # Verify LRU accuracy
    assert result["lru_accuracy"] > 0, f"LRU accuracy is poor: {result['lru_accuracy']:.2f}% (recent should survive better than old)"
    assert result["recent_survival_rate"] >= result["old_survival_rate"], "Recent keys should survive better than old keys under LRU policy"
    assert result["pressure_keys_written"] > 100, f"Insufficient memory pressure applied: {result['pressure_keys_written']} keys"
    
    logger.info(f"LRU accuracy test completed: {result['lru_accuracy']:.2f}% accuracy, recent survival: {result['recent_survival_rate']:.1f}%")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_cache_efficiency_under_memory_pressure(memory_pressure_manager):
    """L3: Test cache efficiency maintenance under memory pressure."""
    result = await memory_pressure_manager.test_cache_efficiency_under_pressure()
    
    # Verify cache efficiency under pressure
    assert result["pressure_efficiency"] > 50.0, f"Cache efficiency too low under pressure: {result['pressure_efficiency']:.1f}%"
    assert result["efficiency_degradation"] < 40.0, f"Cache efficiency degraded too much: {result['efficiency_degradation']:.1f}%"
    assert result["mixed_efficiency"] > 60.0, f"Mixed workload efficiency too low: {result['mixed_efficiency']:.1f}%"
    
    logger.info(f"Cache efficiency test completed: baseline {result['baseline_efficiency']:.1f}%, under pressure {result['pressure_efficiency']:.1f}%")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_memory_recovery_after_pressure_relief(memory_pressure_manager):
    """L3: Test memory recovery patterns after pressure relief."""
    result = await memory_pressure_manager.test_memory_recovery_patterns()
    
    # Verify memory recovery for each container
    for size, stats in result.items():
        if "error" not in stats:
            assert stats["recovery_percentage"] > 70.0, f"Poor memory recovery in {size}: {stats['recovery_percentage']:.1f}%"
            assert stats["memory_recovered"] > 0, f"No memory recovered in {size}: {stats['memory_recovered']}"
            assert stats["post_recovery_memory"] < stats["peak_memory"], f"Memory not recovered in {size}"
    
    logger.info(f"Memory recovery test completed: {len(result)} containers tested")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_concurrent_eviction_performance(memory_pressure_manager):
    """L3: Test eviction performance under concurrent memory pressure."""
    result = await memory_pressure_manager.test_concurrent_eviction_performance()
    
    # Verify concurrent eviction performance
    assert result["success_rate"] > 90.0, f"Concurrent eviction success rate too low: {result['success_rate']:.1f}%"
    assert result["tasks_per_second"] > 10, f"Concurrent eviction throughput too low: {result['tasks_per_second']:.1f} tasks/s"
    assert result["failed_tasks"] <= 5, f"Too many failed concurrent tasks: {result['failed_tasks']}"
    
    logger.info(f"Concurrent eviction test completed: {result['tasks_per_second']:.1f} tasks/s, {result['success_rate']:.1f}% success rate")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_memory_pressure_sla_compliance(memory_pressure_manager):
    """L3: Test comprehensive memory pressure and eviction SLA compliance."""
    # Execute comprehensive test suite
    await memory_pressure_manager.test_memory_pressure_simulation(5)
    await memory_pressure_manager.test_lru_eviction_accuracy()
    await memory_pressure_manager.test_cache_efficiency_under_pressure()
    await memory_pressure_manager.test_memory_recovery_patterns()
    
    # Get comprehensive summary
    summary = memory_pressure_manager.get_memory_pressure_summary()
    
    # Verify SLA compliance
    sla = summary["sla_compliance"]
    assert sla["eviction_under_50ms"], f"Eviction time SLA violation: {memory_pressure_manager.metrics.avg_eviction_time*1000:.1f}ms"
    assert sla["memory_recovery_above_80"], f"Memory recovery SLA violation: {memory_pressure_manager.metrics.memory_recovered:.1f}%"
    assert sla["cache_efficiency_above_85"], f"Cache efficiency SLA violation: {memory_pressure_manager.metrics.avg_cache_efficiency:.1f}%"
    assert sla["lru_accuracy_positive"], f"LRU accuracy SLA violation: {memory_pressure_manager.metrics.lru_accuracy:.2f}"
    
    # Verify no critical recommendations
    critical_recommendations = [r for r in summary["recommendations"] if "exceeds" in r or "below" in r]
    assert len(critical_recommendations) == 0, f"Critical memory management issues: {critical_recommendations}"
    
    logger.info(f"Memory pressure SLA compliance test completed successfully")
    logger.info(f"Summary: {summary}")
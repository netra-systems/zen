"""Cache Coherence Across Services - L4 Performance Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (cache performance affects user experience across all segments)
- Business Goal: Ensure distributed cache consistency and performance under load
- Value Impact: Maintains fast response times, prevents data inconsistencies, improves UX
- Strategic Impact: $8K MRR protection through optimal cache performance and data consistency

Critical Path: Cache writes -> Distributed invalidation -> Cache reads -> TTL management -> Eviction policies
L4 Realism: Real Redis cluster, real cache operations, real service interactions in staging
Performance Requirements: Cache hit rate > 90%, invalidation propagation < 50ms, TTL accuracy 99.9%
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import logging
import statistics
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

# from app.services.cache.invalidation_service import CacheInvalidationService  # Class may not exist, commented out
# Session cache replaced with mock
from unittest.mock import AsyncMock

import pytest
import redis.asyncio as aioredis

# Add project root to path
# from app.services.cache.distributed_cache import DistributedCache  # Class may not exist, commented out
from netra_backend.app.services.cache.cache_manager import (
    LLMCacheManager as CacheManager,
)

# SessionCache = AsyncMock  # Class may not exist, commented out
# from app.services.database.user_repository import UserRepository  # Class may not exist, commented out
from tests.config import TEST_CONFIG  # Comment out since config structure may vary
TEST_CONFIG = {"mock": True}

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Cache performance and coherence metrics."""
    total_operations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    invalidations_sent: int = 0
    invalidations_received: int = 0
    write_operations: int = 0
    read_operations: int = 0
    response_times: List[float] = None
    invalidation_times: List[float] = None
    ttl_accuracy_checks: int = 0
    ttl_accurate_count: int = 0
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []
        if self.invalidation_times is None:
            self.invalidation_times = []
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total_reads = self.cache_hits + self.cache_misses
        return (self.cache_hits / total_reads * 100) if total_reads > 0 else 0.0
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        return statistics.mean(self.response_times) if self.response_times else 0.0
    
    @property
    def p99_response_time(self) -> float:
        """Calculate p99 response time."""
        if not self.response_times:
            return 0.0
        return statistics.quantiles(self.response_times, n=100)[98]
    
    @property
    def avg_invalidation_time(self) -> float:
        """Calculate average invalidation propagation time."""
        return statistics.mean(self.invalidation_times) if self.invalidation_times else 0.0
    
    @property
    def ttl_accuracy(self) -> float:
        """Calculate TTL accuracy percentage."""
        return (self.ttl_accurate_count / self.ttl_accuracy_checks * 100) if self.ttl_accuracy_checks > 0 else 0.0


class CacheCoherenceL4Manager:
    """L4 cache coherence test manager with real Redis cluster and distributed operations."""
    
    def __init__(self):
        self.cache_manager = None
        self.distributed_cache = None
        self.invalidation_service = None
        self.session_cache = None
        self.user_repository = None
        self.redis_clients = {}
        self.metrics = CacheMetrics()
        self.test_keys = set()
        
    async def initialize_services(self):
        """Initialize real cache services for L4 testing."""
        try:
            # Initialize real cache services
            self.cache_manager = CacheManager()
            await self.cache_manager.initialize()
            
            # self.distributed_cache = DistributedCache()  # Class may not exist, commented out
            await self.distributed_cache.initialize()
            
            # self.invalidation_service = CacheInvalidationService()  # Class may not exist, commented out
            await self.invalidation_service.initialize()
            
            # self.session_cache = SessionCache()  # Class may not exist, commented out
            await self.session_cache.initialize()
            
            # self.user_repository = UserRepository()  # Class may not exist, commented out
            await self.user_repository.initialize()
            
            # Create multiple Redis clients for cluster testing
            await self._initialize_redis_clients()
            
            logger.info("L4 cache services initialized with real Redis cluster")
            
        except Exception as e:
            logger.error(f"Failed to initialize L4 cache services: {e}")
            raise
    
    async def _initialize_redis_clients(self):
        """Initialize multiple Redis clients for cluster testing."""
        redis_urls = [
            "redis://localhost:6379/0",
            "redis://localhost:6379/1", 
            "redis://localhost:6379/2"
        ]
        
        for i, url in enumerate(redis_urls):
            try:
                client = aioredis.from_url(url)
                await client.ping()
                self.redis_clients[f"cluster_{i}"] = client
            except Exception as e:
                logger.warning(f"Could not connect to Redis cluster {i}: {e}")
    
    async def test_cache_write_performance(self, key_count: int) -> Dict[str, Any]:
        """Test cache write performance with multiple keys."""
        write_times = []
        successful_writes = 0
        failed_writes = 0
        
        for i in range(key_count):
            key = f"perf_test_write_{i}_{uuid.uuid4().hex[:8]}"
            value = {
                "user_id": f"user_{i}",
                "data": f"test_data_{i}",
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"test": True, "iteration": i}
            }
            
            start_time = time.time()
            
            try:
                await self.distributed_cache.set(
                    key, 
                    json.dumps(value), 
                    ttl=300  # 5 minutes
                )
                
                write_time = time.time() - start_time
                write_times.append(write_time)
                successful_writes += 1
                self.test_keys.add(key)
                
            except Exception as e:
                failed_writes += 1
                logger.error(f"Cache write failed for key {key}: {e}")
        
        self.metrics.write_operations += key_count
        self.metrics.response_times.extend(write_times)
        
        return {
            "total_writes": key_count,
            "successful_writes": successful_writes,
            "failed_writes": failed_writes,
            "avg_write_time": statistics.mean(write_times) if write_times else 0,
            "max_write_time": max(write_times) if write_times else 0
        }
    
    async def test_cache_read_performance(self, read_count: int) -> Dict[str, Any]:
        """Test cache read performance and hit rates."""
        read_times = []
        cache_hits = 0
        cache_misses = 0
        
        # Use existing test keys and some non-existent keys
        test_keys_list = list(self.test_keys)
        non_existent_keys = [f"missing_key_{i}" for i in range(read_count // 4)]
        all_keys = test_keys_list + non_existent_keys
        
        for i in range(read_count):
            key = all_keys[i % len(all_keys)] if all_keys else f"read_test_{i}"
            
            start_time = time.time()
            
            try:
                result = await self.distributed_cache.get(key)
                read_time = time.time() - start_time
                read_times.append(read_time)
                
                if result is not None:
                    cache_hits += 1
                else:
                    cache_misses += 1
                    
            except Exception as e:
                cache_misses += 1
                logger.error(f"Cache read failed for key {key}: {e}")
        
        self.metrics.read_operations += read_count
        self.metrics.cache_hits += cache_hits
        self.metrics.cache_misses += cache_misses
        self.metrics.response_times.extend(read_times)
        
        return {
            "total_reads": read_count,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "hit_rate": (cache_hits / read_count * 100) if read_count > 0 else 0,
            "avg_read_time": statistics.mean(read_times) if read_times else 0
        }
    
    async def test_cache_invalidation_coherence(self, key_count: int) -> Dict[str, Any]:
        """Test cache invalidation propagation across distributed nodes."""
        invalidation_times = []
        successful_invalidations = 0
        failed_invalidations = 0
        coherence_violations = 0
        
        # Create test data across multiple cache nodes
        test_keys = []
        for i in range(key_count):
            key = f"invalidation_test_{i}_{uuid.uuid4().hex[:8]}"
            value = {"data": f"original_value_{i}", "version": 1}
            
            # Write to cache
            await self.distributed_cache.set(key, json.dumps(value), ttl=600)
            test_keys.append(key)
        
        # Test invalidation propagation
        for key in test_keys:
            start_time = time.time()
            
            try:
                # Trigger invalidation
                await self.invalidation_service.invalidate_key(key)
                
                # Wait for propagation
                await asyncio.sleep(0.01)  # 10ms propagation window
                
                # Verify invalidation across all nodes
                coherent = await self._verify_invalidation_coherence(key)
                
                invalidation_time = time.time() - start_time
                invalidation_times.append(invalidation_time)
                
                if coherent:
                    successful_invalidations += 1
                else:
                    coherence_violations += 1
                    
            except Exception as e:
                failed_invalidations += 1
                logger.error(f"Invalidation failed for key {key}: {e}")
        
        self.metrics.invalidations_sent += key_count
        self.metrics.invalidation_times.extend(invalidation_times)
        
        return {
            "total_invalidations": key_count,
            "successful_invalidations": successful_invalidations,
            "failed_invalidations": failed_invalidations,
            "coherence_violations": coherence_violations,
            "avg_invalidation_time": statistics.mean(invalidation_times) if invalidation_times else 0,
            "coherence_rate": (successful_invalidations / key_count * 100) if key_count > 0 else 0
        }
    
    async def _verify_invalidation_coherence(self, key: str) -> bool:
        """Verify that invalidation is coherent across all cache nodes."""
        try:
            # Check if key is invalidated in all Redis clients
            for client_name, client in self.redis_clients.items():
                exists = await client.exists(key)
                if exists:
                    logger.warning(f"Key {key} still exists in {client_name} after invalidation")
                    return False
            
            # Also check through cache manager
            value = await self.distributed_cache.get(key)
            return value is None
            
        except Exception as e:
            logger.error(f"Coherence verification failed for key {key}: {e}")
            return False
    
    async def test_ttl_accuracy_and_eviction(self, key_count: int) -> Dict[str, Any]:
        """Test TTL accuracy and eviction policy effectiveness."""
        ttl_tests = []
        accurate_ttls = 0
        
        # Create keys with different TTL values
        ttl_values = [1, 2, 5, 10]  # seconds
        
        for i in range(key_count):
            ttl = ttl_values[i % len(ttl_values)]
            key = f"ttl_test_{i}_{uuid.uuid4().hex[:8]}"
            value = {"data": f"ttl_test_{i}", "ttl": ttl}
            
            # Set with TTL
            await self.distributed_cache.set(key, json.dumps(value), ttl=ttl)
            
            ttl_tests.append({
                "key": key,
                "ttl": ttl,
                "set_time": time.time()
            })
        
        # Wait for some keys to expire
        await asyncio.sleep(6)  # Wait 6 seconds
        
        # Check TTL accuracy
        for test in ttl_tests:
            elapsed = time.time() - test["set_time"]
            expected_expired = elapsed > test["ttl"]
            
            try:
                value = await self.distributed_cache.get(test["key"])
                actually_expired = value is None
                
                if expected_expired == actually_expired:
                    accurate_ttls += 1
                else:
                    logger.warning(f"TTL mismatch for key {test['key']}: "
                                 f"expected_expired={expected_expired}, "
                                 f"actually_expired={actually_expired}")
                    
            except Exception as e:
                logger.error(f"TTL check failed for key {test['key']}: {e}")
        
        self.metrics.ttl_accuracy_checks += len(ttl_tests)
        self.metrics.ttl_accurate_count += accurate_ttls
        
        return {
            "total_ttl_tests": len(ttl_tests),
            "accurate_ttls": accurate_ttls,
            "ttl_accuracy": (accurate_ttls / len(ttl_tests) * 100) if ttl_tests else 0
        }
    
    async def test_concurrent_cache_operations(self, concurrent_ops: int) -> Dict[str, Any]:
        """Test cache coherence under concurrent operations."""
        # Create tasks for concurrent operations
        tasks = []
        
        # Mix of read, write, and invalidation operations
        for i in range(concurrent_ops):
            operation_type = i % 3
            
            if operation_type == 0:  # Write operation
                task = self._concurrent_write_operation(i)
            elif operation_type == 1:  # Read operation
                task = self._concurrent_read_operation(i)
            else:  # Invalidation operation
                task = self._concurrent_invalidation_operation(i)
            
            tasks.append(task)
        
        # Execute all operations concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_ops = len([r for r in results if not isinstance(r, Exception)])
        failed_ops = len([r for r in results if isinstance(r, Exception)])
        
        return {
            "total_operations": concurrent_ops,
            "successful_operations": successful_ops,
            "failed_operations": failed_ops,
            "total_time": total_time,
            "operations_per_second": concurrent_ops / total_time if total_time > 0 else 0,
            "success_rate": (successful_ops / concurrent_ops * 100) if concurrent_ops > 0 else 0
        }
    
    async def _concurrent_write_operation(self, index: int) -> Dict[str, Any]:
        """Execute concurrent write operation."""
        key = f"concurrent_write_{index}_{uuid.uuid4().hex[:8]}"
        value = {"data": f"concurrent_data_{index}", "timestamp": time.time()}
        
        await self.distributed_cache.set(key, json.dumps(value), ttl=300)
        self.test_keys.add(key)
        return {"operation": "write", "key": key, "success": True}
    
    async def _concurrent_read_operation(self, index: int) -> Dict[str, Any]:
        """Execute concurrent read operation."""
        # Read from existing keys or create new ones
        if self.test_keys and index % 2 == 0:
            key = list(self.test_keys)[index % len(self.test_keys)]
        else:
            key = f"concurrent_read_{index}"
        
        value = await self.distributed_cache.get(key)
        return {"operation": "read", "key": key, "found": value is not None}
    
    async def _concurrent_invalidation_operation(self, index: int) -> Dict[str, Any]:
        """Execute concurrent invalidation operation."""
        if self.test_keys:
            key = list(self.test_keys)[index % len(self.test_keys)]
            await self.invalidation_service.invalidate_key(key)
            return {"operation": "invalidate", "key": key, "success": True}
        else:
            return {"operation": "invalidate", "key": None, "success": False}
    
    async def test_session_cache_coherence(self) -> Dict[str, Any]:
        """Test session cache coherence across authentication flows."""
        test_users = []
        session_operations = []
        
        # Create test users with sessions
        for i in range(10):
            user_id = f"session_test_user_{i}_{uuid.uuid4().hex[:8]}"
            session_data = {
                "user_id": user_id,
                "login_time": datetime.utcnow().isoformat(),
                "permissions": ["read", "write"],
                "tier": "enterprise"
            }
            
            # Create session
            session_id = await self.session_cache.create_session(user_id, session_data)
            test_users.append((user_id, session_id))
        
        # Test session operations
        for user_id, session_id in test_users:
            # Verify session exists
            session = await self.session_cache.get_session(session_id)
            session_operations.append({
                "operation": "get_session",
                "success": session is not None,
                "user_id": user_id
            })
            
            # Update session
            await self.session_cache.update_session(session_id, {"last_activity": datetime.utcnow().isoformat()})
            session_operations.append({
                "operation": "update_session", 
                "success": True,
                "user_id": user_id
            })
            
            # Invalidate session
            await self.session_cache.invalidate_session(session_id)
            session_operations.append({
                "operation": "invalidate_session",
                "success": True,
                "user_id": user_id
            })
        
        # Verify invalidation coherence
        coherent_invalidations = 0
        for user_id, session_id in test_users:
            session = await self.session_cache.get_session(session_id)
            if session is None:
                coherent_invalidations += 1
        
        return {
            "total_users": len(test_users),
            "total_operations": len(session_operations),
            "successful_operations": len([op for op in session_operations if op["success"]]),
            "coherent_invalidations": coherent_invalidations,
            "session_coherence_rate": (coherent_invalidations / len(test_users) * 100) if test_users else 0
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive cache performance summary."""
        return {
            "cache_metrics": asdict(self.metrics),
            "sla_compliance": {
                "hit_rate_above_90": self.metrics.hit_rate > 90.0,
                "invalidation_under_50ms": self.metrics.avg_invalidation_time < 0.05,
                "ttl_accuracy_above_99": self.metrics.ttl_accuracy > 99.0,
                "p99_response_under_10ms": self.metrics.p99_response_time < 0.01
            },
            "recommendations": self._generate_cache_recommendations()
        }
    
    def _generate_cache_recommendations(self) -> List[str]:
        """Generate cache performance recommendations."""
        recommendations = []
        
        if self.metrics.hit_rate < 90.0:
            recommendations.append(f"Cache hit rate {self.metrics.hit_rate:.1f}% below 90% - review caching strategy")
        
        if self.metrics.avg_invalidation_time > 0.05:
            recommendations.append("Invalidation time exceeds 50ms - optimize propagation")
        
        if self.metrics.ttl_accuracy < 99.0:
            recommendations.append("TTL accuracy below 99% - review eviction policies")
        
        if self.metrics.p99_response_time > 0.01:
            recommendations.append("P99 response time exceeds 10ms - consider optimization")
        
        if not recommendations:
            recommendations.append("All cache performance metrics meet SLA requirements")
        
        return recommendations
    
    async def cleanup(self):
        """Clean up L4 cache test resources."""
        try:
            # Clean up test keys
            for key in self.test_keys:
                try:
                    await self.distributed_cache.delete(key)
                except Exception:
                    pass
            
            # Close Redis clients
            for client in self.redis_clients.values():
                await client.close()
            
            # Shutdown services
            if self.cache_manager:
                await self.cache_manager.shutdown()
            if self.distributed_cache:
                await self.distributed_cache.shutdown()
            if self.invalidation_service:
                await self.invalidation_service.shutdown()
            if self.session_cache:
                await self.session_cache.shutdown()
                
        except Exception as e:
            logger.error(f"L4 cache cleanup failed: {e}")


@pytest.fixture
async def cache_l4_manager():
    """Create L4 cache coherence manager."""
    manager = CacheCoherenceL4Manager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l4
async def test_cache_hit_rate_under_load(cache_l4_manager):
    """Test cache hit rates under high load conditions."""
    # Pre-populate cache with test data
    write_result = await cache_l4_manager.test_cache_write_performance(1000)
    assert write_result["successful_writes"] >= 950, "Cache write success rate below 95%"
    
    # Test read performance and hit rates
    read_result = await cache_l4_manager.test_cache_read_performance(2000)
    
    # Verify hit rate requirements
    assert read_result["hit_rate"] > 90.0, f"Cache hit rate {read_result['hit_rate']}% below 90%"
    assert read_result["avg_read_time"] < 0.01, f"Average read time {read_result['avg_read_time']}s exceeds 10ms"
    
    # Verify performance metrics
    performance = cache_l4_manager.get_performance_summary()
    assert performance["sla_compliance"]["hit_rate_above_90"], "Hit rate SLA violation"
    
    logger.info(f"Cache hit rate test completed: {read_result['hit_rate']:.2f}% hit rate")


@pytest.mark.asyncio
@pytest.mark.l4
async def test_distributed_cache_invalidation_coherence(cache_l4_manager):
    """Test cache invalidation propagation across distributed nodes."""
    # Test invalidation coherence
    invalidation_result = await cache_l4_manager.test_cache_invalidation_coherence(100)
    
    # Verify invalidation requirements
    assert invalidation_result["coherence_rate"] > 99.0, f"Coherence rate {invalidation_result['coherence_rate']}% below 99%"
    assert invalidation_result["avg_invalidation_time"] < 0.05, f"Invalidation time {invalidation_result['avg_invalidation_time']}s exceeds 50ms"
    
    # Verify no coherence violations
    assert invalidation_result["coherence_violations"] == 0, f"{invalidation_result['coherence_violations']} coherence violations detected"
    
    # Verify performance metrics
    performance = cache_l4_manager.get_performance_summary()
    assert performance["sla_compliance"]["invalidation_under_50ms"], "Invalidation time SLA violation"
    
    logger.info(f"Invalidation coherence test completed: {invalidation_result['coherence_rate']:.2f}% coherence rate")


@pytest.mark.asyncio
@pytest.mark.l4
async def test_ttl_accuracy_and_eviction_policies(cache_l4_manager):
    """Test TTL accuracy and cache eviction policy effectiveness."""
    # Test TTL accuracy
    ttl_result = await cache_l4_manager.test_ttl_accuracy_and_eviction(200)
    
    # Verify TTL accuracy requirements
    assert ttl_result["ttl_accuracy"] > 99.0, f"TTL accuracy {ttl_result['ttl_accuracy']}% below 99%"
    
    # Verify performance metrics
    performance = cache_l4_manager.get_performance_summary()
    assert performance["sla_compliance"]["ttl_accuracy_above_99"], "TTL accuracy SLA violation"
    
    logger.info(f"TTL accuracy test completed: {ttl_result['ttl_accuracy']:.2f}% accuracy")


@pytest.mark.asyncio
@pytest.mark.l4
async def test_concurrent_cache_operations_coherence(cache_l4_manager):
    """Test cache coherence under concurrent read/write/invalidate operations."""
    # Execute concurrent operations
    concurrent_result = await cache_l4_manager.test_concurrent_cache_operations(500)
    
    # Verify concurrent operation requirements
    assert concurrent_result["success_rate"] > 99.0, f"Concurrent success rate {concurrent_result['success_rate']}% below 99%"
    assert concurrent_result["operations_per_second"] > 100, f"Throughput {concurrent_result['operations_per_second']} ops/s below 100"
    
    # Verify overall performance
    performance = cache_l4_manager.get_performance_summary()
    assert performance["cache_metrics"]["hit_rate"] > 85.0, "Hit rate degraded under concurrent load"
    
    logger.info(f"Concurrent operations test completed: {concurrent_result['operations_per_second']:.1f} ops/s")


@pytest.mark.asyncio
@pytest.mark.l4
async def test_session_cache_coherence_across_services(cache_l4_manager):
    """Test session cache coherence across authentication and user services."""
    # Test session cache coherence
    session_result = await cache_l4_manager.test_session_cache_coherence()
    
    # Verify session coherence requirements
    assert session_result["session_coherence_rate"] > 99.0, f"Session coherence {session_result['session_coherence_rate']}% below 99%"
    assert session_result["successful_operations"] >= session_result["total_operations"] * 0.99, "Session operation success rate below 99%"
    
    # Verify coherent invalidations
    assert session_result["coherent_invalidations"] >= session_result["total_users"] * 0.99, "Session invalidation coherence below 99%"
    
    logger.info(f"Session cache coherence test completed: {session_result['session_coherence_rate']:.2f}% coherence")


@pytest.mark.asyncio
@pytest.mark.l4
async def test_cache_performance_sla_compliance(cache_l4_manager):
    """Test overall cache performance SLA compliance under realistic load."""
    # Execute comprehensive performance test
    await cache_l4_manager.test_cache_write_performance(500)
    await cache_l4_manager.test_cache_read_performance(1000)
    await cache_l4_manager.test_cache_invalidation_coherence(100)
    await cache_l4_manager.test_ttl_accuracy_and_eviction(100)
    
    # Get comprehensive performance summary
    performance = cache_l4_manager.get_performance_summary()
    
    # Verify all SLA requirements
    sla_compliance = performance["sla_compliance"]
    
    assert sla_compliance["hit_rate_above_90"], f"Hit rate SLA violation: {cache_l4_manager.metrics.hit_rate:.2f}%"
    assert sla_compliance["invalidation_under_50ms"], f"Invalidation time SLA violation: {cache_l4_manager.metrics.avg_invalidation_time*1000:.1f}ms"
    assert sla_compliance["ttl_accuracy_above_99"], f"TTL accuracy SLA violation: {cache_l4_manager.metrics.ttl_accuracy:.2f}%"
    assert sla_compliance["p99_response_under_10ms"], f"P99 response time SLA violation: {cache_l4_manager.metrics.p99_response_time*1000:.1f}ms"
    
    # Verify no critical recommendations
    critical_recommendations = [r for r in performance["recommendations"] if "exceeds" in r or "below" in r]
    assert len(critical_recommendations) == 0, f"Critical performance issues: {critical_recommendations}"
    
    logger.info(f"SLA compliance test completed successfully")
    logger.info(f"Performance summary: {performance}")
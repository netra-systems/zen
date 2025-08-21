"""Redis Cache Invalidation Cascade - L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (cache invalidation affects all user operations)
- Business Goal: Ensure reliable cache invalidation across all cache layers and services
- Value Impact: Prevents stale data, maintains data consistency, improves user experience
- Strategic Impact: $5K MRR protection through reliable cache invalidation preventing data corruption

Critical Path: Cache write -> Multi-level invalidation -> Cross-service cache clear -> Data consistency validation
L3 Realism: Real Redis clusters with Testcontainers, actual cache invalidation services, multi-level cache hierarchies
Performance Requirements: Invalidation cascade < 100ms, 99.9% propagation success, zero stale data tolerance
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import redis.asyncio as aioredis

from app.tests.integration.helpers.redis_l3_helpers import RedisContainer as NetraRedisContainer
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class InvalidationMetrics:
    """Metrics for cache invalidation cascade testing."""
    total_invalidations: int = 0
    successful_cascades: int = 0
    failed_cascades: int = 0
    cascade_times: List[float] = None
    stale_data_detected: int = 0
    cross_service_failures: int = 0
    
    def __post_init__(self):
        if self.cascade_times is None:
            self.cascade_times = []
    
    @property
    def cascade_success_rate(self) -> float:
        """Calculate invalidation cascade success rate."""
        if self.total_invalidations == 0:
            return 100.0
        return (self.successful_cascades / self.total_invalidations) * 100.0
    
    @property
    def avg_cascade_time(self) -> float:
        """Calculate average cascade time."""
        if not self.cascade_times:
            return 0.0
        return sum(self.cascade_times) / len(self.cascade_times)


class CacheInvalidationCascadeL3Manager:
    """L3 cache invalidation cascade test manager with real Redis clusters."""
    
    def __init__(self):
        self.redis_containers = {}
        self.redis_clients = {}
        self.metrics = InvalidationMetrics()
        self.test_keys = set()
        self.cache_levels = ["l1_cache", "l2_cache", "l3_cache", "session_cache"]
        
    async def setup_redis_cluster(self) -> Dict[str, str]:
        """Setup multi-level Redis cluster for cascade testing."""
        redis_urls = {}
        
        for level in self.cache_levels:
            try:
                container = NetraRedisContainer(port=6379 + len(self.redis_containers))
                url = await container.start()
                
                self.redis_containers[level] = container
                redis_urls[level] = url
                
                # Create Redis client
                client = aioredis.from_url(url, decode_responses=True)
                await client.ping()
                self.redis_clients[level] = client
                
                logger.info(f"Redis cluster level {level} started: {url}")
                
            except Exception as e:
                logger.error(f"Failed to start Redis container for {level}: {e}")
                raise
        
        return redis_urls
    
    async def test_single_level_invalidation(self, key_count: int) -> Dict[str, Any]:
        """Test invalidation within a single cache level."""
        successful_invalidations = 0
        failed_invalidations = 0
        invalidation_times = []
        
        # Populate cache with test data
        test_keys = []
        for i in range(key_count):
            key = f"single_level_test_{i}_{uuid.uuid4().hex[:8]}"
            value = {
                "data": f"test_data_{i}",
                "timestamp": datetime.utcnow().isoformat(),
                "level": "l1_cache"
            }
            
            # Write to L1 cache
            await self.redis_clients["l1_cache"].setex(
                key, 300, json.dumps(value)
            )
            test_keys.append(key)
            self.test_keys.add(key)
        
        # Test invalidation
        for key in test_keys:
            start_time = time.time()
            
            try:
                # Invalidate key
                deleted = await self.redis_clients["l1_cache"].delete(key)
                
                # Verify invalidation
                exists = await self.redis_clients["l1_cache"].exists(key)
                
                invalidation_time = time.time() - start_time
                invalidation_times.append(invalidation_time)
                
                if deleted and not exists:
                    successful_invalidations += 1
                else:
                    failed_invalidations += 1
                    logger.warning(f"Invalidation failed for key {key}")
                    
            except Exception as e:
                failed_invalidations += 1
                logger.error(f"Invalidation error for key {key}: {e}")
        
        return {
            "total_keys": key_count,
            "successful_invalidations": successful_invalidations,
            "failed_invalidations": failed_invalidations,
            "avg_invalidation_time": sum(invalidation_times) / len(invalidation_times) if invalidation_times else 0,
            "max_invalidation_time": max(invalidation_times) if invalidation_times else 0
        }
    
    async def test_multi_level_cascade(self, key_count: int) -> Dict[str, Any]:
        """Test invalidation cascade across multiple cache levels."""
        successful_cascades = 0
        failed_cascades = 0
        cascade_times = []
        stale_data_detected = 0
        
        # Populate all cache levels with identical data
        test_keys = []
        for i in range(key_count):
            key = f"cascade_test_{i}_{uuid.uuid4().hex[:8]}"
            value = {
                "data": f"cascade_data_{i}",
                "timestamp": datetime.utcnow().isoformat(),
                "version": 1
            }
            
            # Write to all cache levels
            for level in self.cache_levels:
                await self.redis_clients[level].setex(
                    key, 600, json.dumps(value)
                )
            
            test_keys.append(key)
            self.test_keys.add(key)
        
        # Test cascade invalidation
        for key in test_keys:
            start_time = time.time()
            
            try:
                # Trigger cascade invalidation (simulate application logic)
                cascade_successful = await self._execute_cascade_invalidation(key)
                
                cascade_time = time.time() - start_time
                cascade_times.append(cascade_time)
                
                if cascade_successful:
                    successful_cascades += 1
                else:
                    failed_cascades += 1
                    
                # Check for stale data
                stale_detected = await self._detect_stale_data(key)
                if stale_detected:
                    stale_data_detected += 1
                    
            except Exception as e:
                failed_cascades += 1
                logger.error(f"Cascade invalidation failed for key {key}: {e}")
        
        self.metrics.total_invalidations += key_count
        self.metrics.successful_cascades += successful_cascades
        self.metrics.failed_cascades += failed_cascades
        self.metrics.cascade_times.extend(cascade_times)
        self.metrics.stale_data_detected += stale_data_detected
        
        return {
            "total_keys": key_count,
            "successful_cascades": successful_cascades,
            "failed_cascades": failed_cascades,
            "stale_data_detected": stale_data_detected,
            "avg_cascade_time": sum(cascade_times) / len(cascade_times) if cascade_times else 0,
            "cascade_success_rate": (successful_cascades / key_count * 100) if key_count > 0 else 0
        }
    
    async def _execute_cascade_invalidation(self, key: str) -> bool:
        """Execute invalidation cascade across all cache levels."""
        try:
            # Delete from all cache levels in sequence
            deletion_results = []
            
            for level in self.cache_levels:
                deleted = await self.redis_clients[level].delete(key)
                deletion_results.append(deleted)
            
            # Verify all deletions were successful
            verification_results = []
            await asyncio.sleep(0.01)  # Allow for propagation
            
            for level in self.cache_levels:
                exists = await self.redis_clients[level].exists(key)
                verification_results.append(not exists)
            
            # Cascade successful if all levels were invalidated
            return all(verification_results)
            
        except Exception as e:
            logger.error(f"Cascade invalidation execution failed for key {key}: {e}")
            return False
    
    async def _detect_stale_data(self, key: str) -> bool:
        """Detect if stale data exists in any cache level after invalidation."""
        try:
            for level in self.cache_levels:
                exists = await self.redis_clients[level].exists(key)
                if exists:
                    value = await self.redis_clients[level].get(key)
                    logger.warning(f"Stale data detected in {level} for key {key}: {value}")
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Stale data detection failed for key {key}: {e}")
            return False
    
    async def test_cross_service_invalidation(self, service_count: int, keys_per_service: int) -> Dict[str, Any]:
        """Test invalidation coordination across multiple services."""
        cross_service_results = {}
        total_failures = 0
        
        for service_id in range(service_count):
            service_name = f"service_{service_id}"
            service_results = {
                "successful_invalidations": 0,
                "failed_invalidations": 0,
                "cross_service_conflicts": 0
            }
            
            # Create service-specific keys across cache levels
            service_keys = []
            for i in range(keys_per_service):
                key = f"{service_name}_key_{i}_{uuid.uuid4().hex[:8]}"
                value = {
                    "service": service_name,
                    "data": f"service_data_{i}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Write to random cache levels (simulate different service caching strategies)
                cache_level = self.cache_levels[i % len(self.cache_levels)]
                await self.redis_clients[cache_level].setex(
                    key, 300, json.dumps(value)
                )
                service_keys.append((key, cache_level))
                self.test_keys.add(key)
            
            # Simulate cross-service invalidation
            for key, cache_level in service_keys:
                try:
                    # Check if other services have conflicting data
                    conflicts = await self._check_cross_service_conflicts(key, service_name)
                    if conflicts:
                        service_results["cross_service_conflicts"] += 1
                    
                    # Invalidate from service's cache level
                    deleted = await self.redis_clients[cache_level].delete(key)
                    
                    if deleted:
                        service_results["successful_invalidations"] += 1
                    else:
                        service_results["failed_invalidations"] += 1
                        total_failures += 1
                        
                except Exception as e:
                    service_results["failed_invalidations"] += 1
                    total_failures += 1
                    logger.error(f"Cross-service invalidation failed for {key}: {e}")
            
            cross_service_results[service_name] = service_results
        
        self.metrics.cross_service_failures += total_failures
        
        return {
            "total_services": service_count,
            "keys_per_service": keys_per_service,
            "service_results": cross_service_results,
            "total_cross_service_failures": total_failures,
            "cross_service_success_rate": ((service_count * keys_per_service - total_failures) / (service_count * keys_per_service) * 100) if service_count * keys_per_service > 0 else 0
        }
    
    async def _check_cross_service_conflicts(self, key: str, service_name: str) -> bool:
        """Check for cross-service data conflicts."""
        try:
            conflicts = 0
            
            for level in self.cache_levels:
                exists = await self.redis_clients[level].exists(key)
                if exists:
                    value_str = await self.redis_clients[level].get(key)
                    if value_str:
                        try:
                            value = json.loads(value_str)
                            if value.get("service") and value["service"] != service_name:
                                conflicts += 1
                        except json.JSONDecodeError:
                            pass
            
            return conflicts > 0
            
        except Exception as e:
            logger.error(f"Cross-service conflict check failed for key {key}: {e}")
            return False
    
    async def test_invalidation_under_load(self, concurrent_operations: int) -> Dict[str, Any]:
        """Test invalidation cascade under concurrent load."""
        # Create concurrent invalidation tasks
        tasks = []
        
        for i in range(concurrent_operations):
            # Mix of single-level and cascade invalidations
            if i % 3 == 0:
                task = self._concurrent_cascade_invalidation(i)
            elif i % 3 == 1:
                task = self._concurrent_single_invalidation(i)
            else:
                task = self._concurrent_cross_service_invalidation(i)
            
            tasks.append(task)
        
        # Execute all invalidations concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_ops = len([r for r in results if not isinstance(r, Exception) and r.get("success", False)])
        failed_ops = len([r for r in results if isinstance(r, Exception) or not r.get("success", False)])
        
        return {
            "total_operations": concurrent_operations,
            "successful_operations": successful_ops,
            "failed_operations": failed_ops,
            "total_time": total_time,
            "operations_per_second": concurrent_operations / total_time if total_time > 0 else 0,
            "success_rate": (successful_ops / concurrent_operations * 100) if concurrent_operations > 0 else 0
        }
    
    async def _concurrent_cascade_invalidation(self, index: int) -> Dict[str, Any]:
        """Execute concurrent cascade invalidation."""
        key = f"concurrent_cascade_{index}_{uuid.uuid4().hex[:8]}"
        
        # Populate all levels
        for level in self.cache_levels:
            await self.redis_clients[level].setex(
                key, 300, json.dumps({"data": f"concurrent_{index}"})
            )
        
        # Execute cascade
        success = await self._execute_cascade_invalidation(key)
        self.test_keys.add(key)
        
        return {"operation": "cascade", "key": key, "success": success}
    
    async def _concurrent_single_invalidation(self, index: int) -> Dict[str, Any]:
        """Execute concurrent single-level invalidation."""
        key = f"concurrent_single_{index}_{uuid.uuid4().hex[:8]}"
        level = self.cache_levels[index % len(self.cache_levels)]
        
        # Populate single level
        await self.redis_clients[level].setex(
            key, 300, json.dumps({"data": f"single_{index}"})
        )
        
        # Execute single invalidation
        deleted = await self.redis_clients[level].delete(key)
        self.test_keys.add(key)
        
        return {"operation": "single", "key": key, "success": bool(deleted)}
    
    async def _concurrent_cross_service_invalidation(self, index: int) -> Dict[str, Any]:
        """Execute concurrent cross-service invalidation."""
        key = f"concurrent_cross_{index}_{uuid.uuid4().hex[:8]}"
        
        # Populate multiple levels (simulate cross-service caching)
        for i, level in enumerate(self.cache_levels[:2]):  # Use first 2 levels
            await self.redis_clients[level].setex(
                key, 300, json.dumps({"service": f"service_{i}", "data": f"cross_{index}"})
            )
        
        # Execute cross-service invalidation
        success = True
        for level in self.cache_levels[:2]:
            deleted = await self.redis_clients[level].delete(key)
            if not deleted:
                success = False
        
        self.test_keys.add(key)
        return {"operation": "cross_service", "key": key, "success": success}
    
    def get_invalidation_summary(self) -> Dict[str, Any]:
        """Get comprehensive invalidation cascade summary."""
        return {
            "invalidation_metrics": {
                "total_invalidations": self.metrics.total_invalidations,
                "cascade_success_rate": self.metrics.cascade_success_rate,
                "avg_cascade_time": self.metrics.avg_cascade_time,
                "stale_data_detected": self.metrics.stale_data_detected,
                "cross_service_failures": self.metrics.cross_service_failures
            },
            "sla_compliance": {
                "cascade_under_100ms": self.metrics.avg_cascade_time < 0.1,
                "success_rate_above_99_9": self.metrics.cascade_success_rate > 99.9,
                "zero_stale_data": self.metrics.stale_data_detected == 0
            },
            "recommendations": self._generate_invalidation_recommendations()
        }
    
    def _generate_invalidation_recommendations(self) -> List[str]:
        """Generate invalidation performance recommendations."""
        recommendations = []
        
        if self.metrics.cascade_success_rate < 99.9:
            recommendations.append(f"Cascade success rate {self.metrics.cascade_success_rate:.2f}% below 99.9% - review invalidation logic")
        
        if self.metrics.avg_cascade_time > 0.1:
            recommendations.append(f"Average cascade time {self.metrics.avg_cascade_time*1000:.1f}ms exceeds 100ms - optimize propagation")
        
        if self.metrics.stale_data_detected > 0:
            recommendations.append(f"{self.metrics.stale_data_detected} stale data instances detected - review invalidation completeness")
        
        if self.metrics.cross_service_failures > 0:
            recommendations.append(f"{self.metrics.cross_service_failures} cross-service failures - review coordination logic")
        
        if not recommendations:
            recommendations.append("All invalidation cascade metrics meet SLA requirements")
        
        return recommendations
    
    async def cleanup(self):
        """Clean up Redis containers and test resources."""
        try:
            # Clean up test keys
            for key in self.test_keys:
                for level in self.cache_levels:
                    try:
                        if level in self.redis_clients:
                            await self.redis_clients[level].delete(key)
                    except Exception:
                        pass
            
            # Close Redis clients
            for client in self.redis_clients.values():
                await client.close()
            
            # Stop Redis containers
            for container in self.redis_containers.values():
                await container.stop()
                
        except Exception as e:
            logger.error(f"Invalidation cascade cleanup failed: {e}")


@pytest.fixture
async def invalidation_cascade_manager():
    """Create L3 cache invalidation cascade manager."""
    manager = CacheInvalidationCascadeL3Manager()
    await manager.setup_redis_cluster()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_single_level_invalidation_performance(invalidation_cascade_manager):
    """L3: Test single-level cache invalidation performance with real Redis."""
    result = await invalidation_cascade_manager.test_single_level_invalidation(100)
    
    # Verify invalidation performance
    assert result["successful_invalidations"] >= 99, f"Single-level invalidation success rate below 99%: {result['successful_invalidations']}/100"
    assert result["avg_invalidation_time"] < 0.01, f"Average invalidation time {result['avg_invalidation_time']*1000:.1f}ms exceeds 10ms"
    assert result["failed_invalidations"] == 0, f"{result['failed_invalidations']} invalidations failed"
    
    logger.info(f"Single-level invalidation test completed: {result['successful_invalidations']}/100 successful, avg time {result['avg_invalidation_time']*1000:.2f}ms")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_multi_level_cascade_invalidation(invalidation_cascade_manager):
    """L3: Test multi-level cache invalidation cascade with real Redis cluster."""
    result = await invalidation_cascade_manager.test_multi_level_cascade(50)
    
    # Verify cascade performance
    assert result["cascade_success_rate"] > 99.0, f"Cascade success rate {result['cascade_success_rate']:.2f}% below 99%"
    assert result["avg_cascade_time"] < 0.1, f"Average cascade time {result['avg_cascade_time']*1000:.1f}ms exceeds 100ms"
    assert result["stale_data_detected"] == 0, f"{result['stale_data_detected']} stale data instances detected"
    
    logger.info(f"Multi-level cascade test completed: {result['cascade_success_rate']:.2f}% success rate, avg time {result['avg_cascade_time']*1000:.2f}ms")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_cross_service_invalidation_coordination(invalidation_cascade_manager):
    """L3: Test cache invalidation coordination across multiple services."""
    result = await invalidation_cascade_manager.test_cross_service_invalidation(5, 20)
    
    # Verify cross-service coordination
    assert result["cross_service_success_rate"] > 98.0, f"Cross-service success rate {result['cross_service_success_rate']:.2f}% below 98%"
    assert result["total_cross_service_failures"] <= 2, f"{result['total_cross_service_failures']} cross-service failures exceed threshold"
    
    # Verify individual service performance
    for service_name, service_result in result["service_results"].items():
        assert service_result["failed_invalidations"] <= 1, f"Service {service_name} has too many failures: {service_result['failed_invalidations']}"
    
    logger.info(f"Cross-service invalidation test completed: {result['cross_service_success_rate']:.2f}% success rate")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_invalidation_under_concurrent_load(invalidation_cascade_manager):
    """L3: Test cache invalidation cascade under concurrent load."""
    result = await invalidation_cascade_manager.test_invalidation_under_load(200)
    
    # Verify concurrent invalidation performance
    assert result["success_rate"] > 98.0, f"Concurrent invalidation success rate {result['success_rate']:.2f}% below 98%"
    assert result["operations_per_second"] > 50, f"Invalidation throughput {result['operations_per_second']:.1f} ops/s below 50"
    assert result["failed_operations"] <= 4, f"{result['failed_operations']} failed operations exceed threshold"
    
    logger.info(f"Concurrent invalidation test completed: {result['operations_per_second']:.1f} ops/s, {result['success_rate']:.2f}% success rate")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_invalidation_cascade_sla_compliance(invalidation_cascade_manager):
    """L3: Test comprehensive invalidation cascade SLA compliance."""
    # Execute comprehensive test suite
    await invalidation_cascade_manager.test_single_level_invalidation(50)
    await invalidation_cascade_manager.test_multi_level_cascade(30)
    await invalidation_cascade_manager.test_cross_service_invalidation(3, 15)
    
    # Get comprehensive summary
    summary = invalidation_cascade_manager.get_invalidation_summary()
    
    # Verify SLA compliance
    sla = summary["sla_compliance"]
    assert sla["cascade_under_100ms"], f"Cascade time SLA violation: {invalidation_cascade_manager.metrics.avg_cascade_time*1000:.1f}ms"
    assert sla["success_rate_above_99_9"], f"Success rate SLA violation: {invalidation_cascade_manager.metrics.cascade_success_rate:.2f}%"
    assert sla["zero_stale_data"], f"Stale data SLA violation: {invalidation_cascade_manager.metrics.stale_data_detected} instances"
    
    # Verify no critical recommendations
    critical_recommendations = [r for r in summary["recommendations"] if "below" in r or "exceeds" in r]
    assert len(critical_recommendations) == 0, f"Critical invalidation issues: {critical_recommendations}"
    
    logger.info(f"Invalidation cascade SLA compliance test completed successfully")
    logger.info(f"Summary: {summary}")
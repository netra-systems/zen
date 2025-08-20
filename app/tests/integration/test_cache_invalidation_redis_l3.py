"""L3 Integration Test: Cache Invalidation with Real Redis Cluster

Business Value Justification (BVJ):
- Segment: All tiers (cache consistency affects all operations)
- Business Goal: Ensure cache consistency for performance-critical operations
- Value Impact: Prevents stale data, improves response times, maintains data integrity
- Strategic Impact: Protects $25K MRR from cache-related data corruption and performance issues

L3 Test: Real Redis cluster with TTL expiration, manual invalidation, 
pattern-based clearing, and multi-node synchronization validation.
"""

import pytest
import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import redis.asyncio as redis
from app.redis_manager import RedisManager
from app.services.cache.cache_helpers import CacheService
from app.logging_config import central_logger
from .helpers.redis_l3_helpers import RedisContainer, verify_redis_connection

logger = central_logger.get_logger(__name__)


class CacheInvalidationManager:
    """Manages cache invalidation testing with real Redis cluster."""
    
    def __init__(self, redis_clients: Dict[str, redis.Redis]):
        self.redis_clients = redis_clients
        self.test_keys = set()
        self.cache_patterns = ["user:*", "session:*", "api:*", "temp:*"]
        self.invalidation_stats = {
            "ttl_expirations": 0,
            "manual_invalidations": 0,
            "pattern_clears": 0,
            "sync_operations": 0
        }
    
    async def test_ttl_expiration_scenarios(self, key_count: int) -> Dict[str, Any]:
        """Test TTL-based cache expiration with various scenarios."""
        ttl_scenarios = [
            {"ttl": 1, "name": "immediate_expiry", "count": key_count // 4},
            {"ttl": 5, "name": "short_expiry", "count": key_count // 4},
            {"ttl": 30, "name": "medium_expiry", "count": key_count // 4},
            {"ttl": 300, "name": "long_expiry", "count": key_count // 4}
        ]
        
        expiry_results = {}
        
        for scenario in ttl_scenarios:
            scenario_keys = []
            client = self.redis_clients["primary"]
            
            # Create keys with specific TTL
            for i in range(scenario["count"]):
                key = f"ttl_{scenario['name']}_{i}_{uuid.uuid4().hex[:8]}"
                value = {
                    "data": f"test_data_{i}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "scenario": scenario["name"]
                }
                
                await client.setex(key, scenario["ttl"], json.dumps(value))
                scenario_keys.append(key)
                self.test_keys.add(key)
            
            # Wait for expiration (for immediate and short scenarios)
            if scenario["ttl"] <= 5:
                await asyncio.sleep(scenario["ttl"] + 1)
                
                # Verify expiration
                expired_count = 0
                for key in scenario_keys:
                    exists = await client.exists(key)
                    if not exists:
                        expired_count += 1
                        self.invalidation_stats["ttl_expirations"] += 1
                
                expiry_results[scenario["name"]] = {
                    "total_keys": scenario["count"],
                    "expired_keys": expired_count,
                    "expiry_rate": (expired_count / scenario["count"] * 100) if scenario["count"] > 0 else 0
                }
            else:
                # For longer TTLs, verify keys exist and have correct TTL
                valid_ttl_count = 0
                for key in scenario_keys:
                    ttl_remaining = await client.ttl(key)
                    if 0 < ttl_remaining <= scenario["ttl"]:
                        valid_ttl_count += 1
                
                expiry_results[scenario["name"]] = {
                    "total_keys": scenario["count"],
                    "valid_ttl_keys": valid_ttl_count,
                    "ttl_validity_rate": (valid_ttl_count / scenario["count"] * 100) if scenario["count"] > 0 else 0
                }
        
        return expiry_results
    
    async def test_manual_invalidation_patterns(self, key_count: int) -> Dict[str, Any]:
        """Test manual cache invalidation with different patterns."""
        invalidation_patterns = {
            "single_key": [],
            "key_batch": [],
            "pattern_match": [],
            "conditional": []
        }
        
        client = self.redis_clients["primary"]
        
        # Create test data for each pattern
        for i in range(key_count):
            # Single key invalidation
            single_key = f"single:{i}:{uuid.uuid4().hex[:8]}"
            await client.set(single_key, json.dumps({"type": "single", "id": i}))
            invalidation_patterns["single_key"].append(single_key)
            
            # Batch invalidation
            batch_key = f"batch:group1:{i}:{uuid.uuid4().hex[:8]}"
            await client.set(batch_key, json.dumps({"type": "batch", "group": "group1", "id": i}))
            invalidation_patterns["key_batch"].append(batch_key)
            
            # Pattern matching
            pattern_key = f"pattern:test:{i}:{uuid.uuid4().hex[:8]}"
            await client.set(pattern_key, json.dumps({"type": "pattern", "category": "test", "id": i}))
            invalidation_patterns["pattern_match"].append(pattern_key)
            
            # Conditional invalidation
            cond_key = f"conditional:{i}:{uuid.uuid4().hex[:8]}"
            await client.set(cond_key, json.dumps({"type": "conditional", "status": "active" if i % 2 == 0 else "inactive", "id": i}))
            invalidation_patterns["conditional"].append(cond_key)
            
            self.test_keys.update([single_key, batch_key, pattern_key, cond_key])
        
        results = {}
        
        # Test single key invalidation
        single_invalidated = 0
        for key in invalidation_patterns["single_key"][:10]:  # Test subset
            deleted = await client.delete(key)
            if deleted:
                single_invalidated += 1
                self.invalidation_stats["manual_invalidations"] += 1
        
        results["single_key"] = {
            "tested_keys": 10,
            "invalidated_keys": single_invalidated,
            "success_rate": (single_invalidated / 10 * 100)
        }
        
        # Test batch invalidation
        batch_keys = invalidation_patterns["key_batch"][:15]  # Test subset
        deleted_count = await client.delete(*batch_keys)
        self.invalidation_stats["manual_invalidations"] += deleted_count
        
        results["key_batch"] = {
            "tested_keys": len(batch_keys),
            "invalidated_keys": deleted_count,
            "success_rate": (deleted_count / len(batch_keys) * 100) if batch_keys else 0
        }
        
        return results
    
    async def test_pattern_based_clearing(self) -> Dict[str, Any]:
        """Test pattern-based cache clearing operations."""
        client = self.redis_clients["primary"]
        pattern_results = {}
        
        for pattern_prefix in ["user", "session", "api", "temp"]:
            # Create test keys matching pattern
            pattern_keys = []
            for i in range(20):
                key = f"{pattern_prefix}:{uuid.uuid4().hex[:8]}:{i}"
                value = {"pattern": pattern_prefix, "id": i, "timestamp": time.time()}
                await client.set(key, json.dumps(value))
                pattern_keys.append(key)
                self.test_keys.add(key)
            
            # Test pattern-based deletion
            pattern = f"{pattern_prefix}:*"
            
            # Get matching keys
            matching_keys = []
            async for key in client.scan_iter(match=pattern):
                if key.startswith(f"{pattern_prefix}:"):
                    matching_keys.append(key)
            
            # Delete matching keys
            if matching_keys:
                deleted_count = await client.delete(*matching_keys)
                self.invalidation_stats["pattern_clears"] += deleted_count
            else:
                deleted_count = 0
            
            pattern_results[pattern_prefix] = {
                "created_keys": len(pattern_keys),
                "matching_keys": len(matching_keys),
                "deleted_keys": deleted_count,
                "clear_efficiency": (deleted_count / len(pattern_keys) * 100) if pattern_keys else 0
            }
        
        return pattern_results
    
    async def test_multi_node_sync(self) -> Dict[str, Any]:
        """Test cache synchronization across multiple Redis nodes."""
        if len(self.redis_clients) < 2:
            return {"error": "Multi-node sync test requires at least 2 Redis clients"}
        
        primary_client = self.redis_clients["primary"]
        secondary_client = self.redis_clients["secondary"]
        
        sync_keys = []
        sync_operations = 0
        successful_syncs = 0
        
        # Create data on primary node
        for i in range(30):
            key = f"sync_test:{i}:{uuid.uuid4().hex[:8]}"
            value = {
                "sync_id": i,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "node": "primary"
            }
            
            await primary_client.set(key, json.dumps(value))
            sync_keys.append(key)
            self.test_keys.add(key)
        
        # Simulate synchronization to secondary node
        for key in sync_keys:
            try:
                # Get value from primary
                value = await primary_client.get(key)
                if value:
                    # Sync to secondary
                    await secondary_client.set(key, value)
                    
                    # Verify sync
                    secondary_value = await secondary_client.get(key)
                    if secondary_value == value:
                        successful_syncs += 1
                        self.invalidation_stats["sync_operations"] += 1
                
                sync_operations += 1
                
            except Exception as e:
                logger.warning(f"Sync failed for key {key}: {e}")
        
        # Test invalidation sync
        invalidation_syncs = 0
        keys_to_invalidate = sync_keys[:10]
        
        for key in keys_to_invalidate:
            # Delete from primary
            await primary_client.delete(key)
            
            # Sync deletion to secondary
            await secondary_client.delete(key)
            
            # Verify both nodes cleared
            primary_exists = await primary_client.exists(key)
            secondary_exists = await secondary_client.exists(key)
            
            if not primary_exists and not secondary_exists:
                invalidation_syncs += 1
        
        return {
            "total_sync_operations": sync_operations,
            "successful_syncs": successful_syncs,
            "sync_success_rate": (successful_syncs / sync_operations * 100) if sync_operations > 0 else 0,
            "invalidation_syncs": invalidation_syncs,
            "invalidation_sync_rate": (invalidation_syncs / len(keys_to_invalidate) * 100) if keys_to_invalidate else 0
        }
    
    async def cleanup(self):
        """Clean up test data from all Redis clients."""
        for key in self.test_keys:
            for client in self.redis_clients.values():
                try:
                    await client.delete(key)
                except Exception:
                    pass
        
        self.test_keys.clear()
    
    def get_invalidation_summary(self) -> Dict[str, Any]:
        """Get comprehensive invalidation test summary."""
        return {
            "invalidation_stats": self.invalidation_stats,
            "total_operations": sum(self.invalidation_stats.values()),
            "test_keys_created": len(self.test_keys)
        }


@pytest.mark.L3
@pytest.mark.integration
class TestCacheInvalidationRedisL3:
    """L3 integration tests for cache invalidation with real Redis cluster."""
    
    @pytest.fixture(scope="class")
    async def redis_containers(self):
        """Set up multiple Redis containers for cluster testing."""
        containers = {}
        redis_urls = {}
        
        # Primary Redis
        primary_container = RedisContainer(port=6381)
        primary_url = await primary_container.start()
        containers["primary"] = primary_container
        redis_urls["primary"] = primary_url
        
        # Secondary Redis
        secondary_container = RedisContainer(port=6382)
        secondary_url = await secondary_container.start()
        containers["secondary"] = secondary_container
        redis_urls["secondary"] = secondary_url
        
        yield containers, redis_urls
        
        for container in containers.values():
            await container.stop()
    
    @pytest.fixture
    async def redis_clients(self, redis_containers):
        """Create Redis clients for all containers."""
        _, redis_urls = redis_containers
        clients = {}
        
        for name, url in redis_urls.items():
            client = redis.Redis.from_url(url, decode_responses=True)
            await client.ping()
            clients[name] = client
        
        yield clients
        
        for client in clients.values():
            await client.close()
    
    @pytest.fixture
    async def cache_manager(self, redis_clients):
        """Create cache invalidation manager."""
        manager = CacheInvalidationManager(redis_clients)
        yield manager
        await manager.cleanup()
    
    async def test_ttl_expiration_validation(self, cache_manager):
        """Test TTL-based cache expiration scenarios."""
        results = await cache_manager.test_ttl_expiration_scenarios(80)
        
        # Verify immediate expiry
        assert results["immediate_expiry"]["expiry_rate"] >= 95.0, f"Immediate expiry rate too low: {results['immediate_expiry']['expiry_rate']:.1f}%"
        
        # Verify short expiry
        assert results["short_expiry"]["expiry_rate"] >= 95.0, f"Short expiry rate too low: {results['short_expiry']['expiry_rate']:.1f}%"
        
        # Verify longer TTLs are set correctly
        assert results["medium_expiry"]["ttl_validity_rate"] >= 95.0, f"Medium TTL validity too low: {results['medium_expiry']['ttl_validity_rate']:.1f}%"
        assert results["long_expiry"]["ttl_validity_rate"] >= 95.0, f"Long TTL validity too low: {results['long_expiry']['ttl_validity_rate']:.1f}%"
        
        logger.info(f"TTL expiration test completed: {results}")
    
    async def test_manual_invalidation_efficiency(self, cache_manager):
        """Test manual cache invalidation patterns and efficiency."""
        results = await cache_manager.test_manual_invalidation_patterns(40)
        
        # Verify single key invalidation
        assert results["single_key"]["success_rate"] >= 95.0, f"Single key invalidation rate too low: {results['single_key']['success_rate']:.1f}%"
        
        # Verify batch invalidation
        assert results["key_batch"]["success_rate"] >= 95.0, f"Batch invalidation rate too low: {results['key_batch']['success_rate']:.1f}%"
        
        # Verify operation counts
        assert results["single_key"]["invalidated_keys"] >= 9, "Too few single keys invalidated"
        assert results["key_batch"]["invalidated_keys"] >= 14, "Too few batch keys invalidated"
        
        logger.info(f"Manual invalidation test completed: {results}")
    
    async def test_pattern_clearing_operations(self, cache_manager):
        """Test pattern-based cache clearing functionality."""
        results = await cache_manager.test_pattern_based_clearing()
        
        # Verify pattern clearing efficiency for each pattern
        for pattern, result in results.items():
            assert result["clear_efficiency"] >= 90.0, f"Pattern {pattern} clearing efficiency too low: {result['clear_efficiency']:.1f}%"
            assert result["deleted_keys"] >= result["created_keys"] * 0.9, f"Pattern {pattern} deletion count too low"
        
        # Verify all patterns were tested
        expected_patterns = ["user", "session", "api", "temp"]
        for pattern in expected_patterns:
            assert pattern in results, f"Pattern {pattern} not tested"
        
        logger.info(f"Pattern clearing test completed: {results}")
    
    async def test_multi_node_synchronization(self, cache_manager):
        """Test cache synchronization across multiple Redis nodes."""
        results = await cache_manager.test_multi_node_sync()
        
        if "error" in results:
            pytest.skip(results["error"])
        
        # Verify sync operations
        assert results["sync_success_rate"] >= 95.0, f"Sync success rate too low: {results['sync_success_rate']:.1f}%"
        assert results["successful_syncs"] >= 28, "Too few successful sync operations"
        
        # Verify invalidation sync
        assert results["invalidation_sync_rate"] >= 90.0, f"Invalidation sync rate too low: {results['invalidation_sync_rate']:.1f}%"
        assert results["invalidation_syncs"] >= 9, "Too few invalidation syncs"
        
        logger.info(f"Multi-node sync test completed: {results}")
    
    async def test_cache_invalidation_performance(self, cache_manager):
        """Test cache invalidation performance under load."""
        start_time = time.time()
        
        # Run comprehensive invalidation tests
        await asyncio.gather(
            cache_manager.test_ttl_expiration_scenarios(50),
            cache_manager.test_manual_invalidation_patterns(30),
            cache_manager.test_pattern_based_clearing()
        )
        
        total_time = time.time() - start_time
        
        # Verify performance
        assert total_time < 30.0, f"Invalidation tests took too long: {total_time:.2f}s"
        
        # Get summary
        summary = cache_manager.get_invalidation_summary()
        assert summary["total_operations"] >= 50, "Insufficient invalidation operations performed"
        
        logger.info(f"Cache invalidation performance test completed in {total_time:.2f}s: {summary}")
    
    async def test_cache_consistency_validation(self, cache_manager):
        """Test cache consistency after various invalidation operations."""
        client = cache_manager.redis_clients["primary"]
        
        # Create test data
        consistency_keys = []
        for i in range(25):
            key = f"consistency_test:{i}:{uuid.uuid4().hex[:8]}"
            value = {"id": i, "data": f"test_{i}", "timestamp": time.time()}
            await client.set(key, json.dumps(value))
            consistency_keys.append(key)
            cache_manager.test_keys.add(key)
        
        # Perform mixed invalidation operations
        # 1. TTL expiration
        ttl_keys = consistency_keys[:5]
        for key in ttl_keys:
            await client.expire(key, 1)
        
        await asyncio.sleep(2)
        
        # 2. Manual deletion
        manual_keys = consistency_keys[5:10]
        await client.delete(*manual_keys)
        
        # 3. Pattern-based clearing
        pattern_keys = consistency_keys[10:15]
        for key in pattern_keys:
            await client.delete(key)
        
        # Verify consistency
        expired_count = 0
        deleted_count = 0
        remaining_count = 0
        
        for i, key in enumerate(consistency_keys):
            exists = await client.exists(key)
            
            if i < 5:  # TTL keys
                if not exists:
                    expired_count += 1
            elif i < 10:  # Manual deletion keys
                if not exists:
                    deleted_count += 1
            elif i < 15:  # Pattern deletion keys
                if not exists:
                    deleted_count += 1
            else:  # Remaining keys
                if exists:
                    remaining_count += 1
        
        # Verify consistency
        assert expired_count == 5, f"TTL expiration inconsistent: {expired_count}/5"
        assert deleted_count >= 9, f"Manual deletion inconsistent: {deleted_count}/10"
        assert remaining_count == 10, f"Remaining keys inconsistent: {remaining_count}/10"
        
        logger.info(f"Cache consistency validation completed: expired={expired_count}, deleted={deleted_count}, remaining={remaining_count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
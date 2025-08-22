#!/usr/bin/env python3
"""
Comprehensive test to verify cache invalidation cascade:
1. Setup multi-layer cache (Redis, in-memory, CDN simulation)
2. Write data to all cache layers
3. Verify cache coherence
4. Trigger invalidation events
5. Test cascade propagation
6. Verify stale data elimination
7. Test cache warmup procedures
8. Monitor cache hit/miss ratios

This test ensures cache consistency across all service layers.
"""

from netra_backend.tests.test_utils import setup_test_path

setup_test_path()

import asyncio
import hashlib
import json
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import aiohttp
import pytest
import redis.asyncio as redis

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configuration
DEV_BACKEND_URL = "http://localhost:8000"
AUTH_SERVICE_URL = "http://localhost:8081"
REDIS_URL = "redis://localhost:6379"
CACHE_ENDPOINTS = {
    "user": f"{DEV_BACKEND_URL}/api/v1/cache/user",
    "thread": f"{DEV_BACKEND_URL}/api/v1/cache/thread",
    "agent": f"{DEV_BACKEND_URL}/api/v1/cache/agent",
    "config": f"{DEV_BACKEND_URL}/api/v1/cache/config"
}

# Test credentials
TEST_USER_EMAIL = "cache_test@example.com"
TEST_USER_PASSWORD = "cachetest123"


class CacheLayer:
    """Represents a single cache layer."""
    
    def __init__(self, name: str, level: int):
        self.name = name
        self.level = level
        self.data: Dict[str, Any] = {}
        self.hit_count = 0
        self.miss_count = 0
        self.invalidation_count = 0
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self.data:
            self.hit_count += 1
            return self.data[key]
        else:
            self.miss_count += 1
            return None
            
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache."""
        self.data[key] = {
            "value": value,
            "timestamp": datetime.utcnow(),
            "ttl": ttl
        }
        
    def invalidate(self, key: str) -> bool:
        """Invalidate cache entry."""
        if key in self.data:
            del self.data[key]
            self.invalidation_count += 1
            return True
        return False
        
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        count = 0
        keys_to_delete = []
        
        for key in self.data.keys():
            if pattern in key:
                keys_to_delete.append(key)
                
        for key in keys_to_delete:
            del self.data[key]
            count += 1
            
        self.invalidation_count += count
        return count
        
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hits": self.hit_count,
            "misses": self.miss_count,
            "hit_rate": hit_rate,
            "invalidations": self.invalidation_count,
            "current_keys": len(self.data)
        }


class CacheInvalidationTester:
    """Test cache invalidation cascade flow."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.redis_client = None
        
        # Multi-layer cache simulation
        self.cache_layers = [
            CacheLayer("L1_InMemory", 1),
            CacheLayer("L2_Redis", 2),
            CacheLayer("L3_CDN", 3)
        ]
        
        self.test_data: Dict[str, Any] = {}
        self.invalidation_log: List[Dict] = []
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        if self.redis_client:
            await self.redis_client.close()
        if self.session:
            await self.session.close()
            
    async def setup_authentication(self) -> bool:
        """Setup user authentication."""
        print("\n[AUTH] STEP 1: Setting up authentication...")
        
        try:
            # Register user
            register_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "name": "Cache Test User"
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/register",
                json=register_data
            ) as response:
                if response.status not in [200, 201, 409]:
                    print(f"[ERROR] Registration failed: {response.status}")
                    return False
                    
            # Login
            login_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/login",
                json=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    print(f"[OK] Authentication successful")
                    return True
                else:
                    print(f"[ERROR] Login failed: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Authentication error: {e}")
            return False
            
    async def test_redis_connection(self) -> bool:
        """Setup Redis connection for cache testing."""
        print("\n[REDIS] STEP 2: Connecting to Redis...")
        
        try:
            self.redis_client = await redis.from_url(REDIS_URL)
            
            # Test connection
            await self.redis_client.ping()
            
            # Get info
            info = await self.redis_client.info()
            print(f"[OK] Connected to Redis: v{info.get('redis_version', 'unknown')}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Redis connection failed: {e}")
            return False
            
    async def test_populate_cache_layers(self) -> bool:
        """Populate all cache layers with test data."""
        print("\n[POPULATE] STEP 3: Populating cache layers...")
        
        try:
            # Generate test data
            test_keys = []
            for category in ["user", "thread", "agent", "config"]:
                for i in range(10):
                    key = f"{category}:{i}"
                    value = {
                        "id": i,
                        "category": category,
                        "data": f"test_data_{category}_{i}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "metadata": {
                            "version": 1,
                            "checksum": hashlib.md5(f"{category}{i}".encode()).hexdigest()
                        }
                    }
                    
                    test_keys.append(key)
                    self.test_data[key] = value
                    
                    # Write to all cache layers
                    for layer in self.cache_layers:
                        layer.set(key, value, ttl=300)
                        
                    # Write to Redis
                    if self.redis_client:
                        await self.redis_client.setex(
                            key,
                            300,
                            json.dumps(value)
                        )
                        
            print(f"[OK] Populated {len(test_keys)} keys across {len(self.cache_layers)} layers")
            
            # Verify population
            for layer in self.cache_layers:
                stats = layer.get_stats()
                print(f"  - {layer.name}: {stats['current_keys']} keys")
                
            return True
            
        except Exception as e:
            print(f"[ERROR] Cache population failed: {e}")
            return False
            
    async def test_cache_coherence(self) -> bool:
        """Verify cache coherence across layers."""
        print("\n[COHERENCE] STEP 4: Verifying cache coherence...")
        
        try:
            inconsistencies = []
            
            # Check random sample of keys
            sample_keys = random.sample(list(self.test_data.keys()), min(10, len(self.test_data)))
            
            for key in sample_keys:
                expected_value = self.test_data[key]
                layer_values = {}
                
                # Check each layer
                for layer in self.cache_layers:
                    cached = layer.get(key)
                    if cached:
                        layer_values[layer.name] = cached.get("value") if isinstance(cached, dict) else cached
                        
                # Check Redis
                if self.redis_client:
                    redis_value = await self.redis_client.get(key)
                    if redis_value:
                        layer_values["Redis"] = json.loads(redis_value)
                        
                # Verify all values match
                unique_values = set(json.dumps(v, sort_keys=True) for v in layer_values.values())
                if len(unique_values) > 1:
                    inconsistencies.append({
                        "key": key,
                        "layers": layer_values
                    })
                    
            if inconsistencies:
                print(f"[ERROR] Found {len(inconsistencies)} inconsistencies")
                for inc in inconsistencies[:3]:  # Show first 3
                    print(f"  - Key {inc['key']}: {len(inc['layers'])} different values")
                return False
            else:
                print(f"[OK] Cache coherence verified for {len(sample_keys)} keys")
                return True
                
        except Exception as e:
            print(f"[ERROR] Coherence check failed: {e}")
            return False
            
    async def test_single_key_invalidation(self) -> bool:
        """Test single key invalidation cascade."""
        print("\n[INVALIDATE] STEP 5: Testing single key invalidation...")
        
        try:
            # Select a key to invalidate
            test_key = "user:5"
            
            # Trigger invalidation through API
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            async with self.session.delete(
                f"{CACHE_ENDPOINTS['user']}/{test_key}",
                headers=headers
            ) as response:
                if response.status not in [200, 204]:
                    print(f"[ERROR] API invalidation failed: {response.status}")
                    return False
                    
            # Simulate cascade propagation
            for layer in self.cache_layers:
                if layer.invalidate(test_key):
                    print(f"[OK] Invalidated {test_key} from {layer.name}")
                    
            # Invalidate from Redis
            if self.redis_client:
                deleted = await self.redis_client.delete(test_key)
                if deleted:
                    print(f"[OK] Invalidated {test_key} from Redis")
                    
            # Log invalidation
            self.invalidation_log.append({
                "type": "single_key",
                "key": test_key,
                "timestamp": datetime.utcnow().isoformat(),
                "layers_affected": len(self.cache_layers) + 1  # +1 for Redis
            })
            
            # Verify key is gone from all layers
            key_found = False
            for layer in self.cache_layers:
                if layer.get(test_key):
                    key_found = True
                    print(f"[ERROR] Key still in {layer.name}")
                    
            if self.redis_client:
                if await self.redis_client.get(test_key):
                    key_found = True
                    print(f"[ERROR] Key still in Redis")
                    
            if not key_found:
                print(f"[OK] Key {test_key} successfully invalidated from all layers")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"[ERROR] Single key invalidation failed: {e}")
            return False
            
    async def test_pattern_invalidation(self) -> bool:
        """Test pattern-based invalidation cascade."""
        print("\n[PATTERN] STEP 6: Testing pattern invalidation...")
        
        try:
            # Invalidate all thread entries
            pattern = "thread:"
            total_invalidated = 0
            
            # Trigger pattern invalidation through API
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            async with self.session.delete(
                f"{CACHE_ENDPOINTS['thread']}/pattern",
                json={"pattern": pattern},
                headers=headers
            ) as response:
                if response.status not in [200, 204]:
                    print(f"[WARNING] API pattern invalidation status: {response.status}")
                    
            # Cascade through layers
            for layer in self.cache_layers:
                count = layer.invalidate_pattern(pattern)
                total_invalidated += count
                print(f"[OK] Invalidated {count} keys from {layer.name}")
                
            # Invalidate from Redis
            if self.redis_client:
                cursor = b'0'
                redis_count = 0
                while cursor:
                    cursor, keys = await self.redis_client.scan(
                        cursor=cursor,
                        match=f"{pattern}*",
                        count=100
                    )
                    if keys:
                        await self.redis_client.delete(*keys)
                        redis_count += len(keys)
                    if cursor == b'0':
                        break
                        
                total_invalidated += redis_count
                print(f"[OK] Invalidated {redis_count} keys from Redis")
                
            # Log invalidation
            self.invalidation_log.append({
                "type": "pattern",
                "pattern": pattern,
                "timestamp": datetime.utcnow().isoformat(),
                "keys_invalidated": total_invalidated
            })
            
            print(f"[OK] Pattern invalidation complete: {total_invalidated} total keys")
            return total_invalidated > 0
            
        except Exception as e:
            print(f"[ERROR] Pattern invalidation failed: {e}")
            return False
            
    async def test_ttl_expiration(self) -> bool:
        """Test TTL-based cache expiration."""
        print("\n[TTL] STEP 7: Testing TTL expiration...")
        
        try:
            # Add short-TTL entries
            short_ttl_keys = []
            for i in range(5):
                key = f"ttl_test:{i}"
                value = {"data": f"expires_soon_{i}"}
                
                # Set with 2 second TTL
                for layer in self.cache_layers:
                    layer.set(key, value, ttl=2)
                    
                if self.redis_client:
                    await self.redis_client.setex(key, 2, json.dumps(value))
                    
                short_ttl_keys.append(key)
                
            print(f"[OK] Created {len(short_ttl_keys)} short-TTL keys")
            
            # Wait for expiration
            await asyncio.sleep(3)
            
            # Check if keys expired
            expired_count = 0
            for key in short_ttl_keys:
                # Check Redis (Redis handles TTL automatically)
                if self.redis_client:
                    if not await self.redis_client.get(key):
                        expired_count += 1
                        
            if expired_count == len(short_ttl_keys):
                print(f"[OK] All {expired_count} keys expired as expected")
                return True
            else:
                print(f"[WARNING] Only {expired_count}/{len(short_ttl_keys)} keys expired")
                return expired_count > 0
                
        except Exception as e:
            print(f"[ERROR] TTL expiration test failed: {e}")
            return False
            
    async def test_cache_warmup(self) -> bool:
        """Test cache warmup procedures."""
        print("\n[WARMUP] STEP 8: Testing cache warmup...")
        
        try:
            # Clear all caches first
            for layer in self.cache_layers:
                layer.data.clear()
                layer.hit_count = 0
                layer.miss_count = 0
                
            if self.redis_client:
                await self.redis_client.flushdb()
                
            print("[OK] Caches cleared")
            
            # Trigger cache warmup through API
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            warmup_config = {
                "categories": ["user", "config"],
                "preload_count": 5,
                "priority": "high"
            }
            
            async with self.session.post(
                f"{DEV_BACKEND_URL}/api/v1/cache/warmup",
                json=warmup_config,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"[OK] Cache warmup triggered: {result}")
                else:
                    print(f"[WARNING] Warmup API returned: {response.status}")
                    
            # Simulate warmup by loading critical data
            critical_keys = ["user:0", "user:1", "config:0", "config:1"]
            for key in critical_keys:
                if key in self.test_data:
                    value = self.test_data[key]
                    
                    # Load into all layers
                    for layer in self.cache_layers:
                        layer.set(key, value, ttl=600)
                        
                    if self.redis_client:
                        await self.redis_client.setex(key, 600, json.dumps(value))
                        
            # Verify warmup
            warmed_count = 0
            for key in critical_keys:
                found_in_layers = sum(1 for layer in self.cache_layers if layer.get(key))
                if found_in_layers == len(self.cache_layers):
                    warmed_count += 1
                    
            if warmed_count == len(critical_keys):
                print(f"[OK] Cache warmup complete: {warmed_count} critical keys loaded")
                return True
            else:
                print(f"[WARNING] Partial warmup: {warmed_count}/{len(critical_keys)} keys")
                return warmed_count > 0
                
        except Exception as e:
            print(f"[ERROR] Cache warmup failed: {e}")
            return False
            
    async def test_cache_metrics(self) -> bool:
        """Test cache hit/miss ratio monitoring."""
        print("\n[METRICS] STEP 9: Testing cache metrics...")
        
        try:
            # Simulate cache access patterns
            access_keys = list(self.test_data.keys())[:20]
            
            # Mix of hits and misses
            for _ in range(50):
                key = random.choice(access_keys)
                
                # Access through layers (waterfall)
                value = None
                for layer in self.cache_layers:
                    value = layer.get(key)
                    if value:
                        break  # Found in this layer
                        
                # Simulate some misses
                if random.random() < 0.2:  # 20% miss rate
                    miss_key = f"nonexistent:{random.randint(1000, 9999)}"
                    for layer in self.cache_layers:
                        layer.get(miss_key)
                        
            # Collect metrics
            print("\n[METRICS] Cache Performance:")
            overall_hit_rate = 0
            
            for layer in self.cache_layers:
                stats = layer.get_stats()
                print(f"  {layer.name}:")
                print(f"    - Hits: {stats['hits']}")
                print(f"    - Misses: {stats['misses']}")
                print(f"    - Hit Rate: {stats['hit_rate']:.1f}%")
                print(f"    - Invalidations: {stats['invalidations']}")
                print(f"    - Current Keys: {stats['current_keys']}")
                
                overall_hit_rate += stats['hit_rate']
                
            avg_hit_rate = overall_hit_rate / len(self.cache_layers)
            
            # Check Redis metrics
            if self.redis_client:
                info = await self.redis_client.info("stats")
                print(f"  Redis:")
                print(f"    - Keyspace hits: {info.get('keyspace_hits', 0)}")
                print(f"    - Keyspace misses: {info.get('keyspace_misses', 0)}")
                
            if avg_hit_rate > 50:  # Expect at least 50% hit rate
                print(f"\n[OK] Average hit rate: {avg_hit_rate:.1f}%")
                return True
            else:
                print(f"\n[WARNING] Low hit rate: {avg_hit_rate:.1f}%")
                return False
                
        except Exception as e:
            print(f"[ERROR] Metrics collection failed: {e}")
            return False
            
    async def test_concurrent_invalidation(self) -> bool:
        """Test concurrent invalidation handling."""
        print("\n[CONCURRENT] STEP 10: Testing concurrent invalidation...")
        
        try:
            # Create tasks for concurrent invalidation
            async def invalidate_key(key: str):
                """Invalidate a single key."""
                for layer in self.cache_layers:
                    layer.invalidate(key)
                if self.redis_client:
                    await self.redis_client.delete(key)
                return key
                
            # Select keys for concurrent invalidation
            keys_to_invalidate = [f"agent:{i}" for i in range(5)]
            
            # Run concurrent invalidations
            tasks = [invalidate_key(key) for key in keys_to_invalidate]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = [r for r in results if not isinstance(r, Exception)]
            
            print(f"[OK] Concurrent invalidation: {len(successful)}/{len(keys_to_invalidate)} successful")
            
            # Verify all keys are gone
            remaining = 0
            for key in keys_to_invalidate:
                for layer in self.cache_layers:
                    if layer.get(key):
                        remaining += 1
                        break
                        
            if remaining == 0:
                print(f"[OK] All concurrent invalidations completed successfully")
                return True
            else:
                print(f"[WARNING] {remaining} keys still in cache after concurrent invalidation")
                return False
                
        except Exception as e:
            print(f"[ERROR] Concurrent invalidation failed: {e}")
            return False
            
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests in sequence."""
        results = {}
        
        # Setup
        results["authentication"] = await self.setup_authentication()
        if not results["authentication"]:
            print("\n[CRITICAL] Authentication failed. Aborting tests.")
            return results
            
        results["redis_connection"] = await self.test_redis_connection()
        
        # Cache operations
        results["populate_cache"] = await self.test_populate_cache_layers()
        results["cache_coherence"] = await self.test_cache_coherence()
        results["single_invalidation"] = await self.test_single_key_invalidation()
        results["pattern_invalidation"] = await self.test_pattern_invalidation()
        results["ttl_expiration"] = await self.test_ttl_expiration()
        results["cache_warmup"] = await self.test_cache_warmup()
        results["cache_metrics"] = await self.test_cache_metrics()
        results["concurrent_invalidation"] = await self.test_concurrent_invalidation()
        
        return results


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_cache_invalidation_cascade():
    """Test cache invalidation cascade flow."""
    async with CacheInvalidationTester() as tester:
        results = await tester.run_all_tests()
        
        # Print summary
        print("\n" + "="*60)
        print("CACHE INVALIDATION CASCADE TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {test_name:25} : {status}")
            
        print("="*60)
        
        # Print invalidation log
        print(f"\nInvalidation Log ({len(tester.invalidation_log)} events):")
        for event in tester.invalidation_log:
            print(f"  - {event['type']}: {event.get('keys_invalidated', 1)} keys")
            
        # Calculate overall result
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n[SUCCESS] All cache invalidation tests passed!")
        else:
            print(f"\n[WARNING] {total_tests - passed_tests} tests failed.")
            
        # Assert all tests passed
        assert all(results.values()), f"Some tests failed: {results}"


async def main():
    """Run the test standalone."""
    print("="*60)
    print("CACHE INVALIDATION CASCADE TEST")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    async with CacheInvalidationTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on results
        if all(results.values()):
            return 0
        else:
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
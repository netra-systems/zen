"""
Cache Redis Invalidation Integration Tests

Tests focused on Redis-based cache invalidation including cascade propagation,
tag-based invalidation, and distributed cache consistency.

Business Value Justification (BVJ):
1. Segment: Enterprise/Mid-tier ($50K-$100K MRR protection)
2. Business Goal: Data Consistency, Platform Stability, Risk Reduction
3. Value Impact: Prevents stale data corruption in AI responses
4. Strategic/Revenue Impact: Critical for enterprise customers requiring real-time consistency
"""

import pytest
import asyncio
import time
import uuid
import random
from typing import Dict, List, Set

from logging_config import central_logger
from netra_backend.tests.cache_invalidation_fixtures import (

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

    CacheInvalidationMetrics,
    MultiLayerCacheManager,
    CACHE_TEST_CONFIG,
    generate_test_data,
    populate_cache_layers
)

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
@pytest.mark.cache
@pytest.mark.asyncio
class TestCacheRedisInvalidation:
    """Redis-focused cache invalidation test suite."""
    
    @pytest.fixture(autouse=True)
    async def setup_redis_test_environment(self):
        """Setup Redis cache environment for testing."""
        self.metrics = CacheInvalidationMetrics()
        self.cache_manager = MultiLayerCacheManager(CACHE_TEST_CONFIG)
        await self.cache_manager.initialize()
        
        self.test_keys, self.test_values, self.test_tags = await generate_test_data()
        
        yield
        
        await self.cache_manager.cleanup()
    
    async def test_cascade_invalidation_propagation(self):
        """Test cascade invalidation propagates through all cache layers."""
        logger.info("Testing cascade invalidation propagation")
        
        await populate_cache_layers(self.cache_manager, self.test_keys, self.test_values, self.test_tags)
        self.metrics.start_measurement()
        
        test_keys = random.sample(self.test_keys, 50)
        
        for key in test_keys:
            cascade_time = await self.cache_manager.invalidate_cascade(key, tags={"user_data", "session_data"})
            self.metrics.record_cascade(cascade_time)
            
            consistency_check = await self.cache_manager.check_consistency(key)
            self.metrics.record_consistency_check(consistency_check)
            
            assert cascade_time < CACHE_TEST_CONFIG["performance_targets"]["cascade_propagation_ms"]
            assert consistency_check, f"Cache consistency violation detected for key {key}"
        
        self.metrics.end_measurement()
        
        avg_cascade_time = sum(self.metrics.cascade_times) / len(self.metrics.cascade_times)
        consistency_rate = (sum(self.metrics.consistency_checks) / len(self.metrics.consistency_checks)) * 100
        
        assert avg_cascade_time < CACHE_TEST_CONFIG["performance_targets"]["cascade_propagation_ms"]
        assert consistency_rate >= 100.0
        
        logger.info(f"Cascade test passed: avg_time={avg_cascade_time:.2f}ms, consistency={consistency_rate}%")
    
    async def test_tag_based_invalidation_redis(self):
        """Test tag-based cache invalidation across Redis layer."""
        logger.info("Testing Redis tag-based invalidation")
        
        tag_scenarios = {
            "user_session": [f"session:{i}" for i in range(20)],
            "ai_model_cache": [f"model:response:{i}" for i in range(15)],
            "schema_metadata": [f"schema:table:{i}" for i in range(10)]
        }
        
        for tag, keys in tag_scenarios.items():
            for key in keys:
                value = f"tagged_value_{tag}_{uuid.uuid4().hex[:8]}"
                await self.cache_manager.set_multi_layer(key, value, tags={tag})
        
        self.metrics.start_measurement()
        
        for tag, expected_keys in tag_scenarios.items():
            invalidation_start = time.time()
            
            batch_size = 5
            semaphore = asyncio.Semaphore(4)
            
            async def invalidate_key_batch(key_batch):
                async with semaphore:
                    tasks = [self.cache_manager.invalidate_cascade(key, tags={tag}) for key in key_batch]
                    return await asyncio.gather(*tasks, return_exceptions=True)
            
            batch_tasks = []
            for i in range(0, len(expected_keys), batch_size):
                batch = expected_keys[i:i + batch_size]
                batch_tasks.append(invalidate_key_batch(batch))
            
            await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            invalidated_count = 0
            for key in expected_keys:
                consistency_check = await self.cache_manager.check_consistency(key)
                self.metrics.record_consistency_check(consistency_check)
                if consistency_check:
                    invalidated_count += 1
            
            invalidation_rate = (invalidated_count / len(expected_keys)) * 100
            assert invalidation_rate >= 100.0
            
            logger.info(f"Tag invalidation {tag}: {invalidated_count}/{len(expected_keys)} keys")
        
        self.metrics.end_measurement()
        
        metrics_summary = self.metrics.get_summary()
        assert metrics_summary["consistency_metrics"]["consistency_success_rate"] == 100.0
        
        logger.info("Redis tag-based invalidation test passed")
    
    async def test_redis_distributed_consistency(self):
        """Test Redis distributed cache consistency validation."""
        logger.info("Testing Redis distributed consistency")
        
        consistency_scenarios = [
            {"key": "distributed:test:1", "layers": ["redis"], "value": "dist_value_1"},
            {"key": "distributed:test:2", "layers": ["l1_cache", "redis"], "value": "dist_value_2"},
            {"key": "distributed:test:3", "layers": ["l2_cache", "redis"], "value": "dist_value_3"}
        ]
        
        self.metrics.start_measurement()
        
        for scenario in consistency_scenarios:
            key = scenario["key"]
            value = scenario["value"]
            
            await self.cache_manager.set_multi_layer(key, value, tags={"distributed_test"})
            
            for layer in scenario["layers"]:
                retrieved_value = await self.cache_manager.get_from_layer(layer, key)
                assert retrieved_value == value, f"Value mismatch in {layer} for key {key}"
            
            invalidation_time = await self.cache_manager.invalidate_single_layer("redis", key)
            self.metrics.record_invalidation("redis", invalidation_time)
            
            redis_value = await self.cache_manager.get_from_layer("redis", key)
            assert redis_value is None, f"Redis value not invalidated for key {key}"
            
            consistency_check = await self.cache_manager.check_consistency(key)
            self.metrics.record_consistency_check(consistency_check)
        
        self.metrics.end_measurement()
        
        metrics_summary = self.metrics.get_summary()
        assert metrics_summary["performance_metrics"]["avg_invalidation_ms"] < CACHE_TEST_CONFIG["performance_targets"]["invalidation_latency_ms"]
        
        logger.info("Redis distributed consistency test passed")
    
    async def test_redis_concurrent_invalidation(self):
        """Test concurrent Redis invalidation operations."""
        logger.info("Testing Redis concurrent invalidation")
        
        concurrent_keys = [f"concurrent:redis:{i}" for i in range(30)]
        
        for key in concurrent_keys:
            value = f"concurrent_value_{uuid.uuid4().hex[:8]}"
            await self.cache_manager.set_multi_layer(key, value, tags={"concurrent_test"})
        
        self.metrics.start_measurement()
        
        async def concurrent_invalidation_worker(worker_keys):
            for key in worker_keys:
                invalidation_time = await self.cache_manager.invalidate_cascade(key)
                self.metrics.record_cascade(invalidation_time)
                
                consistency_check = await self.cache_manager.check_consistency(key)
                self.metrics.record_consistency_check(consistency_check)
        
        batch_size = 10
        worker_tasks = []
        for i in range(0, len(concurrent_keys), batch_size):
            batch = concurrent_keys[i:i + batch_size]
            worker_tasks.append(concurrent_invalidation_worker(batch))
        
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        
        self.metrics.end_measurement()
        
        consistency_rate = (sum(self.metrics.consistency_checks) / len(self.metrics.consistency_checks)) * 100
        avg_cascade_time = sum(self.metrics.cascade_times) / len(self.metrics.cascade_times)
        
        assert consistency_rate >= 95.0
        assert avg_cascade_time < CACHE_TEST_CONFIG["performance_targets"]["cascade_propagation_ms"] * 2
        
        logger.info(f"Concurrent Redis invalidation passed: {consistency_rate}% consistency, {avg_cascade_time:.2f}ms avg")
    
    async def test_redis_connection_resilience(self):
        """Test Redis invalidation with connection issues."""
        logger.info("Testing Redis connection resilience")
        
        test_key = "resilience:test:key"
        test_value = "resilience_test_value"
        
        await self.cache_manager.set_multi_layer(test_key, test_value)
        
        original_client = self.cache_manager.redis_client
        
        try:
            # Simulate Redis connection issue
            self.cache_manager.redis_client = None
            
            # Should still work with local cache layers
            invalidation_time = await self.cache_manager.invalidate_single_layer("l1_cache", test_key)
            assert invalidation_time >= 0
            
            # Restore connection
            self.cache_manager.redis_client = original_client
            
            # Test full cascade after restoration
            cascade_time = await self.cache_manager.invalidate_cascade(test_key)
            assert cascade_time < CACHE_TEST_CONFIG["performance_targets"]["cascade_propagation_ms"] * 2
            
            logger.info("Redis resilience test passed")
            
        finally:
            self.cache_manager.redis_client = original_client
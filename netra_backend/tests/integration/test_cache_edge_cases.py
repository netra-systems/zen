"""
Cache Edge Cases Integration Tests

Tests focused on edge cases, error conditions, and comprehensive
cache invalidation validation scenarios.

Business Value Justification (BVJ):
1. Segment: Enterprise/Mid-tier ($50K-$100K MRR protection)
2. Business Goal: Risk Reduction, System Resilience
3. Value Impact: Ensures system stability under edge conditions
4. Strategic/Revenue Impact: Prevents cache-related failures in production
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import random
import time
import uuid
from typing import Dict, List

import pytest
from logging_config import central_logger

from netra_backend.tests.integration.cache_invalidation_fixtures import (
    CACHE_TEST_CONFIG,
    CacheInvalidationMetrics,
    MultiLayerCacheManager,
    generate_test_data,
)

logger = central_logger.get_logger(__name__)

@pytest.mark.integration
@pytest.mark.cache
@pytest.mark.asyncio
class TestCacheEdgeCases:
    """Edge cases focused cache test suite."""
    
    @pytest.fixture(autouse=True)
    async def setup_edge_cases_environment(self):
        """Setup cache environment for edge cases testing."""
        self.metrics = CacheInvalidationMetrics()
        self.cache_manager = MultiLayerCacheManager(CACHE_TEST_CONFIG)
        await self.cache_manager.initialize()
        
        self.test_keys, self.test_values, self.test_tags = await generate_test_data()
        
        yield
        
        await self.cache_manager.cleanup()
    
    async def test_empty_cache_invalidation(self):
        """Test invalidation operations on empty cache."""
        logger.info("Testing empty cache invalidation")
        
        empty_test_keys = [f"empty:test:{i}" for i in range(10)]
        
        self.metrics.start_measurement()
        
        for key in empty_test_keys:
            cascade_time = await self.cache_manager.invalidate_cascade(key)
            self.metrics.record_cascade(cascade_time)
            
            consistency_check = await self.cache_manager.check_consistency(key)
            self.metrics.record_consistency_check(consistency_check)
            
            assert cascade_time >= 0, f"Invalid cascade time for empty key {key}"
            assert consistency_check, f"Empty cache consistency failed for {key}"
        
        self.metrics.end_measurement()
        
        avg_cascade_time = sum(self.metrics.cascade_times) / len(self.metrics.cascade_times)
        assert avg_cascade_time < CACHE_TEST_CONFIG["performance_targets"]["cascade_propagation_ms"]
        
        logger.info(f"Empty cache invalidation passed: avg_time={avg_cascade_time:.2f}ms")
    
    async def test_large_value_invalidation(self):
        """Test invalidation of large cache values."""
        logger.info("Testing large value invalidation")
        
        large_value_sizes = [1024, 4096, 8192]  # bytes
        
        self.metrics.start_measurement()
        
        for size in large_value_sizes:
            key = f"large:value:{size}"
            large_value = "x" * size  # Create large string value
            
            success = await self.cache_manager.set_multi_layer(key, large_value, tags={"large_test"})
            assert success, f"Failed to set large value of size {size}"
            
            cascade_time = await self.cache_manager.invalidate_cascade(key)
            self.metrics.record_cascade(cascade_time)
            
            consistency_check = await self.cache_manager.check_consistency(key)
            self.metrics.record_consistency_check(consistency_check)
            
            assert consistency_check, f"Large value consistency failed for size {size}"
            assert cascade_time < CACHE_TEST_CONFIG["performance_targets"]["cascade_propagation_ms"] * 3
            
            logger.info(f"Large value {size} bytes invalidated in {cascade_time:.2f}ms")
        
        self.metrics.end_measurement()
        
        metrics_summary = self.metrics.get_summary()
        assert metrics_summary["consistency_metrics"]["consistency_success_rate"] == 100.0
        
        logger.info("Large value invalidation test passed")
    
    async def test_special_character_keys(self):
        """Test invalidation with special character keys."""
        logger.info("Testing special character keys")
        
        special_keys = ["key:with:colons", "key-with-dashes", "key_with_underscores", "key.with.dots", "key with spaces"]
        
        self.metrics.start_measurement()
        
        for key in special_keys:
            value = f"special_value_{uuid.uuid4().hex[:8]}"
            
            try:
                success = await self.cache_manager.set_multi_layer(key, value, tags={"special_test"})
                if success:
                    cascade_time = await self.cache_manager.invalidate_cascade(key)
                    self.metrics.record_cascade(cascade_time)
                    
                    consistency_check = await self.cache_manager.check_consistency(key)
                    self.metrics.record_consistency_check(consistency_check)
                    assert consistency_check, f"Special character key consistency failed: {key}"
                
            except Exception as e:
                logger.warning(f"Special key {key} caused exception: {e}")
        
        self.metrics.end_measurement()
        
        if self.metrics.consistency_checks:
            consistency_rate = (sum(self.metrics.consistency_checks) / len(self.metrics.consistency_checks)) * 100
            assert consistency_rate >= 90.0, f"Special character consistency rate {consistency_rate}% too low"
        
        logger.info("Special character keys test passed")
    
    async def test_concurrent_access_patterns(self):
        """Test various concurrent access patterns."""
        logger.info("Testing concurrent access patterns")
        
        concurrent_test_key = "concurrent:access:test"
        concurrent_value = "concurrent_test_value"
        
        self.metrics.start_measurement()
        
        async def concurrent_reader():
            for _ in range(5):
                value = await self.cache_manager.get_from_layer("l1_cache", concurrent_test_key)
                await asyncio.sleep(0.001)
        
        async def concurrent_writer():
            for i in range(3):
                new_value = f"{concurrent_value}_{i}"
                await self.cache_manager.set_multi_layer(concurrent_test_key, new_value)
                await asyncio.sleep(0.002)
        
        async def concurrent_invalidator():
            for _ in range(2):
                await asyncio.sleep(0.003)
                cascade_time = await self.cache_manager.invalidate_cascade(concurrent_test_key)
                self.metrics.record_cascade(cascade_time)
        
        await self.cache_manager.set_multi_layer(concurrent_test_key, concurrent_value)
        
        tasks = [
            concurrent_reader(),
            concurrent_reader(),
            concurrent_writer(),
            concurrent_invalidator()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        final_consistency = await self.cache_manager.check_consistency(concurrent_test_key)
        self.metrics.record_consistency_check(final_consistency)
        
        self.metrics.end_measurement()
        
        assert final_consistency, "Concurrent access pattern consistency failed"
        
        logger.info("Concurrent access patterns test passed")
    
    async def test_memory_pressure_scenarios(self):
        """Test cache behavior under memory pressure."""
        logger.info("Testing memory pressure scenarios")
        
        pressure_keys = [f"pressure:test:{i}" for i in range(100)]  # Reduced size
        
        self.metrics.start_measurement()
        
        for key in pressure_keys:
            value = f"pressure_value_{uuid.uuid4().hex[:16]}"
            await self.cache_manager.set_multi_layer(key, value, tags={"pressure_test"})
        
        batch_tasks = [self.cache_manager.invalidate_cascade(key) for key in pressure_keys]
        cascade_times = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        for cascade_time in cascade_times:
            if isinstance(cascade_time, (int, float)):
                self.metrics.record_cascade(cascade_time)
        
        self.metrics.end_measurement()
        
        metrics_summary = self.metrics.get_summary()
        assert metrics_summary["consistency_metrics"]["consistency_success_rate"] >= 85.0
        
        logger.info("Memory pressure scenarios test passed")
    
    async def test_network_partition_simulation(self):
        """Test cache behavior during simulated network partitions."""
        logger.info("Testing network partition simulation")
        
        partition_test_key = "partition:test:key"
        partition_test_value = "partition_test_value"
        
        await self.cache_manager.set_multi_layer(partition_test_key, partition_test_value)
        
        self.metrics.start_measurement()
        
        original_redis_client = self.cache_manager.redis_client
        
        try:
            # Simulate network partition by disabling Redis
            self.cache_manager.redis_client = None
            
            local_cascade_time = await self.cache_manager.invalidate_cascade(partition_test_key)
            self.metrics.record_cascade(local_cascade_time)
            
            # Should still work with local caches
            assert local_cascade_time >= 0, "Local invalidation failed during partition"
            
            # Restore Redis connection
            self.cache_manager.redis_client = original_redis_client
            
            # Test recovery
            recovery_cascade_time = await self.cache_manager.invalidate_cascade(partition_test_key)
            self.metrics.record_cascade(recovery_cascade_time)
            
            final_consistency = await self.cache_manager.check_consistency(partition_test_key)
            self.metrics.record_consistency_check(final_consistency)
            
            assert final_consistency, "Recovery consistency failed"
            
        finally:
            self.cache_manager.redis_client = original_redis_client
        
        self.metrics.end_measurement()
        
        logger.info("Network partition simulation test passed")
    
    async def test_extreme_load_conditions(self):
        """Test cache invalidation under extreme load conditions."""
        logger.info("Testing extreme load conditions")
        
        extreme_load_keys = [f"extreme:load:{i}" for i in range(100)]
        
        for key in extreme_load_keys:
            value = f"extreme_value_{uuid.uuid4().hex[:8]}"
            await self.cache_manager.set_multi_layer(key, value, tags={"extreme_test"})
        
        self.metrics.start_measurement()
        
        # High concurrency invalidation
        semaphore = asyncio.Semaphore(20)  # Higher concurrency
        
        async def extreme_invalidation_worker(key):
            async with semaphore:
                cascade_time = await self.cache_manager.invalidate_cascade(key)
                self.metrics.record_cascade(cascade_time)
                
                consistency_check = await self.cache_manager.check_consistency(key)
                self.metrics.record_consistency_check(consistency_check)
                return consistency_check
        
        extreme_tasks = [extreme_invalidation_worker(key) for key in extreme_load_keys]
        results = await asyncio.gather(*extreme_tasks, return_exceptions=True)
        
        success_count = sum(1 for result in results if result is True)
        success_rate = (success_count / len(extreme_load_keys)) * 100
        
        self.metrics.end_measurement()
        
        assert success_rate >= 80.0, f"Extreme load success rate {success_rate}% below 80%"
        
        logger.info(f"Extreme load conditions test passed: {success_rate}% success rate")

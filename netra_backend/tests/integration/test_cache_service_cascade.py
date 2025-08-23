"""
Cache Service Cascade Integration Tests

Tests focused on cache warming performance, race condition prevention,
and service-level cache invalidation patterns.

Business Value Justification (BVJ):
1. Segment: Enterprise/Mid-tier ($50K-$100K MRR protection)
2. Business Goal: Performance Optimization, Service Reliability
3. Value Impact: Ensures optimal cache warming and service coordination
4. Strategic/Revenue Impact: Prevents performance degradation in high-load scenarios
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
from netra_backend.app.logging_config import central_logger

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
class TestCacheServiceCascade:
    """Service cascade focused cache test suite."""
    
    @pytest.fixture(autouse=True)
    async def setup_service_cascade_environment(self):
        """Setup cache environment for service cascade testing."""
        self.metrics = CacheInvalidationMetrics()
        self.cache_manager = MultiLayerCacheManager(CACHE_TEST_CONFIG)
        await self.cache_manager.initialize()
        
        self.test_keys, self.test_values, self.test_tags = await generate_test_data()
        
        yield
        
        await self.cache_manager.cleanup()
    
    async def test_cache_warming_performance(self):
        """Validate cache warming performance and consistency."""
        logger.info("Testing cache warming performance")
        
        warming_scenarios = [
            {"name": "small_batch", "key_count": 50, "target_time_ms": 500},
            {"name": "medium_batch", "key_count": 200, "target_time_ms": 1500},
            {"name": "large_batch", "key_count": 500, "target_time_ms": 3000}
        ]
        
        async def value_generator(key: str) -> str:
            """Generate test values for cache warming."""
            return f"warmed_value_{key}_{uuid.uuid4().hex[:8]}"
        
        self.metrics.start_measurement()
        
        for scenario in warming_scenarios:
            scenario_name = scenario["name"]
            key_count = scenario["key_count"]
            target_time = scenario["target_time_ms"]
            
            warming_keys = [f"warm:{scenario_name}:{i}" for i in range(key_count)]
            
            warming_time = await self.cache_manager.warm_cache(warming_keys, value_generator)
            self.metrics.record_warming(warming_time)
            
            warming_success_count = 0
            for key in warming_keys:
                found_in_layer = False
                for layer_name in self.cache_manager.layers.keys():
                    value = await self.cache_manager.get_from_layer(layer_name, key)
                    if value is not None and "warmed_value" in value:
                        found_in_layer = True
                        break
                
                if found_in_layer:
                    warming_success_count += 1
            
            warming_success_rate = (warming_success_count / key_count) * 100
            
            assert warming_time < target_time, f"Warming for {scenario_name} took {warming_time}ms, exceeds {target_time}ms"
            assert warming_success_rate >= 95.0, f"Warming success rate {warming_success_rate}% below 95%"
            
            logger.info(f"Cache warming {scenario_name}: {warming_time:.2f}ms, {warming_success_rate}% success")
        
        self.metrics.end_measurement()
        
        metrics_summary = self.metrics.get_summary()
        avg_warming_time = metrics_summary["performance_metrics"]["avg_warming_ms"]
        
        assert avg_warming_time < CACHE_TEST_CONFIG["performance_targets"]["cache_warming_latency_ms"]
        
        logger.info(f"Cache warming test passed: avg_time={avg_warming_time:.2f}ms")
    
    async def test_race_condition_prevention(self):
        """Validate prevention of race conditions during concurrent invalidation."""
        logger.info("Testing race condition prevention")
        
        num_workers = CACHE_TEST_CONFIG["test_data"]["num_workers"]
        operations_per_worker = 8
        test_key_base = "race:test"
        
        race_condition_detected = []
        operation_results = []
        
        async def concurrent_worker(worker_id: int):
            """Worker performing concurrent cache operations."""
            worker_results = []
            worker_semaphore = asyncio.Semaphore(2)
            
            for i in range(operations_per_worker):
                key = f"{test_key_base}:{worker_id}:{i}"
                value = f"worker_{worker_id}_value_{i}"
                operation_start = time.time()
                
                try:
                    async with worker_semaphore:
                        if i % 3 == 0:
                            success = await self.cache_manager.set_multi_layer(key, value, tags={"race_test"})
                            operation_time = (time.time() - operation_start) * 1000
                            worker_results.append(("set", key, operation_time, success))
                            
                        elif i % 3 == 1:
                            await self.cache_manager.set_multi_layer(key, value)
                            retrieved = await self.cache_manager.get_from_layer("l1_cache", key)
                            operation_time = (time.time() - operation_start) * 1000
                            worker_results.append(("get", key, operation_time, retrieved is not None))
                            
                        else:
                            await self.cache_manager.set_multi_layer(key, value)
                            await self.cache_manager.invalidate_cascade(key)
                            operation_time = (time.time() - operation_start) * 1000
                            worker_results.append(("invalidate", key, operation_time, True))
                            
                            await asyncio.sleep(0.001)
                            consistency = await self.cache_manager.check_consistency(key)
                            if not consistency:
                                race_condition_detected.append({
                                    "worker_id": worker_id,
                                    "key": key,
                                    "timestamp": time.time(),
                                    "operation": "invalidate"
                                })
                
                except Exception as e:
                    operation_time = (time.time() - operation_start) * 1000
                    worker_results.append(("error", key, operation_time, False))
                    logger.error(f"Worker {worker_id} operation failed: {e}")
                
                await asyncio.sleep(0.002)
            
            return worker_results
        
        self.metrics.start_measurement()
        
        tasks = [concurrent_worker(i) for i in range(num_workers)]
        worker_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for worker_result in worker_results:
            if isinstance(worker_result, list):
                operation_results.extend(worker_result)
        
        self.metrics.end_measurement()
        
        race_condition_count = len(race_condition_detected)
        total_operations = len(operation_results)
        success_operations = sum(1 for op in operation_results if op[3])
        
        for race_condition in race_condition_detected:
            self.metrics.record_race_condition(race_condition)
        
        success_rate = (success_operations / total_operations) if total_operations > 0 else 0
        
        assert race_condition_count == 0, f"Race conditions detected: {race_condition_count} instances"
        assert success_rate >= 0.70, f"Too many failed operations: {success_rate*100:.1f}% success (need >= 70%)"
        
        logger.info(f"Race condition test passed: {total_operations} operations, {success_operations} successful")
    
    async def test_service_level_invalidation(self):
        """Test service-level cache invalidation patterns."""
        logger.info("Testing service-level invalidation")
        
        service_scenarios = {
            "auth_service": [f"auth:session:{i}" for i in range(15)],
            "user_service": [f"user:profile:{i}" for i in range(20)],
            "ai_service": [f"ai:response:{i}" for i in range(25)]
        }
        
        for service, keys in service_scenarios.items():
            for key in keys:
                value = f"service_value_{service}_{uuid.uuid4().hex[:8]}"
                await self.cache_manager.set_multi_layer(key, value, tags={service})
        
        self.metrics.start_measurement()
        
        for service, service_keys in service_scenarios.items():
            invalidation_start = time.time()
            
            async def invalidate_service_key(key):
                return await self.cache_manager.invalidate_cascade(key, tags={service})
            
            invalidation_tasks = [invalidate_service_key(key) for key in service_keys]
            await asyncio.gather(*invalidation_tasks, return_exceptions=True)
            
            total_invalidation_time = (time.time() - invalidation_start) * 1000
            
            invalidated_count = 0
            for key in service_keys:
                consistency_check = await self.cache_manager.check_consistency(key)
                self.metrics.record_consistency_check(consistency_check)
                if consistency_check:
                    invalidated_count += 1
            
            invalidation_success_rate = (invalidated_count / len(service_keys)) * 100
            avg_time_per_key = total_invalidation_time / len(service_keys)
            
            assert invalidation_success_rate >= 95.0, f"Service invalidation incomplete for {service}"
            assert avg_time_per_key < CACHE_TEST_CONFIG["performance_targets"]["invalidation_latency_ms"] * 2
            
            logger.info(f"Service invalidation {service}: {invalidated_count}/{len(service_keys)} keys")
        
        self.metrics.end_measurement()
        
        metrics_summary = self.metrics.get_summary()
        assert metrics_summary["consistency_metrics"]["consistency_success_rate"] >= 95.0
        
        logger.info("Service-level invalidation test passed")
    
    async def test_cascade_propagation_timing(self):
        """Test timing and performance of cascade propagation."""
        logger.info("Testing cascade propagation timing")
        
        propagation_test_keys = [f"propagation:test:{i}" for i in range(30)]
        
        for key in propagation_test_keys:
            value = f"propagation_value_{uuid.uuid4().hex[:8]}"
            await self.cache_manager.set_multi_layer(key, value, tags={"propagation_test"})
        
        self.metrics.start_measurement()
        
        propagation_times = []
        
        for key in propagation_test_keys:
            start_time = time.time()
            
            cascade_time = await self.cache_manager.invalidate_cascade(key)
            self.metrics.record_cascade(cascade_time)
            
            await asyncio.sleep(0.001)
            
            consistency_check = await self.cache_manager.check_consistency(key)
            self.metrics.record_consistency_check(consistency_check)
            
            total_propagation_time = (time.time() - start_time) * 1000
            propagation_times.append(total_propagation_time)
            
            assert consistency_check, f"Propagation consistency failed for {key}"
            assert cascade_time < CACHE_TEST_CONFIG["performance_targets"]["cascade_propagation_ms"]
        
        self.metrics.end_measurement()
        
        avg_propagation_time = sum(propagation_times) / len(propagation_times)
        max_propagation_time = max(propagation_times)
        
        assert avg_propagation_time < CACHE_TEST_CONFIG["performance_targets"]["cascade_propagation_ms"]
        assert max_propagation_time < CACHE_TEST_CONFIG["performance_targets"]["cascade_propagation_ms"] * 2
        
        logger.info(f"Cascade propagation test passed: avg={avg_propagation_time:.2f}ms, max={max_propagation_time:.2f}ms")
    
    async def test_batch_invalidation_efficiency(self):
        """Test efficiency of batch invalidation operations."""
        logger.info("Testing batch invalidation efficiency")
        
        batch_sizes = [10, 25, 50]
        self.metrics.start_measurement()
        
        for batch_size in batch_sizes:
            batch_keys = [f"batch:{batch_size}:{i}" for i in range(batch_size)]
            
            for key in batch_keys:
                value = f"batch_value_{batch_size}_{uuid.uuid4().hex[:8]}"
                await self.cache_manager.set_multi_layer(key, value, tags={"batch_test"})
            
            batch_start = time.time()
            batch_tasks = [self.cache_manager.invalidate_cascade(key) for key in batch_keys]
            await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            batch_time = (time.time() - batch_start) * 1000
            avg_time_per_key = batch_time / batch_size
            throughput = batch_size / (batch_time / 1000)
            
            assert avg_time_per_key < CACHE_TEST_CONFIG["performance_targets"]["invalidation_latency_ms"]
            assert throughput > 10, f"Batch throughput {throughput:.2f} ops/sec too low for batch size {batch_size}"
            
            logger.info(f"Batch size {batch_size}: {avg_time_per_key:.2f}ms/key, {throughput:.2f} ops/sec")
        
        self.metrics.end_measurement()
        logger.info("Batch invalidation efficiency test passed")
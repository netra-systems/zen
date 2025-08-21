"""Cache TTL Expiration Accuracy - L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (TTL accuracy affects cache efficiency across all user segments)
- Business Goal: Ensure precise TTL expiration for optimal cache management and memory usage
- Value Impact: Prevents stale data, optimizes memory usage, maintains cache effectiveness
- Strategic Impact: $3K MRR protection through accurate cache management and resource optimization

Critical Path: TTL setting -> Expiration monitoring -> Accuracy validation -> Memory optimization
L3 Realism: Real Redis with actual TTL mechanisms, precision timing tests, memory impact analysis
Performance Requirements: TTL accuracy > 99.5%, expiration variance < 50ms, memory recovery > 95%
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
import random
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import redis.asyncio as aioredis
import statistics

from tests.integration.helpers.redis_l3_helpers import RedisContainer as NetraRedisContainer
from logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class TTLAccuracyMetrics:
    """Metrics for TTL expiration accuracy testing."""
    ttl_tests: int = 0
    accurate_expirations: int = 0
    early_expirations: int = 0
    late_expirations: int = 0
    expiration_variances: List[float] = None
    memory_before_expiration: List[int] = None
    memory_after_expiration: List[int] = None
    ttl_precision_samples: List[float] = None
    
    def __post_init__(self):
        if self.expiration_variances is None:
            self.expiration_variances = []
        if self.memory_before_expiration is None:
            self.memory_before_expiration = []
        if self.memory_after_expiration is None:
            self.memory_after_expiration = []
        if self.ttl_precision_samples is None:
            self.ttl_precision_samples = []
    
    @property
    def ttl_accuracy_rate(self) -> float:
        """Calculate TTL accuracy rate."""
        if self.ttl_tests == 0:
            return 100.0
        return (self.accurate_expirations / self.ttl_tests) * 100.0
    
    @property
    def avg_expiration_variance(self) -> float:
        """Calculate average expiration variance."""
        return statistics.mean(self.expiration_variances) if self.expiration_variances else 0.0
    
    @property
    def memory_recovery_rate(self) -> float:
        """Calculate memory recovery rate after expiration."""
        if not self.memory_before_expiration or not self.memory_after_expiration:
            return 100.0
        
        avg_before = statistics.mean(self.memory_before_expiration)
        avg_after = statistics.mean(self.memory_after_expiration)
        
        if avg_before == 0:
            return 100.0
        
        return ((avg_before - avg_after) / avg_before) * 100.0


class CacheTTLExpirationAccuracyL3Manager:
    """L3 cache TTL expiration accuracy test manager with real Redis TTL mechanisms."""
    
    def __init__(self):
        self.redis_containers = {}
        self.redis_clients = {}
        self.metrics = TTLAccuracyMetrics()
        self.test_keys = set()
        self.ttl_test_scenarios = ["short_ttl", "medium_ttl", "long_ttl", "mixed_ttl"]
        
    async def setup_redis_for_ttl_testing(self) -> Dict[str, str]:
        """Setup Redis instances for TTL accuracy testing."""
        redis_configs = {
            "ttl_primary": {"port": 6440, "role": "primary TTL testing"},
            "ttl_precision": {"port": 6441, "role": "precision TTL testing"},
            "ttl_memory": {"port": 6442, "role": "memory impact testing"},
            "ttl_bulk": {"port": 6443, "role": "bulk TTL testing"}
        }
        
        redis_urls = {}
        
        for name, config in redis_configs.items():
            try:
                container = NetraRedisContainer(port=config["port"])
                container.container_name = f"netra-ttl-{name}-{uuid.uuid4().hex[:8]}"
                
                url = await container.start()
                
                self.redis_containers[name] = container
                redis_urls[name] = url
                
                # Create Redis client
                client = aioredis.from_url(url, decode_responses=True)
                await client.ping()
                self.redis_clients[name] = client
                
                logger.info(f"Redis {name} ({config['role']}) started: {url}")
                
            except Exception as e:
                logger.error(f"Failed to start Redis {name}: {e}")
                raise
        
        return redis_urls
    
    async def test_ttl_expiration_accuracy(self, ttl_seconds: float, test_count: int, redis_instance: str = "ttl_primary") -> Dict[str, Any]:
        """Test TTL expiration accuracy for specific TTL value."""
        client = self.redis_clients[redis_instance]
        
        accuracy_results = {
            "ttl_seconds": ttl_seconds,
            "test_count": test_count,
            "accurate_expirations": 0,
            "early_expirations": 0,
            "late_expirations": 0,
            "expiration_variances": [],
            "accuracy_rate": 0.0
        }
        
        # Tolerance for TTL accuracy (Redis typically has ~1ms precision)
        tolerance = 0.050  # 50ms tolerance
        
        for test_id in range(test_count):
            key = f"ttl_test_{ttl_seconds}_{test_id}_{uuid.uuid4().hex[:8]}"
            value = {
                "data": f"ttl_test_data_{test_id}",
                "ttl": ttl_seconds,
                "set_time": time.time()
            }
            
            # Set key with TTL
            set_time = time.time()
            await client.setex(key, int(ttl_seconds), json.dumps(value))
            self.test_keys.add(key)
            
            # Monitor expiration
            expected_expiration = set_time + ttl_seconds
            
            # Check if key exists just before expected expiration
            await asyncio.sleep(max(0, ttl_seconds - 0.1))  # Wait until 100ms before expiration
            
            # Poll for expiration with high precision
            expiration_detected = False
            actual_expiration_time = None
            
            while time.time() < expected_expiration + tolerance:
                current_time = time.time()
                exists = await client.exists(key)
                
                if not exists and not expiration_detected:
                    actual_expiration_time = current_time
                    expiration_detected = True
                    break
                
                await asyncio.sleep(0.001)  # 1ms polling interval
            
            if not expiration_detected:
                # Key didn't expire within tolerance - late expiration
                actual_expiration_time = time.time()
                accuracy_results["late_expirations"] += 1
            else:
                # Calculate variance
                variance = actual_expiration_time - expected_expiration
                accuracy_results["expiration_variances"].append(variance)
                self.metrics.expiration_variances.append(variance)
                
                if abs(variance) <= tolerance:
                    accuracy_results["accurate_expirations"] += 1
                    self.metrics.accurate_expirations += 1
                elif variance < 0:
                    accuracy_results["early_expirations"] += 1
                    self.metrics.early_expirations += 1
                else:
                    accuracy_results["late_expirations"] += 1
                    self.metrics.late_expirations += 1
            
            self.metrics.ttl_tests += 1
        
        accuracy_results["accuracy_rate"] = (accuracy_results["accurate_expirations"] / test_count) * 100.0
        
        return accuracy_results
    
    async def test_ttl_precision_under_load(self, concurrent_ttls: int, ttl_range: Tuple[float, float]) -> Dict[str, Any]:
        """Test TTL precision under concurrent load."""
        min_ttl, max_ttl = ttl_range
        
        async def concurrent_ttl_test(test_id: int):
            client = self.redis_clients["ttl_precision"]
            ttl = random.uniform(min_ttl, max_ttl)
            
            key = f"precision_test_{test_id}_{uuid.uuid4().hex[:8]}"
            value = {"data": f"precision_data_{test_id}", "ttl": ttl}
            
            set_time = time.time()
            await client.setex(key, int(ttl * 1000) / 1000, json.dumps(value))  # Millisecond precision
            self.test_keys.add(key)
            
            # Wait for expiration
            await asyncio.sleep(ttl + 0.1)  # Wait a bit past expiration
            
            # Check if expired
            exists = await client.exists(key)
            actual_expiration_time = time.time()
            
            expected_expiration = set_time + ttl
            variance = actual_expiration_time - expected_expiration if not exists else None
            
            return {
                "test_id": test_id,
                "ttl": ttl,
                "set_time": set_time,
                "expected_expiration": expected_expiration,
                "expired_correctly": not exists,
                "variance": variance
            }
        
        # Execute concurrent TTL tests
        tasks = [concurrent_ttl_test(i) for i in range(concurrent_ttls)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze precision results
        successful_tests = [r for r in results if not isinstance(r, Exception)]
        correct_expirations = [r for r in successful_tests if r["expired_correctly"]]
        
        variances = [r["variance"] for r in correct_expirations if r["variance"] is not None]
        self.metrics.ttl_precision_samples.extend(variances)
        
        return {
            "concurrent_ttls": concurrent_ttls,
            "ttl_range": ttl_range,
            "total_tests": len(successful_tests),
            "correct_expirations": len(correct_expirations),
            "precision_rate": (len(correct_expirations) / len(successful_tests) * 100) if successful_tests else 0,
            "avg_variance": statistics.mean(variances) if variances else 0,
            "max_variance": max(variances) if variances else 0,
            "total_time": total_time
        }
    
    async def test_memory_recovery_after_ttl_expiration(self, key_count: int, data_size_kb: int) -> Dict[str, Any]:
        """Test memory recovery after TTL expiration."""
        client = self.redis_clients["ttl_memory"]
        
        # Get initial memory usage
        initial_info = await client.info("memory")
        initial_memory = int(initial_info.get("used_memory", 0))
        
        # Create keys with data
        test_keys = []
        data_payload = "x" * (data_size_kb * 1024)  # KB of data
        ttl_seconds = 2.0  # 2 second TTL
        
        for i in range(key_count):
            key = f"memory_test_{i}_{uuid.uuid4().hex[:8]}"
            value = {
                "data": data_payload,
                "index": i,
                "size_kb": data_size_kb
            }
            
            await client.setex(key, int(ttl_seconds), json.dumps(value))
            test_keys.append(key)
            self.test_keys.add(key)
        
        # Measure peak memory usage
        peak_info = await client.info("memory")
        peak_memory = int(peak_info.get("used_memory", 0))
        self.metrics.memory_before_expiration.append(peak_memory)
        
        # Wait for TTL expiration
        await asyncio.sleep(ttl_seconds + 0.5)  # Wait for expiration + buffer
        
        # Verify keys are expired
        expired_keys = 0
        for key in test_keys:
            if not await client.exists(key):
                expired_keys += 1
        
        # Measure memory after expiration
        await asyncio.sleep(0.5)  # Allow garbage collection
        post_expiration_info = await client.info("memory")
        post_expiration_memory = int(post_expiration_info.get("used_memory", 0))
        self.metrics.memory_after_expiration.append(post_expiration_memory)
        
        # Calculate memory recovery
        memory_used = peak_memory - initial_memory
        memory_recovered = peak_memory - post_expiration_memory
        recovery_rate = (memory_recovered / memory_used * 100) if memory_used > 0 else 100.0
        
        return {
            "key_count": key_count,
            "data_size_kb": data_size_kb,
            "ttl_seconds": ttl_seconds,
            "initial_memory": initial_memory,
            "peak_memory": peak_memory,
            "post_expiration_memory": post_expiration_memory,
            "memory_used": memory_used,
            "memory_recovered": memory_recovered,
            "recovery_rate": recovery_rate,
            "expired_keys": expired_keys,
            "expiration_rate": (expired_keys / key_count * 100) if key_count > 0 else 0
        }
    
    async def test_bulk_ttl_accuracy(self, bulk_size: int, ttl_distribution: Dict[str, int]) -> Dict[str, Any]:
        """Test TTL accuracy for bulk operations with different TTL values."""
        client = self.redis_clients["ttl_bulk"]
        
        # Create bulk data with different TTLs
        bulk_keys = {}
        set_times = {}
        
        for ttl_category, ttl_seconds in ttl_distribution.items():
            category_keys = []
            
            for i in range(bulk_size // len(ttl_distribution)):
                key = f"bulk_{ttl_category}_{i}_{uuid.uuid4().hex[:8]}"
                value = {
                    "data": f"bulk_data_{ttl_category}_{i}",
                    "ttl_category": ttl_category,
                    "ttl_seconds": ttl_seconds
                }
                
                set_time = time.time()
                await client.setex(key, ttl_seconds, json.dumps(value))
                
                category_keys.append(key)
                set_times[key] = set_time
                self.test_keys.add(key)
            
            bulk_keys[ttl_category] = category_keys
        
        # Monitor expiration for all TTL categories
        expiration_results = {}
        
        for ttl_category, ttl_seconds in ttl_distribution.items():
            await asyncio.sleep(ttl_seconds + 0.2)  # Wait for expiration + buffer
            
            category_keys = bulk_keys[ttl_category]
            expired_count = 0
            variance_sum = 0
            
            for key in category_keys:
                exists = await client.exists(key)
                if not exists:
                    expired_count += 1
                    # Calculate approximate variance
                    expected_expiration = set_times[key] + ttl_seconds
                    actual_expiration = time.time()  # Approximate
                    variance = actual_expiration - expected_expiration
                    variance_sum += abs(variance)
            
            expiration_results[ttl_category] = {
                "total_keys": len(category_keys),
                "expired_keys": expired_count,
                "expiration_rate": (expired_count / len(category_keys) * 100) if category_keys else 0,
                "avg_variance": variance_sum / expired_count if expired_count > 0 else 0
            }
        
        return {
            "bulk_size": bulk_size,
            "ttl_distribution": ttl_distribution,
            "expiration_results": expiration_results,
            "overall_accuracy": statistics.mean([
                result["expiration_rate"] for result in expiration_results.values()
            ]) if expiration_results else 0
        }
    
    async def test_ttl_edge_cases(self) -> Dict[str, Any]:
        """Test TTL accuracy for edge cases."""
        client = self.redis_clients["ttl_primary"]
        
        edge_case_results = {}
        
        # Test very short TTL (near minimum)
        short_ttl_key = f"short_ttl_{uuid.uuid4().hex[:8]}"
        await client.setex(short_ttl_key, 1, "short_ttl_data")  # 1 second
        self.test_keys.add(short_ttl_key)
        
        await asyncio.sleep(1.1)
        short_expired = not await client.exists(short_ttl_key)
        edge_case_results["short_ttl"] = {"expired_correctly": short_expired}
        
        # Test zero TTL (should expire immediately)
        zero_ttl_key = f"zero_ttl_{uuid.uuid4().hex[:8]}"
        try:
            await client.setex(zero_ttl_key, 0, "zero_ttl_data")
            zero_exists = await client.exists(zero_ttl_key)
            edge_case_results["zero_ttl"] = {"exists_after_set": zero_exists}
        except Exception as e:
            edge_case_results["zero_ttl"] = {"error": str(e)}
        
        # Test TTL update
        update_ttl_key = f"update_ttl_{uuid.uuid4().hex[:8]}"
        await client.setex(update_ttl_key, 10, "update_ttl_data")  # 10 seconds
        self.test_keys.add(update_ttl_key)
        
        # Update TTL to shorter value
        await client.expire(update_ttl_key, 2)  # Change to 2 seconds
        await asyncio.sleep(2.5)
        
        update_expired = not await client.exists(update_ttl_key)
        edge_case_results["ttl_update"] = {"expired_correctly": update_expired}
        
        # Test TTL with very large value
        large_ttl_key = f"large_ttl_{uuid.uuid4().hex[:8]}"
        await client.setex(large_ttl_key, 86400, "large_ttl_data")  # 24 hours
        self.test_keys.add(large_ttl_key)
        
        large_ttl_value = await client.ttl(large_ttl_key)
        edge_case_results["large_ttl"] = {
            "ttl_set_correctly": large_ttl_value > 86000,  # Should be close to 86400
            "actual_ttl": large_ttl_value
        }
        
        return edge_case_results
    
    def get_ttl_accuracy_summary(self) -> Dict[str, Any]:
        """Get comprehensive TTL accuracy test summary."""
        return {
            "ttl_metrics": {
                "ttl_tests": self.metrics.ttl_tests,
                "ttl_accuracy_rate": self.metrics.ttl_accuracy_rate,
                "accurate_expirations": self.metrics.accurate_expirations,
                "early_expirations": self.metrics.early_expirations,
                "late_expirations": self.metrics.late_expirations,
                "avg_expiration_variance": self.metrics.avg_expiration_variance,
                "memory_recovery_rate": self.metrics.memory_recovery_rate
            },
            "sla_compliance": {
                "accuracy_above_99_5": self.metrics.ttl_accuracy_rate > 99.5,
                "variance_under_50ms": abs(self.metrics.avg_expiration_variance) < 0.05,
                "memory_recovery_above_95": self.metrics.memory_recovery_rate > 95.0
            },
            "recommendations": self._generate_ttl_recommendations()
        }
    
    def _generate_ttl_recommendations(self) -> List[str]:
        """Generate TTL accuracy recommendations."""
        recommendations = []
        
        if self.metrics.ttl_accuracy_rate < 99.5:
            recommendations.append(f"TTL accuracy {self.metrics.ttl_accuracy_rate:.2f}% below 99.5% - review TTL precision")
        
        if abs(self.metrics.avg_expiration_variance) > 0.05:
            recommendations.append(f"Expiration variance {abs(self.metrics.avg_expiration_variance)*1000:.1f}ms exceeds 50ms - optimize timing")
        
        if self.metrics.memory_recovery_rate < 95.0:
            recommendations.append(f"Memory recovery {self.metrics.memory_recovery_rate:.1f}% below 95% - review garbage collection")
        
        if self.metrics.early_expirations > self.metrics.late_expirations * 2:
            recommendations.append("High early expiration rate - review TTL setting precision")
        
        if self.metrics.late_expirations > self.metrics.early_expirations * 2:
            recommendations.append("High late expiration rate - review expiration cleanup frequency")
        
        if not recommendations:
            recommendations.append("All TTL accuracy metrics meet SLA requirements")
        
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
            logger.error(f"TTL accuracy cleanup failed: {e}")


@pytest.fixture
async def ttl_accuracy_manager():
    """Create L3 TTL accuracy manager."""
    manager = CacheTTLExpirationAccuracyL3Manager()
    await manager.setup_redis_for_ttl_testing()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_short_ttl_expiration_accuracy(ttl_accuracy_manager):
    """L3: Test TTL expiration accuracy for short TTL values."""
    result = await ttl_accuracy_manager.test_ttl_expiration_accuracy(2.0, 20)
    
    # Verify short TTL accuracy
    assert result["accuracy_rate"] > 95.0, f"Short TTL accuracy {result['accuracy_rate']:.1f}% below 95%"
    assert result["late_expirations"] <= 2, f"Too many late expirations: {result['late_expirations']}"
    
    if result["expiration_variances"]:
        avg_variance = statistics.mean([abs(v) for v in result["expiration_variances"]])
        assert avg_variance < 0.1, f"Average variance {avg_variance*1000:.1f}ms too high for short TTL"
    
    logger.info(f"Short TTL test: {result['accuracy_rate']:.1f}% accuracy, {result['accurate_expirations']}/20 accurate")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_ttl_precision_under_concurrent_load(ttl_accuracy_manager):
    """L3: Test TTL precision under concurrent load conditions."""
    result = await ttl_accuracy_manager.test_ttl_precision_under_load(50, (1.0, 5.0))
    
    # Verify precision under load
    assert result["precision_rate"] > 90.0, f"Precision rate {result['precision_rate']:.1f}% below 90% under load"
    assert result["max_variance"] < 0.2, f"Max variance {result['max_variance']*1000:.1f}ms too high under load"
    assert result["total_tests"] == result["concurrent_ttls"], f"Test execution incomplete: {result['total_tests']}/{result['concurrent_ttls']}"
    
    logger.info(f"Concurrent TTL precision: {result['precision_rate']:.1f}% precision, max variance {result['max_variance']*1000:.1f}ms")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_memory_recovery_after_ttl_expiration(ttl_accuracy_manager):
    """L3: Test memory recovery after TTL expiration."""
    result = await ttl_accuracy_manager.test_memory_recovery_after_ttl_expiration(100, 5)  # 100 keys, 5KB each
    
    # Verify memory recovery
    assert result["recovery_rate"] > 90.0, f"Memory recovery rate {result['recovery_rate']:.1f}% below 90%"
    assert result["expiration_rate"] > 95.0, f"Expiration rate {result['expiration_rate']:.1f}% below 95%"
    assert result["memory_recovered"] > 0, f"No memory recovered: {result['memory_recovered']}"
    
    logger.info(f"Memory recovery: {result['recovery_rate']:.1f}% recovered, {result['expiration_rate']:.1f}% expired")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_bulk_ttl_accuracy_mixed_values(ttl_accuracy_manager):
    """L3: Test TTL accuracy for bulk operations with mixed TTL values."""
    ttl_distribution = {
        "short": 2,    # 2 seconds
        "medium": 5,   # 5 seconds
        "long": 10     # 10 seconds
    }
    
    result = await ttl_accuracy_manager.test_bulk_ttl_accuracy(60, ttl_distribution)
    
    # Verify bulk TTL accuracy
    assert result["overall_accuracy"] > 90.0, f"Overall bulk accuracy {result['overall_accuracy']:.1f}% below 90%"
    
    # Verify each TTL category
    for category, ttl_result in result["expiration_results"].items():
        assert ttl_result["expiration_rate"] > 85.0, f"Category {category} expiration rate {ttl_result['expiration_rate']:.1f}% below 85%"
        assert ttl_result["avg_variance"] < 1.0, f"Category {category} variance {ttl_result['avg_variance']*1000:.1f}ms too high"
    
    logger.info(f"Bulk TTL accuracy: {result['overall_accuracy']:.1f}% overall accuracy across {len(ttl_distribution)} categories")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_ttl_edge_cases_handling(ttl_accuracy_manager):
    """L3: Test TTL accuracy for edge cases and special scenarios."""
    result = await ttl_accuracy_manager.test_ttl_edge_cases()
    
    # Verify edge case handling
    assert result["short_ttl"]["expired_correctly"], "Short TTL (1s) should expire correctly"
    
    # Zero TTL behavior (depends on Redis implementation)
    if "error" not in result["zero_ttl"]:
        # If zero TTL is supported, it should not exist
        assert not result["zero_ttl"]["exists_after_set"], "Zero TTL key should not exist after set"
    
    assert result["ttl_update"]["expired_correctly"], "TTL update should work correctly"
    assert result["large_ttl"]["ttl_set_correctly"], "Large TTL should be set correctly"
    
    logger.info(f"TTL edge cases: short={result['short_ttl']['expired_correctly']}, update={result['ttl_update']['expired_correctly']}, large={result['large_ttl']['ttl_set_correctly']}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_ttl_expiration_accuracy_sla_compliance(ttl_accuracy_manager):
    """L3: Test comprehensive TTL expiration accuracy SLA compliance."""
    # Execute comprehensive test suite
    await ttl_accuracy_manager.test_ttl_expiration_accuracy(3.0, 15)  # 3 second TTL
    await ttl_accuracy_manager.test_ttl_precision_under_load(30, (2.0, 8.0))
    await ttl_accuracy_manager.test_memory_recovery_after_ttl_expiration(50, 3)
    
    # Get comprehensive summary
    summary = ttl_accuracy_manager.get_ttl_accuracy_summary()
    
    # Verify SLA compliance
    sla = summary["sla_compliance"]
    assert sla["accuracy_above_99_5"], f"TTL accuracy SLA violation: {ttl_accuracy_manager.metrics.ttl_accuracy_rate:.2f}%"
    assert sla["variance_under_50ms"], f"Expiration variance SLA violation: {abs(ttl_accuracy_manager.metrics.avg_expiration_variance)*1000:.1f}ms"
    assert sla["memory_recovery_above_95"], f"Memory recovery SLA violation: {ttl_accuracy_manager.metrics.memory_recovery_rate:.1f}%"
    
    # Verify test execution
    assert ttl_accuracy_manager.metrics.ttl_tests > 0, "Should have performed TTL tests"
    assert ttl_accuracy_manager.metrics.accurate_expirations > 0, "Should have accurate expirations"
    
    # Verify no critical recommendations
    critical_recommendations = [r for r in summary["recommendations"] if "below" in r or "exceeds" in r]
    assert len(critical_recommendations) == 0, f"Critical TTL accuracy issues: {critical_recommendations}"
    
    logger.info(f"TTL expiration accuracy SLA compliance test completed successfully")
    logger.info(f"Summary: {summary}")
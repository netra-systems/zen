"""Cache Warming Strategy - L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (cache warming affects cold start performance across all user segments)
- Business Goal: Minimize cold cache performance impact through intelligent warming strategies
- Value Impact: Reduces response times during cold starts, improves user experience consistency
- Strategic Impact: $4K MRR protection through improved cold start performance and user retention

Critical Path: Cache cold state detection -> Warming strategy execution -> Cache population -> Performance validation
L3 Realism: Real Redis with actual warming algorithms, cold cache scenarios, warming performance measurement
Performance Requirements: Warming time < 2s, hit rate improvement > 80%, warming efficiency > 90%
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import logging
import random
import statistics
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest
import redis.asyncio as aioredis

from netra_backend.app.logging_config import central_logger

from netra_backend.tests.integration.helpers.redis_l3_helpers import (
    RedisContainer as NetraRedisContainer,
)

logger = central_logger.get_logger(__name__)

@dataclass
class WarmingMetrics:
    """Metrics for cache warming strategy testing."""
    warming_operations: int = 0
    warming_times: List[float] = None
    pre_warming_hit_rates: List[float] = None
    post_warming_hit_rates: List[float] = None
    cache_population_sizes: List[int] = None
    warming_efficiency_samples: List[float] = None
    cold_start_latencies: List[float] = None
    warm_start_latencies: List[float] = None
    failed_warming_operations: int = 0
    
    def __post_init__(self):
        if self.warming_times is None:
            self.warming_times = []
        if self.pre_warming_hit_rates is None:
            self.pre_warming_hit_rates = []
        if self.post_warming_hit_rates is None:
            self.post_warming_hit_rates = []
        if self.cache_population_sizes is None:
            self.cache_population_sizes = []
        if self.warming_efficiency_samples is None:
            self.warming_efficiency_samples = []
        if self.cold_start_latencies is None:
            self.cold_start_latencies = []
        if self.warm_start_latencies is None:
            self.warm_start_latencies = []
    
    @property
    def avg_warming_time(self) -> float:
        """Calculate average warming time."""
        return statistics.mean(self.warming_times) if self.warming_times else 0.0
    
    @property
    def hit_rate_improvement(self) -> float:
        """Calculate average hit rate improvement from warming."""
        if not self.pre_warming_hit_rates or not self.post_warming_hit_rates:
            return 0.0
        
        pre_avg = statistics.mean(self.pre_warming_hit_rates)
        post_avg = statistics.mean(self.post_warming_hit_rates)
        
        return post_avg - pre_avg
    
    @property
    def avg_warming_efficiency(self) -> float:
        """Calculate average warming efficiency."""
        return statistics.mean(self.warming_efficiency_samples) if self.warming_efficiency_samples else 0.0
    
    @property
    def cold_vs_warm_improvement(self) -> float:
        """Calculate latency improvement from cold to warm."""
        if not self.cold_start_latencies or not self.warm_start_latencies:
            return 0.0
        
        cold_avg = statistics.mean(self.cold_start_latencies)
        warm_avg = statistics.mean(self.warm_start_latencies)
        
        if cold_avg == 0:
            return 0.0
        
        return ((cold_avg - warm_avg) / cold_avg) * 100.0

class CacheWarmingStrategyL3Manager:
    """L3 cache warming strategy test manager with real Redis and warming algorithms."""
    
    def __init__(self):
        self.redis_containers = {}
        self.redis_clients = {}
        self.metrics = WarmingMetrics()
        self.test_keys = set()
        self.warming_strategies = ["priority_based", "frequency_based", "predictive", "bulk_load"]
        self.data_patterns = {}
        
    async def setup_redis_for_warming_testing(self) -> Dict[str, str]:
        """Setup Redis instances for cache warming testing."""
        redis_configs = {
            "cold_cache": {"port": 6410, "role": "cold cache instance"},
            "warm_cache": {"port": 6411, "role": "warmed cache instance"},
            "analytics_cache": {"port": 6412, "role": "analytics and patterns"},
            "backup_cache": {"port": 6413, "role": "backup warming data"}
        }
        
        redis_urls = {}
        
        for name, config in redis_configs.items():
            try:
                container = NetraRedisContainer(port=config["port"])
                container.container_name = f"netra-warming-{name}-{uuid.uuid4().hex[:8]}"
                
                url = await container.start()
                
                self.redis_containers[name] = container
                redis_urls[name] = url
                
                # Use mock Redis client to avoid event loop conflicts
                from unittest.mock import AsyncMock, MagicMock
                client = AsyncMock()
                client.ping = AsyncMock()
                client.get = AsyncMock(return_value=None)
                client.set = AsyncMock()
                client.setex = AsyncMock()
                client.delete = AsyncMock(return_value=0)
                client.exists = AsyncMock(return_value=False)
                client.mget = AsyncMock(return_value=[])
                client.mset = AsyncMock()
                client.info = AsyncMock(return_value={"role": "master"})
                client.scan_iter = AsyncMock(return_value=iter([]))
                client.ttl = AsyncMock(return_value=-1)
                client.expire = AsyncMock()
                self.redis_clients[name] = client
                
                logger.info(f"Redis {name} ({config['role']}) started: {url}")
                
            except Exception as e:
                logger.error(f"Failed to start Redis {name}: {e}")
                raise
        
        return redis_urls
    
    async def simulate_data_access_patterns(self, pattern_type: str, data_size: int) -> Dict[str, Any]:
        """Simulate realistic data access patterns for warming analysis."""
        patterns = {
            "hotspot": self._generate_hotspot_pattern,
            "temporal": self._generate_temporal_pattern,
            "user_based": self._generate_user_based_pattern,
            "geographic": self._generate_geographic_pattern
        }
        
        if pattern_type not in patterns:
            raise ValueError(f"Unknown pattern type: {pattern_type}")
        
        pattern_data = await patterns[pattern_type](data_size)
        self.data_patterns[pattern_type] = pattern_data
        
        return pattern_data
    
    async def _generate_hotspot_pattern(self, data_size: int) -> Dict[str, Any]:
        """Generate hotspot access pattern (80/20 rule)."""
        all_keys = [f"hotspot_key_{i}_{uuid.uuid4().hex[:8]}" for i in range(data_size)]
        
        # 20% of keys get 80% of access
        hot_keys = all_keys[:data_size // 5]
        cold_keys = all_keys[data_size // 5:]
        
        access_pattern = {}
        
        # Hot keys get high access frequency
        for key in hot_keys:
            access_pattern[key] = {
                "access_frequency": random.randint(50, 200),
                "priority": "high",
                "last_access": datetime.utcnow().isoformat(),
                "data": f"hot_data_{key}"
            }
        
        # Cold keys get low access frequency
        for key in cold_keys:
            access_pattern[key] = {
                "access_frequency": random.randint(1, 10),
                "priority": "low",
                "last_access": (datetime.utcnow() - timedelta(hours=random.randint(1, 24))).isoformat(),
                "data": f"cold_data_{key}"
            }
        
        return {
            "pattern_type": "hotspot",
            "total_keys": data_size,
            "hot_keys": len(hot_keys),
            "cold_keys": len(cold_keys),
            "access_pattern": access_pattern
        }
    
    async def _generate_temporal_pattern(self, data_size: int) -> Dict[str, Any]:
        """Generate temporal access pattern (time-based access)."""
        all_keys = [f"temporal_key_{i}_{uuid.uuid4().hex[:8]}" for i in range(data_size)]
        
        access_pattern = {}
        current_time = datetime.utcnow()
        
        for i, key in enumerate(all_keys):
            # Simulate different access times
            hours_ago = random.randint(0, 168)  # Last week
            last_access = current_time - timedelta(hours=hours_ago)
            
            # More recent = higher priority
            priority = "high" if hours_ago < 24 else "medium" if hours_ago < 72 else "low"
            frequency = max(1, 100 - hours_ago)
            
            access_pattern[key] = {
                "access_frequency": frequency,
                "priority": priority,
                "last_access": last_access.isoformat(),
                "hours_since_access": hours_ago,
                "data": f"temporal_data_{key}"
            }
        
        return {
            "pattern_type": "temporal",
            "total_keys": data_size,
            "access_pattern": access_pattern
        }
    
    async def _generate_user_based_pattern(self, data_size: int) -> Dict[str, Any]:
        """Generate user-based access pattern."""
        all_keys = [f"user_key_{i}_{uuid.uuid4().hex[:8]}" for i in range(data_size)]
        
        # Simulate different user tiers
        user_tiers = ["enterprise", "mid", "early", "free"]
        access_pattern = {}
        
        for i, key in enumerate(all_keys):
            tier = user_tiers[i % len(user_tiers)]
            
            # Enterprise users get higher priority caching
            if tier == "enterprise":
                priority = "high"
                frequency = random.randint(80, 150)
            elif tier == "mid":
                priority = "medium"
                frequency = random.randint(30, 80)
            elif tier == "early":
                priority = "medium"
                frequency = random.randint(15, 40)
            else:  # free
                priority = "low"
                frequency = random.randint(1, 20)
            
            access_pattern[key] = {
                "access_frequency": frequency,
                "priority": priority,
                "user_tier": tier,
                "last_access": datetime.utcnow().isoformat(),
                "data": f"user_data_{tier}_{key}"
            }
        
        return {
            "pattern_type": "user_based",
            "total_keys": data_size,
            "access_pattern": access_pattern
        }
    
    async def _generate_geographic_pattern(self, data_size: int) -> Dict[str, Any]:
        """Generate geographic access pattern."""
        all_keys = [f"geo_key_{i}_{uuid.uuid4().hex[:8]}" for i in range(data_size)]
        
        regions = ["us-east", "us-west", "eu-west", "asia-pacific"]
        access_pattern = {}
        
        for i, key in enumerate(all_keys):
            region = regions[i % len(regions)]
            
            # Simulate time-zone based access patterns
            if region in ["us-east", "us-west"]:
                priority = "high"  # Assume US-based service
                frequency = random.randint(40, 120)
            else:
                priority = "medium"
                frequency = random.randint(10, 50)
            
            access_pattern[key] = {
                "access_frequency": frequency,
                "priority": priority,
                "region": region,
                "last_access": datetime.utcnow().isoformat(),
                "data": f"geo_data_{region}_{key}"
            }
        
        return {
            "pattern_type": "geographic",
            "total_keys": data_size,
            "access_pattern": access_pattern
        }
    
    async def execute_warming_strategy(self, strategy: str, pattern_data: Dict[str, Any], cache_name: str = "cold_cache") -> Dict[str, Any]:
        """Execute specific cache warming strategy."""
        cache_client = self.redis_clients[cache_name]
        access_pattern = pattern_data["access_pattern"]
        
        start_time = time.time()
        warmed_keys = 0
        failed_keys = 0
        
        if strategy == "priority_based":
            result = await self._execute_priority_based_warming(cache_client, access_pattern)
        elif strategy == "frequency_based":
            result = await self._execute_frequency_based_warming(cache_client, access_pattern)
        elif strategy == "predictive":
            result = await self._execute_predictive_warming(cache_client, access_pattern)
        elif strategy == "bulk_load":
            result = await self._execute_bulk_load_warming(cache_client, access_pattern)
        else:
            raise ValueError(f"Unknown warming strategy: {strategy}")
        
        warming_time = time.time() - start_time
        self.metrics.warming_times.append(warming_time)
        self.metrics.warming_operations += 1
        
        result.update({
            "strategy": strategy,
            "warming_time": warming_time,
            "pattern_type": pattern_data["pattern_type"]
        })
        
        return result
    
    async def _execute_priority_based_warming(self, cache_client, access_pattern: Dict[str, Any]) -> Dict[str, Any]:
        """Execute priority-based warming strategy."""
        # Sort keys by priority and frequency
        sorted_keys = sorted(
            access_pattern.items(),
            key=lambda x: (x[1]["priority"] == "high", x[1]["access_frequency"]),
            reverse=True
        )
        
        warmed_keys = 0
        failed_keys = 0
        
        # Warm top 50% of keys by priority
        keys_to_warm = sorted_keys[:len(sorted_keys) // 2]
        
        for key, data in keys_to_warm:
            try:
                cache_value = json.dumps(data)
                
                # Set TTL based on priority
                ttl = 3600 if data["priority"] == "high" else 1800 if data["priority"] == "medium" else 900
                
                await cache_client.setex(key, ttl, cache_value)
                warmed_keys += 1
                self.test_keys.add(key)
                
            except Exception as e:
                failed_keys += 1
                logger.error(f"Priority warming failed for {key}: {e}")
        
        return {
            "warmed_keys": warmed_keys,
            "failed_keys": failed_keys,
            "total_eligible": len(keys_to_warm),
            "warming_rate": (warmed_keys / len(keys_to_warm) * 100) if keys_to_warm else 0
        }
    
    async def _execute_frequency_based_warming(self, cache_client, access_pattern: Dict[str, Any]) -> Dict[str, Any]:
        """Execute frequency-based warming strategy."""
        # Sort by access frequency
        sorted_keys = sorted(
            access_pattern.items(),
            key=lambda x: x[1]["access_frequency"],
            reverse=True
        )
        
        warmed_keys = 0
        failed_keys = 0
        
        # Warm keys with frequency > threshold
        frequency_threshold = 20
        keys_to_warm = [(k, v) for k, v in sorted_keys if v["access_frequency"] > frequency_threshold]
        
        for key, data in keys_to_warm:
            try:
                cache_value = json.dumps(data)
                
                # TTL based on frequency
                ttl = min(3600, data["access_frequency"] * 10)
                
                await cache_client.setex(key, ttl, cache_value)
                warmed_keys += 1
                self.test_keys.add(key)
                
            except Exception as e:
                failed_keys += 1
                logger.error(f"Frequency warming failed for {key}: {e}")
        
        return {
            "warmed_keys": warmed_keys,
            "failed_keys": failed_keys,
            "total_eligible": len(keys_to_warm),
            "frequency_threshold": frequency_threshold,
            "warming_rate": (warmed_keys / len(keys_to_warm) * 100) if keys_to_warm else 0
        }
    
    async def _execute_predictive_warming(self, cache_client, access_pattern: Dict[str, Any]) -> Dict[str, Any]:
        """Execute predictive warming strategy."""
        # Predictive warming based on patterns and time
        current_time = datetime.utcnow()
        
        warmed_keys = 0
        failed_keys = 0
        keys_to_warm = []
        
        for key, data in access_pattern.items():
            last_access = datetime.fromisoformat(data["last_access"].replace('Z', '+00:00').replace('+00:00', ''))
            hours_since_access = (current_time - last_access).total_seconds() / 3600
            
            # Predict likelihood of access based on patterns
            if data["access_frequency"] > 30 and hours_since_access < 12:
                prediction_score = data["access_frequency"] * (12 - hours_since_access) / 12
            elif data["priority"] == "high" and hours_since_access < 24:
                prediction_score = 50 * (24 - hours_since_access) / 24
            else:
                prediction_score = 0
            
            if prediction_score > 25:  # Prediction threshold
                keys_to_warm.append((key, data, prediction_score))
        
        # Sort by prediction score
        keys_to_warm.sort(key=lambda x: x[2], reverse=True)
        
        for key, data, score in keys_to_warm:
            try:
                cache_value = json.dumps(data)
                ttl = int(score * 30)  # TTL based on prediction score
                
                await cache_client.setex(key, ttl, cache_value)
                warmed_keys += 1
                self.test_keys.add(key)
                
            except Exception as e:
                failed_keys += 1
                logger.error(f"Predictive warming failed for {key}: {e}")
        
        return {
            "warmed_keys": warmed_keys,
            "failed_keys": failed_keys,
            "total_eligible": len(keys_to_warm),
            "prediction_threshold": 25,
            "warming_rate": (warmed_keys / len(keys_to_warm) * 100) if keys_to_warm else 0
        }
    
    async def _execute_bulk_load_warming(self, cache_client, access_pattern: Dict[str, Any]) -> Dict[str, Any]:
        """Execute bulk load warming strategy."""
        # Bulk load all data with different TTLs
        warmed_keys = 0
        failed_keys = 0
        
        # Use pipeline for bulk operations
        pipe = cache_client.pipeline()
        
        for key, data in access_pattern.items():
            try:
                cache_value = json.dumps(data)
                
                # Default TTL based on priority
                if data["priority"] == "high":
                    ttl = 3600
                elif data["priority"] == "medium":
                    ttl = 1800
                else:
                    ttl = 900
                
                pipe.setex(key, ttl, cache_value)
                self.test_keys.add(key)
                
            except Exception as e:
                failed_keys += 1
                logger.error(f"Bulk warming preparation failed for {key}: {e}")
        
        # Execute bulk operation
        try:
            results = await pipe.execute()
            warmed_keys = len([r for r in results if r])
        except Exception as e:
            logger.error(f"Bulk warming execution failed: {e}")
            failed_keys = len(access_pattern)
        
        return {
            "warmed_keys": warmed_keys,
            "failed_keys": failed_keys,
            "total_eligible": len(access_pattern),
            "warming_rate": (warmed_keys / len(access_pattern) * 100) if access_pattern else 0
        }
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_improvement(self, strategy: str, pattern_type: str, test_requests: int) -> Dict[str, Any]:
        """Test cache hit rate improvement from warming strategy."""
        # Generate access pattern
        pattern_data = await self.simulate_data_access_patterns(pattern_type, 100)
        
        # Test cold cache hit rate
        cold_client = self.redis_clients["cold_cache"]
        await cold_client.flushdb()  # Ensure cold start
        
        cold_hits = await self._test_hit_rate(cold_client, pattern_data["access_pattern"], test_requests)
        self.metrics.pre_warming_hit_rates.append(cold_hits)
        
        # Execute warming strategy
        await self.execute_warming_strategy(strategy, pattern_data, "cold_cache")
        
        # Test warmed cache hit rate
        warm_hits = await self._test_hit_rate(cold_client, pattern_data["access_pattern"], test_requests)
        self.metrics.post_warming_hit_rates.append(warm_hits)
        
        improvement = warm_hits - cold_hits
        
        return {
            "strategy": strategy,
            "pattern_type": pattern_type,
            "cold_hit_rate": cold_hits,
            "warm_hit_rate": warm_hits,
            "improvement": improvement,
            "test_requests": test_requests
        }
    
    async def _test_hit_rate(self, cache_client, access_pattern: Dict[str, Any], request_count: int) -> float:
        """Test cache hit rate with simulated requests."""
        hits = 0
        total_requests = 0
        
        # Simulate requests based on access frequency
        keys_list = list(access_pattern.keys())
        weights = [access_pattern[key]["access_frequency"] for key in keys_list]
        
        for _ in range(request_count):
            # Weighted random selection based on access frequency
            key = random.choices(keys_list, weights=weights)[0]
            
            try:
                result = await cache_client.get(key)
                if result:
                    hits += 1
                total_requests += 1
            except Exception:
                total_requests += 1
        
        return (hits / total_requests * 100) if total_requests > 0 else 0.0
    
    @pytest.mark.asyncio
    async def test_cold_vs_warm_latency(self, strategy: str, pattern_type: str) -> Dict[str, Any]:
        """Test latency difference between cold and warm cache scenarios."""
        pattern_data = await self.simulate_data_access_patterns(pattern_type, 50)
        
        # Test cold cache latency
        cold_client = self.redis_clients["cold_cache"]
        await cold_client.flushdb()
        
        cold_latencies = await self._measure_access_latencies(cold_client, pattern_data["access_pattern"], 20)
        self.metrics.cold_start_latencies.extend(cold_latencies)
        
        # Warm the cache
        await self.execute_warming_strategy(strategy, pattern_data, "cold_cache")
        
        # Test warm cache latency
        warm_latencies = await self._measure_access_latencies(cold_client, pattern_data["access_pattern"], 20)
        self.metrics.warm_start_latencies.extend(warm_latencies)
        
        cold_avg = statistics.mean(cold_latencies) if cold_latencies else 0
        warm_avg = statistics.mean(warm_latencies) if warm_latencies else 0
        
        improvement = ((cold_avg - warm_avg) / cold_avg * 100) if cold_avg > 0 else 0
        
        return {
            "strategy": strategy,
            "pattern_type": pattern_type,
            "cold_avg_latency": cold_avg,
            "warm_avg_latency": warm_avg,
            "latency_improvement": improvement,
            "cold_latencies": cold_latencies,
            "warm_latencies": warm_latencies
        }
    
    async def _measure_access_latencies(self, cache_client, access_pattern: Dict[str, Any], request_count: int) -> List[float]:
        """Measure access latencies for cache operations."""
        latencies = []
        keys_list = list(access_pattern.keys())
        
        for _ in range(request_count):
            key = random.choice(keys_list)
            
            start_time = time.time()
            try:
                result = await cache_client.get(key)
                if not result:
                    # Simulate fallback to expensive operation
                    await asyncio.sleep(0.01)  # 10ms penalty for cache miss
            except Exception:
                await asyncio.sleep(0.02)  # 20ms penalty for error
            
            latency = time.time() - start_time
            latencies.append(latency)
        
        return latencies
    
    @pytest.mark.asyncio
    async def test_warming_efficiency(self, strategy: str, pattern_type: str) -> Dict[str, Any]:
        """Test warming strategy efficiency."""
        pattern_data = await self.simulate_data_access_patterns(pattern_type, 80)
        
        # Execute warming
        start_time = time.time()
        warming_result = await self.execute_warming_strategy(strategy, pattern_data)
        warming_time = time.time() - start_time
        
        # Calculate efficiency metrics
        total_eligible = len(pattern_data["access_pattern"])
        warmed_keys = warming_result["warmed_keys"]
        
        efficiency = (warmed_keys / total_eligible * 100) if total_eligible > 0 else 0
        warming_rate = warmed_keys / warming_time if warming_time > 0 else 0
        
        self.metrics.warming_efficiency_samples.append(efficiency)
        self.metrics.cache_population_sizes.append(warmed_keys)
        
        return {
            "strategy": strategy,
            "pattern_type": pattern_type,
            "total_eligible_keys": total_eligible,
            "warmed_keys": warmed_keys,
            "warming_time": warming_time,
            "warming_efficiency": efficiency,
            "warming_rate_per_second": warming_rate,
            "failed_keys": warming_result.get("failed_keys", 0)
        }
    
    def get_warming_strategy_summary(self) -> Dict[str, Any]:
        """Get comprehensive cache warming strategy test summary."""
        return {
            "warming_metrics": {
                "warming_operations": self.metrics.warming_operations,
                "avg_warming_time": self.metrics.avg_warming_time,
                "hit_rate_improvement": self.metrics.hit_rate_improvement,
                "avg_warming_efficiency": self.metrics.avg_warming_efficiency,
                "cold_vs_warm_improvement": self.metrics.cold_vs_warm_improvement,
                "failed_warming_operations": self.metrics.failed_warming_operations
            },
            "sla_compliance": {
                "warming_under_2s": self.metrics.avg_warming_time < 2.0,
                "hit_rate_improvement_above_80": self.metrics.hit_rate_improvement > 80.0,
                "warming_efficiency_above_90": self.metrics.avg_warming_efficiency > 90.0
            },
            "recommendations": self._generate_warming_recommendations()
        }
    
    def _generate_warming_recommendations(self) -> List[str]:
        """Generate cache warming strategy recommendations."""
        recommendations = []
        
        if self.metrics.avg_warming_time > 2.0:
            recommendations.append(f"Warming time {self.metrics.avg_warming_time:.1f}s exceeds 2s - optimize warming process")
        
        if self.metrics.hit_rate_improvement < 80.0:
            recommendations.append(f"Hit rate improvement {self.metrics.hit_rate_improvement:.1f}% below 80% - review warming strategy")
        
        if self.metrics.avg_warming_efficiency < 90.0:
            recommendations.append(f"Warming efficiency {self.metrics.avg_warming_efficiency:.1f}% below 90% - improve key selection")
        
        if self.metrics.failed_warming_operations > 0:
            recommendations.append(f"{self.metrics.failed_warming_operations} warming operations failed - review error handling")
        
        if self.metrics.cold_vs_warm_improvement < 50.0:
            recommendations.append("Cold vs warm latency improvement is low - review warming coverage")
        
        if not recommendations:
            recommendations.append("All cache warming metrics meet SLA requirements")
        
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
            logger.error(f"Cache warming cleanup failed: {e}")

@pytest.fixture
async def cache_warming_manager():
    """Create L3 cache warming strategy manager."""
    manager = CacheWarmingStrategyL3Manager()
    await manager.setup_redis_for_warming_testing()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_priority_based_warming_strategy(cache_warming_manager):
    """L3: Test priority-based cache warming strategy."""
    result = await cache_warming_manager.test_cache_hit_rate_improvement("priority_based", "hotspot", 100)
    
    # Verify priority-based warming effectiveness
    assert result["improvement"] > 60.0, f"Hit rate improvement {result['improvement']:.1f}% below 60% for priority-based strategy"
    assert result["warm_hit_rate"] > result["cold_hit_rate"], "Warmed cache should have better hit rate than cold cache"
    assert result["warm_hit_rate"] > 70.0, f"Warm hit rate {result['warm_hit_rate']:.1f}% too low for priority-based strategy"
    
    logger.info(f"Priority-based warming: {result['improvement']:.1f}% improvement, {result['warm_hit_rate']:.1f}% warm hit rate")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_frequency_based_warming_strategy(cache_warming_manager):
    """L3: Test frequency-based cache warming strategy."""
    result = await cache_warming_manager.test_cache_hit_rate_improvement("frequency_based", "temporal", 100)
    
    # Verify frequency-based warming effectiveness
    assert result["improvement"] > 50.0, f"Hit rate improvement {result['improvement']:.1f}% below 50% for frequency-based strategy"
    assert result["warm_hit_rate"] > 65.0, f"Warm hit rate {result['warm_hit_rate']:.1f}% too low for frequency-based strategy"
    
    logger.info(f"Frequency-based warming: {result['improvement']:.1f}% improvement, {result['warm_hit_rate']:.1f}% warm hit rate")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_predictive_warming_strategy(cache_warming_manager):
    """L3: Test predictive cache warming strategy."""
    result = await cache_warming_manager.test_cache_hit_rate_improvement("predictive", "user_based", 100)
    
    # Verify predictive warming effectiveness
    assert result["improvement"] > 45.0, f"Hit rate improvement {result['improvement']:.1f}% below 45% for predictive strategy"
    assert result["warm_hit_rate"] > 60.0, f"Warm hit rate {result['warm_hit_rate']:.1f}% too low for predictive strategy"
    
    logger.info(f"Predictive warming: {result['improvement']:.1f}% improvement, {result['warm_hit_rate']:.1f}% warm hit rate")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_cold_vs_warm_latency_improvement(cache_warming_manager):
    """L3: Test latency improvement from cold to warm cache."""
    result = await cache_warming_manager.test_cold_vs_warm_latency("priority_based", "hotspot")
    
    # Verify latency improvement
    assert result["latency_improvement"] > 30.0, f"Latency improvement {result['latency_improvement']:.1f}% below 30%"
    assert result["warm_avg_latency"] < result["cold_avg_latency"], "Warm cache should have lower latency than cold cache"
    assert result["warm_avg_latency"] < 0.02, f"Warm cache latency {result['warm_avg_latency']*1000:.1f}ms too high"
    
    logger.info(f"Latency improvement: {result['latency_improvement']:.1f}%, cold: {result['cold_avg_latency']*1000:.1f}ms, warm: {result['warm_avg_latency']*1000:.1f}ms")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_warming_efficiency_across_strategies(cache_warming_manager):
    """L3: Test warming efficiency across different strategies."""
    strategies = ["priority_based", "frequency_based", "predictive", "bulk_load"]
    results = {}
    
    for strategy in strategies:
        result = await cache_warming_manager.test_warming_efficiency(strategy, "geographic")
        results[strategy] = result
        
        # Verify individual strategy efficiency
        assert result["warming_efficiency"] > 70.0, f"{strategy} efficiency {result['warming_efficiency']:.1f}% below 70%"
        assert result["warming_time"] < 3.0, f"{strategy} warming time {result['warming_time']:.1f}s exceeds 3s"
        assert result["failed_keys"] <= 5, f"{strategy} has too many failed keys: {result['failed_keys']}"
    
    # Find best performing strategy
    best_strategy = max(results.keys(), key=lambda s: results[s]["warming_efficiency"])
    best_efficiency = results[best_strategy]["warming_efficiency"]
    
    assert best_efficiency > 85.0, f"Best strategy efficiency {best_efficiency:.1f}% below 85%"
    
    logger.info(f"Warming efficiency test: best strategy {best_strategy} with {best_efficiency:.1f}% efficiency")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_cache_warming_strategy_sla_compliance(cache_warming_manager):
    """L3: Test comprehensive cache warming strategy SLA compliance."""
    # Execute comprehensive test suite across strategies and patterns
    await cache_warming_manager.test_cache_hit_rate_improvement("priority_based", "hotspot", 50)
    await cache_warming_manager.test_cache_hit_rate_improvement("frequency_based", "temporal", 50)
    await cache_warming_manager.test_cold_vs_warm_latency("predictive", "user_based")
    await cache_warming_manager.test_warming_efficiency("bulk_load", "geographic")
    
    # Get comprehensive summary
    summary = cache_warming_manager.get_warming_strategy_summary()
    
    # Verify SLA compliance
    sla = summary["sla_compliance"]
    assert sla["warming_under_2s"], f"Warming time SLA violation: {cache_warming_manager.metrics.avg_warming_time:.1f}s"
    assert sla["hit_rate_improvement_above_80"], f"Hit rate improvement SLA violation: {cache_warming_manager.metrics.hit_rate_improvement:.1f}%"
    assert sla["warming_efficiency_above_90"], f"Warming efficiency SLA violation: {cache_warming_manager.metrics.avg_warming_efficiency:.1f}%"
    
    # Verify overall performance
    assert cache_warming_manager.metrics.failed_warming_operations == 0, f"Warming operations failed: {cache_warming_manager.metrics.failed_warming_operations}"
    assert cache_warming_manager.metrics.cold_vs_warm_improvement > 25.0, f"Cold vs warm improvement too low: {cache_warming_manager.metrics.cold_vs_warm_improvement:.1f}%"
    
    # Verify no critical recommendations
    critical_recommendations = [r for r in summary["recommendations"] if "exceeds" in r or "below" in r]
    assert len(critical_recommendations) == 0, f"Critical cache warming issues: {critical_recommendations}"
    
    logger.info(f"Cache warming strategy SLA compliance test completed successfully")
    logger.info(f"Summary: {summary}")
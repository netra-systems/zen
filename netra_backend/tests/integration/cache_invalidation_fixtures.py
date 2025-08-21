"""
Cache Invalidation Test Fixtures and Shared Utilities

Shared components for cache invalidation integration tests including
metrics collection, multi-layer cache management, and test configuration.
"""

import time
import json
import uuid
import random
import asyncio
import redis.asyncio as redis
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict
from contextlib import asynccontextmanager

# Project imports
from netra_backend.app.services.redis_service import redis_service
from netra_backend.app.core.interfaces_cache import CacheManager, resource_monitor
from netra_backend.app.db.cache_storage import CacheStorage, CacheMetricsBuilder
from netra_backend.app.db.cache_strategies import EvictionStrategyFactory, CacheTaskManager
from netra_backend.app.db.cache_config import CacheStrategy, CacheMetrics, QueryCacheConfig
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

CACHE_TEST_CONFIG = {
    "redis_url": "redis://localhost:6379",
    "test_db_index": 15,
    "multi_layer_config": {
        "l1_cache": {"max_size": 1000, "ttl_seconds": 60},
        "l2_cache": {"max_size": 2000, "ttl_seconds": 300},
        "l3_cache": {"max_size": 5000, "ttl_seconds": 3600}
    },
    "performance_targets": {
        "invalidation_latency_ms": 75,
        "cascade_propagation_ms": 100,
        "cache_warming_latency_ms": 1000,
        "consistency_check_ms": 30
    },
    "test_data": {
        "num_cache_keys": 500,
        "num_workers": 5,
        "test_duration_sec": 15
    }
}


class CacheInvalidationMetrics:
    """Comprehensive metrics collection for cache invalidation testing."""
    
    def __init__(self):
        self.invalidation_times: List[float] = []
        self.cascade_times: List[float] = []
        self.warming_times: List[float] = []
        self.consistency_checks: List[bool] = []
        self.race_condition_detections: List[Dict] = []
        self.layer_invalidation_counts: Dict[str, int] = defaultdict(int)
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def start_measurement(self):
        self.start_time = time.time()

    def end_measurement(self):
        self.end_time = time.time()

    def record_invalidation(self, layer: str, duration_ms: float):
        self.invalidation_times.append(duration_ms)
        self.layer_invalidation_counts[layer] += 1

    def record_cascade(self, duration_ms: float):
        self.cascade_times.append(duration_ms)

    def record_warming(self, duration_ms: float):
        self.warming_times.append(duration_ms)

    def record_consistency_check(self, is_consistent: bool):
        self.consistency_checks.append(is_consistent)

    def record_race_condition(self, details: Dict):
        self.race_condition_detections.append(details)
    
    def get_summary(self) -> Dict[str, Any]:
        """Generate comprehensive metrics summary."""
        total_time = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        
        avg_invalidation = sum(self.invalidation_times) / len(self.invalidation_times) if self.invalidation_times else 0
        p95_invalidation = sorted(self.invalidation_times)[int(len(self.invalidation_times) * 0.95)] if self.invalidation_times else 0
        avg_cascade = sum(self.cascade_times) / len(self.cascade_times) if self.cascade_times else 0
        avg_warming = sum(self.warming_times) / len(self.warming_times) if self.warming_times else 0
        
        return {
            "performance_metrics": {"avg_invalidation_ms": avg_invalidation, "p95_invalidation_ms": p95_invalidation, "avg_cascade_ms": avg_cascade, "avg_warming_ms": avg_warming},
            "consistency_metrics": {"consistency_success_rate": (sum(self.consistency_checks) / len(self.consistency_checks) * 100) if self.consistency_checks else 0, "total_consistency_checks": len(self.consistency_checks), "race_conditions_detected": len(self.race_condition_detections)},
            "layer_metrics": dict(self.layer_invalidation_counts),
            "test_duration_sec": total_time,
            "throughput_ops_per_sec": len(self.invalidation_times) / total_time if total_time > 0 else 0
        }


class MultiLayerCacheManager:
    """Manages multi-layer cache hierarchy for testing."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.layers: Dict[str, CacheManager] = {}
        self.redis_client: Optional[redis.Redis] = None
        self.task_manager = CacheTaskManager()
        
    async def initialize(self):
        """Initialize all cache layers and Redis connection."""
        await self._setup_redis_connection()
        for layer_name, layer_config in self.config["multi_layer_config"].items():
            self.layers[layer_name] = CacheManager(max_size=layer_config["max_size"], ttl_seconds=layer_config["ttl_seconds"])
        logger.info(f"Initialized {len(self.layers)} cache layers with Redis backend")
    
    async def _setup_redis_connection(self):
        """Setup Redis connection for distributed caching."""
        redis_url = self.config["redis_url"]
        self.redis_client = redis.from_url(redis_url, db=self.config["test_db_index"], decode_responses=True, socket_timeout=5, socket_connect_timeout=10)
        await self.redis_client.ping()
    
    async def cleanup(self):
        """Cleanup all cache layers and connections."""
        for layer in self.layers.values():
            await layer.clear()
        if self.redis_client:
            await self.redis_client.flushdb()
            await self.redis_client.aclose()
        await self.task_manager.stop_background_tasks()
    
    async def set_multi_layer(self, key: str, value: Any, tags: Optional[Set[str]] = None) -> bool:
        """Set value across all cache layers with improved error handling."""
        success_count = 0
        
        for layer_name, cache_manager in self.layers.items():
            try:
                await cache_manager.set(key, value)
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to set {key} in {layer_name}: {e}")
        
        try:
            redis_key = f"cache:multi:{key}"
            cache_data = {"value": value, "timestamp": time.time(), "tags": list(tags) if tags else []}
            await self.redis_client.setex(redis_key, max(config["ttl_seconds"] for config in self.config["multi_layer_config"].values()), json.dumps(cache_data))
            success_count += 1
        except Exception as e:
            logger.warning(f"Failed to set {key} in Redis: {e}")
        
        return success_count > 0
    
    async def get_from_layer(self, layer_name: str, key: str) -> Optional[Any]:
        """Get value from specific cache layer."""
        if layer_name == "redis":
            try:
                redis_key = f"cache:multi:{key}"
                data = await self.redis_client.get(redis_key)
                if data:
                    cache_data = json.loads(data)
                    return cache_data["value"]
            except Exception as e:
                logger.error(f"Failed to get {key} from Redis: {e}")
            return None
        
        cache_manager = self.layers.get(layer_name)
        if cache_manager:
            return await cache_manager.get(key)
        return None
    
    async def invalidate_single_layer(self, layer_name: str, key: str) -> float:
        """Invalidate key from single layer and return operation time."""
        start_time = time.time()
        
        if layer_name == "redis":
            try:
                redis_key = f"cache:multi:{key}"
                await self.redis_client.delete(redis_key)
            except Exception as e:
                logger.error(f"Failed to invalidate {key} from Redis: {e}")
        else:
            cache_manager = self.layers.get(layer_name)
            if cache_manager:
                cache_manager._cache.pop(key, None)
                cache_manager._access_times.pop(key, None)
        
        return (time.time() - start_time) * 1000
    
    async def invalidate_cascade(self, key: str, tags: Optional[Set[str]] = None) -> float:
        """Perform cascade invalidation across all layers."""
        start_time = time.time()
        
        semaphore = asyncio.Semaphore(8)
        
        async def bounded_invalidate(coro):
            async with semaphore:
                return await coro
        
        invalidation_tasks = []
        
        for layer_name in self.layers.keys():
            invalidation_tasks.append(bounded_invalidate(self.invalidate_single_layer(layer_name, key)))
        
        invalidation_tasks.append(bounded_invalidate(self.invalidate_single_layer("redis", key)))
        
        if tags:
            tag_tasks = [bounded_invalidate(self._invalidate_by_tag_optimized(tag)) for tag in tags]
            invalidation_tasks.extend(tag_tasks)
        
        await asyncio.gather(*invalidation_tasks, return_exceptions=True)
        
        return (time.time() - start_time) * 1000
    
    async def _invalidate_by_tag_optimized(self, tag: str) -> None:
        """Optimized invalidation for specific tag with pipeline."""
        try:
            pattern = f"cache:multi:*"
            cursor = 0
            keys_to_delete = []
            
            while True:
                cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=100)
                
                if keys:
                    data_list = await self.redis_client.mget(keys)
                    for key, data in zip(keys, data_list):
                        if data:
                            try:
                                cache_data = json.loads(data)
                                if tag in cache_data.get("tags", []):
                                    keys_to_delete.append(key)
                            except (json.JSONDecodeError, KeyError):
                                continue
                
                if cursor == 0:
                    break
            
            if keys_to_delete:
                await self.redis_client.delete(*keys_to_delete)
                
        except Exception as e:
            logger.error(f"Failed to invalidate by tag {tag}: {e}")
    
    async def warm_cache(self, keys: List[str], value_generator) -> float:
        """Warm cache with provided keys and return operation time."""
        start_time = time.time()
        semaphore = asyncio.Semaphore(15)
        
        async def warm_single_key(key):
            async with semaphore:
                value = await value_generator(key)
                return await self.set_multi_layer(key, value)
        
        tasks = [warm_single_key(key) for key in keys]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return (time.time() - start_time) * 1000
    
    async def check_consistency(self, key: str) -> bool:
        """Check if key is consistently invalidated across all layers."""
        results = {}
        
        for layer_name in self.layers.keys():
            results[layer_name] = await self.get_from_layer(layer_name, key)
        
        results["redis"] = await self.get_from_layer("redis", key)
        
        values = [v for v in results.values() if v is not None]
        
        if len(values) == 0:
            return True
        elif len(set(str(v) for v in values)) == 1:
            return True
        else:
            logger.warning(f"Consistency violation for key {key}: {results}")
            return False


async def generate_test_data(num_keys: int = 500) -> tuple[List[str], Dict[str, str], Set[str]]:
    """Generate test data for cache invalidation tests."""
    test_keys = [f"test:key:{i}" for i in range(num_keys)]
    test_values = {key: f"value_{uuid.uuid4().hex[:8]}" for key in test_keys}
    test_tags = {
        "user_data", "session_data", "ai_responses", 
        "metrics_cache", "schema_cache"
    }
    return test_keys, test_values, test_tags


async def populate_cache_layers(cache_manager: MultiLayerCacheManager, test_keys: List[str], test_values: Dict[str, str], test_tags: Set[str], sample_size: int = 100):
    """Helper method to populate cache layers with test data."""
    populate_keys = random.sample(test_keys, min(sample_size, len(test_keys)))
    
    for key in populate_keys:
        value = test_values[key]
        tags = random.sample(list(test_tags), 2)
        await cache_manager.set_multi_layer(key, value, tags=set(tags))
    
    logger.info(f"Populated cache layers with {len(populate_keys)} test entries")
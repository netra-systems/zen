"""Database Query Cache Retrieval

Cache retrieval operations for getting cached queries.
"""

import time
import json
from typing import Any, Dict, Optional

from app.logging_config import central_logger
from .cache_config import (
    CacheEntry, CacheMetrics, QueryCacheConfig, CacheKeyGenerator,
    QueryPatternAnalyzer
)

logger = central_logger.get_logger(__name__)


class CacheRetrieval:
    """Handle cache retrieval operations."""
    
    @staticmethod
    async def get_cached_data(redis, cache_key: str) -> Optional[str]:
        """Get cached data from Redis."""
        return await redis.get(cache_key)

    @staticmethod
    def deserialize_cache_entry(cached_data: str) -> Optional[CacheEntry]:
        """Deserialize cached data to cache entry."""
        try:
            entry_data = json.loads(cached_data)
            return CacheEntry.from_dict(entry_data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to deserialize cache entry: {e}")
            return None

    @staticmethod
    async def update_access_data(redis, cache_key: str, entry: CacheEntry) -> None:
        """Update cache entry with new access data."""
        await redis.set(
            cache_key,
            json.dumps(entry.to_dict()),
            ex=int(entry.expires_at - time.time())
        )

    @staticmethod
    async def handle_expired_entry(redis, cache_key: str, metrics: CacheMetrics) -> None:
        """Handle expired cache entry."""
        await redis.delete(cache_key)
        metrics.cache_size = max(0, metrics.cache_size - 1)

    @staticmethod
    def update_hit_metrics(metrics: CacheMetrics, start_time: float) -> None:
        """Update cache hit metrics."""
        metrics.hits += 1
        metrics.total_cache_time += time.time() - start_time

    @staticmethod
    def update_miss_metrics(metrics: CacheMetrics) -> None:
        """Update cache miss metrics."""
        metrics.misses += 1

    @staticmethod
    async def _process_valid_entry(redis, cache_key: str, entry: CacheEntry, metrics: CacheMetrics, query: str, start_time: float) -> Any:
        """Process valid cache entry."""
        entry.access()
        await CacheRetrieval.update_access_data(redis, cache_key, entry)
        CacheRetrieval.update_hit_metrics(metrics, start_time)
        pattern = QueryPatternAnalyzer.normalize_query_pattern(query)
        logger.debug(f"Cache hit for query pattern: {pattern}")
        return entry.value

    @staticmethod
    async def _handle_cache_hit(redis, cache_key: str, entry: CacheEntry, metrics: CacheMetrics, query: str, start_time: float) -> Optional[Any]:
        """Handle cache hit processing."""
        if entry and not entry.is_expired():
            return await CacheRetrieval._process_valid_entry(redis, cache_key, entry, metrics, query, start_time)
        await CacheRetrieval._handle_invalid_entry(redis, cache_key, entry, metrics)
        return None
    
    @staticmethod
    async def _handle_invalid_entry(redis, cache_key: str, entry: CacheEntry, metrics: CacheMetrics) -> None:
        """Handle invalid or expired cache entry."""
        if entry:
            await CacheRetrieval.handle_expired_entry(redis, cache_key, metrics)
        else:
            await redis.delete(cache_key)

    @staticmethod
    async def _process_cache_lookup(redis, cache_key: str, query: str, metrics: CacheMetrics, start_time: float) -> Optional[Any]:
        """Process cache lookup and return result if found."""
        cached_data = await CacheRetrieval.get_cached_data(redis, cache_key)
        if cached_data:
            entry = CacheRetrieval.deserialize_cache_entry(cached_data)
            return await CacheRetrieval._handle_cache_hit(redis, cache_key, entry, metrics, query, start_time)
        return None

    @staticmethod
    async def get_cached_result(
        redis, query: str, params: Optional[Dict], config: QueryCacheConfig, metrics: CacheMetrics
    ) -> Optional[Any]:
        """Get cached query result."""
        if not config.enabled:
            return None
        start_time = time.time()
        cache_key = CacheKeyGenerator.generate_cache_key(query, params, config.cache_prefix)
        try:
            result = await CacheRetrieval._process_cache_lookup(redis, cache_key, query, metrics, start_time)
            if result is not None:
                return result
            CacheRetrieval.update_miss_metrics(metrics)
            return None
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            CacheRetrieval.update_miss_metrics(metrics)
            return None


class CacheInvalidation:
    """Handle cache invalidation operations."""
    
    @staticmethod
    async def get_keys_by_tag(redis, tag: str, cache_prefix: str) -> set:
        """Get cache keys associated with a tag."""
        tag_key = f"{cache_prefix}tag:{tag}"
        return await redis.smembers(tag_key)

    @staticmethod
    async def delete_tagged_keys(redis, cache_keys: set, tag_key: str, metrics: CacheMetrics) -> int:
        """Delete keys associated with a tag."""
        if not cache_keys:
            return 0
        await redis.delete(*cache_keys)
        await redis.delete(tag_key)
        metrics.cache_size = max(0, metrics.cache_size - len(cache_keys))
        return len(cache_keys)

    @staticmethod
    async def _execute_tag_invalidation(redis, tag: str, config: QueryCacheConfig, metrics: CacheMetrics) -> int:
        """Execute tag-based cache invalidation."""
        tag_key = f"{config.cache_prefix}tag:{tag}"
        cache_keys = await CacheInvalidation.get_keys_by_tag(redis, tag, config.cache_prefix)
        count = await CacheInvalidation.delete_tagged_keys(redis, cache_keys, tag_key, metrics)
        if count > 0:
            logger.info(f"Invalidated {count} entries with tag: {tag}")
        return count

    @staticmethod
    async def invalidate_by_tag(redis, tag: str, config: QueryCacheConfig, metrics: CacheMetrics) -> int:
        """Invalidate all cached entries with specific tag."""
        try:
            return await CacheInvalidation._execute_tag_invalidation(redis, tag, config, metrics)
        except Exception as e:
            logger.error(f"Error invalidating cache by tag {tag}: {e}")
            return 0

    @staticmethod
    async def get_keys_by_pattern(redis, pattern: str, cache_prefix: str) -> list:
        """Get cache keys matching a pattern."""
        return await redis.keys(f"{cache_prefix}*{pattern}*")

    @staticmethod
    async def delete_pattern_keys(redis, cache_keys: list, metrics: CacheMetrics) -> int:
        """Delete keys matching a pattern."""
        if cache_keys:
            await redis.delete(*cache_keys)
            metrics.cache_size = max(0, metrics.cache_size - len(cache_keys))
            return len(cache_keys)
        return 0

    @staticmethod
    async def _execute_pattern_invalidation(redis, pattern: str, config: QueryCacheConfig, metrics: CacheMetrics) -> int:
        """Execute pattern-based cache invalidation."""
        cache_keys = await CacheInvalidation.get_keys_by_pattern(redis, pattern, config.cache_prefix)
        count = await CacheInvalidation.delete_pattern_keys(redis, cache_keys, metrics)
        if count > 0:
            logger.info(f"Invalidated {count} entries matching pattern: {pattern}")
        return count

    @staticmethod
    async def invalidate_pattern(redis, pattern: str, config: QueryCacheConfig, metrics: CacheMetrics) -> int:
        """Invalidate cached entries matching pattern."""
        try:
            return await CacheInvalidation._execute_pattern_invalidation(redis, pattern, config, metrics)
        except Exception as e:
            logger.error(f"Error invalidating cache by pattern {pattern}: {e}")
            return 0

    @staticmethod
    async def _execute_clear_all(redis, config: QueryCacheConfig, metrics: CacheMetrics) -> int:
        """Execute clear all cache operation."""
        cache_keys = await redis.keys(f"{config.cache_prefix}*")
        if not cache_keys:
            return 0
        return await CacheInvalidation._clear_keys_and_update_metrics(redis, cache_keys, metrics)
    
    @staticmethod
    async def _clear_keys_and_update_metrics(redis, cache_keys: list, metrics: CacheMetrics) -> int:
        """Clear cache keys and update metrics."""
        await redis.delete(*cache_keys)
        cleared_count = len(cache_keys)
        metrics.cache_size = 0
        logger.info(f"Cleared {cleared_count} cached entries")
        return cleared_count

    @staticmethod
    async def clear_all_cache(redis, config: QueryCacheConfig, metrics: CacheMetrics) -> int:
        """Clear all cached entries."""
        try:
            return await CacheInvalidation._execute_clear_all(redis, config, metrics)
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0
"""Database Query Cache Storage

Cache storage operations for setting and managing cached queries.
"""

import time
import json
from typing import Any, Dict, List, Optional, Set

from app.logging_config import central_logger
from .cache_config import (
    CacheEntry, CacheMetrics, QueryCacheConfig, CacheKeyGenerator,
    QueryPatternAnalyzer, CacheabilityChecker, AdaptiveTTLCalculator
)

logger = central_logger.get_logger(__name__)


class CacheStorage:
    """Handle cache storage operations."""
    
    @staticmethod
    def create_cache_entry(cache_key: str, result: Any, ttl: int, duration: float, tags: Optional[Set[str]]) -> CacheEntry:
        """Create cache entry for storage."""
        now = time.time()
        return CacheEntry(
            key=cache_key,
            value=result,
            created_at=now,
            expires_at=now + ttl,
            query_duration=duration,
            tags=tags or set()
        )

    @staticmethod
    async def store_cache_entry(redis, cache_key: str, entry: CacheEntry, ttl: int) -> None:
        """Store cache entry in Redis."""
        await redis.set(
            cache_key,
            json.dumps(entry.to_dict()),
            ex=ttl
        )

    @staticmethod
    async def store_tag_associations(redis, tags: Set[str], cache_key: str, cache_prefix: str, ttl: int) -> None:
        """Store tag associations for cache entry."""
        for tag in tags:
            tag_key = f"{cache_prefix}tag:{tag}"
            await redis.sadd(tag_key, cache_key)
            await redis.expire(tag_key, ttl + 60)  # Slight buffer

    @staticmethod
    def update_pattern_tracking(
        query: str, 
        duration: float, 
        query_patterns: Dict[str, int], 
        query_durations: Dict[str, List[float]]
    ) -> None:
        """Update query pattern and performance tracking."""
        pattern = QueryPatternAnalyzer.normalize_query_pattern(query)
        query_patterns[pattern] = query_patterns.get(pattern, 0) + 1
        
        if pattern not in query_durations:
            query_durations[pattern] = []
        query_durations[pattern].append(duration)
        
        # Keep only recent durations
        if len(query_durations[pattern]) > 10:
            query_durations[pattern] = query_durations[pattern][-10:]

    @staticmethod
    def _prepare_cache_data(query: str, params: Optional[Dict], duration: Optional[float], config: QueryCacheConfig) -> tuple:
        """Prepare cache key and duration data."""
        cache_key = CacheKeyGenerator.generate_cache_key(query, params, config.cache_prefix)
        query_duration = duration or 0.0
        return cache_key, query_duration
    
    @staticmethod
    async def _store_cache_data(redis, cache_key: str, entry: CacheEntry, tags: Optional[Set[str]], config: QueryCacheConfig, ttl: int) -> None:
        """Store cache entry and tag associations."""
        await CacheStorage.store_cache_entry(redis, cache_key, entry, ttl)
        if tags:
            await CacheStorage.store_tag_associations(redis, tags, cache_key, config.cache_prefix, ttl)
    
    @staticmethod
    def _update_metrics_and_log(metrics: CacheMetrics, ttl: int) -> None:
        """Update cache metrics and log success."""
        metrics.cache_size += 1
        logger.debug(f"Cached query result with TTL {ttl}s")
    
    @staticmethod
    async def cache_result(
        redis,
        query: str,
        result: Any,
        params: Optional[Dict],
        duration: Optional[float],
        tags: Optional[Set[str]],
        config: QueryCacheConfig,
        metrics: CacheMetrics,
        query_patterns: Dict[str, int],
        query_durations: Dict[str, List[float]]
    ) -> bool:
        """Cache query result."""
        if not CacheabilityChecker.should_cache_query(query, result, config):
            return False
        
        try:
            return await CacheStorage._execute_cache_operation(
                redis, query, result, params, duration, tags, config, metrics, query_patterns, query_durations
            )
        except Exception as e:
            logger.error(f"Error caching query result: {e}")
            return False
    
    @staticmethod
    async def _execute_cache_operation(
        redis, query: str, result: Any, params: Optional[Dict], duration: Optional[float],
        tags: Optional[Set[str]], config: QueryCacheConfig, metrics: CacheMetrics,
        query_patterns: Dict[str, int], query_durations: Dict[str, List[float]]
    ) -> bool:
        """Execute the cache operation with all required steps."""
        cache_key, query_duration = CacheStorage._prepare_cache_data(query, params, duration, config)
        CacheStorage.update_pattern_tracking(query, query_duration, query_patterns, query_durations)
        ttl = AdaptiveTTLCalculator.calculate_adaptive_ttl(query, query_duration, query_patterns, config)
        entry = CacheStorage.create_cache_entry(cache_key, result, ttl, query_duration, tags)
        await CacheStorage._store_cache_data(redis, cache_key, entry, tags, config, ttl)
        CacheStorage._update_metrics_and_log(metrics, ttl)
        return True


class CacheMetricsBuilder:
    """Build cache metrics and statistics."""
    
    @staticmethod
    def add_query_pattern_stats(metrics_dict: Dict[str, Any], query_patterns: Dict[str, int]) -> None:
        """Add query pattern statistics to metrics."""
        metrics_dict['top_query_patterns'] = sorted(
            query_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

    @staticmethod
    def add_performance_stats(metrics_dict: Dict[str, Any], query_durations: Dict[str, List[float]]) -> None:
        """Add performance statistics to metrics."""
        avg_durations = {}
        for pattern, durations in query_durations.items():
            if durations:
                avg_durations[pattern] = sum(durations) / len(durations)
        
        metrics_dict['avg_query_durations'] = sorted(
            avg_durations.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

    @staticmethod
    def build_metrics(
        metrics: CacheMetrics, 
        query_patterns: Dict[str, int], 
        query_durations: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """Build comprehensive cache metrics."""
        metrics_dict = metrics.to_dict()
        
        CacheMetricsBuilder.add_query_pattern_stats(metrics_dict, query_patterns)
        CacheMetricsBuilder.add_performance_stats(metrics_dict, query_durations)
        
        return metrics_dict
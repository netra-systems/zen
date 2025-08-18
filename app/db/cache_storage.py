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
    def _calculate_cache_timestamps(ttl: int) -> tuple[float, float]:
        """Calculate created_at and expires_at timestamps."""
        now = time.time()
        expires_at = now + ttl
        return now, expires_at
    
    @staticmethod
    def _build_cache_entry_object(cache_key: str, result: Any, created_at: float, expires_at: float, duration: float, tags: Optional[Set[str]]) -> CacheEntry:
        """Build CacheEntry object with provided timestamps."""
        return CacheEntry(
            key=cache_key, value=result, created_at=created_at,
            expires_at=expires_at, query_duration=duration,
            tags=tags or set()
        )
    
    @staticmethod
    def create_cache_entry(cache_key: str, result: Any, ttl: int, duration: float, tags: Optional[Set[str]]) -> CacheEntry:
        """Create cache entry for storage."""
        created_at, expires_at = CacheStorage._calculate_cache_timestamps(ttl)
        return CacheStorage._build_cache_entry_object(
            cache_key, result, created_at, expires_at, duration, tags
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
    def _update_pattern_counter(pattern: str, query_patterns: Dict[str, int]) -> None:
        """Update the pattern counter in query_patterns."""
        query_patterns[pattern] = query_patterns.get(pattern, 0) + 1
    
    @staticmethod
    def _initialize_pattern_durations(pattern: str, query_durations: Dict[str, List[float]]) -> None:
        """Initialize duration list for pattern if not exists."""
        if pattern not in query_durations:
            query_durations[pattern] = []
    
    @staticmethod
    def _add_and_trim_duration(pattern: str, duration: float, query_durations: Dict[str, List[float]]) -> None:
        """Add duration and trim to recent 10 entries."""
        query_durations[pattern].append(duration)
        if len(query_durations[pattern]) > 10:
            query_durations[pattern] = query_durations[pattern][-10:]
    
    @staticmethod
    def _update_all_pattern_data(pattern: str, duration: float, query_patterns: Dict[str, int], query_durations: Dict[str, List[float]]) -> None:
        """Update all pattern tracking data."""
        CacheStorage._update_pattern_counter(pattern, query_patterns)
        CacheStorage._initialize_pattern_durations(pattern, query_durations)
        CacheStorage._add_and_trim_duration(pattern, duration, query_durations)
    
    @staticmethod
    def update_pattern_tracking(
        query: str, duration: float, 
        query_patterns: Dict[str, int], query_durations: Dict[str, List[float]]
    ) -> None:
        """Update query pattern and performance tracking."""
        pattern = QueryPatternAnalyzer.normalize_query_pattern(query)
        CacheStorage._update_all_pattern_data(pattern, duration, query_patterns, query_durations)

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
    def _calculate_average_durations(query_durations: Dict[str, List[float]]) -> Dict[str, float]:
        """Calculate average durations for each pattern."""
        avg_durations = {}
        for pattern, durations in query_durations.items():
            if durations:
                avg_durations[pattern] = sum(durations) / len(durations)
        return avg_durations
    
    @staticmethod
    def _sort_durations_by_time(avg_durations: Dict[str, float]) -> List[tuple]:
        """Sort average durations by time, return top 10."""
        return sorted(
            avg_durations.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
    
    @staticmethod
    def add_performance_stats(metrics_dict: Dict[str, Any], query_durations: Dict[str, List[float]]) -> None:
        """Add performance statistics to metrics."""
        avg_durations = CacheMetricsBuilder._calculate_average_durations(query_durations)
        metrics_dict['avg_query_durations'] = CacheMetricsBuilder._sort_durations_by_time(avg_durations)

    @staticmethod
    def _build_base_metrics_dict(metrics: CacheMetrics) -> Dict[str, Any]:
        """Build base metrics dictionary from CacheMetrics object."""
        return metrics.to_dict()
    
    @staticmethod
    def _add_all_metrics_stats(
        metrics_dict: Dict[str, Any], 
        query_patterns: Dict[str, int], 
        query_durations: Dict[str, List[float]]
    ) -> None:
        """Add all metrics statistics to the metrics dictionary."""
        CacheMetricsBuilder.add_query_pattern_stats(metrics_dict, query_patterns)
        CacheMetricsBuilder.add_performance_stats(metrics_dict, query_durations)
    
    @staticmethod
    def _create_enhanced_metrics_dict(metrics: CacheMetrics, query_patterns: Dict[str, int], query_durations: Dict[str, List[float]]) -> Dict[str, Any]:
        """Create metrics dictionary with all statistics."""
        metrics_dict = CacheMetricsBuilder._build_base_metrics_dict(metrics)
        CacheMetricsBuilder._add_all_metrics_stats(metrics_dict, query_patterns, query_durations)
        return metrics_dict
    
    @staticmethod
    def build_metrics(
        metrics: CacheMetrics, query_patterns: Dict[str, int], 
        query_durations: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """Build comprehensive cache metrics."""
        return CacheMetricsBuilder._create_enhanced_metrics_dict(
            metrics, query_patterns, query_durations
        )
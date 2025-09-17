"""Database Query Cache Core

Main QueryCache class for coordinating query caching operations.
"""

from typing import Any, Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.cache_config import CacheMetrics
from netra_backend.app.db.cache_retrieval import CacheInvalidation, CacheRetrieval
from netra_backend.app.db.cache_storage import CacheMetricsBuilder, CacheStorage
from netra_backend.app.db.cache_strategies import (
    CacheTaskManager,
    EvictionStrategyFactory,
    QueryPatternTracker,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.config import get_config

logger = central_logger.get_logger(__name__)


class QueryCache:
    """Intelligent database query cache."""
    
    def __init__(self, config: Optional[Any] = None):
        """Initialize query cache."""
        # Use unified config for cache settings
        unified_config = get_config()
        self.config = self._build_cache_config(unified_config)
        self.redis = redis_manager
        self.metrics = CacheMetrics()
        self.pattern_tracker = QueryPatternTracker()
        self.task_manager = CacheTaskManager()
    
    def _build_cache_config(self, config):
        """Build cache configuration from unified config."""
        # Create a simple config object with attributes from unified config
        class CacheConfig:
            enabled = config.cache_enabled
            default_ttl = config.cache_default_ttl
            max_cache_size = config.cache_max_size
            cache_prefix = config.cache_prefix
            metrics_enabled = config.cache_metrics_enabled
            frequent_query_threshold = config.cache_frequent_query_threshold
            frequent_query_ttl_multiplier = config.cache_frequent_query_ttl_multiplier
            slow_query_threshold = config.cache_slow_query_threshold
            slow_query_ttl_multiplier = config.cache_slow_query_ttl_multiplier
            strategy = config.cache_strategy
        return CacheConfig()

    async def start(self) -> None:
        """Start background tasks."""
        if self.task_manager._running:
            return
        
        await self.task_manager.start_background_tasks(self.redis, self.config, self.metrics)
        logger.info("Query cache started")

    async def stop(self) -> None:
        """Stop background tasks."""
        await self.task_manager.stop_background_tasks()
        logger.info("Query cache stopped")

    async def get_cached_result(
        self,
        query: str,
        params: Optional[Dict] = None
    ) -> Optional[Any]:
        """Get cached query result."""
        return await CacheRetrieval.get_cached_result(
            self.redis, query, params, self.config, self.metrics
        )

    async def _store_cache_result(self, query: str, result: Any, params: Optional[Dict], duration: Optional[float], tags: Optional[Set[str]]) -> bool:
        """Store result in cache storage."""
        return await CacheStorage.cache_result(
            self.redis, query, result, params, duration, tags,
            self.config, self.metrics, 
            self.pattern_tracker.query_patterns,
            self.pattern_tracker.query_durations
        )
    
    async def _handle_cache_eviction_if_needed(self, success: bool):
        """Trigger eviction if cache size exceeded."""
        if success and self.metrics.cache_size > self.config.max_cache_size:
            await self._trigger_eviction()
    
    async def cache_result(self, query: str, result: Any, params: Optional[Dict] = None, duration: Optional[float] = None, tags: Optional[Set[str]] = None) -> bool:
        """Cache query result."""
        success = await self._store_cache_result(query, result, params, duration, tags)
        await self._handle_cache_eviction_if_needed(success)
        return success

    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cached entries with specific tag."""
        return await CacheInvalidation.invalidate_by_tag(self.redis, tag, self.config, self.metrics)

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cached entries matching pattern."""
        return await CacheInvalidation.invalidate_pattern(self.redis, pattern, self.config, self.metrics)

    async def clear_all(self) -> int:
        """Clear all cached entries."""
        return await CacheInvalidation.clear_all_cache(self.redis, self.config, self.metrics)

    async def _trigger_eviction(self) -> None:
        """Trigger cache eviction based on strategy."""
        try:
            await EvictionStrategyFactory.execute_eviction(self.redis, self.config, self.metrics)
        except Exception as e:
            logger.error(f"Error during cache eviction: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        return CacheMetricsBuilder.build_metrics(
            self.metrics,
            self.pattern_tracker.query_patterns,
            self.pattern_tracker.query_durations
        )


# Global query cache instance
query_cache = QueryCache()


class CachedQueryExecutor:
    """Execute cached queries using strategy pattern."""
    
    @staticmethod
    async def _check_cache_for_result(cache: QueryCache, query: str, params: Optional[Dict], force_refresh: bool):
        """Check cache for existing result if not forcing refresh."""
        if not force_refresh:
            return await cache.get_cached_result(query, params)
        return None
    
    @staticmethod
    async def _execute_and_format_query(session: AsyncSession, query: str, params: Optional[Dict]):
        """Execute query and format result."""
        from sqlalchemy import text
        result = await session.execute(text(query), params or {})
        return [dict(row._mapping) for row in result.fetchall()]
    
    @staticmethod
    async def _cache_query_result(cache: QueryCache, query: str, query_result, params: Optional[Dict]):
        """Cache the query result."""
        await cache.cache_result(query, query_result, params)
        return query_result
    
    @staticmethod
    async def execute_with_cache_check(cache: QueryCache, session: AsyncSession, query: str, params: Optional[Dict], force_refresh: bool) -> Any:
        """Execute query with cache check."""
        cached_result = await CachedQueryExecutor._check_cache_for_result(cache, query, params, force_refresh)
        if cached_result is not None:
            return cached_result
        
        query_result = await CachedQueryExecutor._execute_and_format_query(session, query, params)
        return await CachedQueryExecutor._cache_query_result(cache, query, query_result, params)

    @staticmethod
    async def _cache_query_result_with_tags(cache: QueryCache, query: str, query_result, params: Optional[Dict], cache_tags: Optional[Set[str]]):
        """Cache the query result with tags."""
        await cache.cache_result(query, query_result, params, tags=cache_tags)
        return query_result
    
    @staticmethod
    async def execute_with_tags(cache: QueryCache, session: AsyncSession, query: str, params: Optional[Dict], cache_tags: Optional[Set[str]]) -> Any:
        """Execute query with cache tags."""
        cached_result = await cache.get_cached_result(query, params)
        if cached_result is not None:
            return cached_result
        
        query_result = await CachedQueryExecutor._execute_and_format_query(session, query, params)
        return await CachedQueryExecutor._cache_query_result_with_tags(cache, query, query_result, params, cache_tags)


async def _execute_with_force_refresh(session: AsyncSession, query: str, params: Optional[Dict], force_refresh: bool) -> Any:
    """Execute query with force refresh strategy."""
    return await CachedQueryExecutor.execute_with_cache_check(
        query_cache, session, query, params, force_refresh
    )

async def _execute_with_cache_tags(session: AsyncSession, query: str, params: Optional[Dict], cache_tags: Optional[Set[str]]) -> Any:
    """Execute query with cache tags strategy."""
    return await CachedQueryExecutor.execute_with_tags(
        query_cache, session, query, params, cache_tags
    )

async def _execute_with_standard_cache(session: AsyncSession, query: str, params: Optional[Dict]) -> Any:
    """Execute query with standard cache strategy."""
    return await CachedQueryExecutor.execute_with_cache_check(
        query_cache, session, query, params, False
    )

async def cached_query(session: AsyncSession, query: str, params: Optional[Dict] = None, cache_tags: Optional[Set[str]] = None, force_refresh: bool = False) -> Any:
    """Execute query using cache strategy."""
    if force_refresh:
        return await _execute_with_force_refresh(session, query, params, force_refresh)
    elif cache_tags:
        return await _execute_with_cache_tags(session, query, params, cache_tags)
    else:
        return await _execute_with_standard_cache(session, query, params)
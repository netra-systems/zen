"""Database Query Cache Core

Main QueryCache class for coordinating query caching operations.
"""

from typing import Any, Dict, List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import central_logger
from app.redis_manager import redis_manager
from .cache_config import QueryCacheConfig, CacheMetrics
from .cache_strategies import CacheTaskManager, EvictionStrategyFactory, QueryPatternTracker
from .cache_retrieval import CacheRetrieval, CacheInvalidation
from .cache_storage import CacheStorage, CacheMetricsBuilder

logger = central_logger.get_logger(__name__)


class QueryCache:
    """Intelligent database query cache."""
    
    def __init__(self, config: Optional[QueryCacheConfig] = None):
        """Initialize query cache."""
        self.config = config or QueryCacheConfig()
        self.redis = redis_manager
        self.metrics = CacheMetrics()
        self.pattern_tracker = QueryPatternTracker()
        self.task_manager = CacheTaskManager()

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

    async def cache_result(
        self,
        query: str,
        result: Any,
        params: Optional[Dict] = None,
        duration: Optional[float] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Cache query result."""
        success = await CacheStorage.cache_result(
            self.redis, query, result, params, duration, tags,
            self.config, self.metrics, 
            self.pattern_tracker.query_patterns,
            self.pattern_tracker.query_durations
        )
        
        # Trigger eviction if cache is too large
        if success and self.metrics.cache_size > self.config.max_cache_size:
            await self._trigger_eviction()
        
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
    async def execute_with_cache_check(
        cache: QueryCache,
        session: AsyncSession,
        query: str,
        params: Optional[Dict],
        force_refresh: bool
    ) -> Any:
        """Execute query with cache check."""
        if not force_refresh:
            cached_result = await cache.get_cached_result(query, params)
            if cached_result is not None:
                return cached_result
        
        # Execute query and cache result
        from sqlalchemy import text
        result = await session.execute(text(query), params or {})
        query_result = [dict(row._mapping) for row in result.fetchall()]
        
        # Cache the result
        await cache.cache_result(query, query_result, params)
        
        return query_result

    @staticmethod
    async def execute_with_tags(
        cache: QueryCache,
        session: AsyncSession,
        query: str,
        params: Optional[Dict],
        cache_tags: Optional[Set[str]]
    ) -> Any:
        """Execute query with cache tags."""
        cached_result = await cache.get_cached_result(query, params)
        if cached_result is not None:
            return cached_result
        
        # Execute query and cache result with tags
        from sqlalchemy import text
        result = await session.execute(text(query), params or {})
        query_result = [dict(row._mapping) for row in result.fetchall()]
        
        # Cache the result with tags
        await cache.cache_result(query, query_result, params, tags=cache_tags)
        
        return query_result


async def cached_query(
    session: AsyncSession,
    query: str,
    params: Optional[Dict] = None,
    cache_tags: Optional[Set[str]] = None,
    force_refresh: bool = False
) -> Any:
    """Execute query using cache strategy."""
    if force_refresh:
        return await CachedQueryExecutor.execute_with_cache_check(
            query_cache, session, query, params, force_refresh
        )
    elif cache_tags:
        return await CachedQueryExecutor.execute_with_tags(
            query_cache, session, query, params, cache_tags
        )
    else:
        return await CachedQueryExecutor.execute_with_cache_check(
            query_cache, session, query, params, False
        )
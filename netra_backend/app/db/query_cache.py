"""Database Query Caching System

Provides intelligent query result caching with TTL, invalidation,
and performance optimization.

This module has been refactored into focused sub-modules for maintainability.
"""

# Import all components from the refactored modules
from netra_backend.app.db.cache_config import (
    AdaptiveTTLCalculator,
    CacheabilityChecker,
    CacheEntry,
    CacheKeyGenerator,
    CacheMetrics,
    CacheStrategy,
    QueryCacheConfig,
    QueryPatternAnalyzer,
)
from netra_backend.app.db.cache_core import (
    CachedQueryExecutor,
    QueryCache,
    cached_query,
    query_cache,
)
from netra_backend.app.db.cache_operations import (
    CacheInvalidation,
    CacheMetricsBuilder,
    CacheRetrieval,
    CacheStorage,
)
from netra_backend.app.db.cache_strategies import (
    AdaptiveEvictionStrategy,
    CacheCleanupWorker,
    CacheMetricsWorker,
    CacheTaskManager,
    EvictionStrategyFactory,
    LRUEvictionStrategy,
    QueryPatternTracker,
    TTLEvictionStrategy,
)

# Maintain backward compatibility exports
__all__ = [
    'CacheStrategy',
    'QueryCacheConfig',
    'CacheEntry',
    'CacheMetrics',
    'QueryCache',
    'query_cache',
    'cached_query'
]
"""Database Query Caching System

Provides intelligent query result caching with TTL, invalidation,
and performance optimization.

This module has been refactored into focused sub-modules for maintainability.
"""

# Import all components from the refactored modules
from .cache_config import (
    CacheStrategy, QueryCacheConfig, CacheEntry, CacheMetrics,
    CacheKeyGenerator, QueryPatternAnalyzer, CacheabilityChecker,
    AdaptiveTTLCalculator
)
from .cache_strategies import (
    LRUEvictionStrategy, TTLEvictionStrategy, AdaptiveEvictionStrategy,
    EvictionStrategyFactory, CacheCleanupWorker, CacheMetricsWorker,
    QueryPatternTracker, CacheTaskManager
)
from .cache_operations import (
    CacheRetrieval, CacheStorage, CacheInvalidation, CacheMetricsBuilder
)
from .cache_core import (
    QueryCache, query_cache, CachedQueryExecutor, cached_query
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
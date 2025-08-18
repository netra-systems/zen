"""Cache interfaces - Single source of truth.

Consolidated cache management for both schema-specific agent caching
and general LLM caching with memory limits and TTL management.
Follows 300-line limit and 8-line functions.
"""

import asyncio
import time
import weakref
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CacheManager:
    """Unified cache manager supporting both schema-specific and general LLM caching."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600, agent=None):
        """Initialize cache manager with memory limits and optional agent reference."""
        self._set_basic_properties(max_size, ttl_seconds, agent)
        self._initialize_cache_structures()
        self._init_schema_cache()
    
    def _set_basic_properties(self, max_size: int, ttl_seconds: int, agent) -> None:
        """Set basic cache properties."""
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.agent = agent
    
    def _initialize_cache_structures(self) -> None:
        """Initialize cache data structures."""
        self._cache: Dict[str, Dict] = {}
        self._access_times: Dict[str, datetime] = {}
        self._weak_refs: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        self._lock = asyncio.Lock()
    
    def _init_schema_cache(self) -> None:
        """Initialize schema-specific cache if agent is provided."""
        if self.agent:
            if not hasattr(self.agent, '_schema_cache'):
                self.agent._schema_cache: Dict[str, Dict[str, Any]] = {}
                self.agent._schema_cache_timestamps: Dict[str, float] = {}
    
    # General cache methods
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with expiration check."""
        async with self._lock:
            return await self._get_from_cache_with_validation(key)
    
    async def _get_from_cache_with_validation(self, key: str) -> Optional[Any]:
        """Get from cache with expiration and access time updates."""
        if key not in self._cache:
            return None
        return self._handle_cache_hit(key)
    
    def _handle_cache_hit(self, key: str) -> Optional[Any]:
        """Handle cache hit with expiration check."""
        if self._is_expired(key):
            self._remove_entry(key)
            return None
        self._update_access_time(key)
        return self._cache[key]['value']
    
    async def set(self, key: str, value: Any) -> None:
        """Set value in cache with eviction and TTL."""
        async with self._lock:
            await self._ensure_capacity()
            self._cache[key] = {'value': value, 'created': datetime.now()}
            self._access_times[key] = datetime.now()
            self._try_add_weak_ref(key, value)
    
    def _try_add_weak_ref(self, key: str, value: Any) -> None:
        """Try to add weak reference if object supports it."""
        try:
            self._weak_refs[key] = value
        except TypeError:
            pass  # Strings and primitives can't be weakly referenced
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._weak_refs.clear()
    
    # Schema-specific cache methods
    
    async def get_cached_schema(self, table_name: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get cached schema information with TTL and cache invalidation."""
        if not self.agent:
            return None
        return await self._get_schema_with_cache_logic(table_name, force_refresh)
    
    async def _get_schema_with_cache_logic(self, table_name: str, force_refresh: bool) -> Optional[Dict[str, Any]]:
        """Handle schema cache logic with validation and refresh."""
        self._ensure_schema_cache_initialized()
        current_time = time.time()
        return await self._check_cache_or_fetch(table_name, force_refresh, current_time)
    
    async def _check_cache_or_fetch(self, table_name: str, force_refresh: bool, current_time: float) -> Optional[Dict[str, Any]]:
        """Check cache validity or fetch new schema."""
        if not force_refresh and self._is_schema_cache_valid(table_name, current_time):
            return self.agent._schema_cache[table_name]
        
        return await self._fetch_and_cache_schema(table_name, current_time)
    
    async def invalidate_schema_cache(self, table_name: Optional[str] = None) -> None:
        """Invalidate schema cache for specific table or all tables."""
        if not self._can_invalidate_schema_cache():
            return
        self._perform_cache_invalidation(table_name)
    
    def _can_invalidate_schema_cache(self) -> bool:
        """Check if schema cache can be invalidated."""
        return self.agent and hasattr(self.agent, '_schema_cache')
    
    def _perform_cache_invalidation(self, table_name: Optional[str]) -> None:
        """Perform the actual cache invalidation."""
        if table_name:
            self._invalidate_single_table_cache(table_name)
        else:
            self._invalidate_all_schema_cache_entries()
    
    def cache_clear(self) -> None:
        """Clear the schema cache (for test compatibility)."""
        if self.agent:
            if hasattr(self.agent, '_schema_cache'):
                self.agent._schema_cache.clear()
            if hasattr(self.agent, '_schema_cache_timestamps'):
                self.agent._schema_cache_timestamps.clear()
    
    # Helper methods for general cache
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        entry = self._cache.get(key)
        if not entry:
            return True
        age = (datetime.now() - entry['created']).total_seconds()
        return age > self.ttl_seconds
    
    def _update_access_time(self, key: str) -> None:
        """Update last access time for LRU tracking."""
        self._access_times[key] = datetime.now()
    
    def _remove_entry(self, key: str) -> None:
        """Remove cache entry and associated metadata."""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
        self._weak_refs.pop(key, None)
    
    async def _ensure_capacity(self) -> None:
        """Ensure cache doesn't exceed max size."""
        if len(self._cache) >= self.max_size:
            await self._evict_lru()
    
    async def _evict_lru(self) -> None:
        """Evict least recently used entries."""
        if not self._access_times:
            return
        self._evict_keys_by_access_time()
    
    def _evict_keys_by_access_time(self) -> None:
        """Evict keys based on access time order."""
        sorted_keys = sorted(self._access_times.keys(), key=lambda k: self._access_times[k])
        evict_count = len(self._cache) - self.max_size + 1
        
        for key in sorted_keys[:evict_count]:
            self._remove_entry(key)
            logger.debug(f"Evicted cache entry: {key}")
    
    # Helper methods for schema cache
    
    def _ensure_schema_cache_initialized(self) -> None:
        """Ensure schema cache dictionaries are initialized."""
        if not hasattr(self.agent, '_schema_cache'):
            self.agent._schema_cache: Dict[str, Dict[str, Any]] = {}
            self.agent._schema_cache_timestamps: Dict[str, float] = {}
    
    def _is_schema_cache_valid(self, table_name: str, current_time: float) -> bool:
        """Check if schema cache entry exists and is still valid."""
        if table_name not in self.agent._schema_cache:
            return False
        
        cache_time = self.agent._schema_cache_timestamps.get(table_name, 0)
        cache_age = current_time - cache_time
        return cache_age < 300  # 5 minutes TTL for schema cache
    
    async def _fetch_and_cache_schema(self, table_name: str, current_time: float) -> Optional[Dict[str, Any]]:
        """Fetch fresh schema and update cache."""
        if not hasattr(self.agent, 'clickhouse_ops'):
            return None
        return await self._get_and_cache_schema(table_name, current_time)
    
    async def _get_and_cache_schema(self, table_name: str, current_time: float) -> Optional[Dict[str, Any]]:
        """Get schema from ClickHouse and cache it."""
        schema = await self.agent.clickhouse_ops.get_table_schema(table_name)
        if schema:
            self._update_schema_cache(table_name, schema, current_time)
            await self.cleanup_old_schema_cache_entries(current_time)
        return schema
    
    def _update_schema_cache(self, table_name: str, schema: Dict[str, Any], current_time: float) -> None:
        """Update schema cache with new data."""
        self.agent._schema_cache[table_name] = schema
        self.agent._schema_cache_timestamps[table_name] = current_time
    
    async def cleanup_old_schema_cache_entries(self, current_time: float) -> None:
        """Clean up old schema cache entries to prevent memory leaks."""
        max_cache_age = 3600  # 1 hour
        tables_to_remove = self._identify_expired_schema_cache_entries(current_time, max_cache_age)
        self._remove_expired_schema_cache_entries(tables_to_remove)
    
    def _identify_expired_schema_cache_entries(self, current_time: float, max_cache_age: float) -> List[str]:
        """Identify schema cache entries that have expired."""
        return [
            table_name for table_name, timestamp in self.agent._schema_cache_timestamps.items()
            if current_time - timestamp > max_cache_age
        ]
    
    def _remove_expired_schema_cache_entries(self, tables_to_remove: List[str]) -> None:
        """Remove expired entries from schema cache."""
        for table_name in tables_to_remove:
            self.agent._schema_cache.pop(table_name, None)
            self.agent._schema_cache_timestamps.pop(table_name, None)
    
    def _invalidate_single_table_cache(self, table_name: str) -> None:
        """Invalidate cache for a specific table."""
        self.agent._schema_cache.pop(table_name, None)
        self.agent._schema_cache_timestamps.pop(table_name, None)
    
    def _invalidate_all_schema_cache_entries(self) -> None:
        """Clear entire schema cache."""
        self.agent._schema_cache.clear()
        self.agent._schema_cache_timestamps.clear()
    
    # Statistics and monitoring
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        async with self._lock:
            general_stats = self._get_general_cache_stats()
            schema_stats = self._get_schema_cache_stats()
            return {**general_stats, **schema_stats}
    
    def _get_general_cache_stats(self) -> Dict[str, Any]:
        """Get general cache statistics."""
        return {
            'general_cache_size': len(self._cache),
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds,
            'weak_refs_count': len(self._weak_refs)
        }
    
    def _get_schema_cache_stats(self) -> Dict[str, Any]:
        """Get schema cache statistics."""
        if not self._has_schema_cache():
            return {'schema_cache_size': 0, 'schema_cache_enabled': False}
        return self._build_schema_stats()
    
    def _has_schema_cache(self) -> bool:
        """Check if agent has schema cache."""
        return self.agent and hasattr(self.agent, '_schema_cache')
    
    def _build_schema_stats(self) -> Dict[str, Any]:
        """Build schema cache statistics dictionary."""
        return {
            'schema_cache_size': len(self.agent._schema_cache),
            'schema_cache_enabled': True,
            'schema_timestamps_count': len(self.agent._schema_cache_timestamps)
        }


class RequestPool:
    """Manages LLM request pooling with rate limiting."""
    
    def __init__(self, max_concurrent: int = 5, requests_per_minute: int = 60):
        """Initialize request pool with concurrency and rate limits."""
        self.max_concurrent = max_concurrent
        self.requests_per_minute = requests_per_minute
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._request_times = deque(maxlen=requests_per_minute)
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire permission to make request with rate limiting."""
        await self._check_rate_limit()
        await self._semaphore.acquire()
        await self._record_request()
    
    def release(self) -> None:
        """Release request slot."""
        self._semaphore.release()
    
    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        async with self._lock:
            await self._clean_old_requests()
            await self._wait_if_at_limit()
    
    async def _clean_old_requests(self) -> None:
        """Remove requests older than 1 minute."""
        cutoff = datetime.now() - timedelta(minutes=1)
        while self._request_times and self._request_times[0] < cutoff:
            self._request_times.popleft()
    
    async def _wait_if_at_limit(self) -> None:
        """Wait if at rate limit."""
        if len(self._request_times) >= self.requests_per_minute:
            oldest = self._request_times[0]
            wait_time = self._calculate_wait_time(oldest)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
    
    def _calculate_wait_time(self, oldest: datetime) -> float:
        """Calculate wait time until rate limit clears."""
        elapsed = (datetime.now() - oldest).total_seconds()
        return max(0, 60 - elapsed + 0.1)
    
    async def _record_request(self) -> None:
        """Record request timestamp."""
        async with self._lock:
            self._request_times.append(datetime.now())
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, *args):
        """Context manager exit."""
        self.release()


class ResourceMonitor:
    """Monitors and manages cache and resource usage."""
    
    def __init__(self):
        """Initialize resource monitor."""
        self.request_pools: Dict[str, RequestPool] = {}
        self.cache_managers: Dict[str, CacheManager] = {}
        self._metrics: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
    
    def get_request_pool(self, config_name: str) -> RequestPool:
        """Get or create request pool for configuration."""
        if config_name not in self.request_pools:
            self.request_pools[config_name] = self._create_pool_for_config(config_name)
        return self.request_pools[config_name]
    
    def get_cache_manager(self, config_name: str, agent=None) -> CacheManager:
        """Get or create cache manager for configuration."""
        if config_name not in self.cache_managers:
            self.cache_managers[config_name] = CacheManager(agent=agent)
        return self.cache_managers[config_name]
    
    def _create_pool_for_config(self, config_name: str) -> RequestPool:
        """Create request pool based on config type."""
        if 'fast' in config_name.lower():
            return RequestPool(max_concurrent=10, requests_per_minute=120)
        elif 'slow' in config_name.lower():
            return RequestPool(max_concurrent=3, requests_per_minute=30)
        return RequestPool(max_concurrent=5, requests_per_minute=60)
    
    async def record_request(self, config_name: str, success: bool, duration_ms: float) -> None:
        """Record request metrics for monitoring."""
        async with self._lock:
            self._ensure_metrics_exist(config_name)
            self._update_metrics(config_name, success, duration_ms)
    
    def _ensure_metrics_exist(self, config_name: str) -> None:
        """Ensure metrics dictionary exists for config."""
        if config_name not in self._metrics:
            self._metrics[config_name] = self._init_metrics()
    
    def _update_metrics(self, config_name: str, success: bool, duration_ms: float) -> None:
        """Update metrics with request data."""
        metrics = self._metrics[config_name]
        metrics['total_requests'] += 1
        metrics['total_duration_ms'] += duration_ms
        self._update_success_metrics(metrics, success)
    
    def _update_success_metrics(self, metrics: Dict, success: bool) -> None:
        """Update success/failure metrics."""
        if success:
            metrics['successful_requests'] += 1
        else:
            metrics['failed_requests'] += 1
    
    def _init_metrics(self) -> Dict:
        """Initialize metrics dictionary."""
        return {
            'total_requests': 0, 'successful_requests': 0,
            'failed_requests': 0, 'total_duration_ms': 0
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive resource usage metrics."""
        async with self._lock:
            pool_metrics = self._get_pool_metrics()
            cache_metrics = await self._get_cache_metrics()
            return self._build_metrics_response(pool_metrics, cache_metrics)
    
    def _get_pool_metrics(self) -> Dict[str, Dict[str, int]]:
        """Get request pool metrics."""
        return {name: {'max_concurrent': pool.max_concurrent, 'requests_per_minute': pool.requests_per_minute}
               for name, pool in self.request_pools.items()}
    
    async def _get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache manager metrics."""
        cache_metrics = {}
        for name, cache in self.cache_managers.items():
            cache_metrics[name] = await cache.get_stats()
        return cache_metrics
    
    def _build_metrics_response(self, pool_metrics: Dict, cache_metrics: Dict) -> Dict[str, Any]:
        """Build final metrics response dictionary."""
        return {
            'pools': pool_metrics,
            'caches': cache_metrics,
            'metrics': self._metrics.copy()
        }
    
    async def cleanup(self) -> None:
        """Cleanup all managed resources."""
        for cache in self.cache_managers.values():
            await cache.clear()
        self._metrics.clear()
        logger.info("Resource monitor cleaned up")


# Global resource monitor instance
resource_monitor = ResourceMonitor()
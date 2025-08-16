"""Resource management for LLM operations.

Provides request pooling, batching, and memory management
to prevent API overload and resource exhaustion.
"""

import asyncio
from typing import Any, Dict, List, Optional
from collections import deque
from datetime import datetime, timedelta
import weakref

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class RequestPool:
    """Manages LLM request pooling with rate limiting."""
    
    def __init__(self, max_concurrent: int = 5, 
                 requests_per_minute: int = 60):
        self.max_concurrent = max_concurrent
        self.requests_per_minute = requests_per_minute
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._request_times = deque(maxlen=requests_per_minute)
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire permission to make request."""
        await self._check_rate_limit()
        await self._semaphore.acquire()
        await self._record_request()
    
    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        async with self._lock:
            await self._clean_old_requests()
            await self._wait_if_at_limit()
    
    async def _clean_old_requests(self) -> None:
        """Remove requests older than 1 minute."""
        cutoff = datetime.now() - timedelta(minutes=1)
        while self._request_times:
            if self._request_times[0] >= cutoff:
                break
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
    
    def release(self) -> None:
        """Release request slot."""
        self._semaphore.release()
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, *args):
        """Context manager exit."""
        self.release()


class RequestBatcher:
    """Batches multiple requests for efficient processing."""
    
    def __init__(self, batch_size: int = 5, 
                 batch_timeout: float = 0.1):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._pending_requests: List[Dict] = []
        self._lock = asyncio.Lock()
        self._batch_event = asyncio.Event()
    
    async def add_request(self, request: Dict) -> asyncio.Future:
        """Add request to batch and return future."""
        future = asyncio.Future()
        async with self._lock:
            self._pending_requests.append({
                'request': request,
                'future': future
            })
            if len(self._pending_requests) >= self.batch_size:
                self._batch_event.set()
        return future
    
    async def process_batches(self, processor) -> None:
        """Process batches continuously."""
        while True:
            await self._wait_for_batch()
            batch = await self._get_batch()
            if batch:
                await self._process_batch(batch, processor)
    
    async def _wait_for_batch(self) -> None:
        """Wait for batch to be ready."""
        try:
            await asyncio.wait_for(
                self._batch_event.wait(), 
                timeout=self.batch_timeout
            )
        except asyncio.TimeoutError:
            pass
        self._batch_event.clear()
    
    async def _get_batch(self) -> List[Dict]:
        """Get current batch of requests."""
        async with self._lock:
            batch = self._pending_requests[:self.batch_size]
            self._pending_requests = self._pending_requests[self.batch_size:]
            return batch
    
    async def _process_batch(self, batch: List[Dict], processor) -> None:
        """Process batch of requests."""
        try:
            results = await processor(batch)
            self._set_results(batch, results)
        except Exception as e:
            self._set_errors(batch, e)
    
    def _set_results(self, batch: List[Dict], results: List) -> None:
        """Set results for batch futures."""
        for item, result in zip(batch, results):
            if not item['future'].done():
                item['future'].set_result(result)
    
    def _set_errors(self, batch: List[Dict], error: Exception) -> None:
        """Set error for batch futures."""
        for item in batch:
            if not item['future'].done():
                item['future'].set_exception(error)


class CacheManager:
    """Manages LLM cache with memory limits."""
    
    def __init__(self, max_size: int = 1000, 
                 ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict] = {}
        self._access_times: Dict[str, datetime] = {}
        self._weak_refs: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key not in self._cache:
                return None
            if self._is_expired(key):
                self._remove_entry(key)
                return None
            self._update_access_time(key)
            return self._cache[key]['value']
    
    async def set(self, key: str, value: Any) -> None:
        """Set value in cache with eviction."""
        async with self._lock:
            await self._ensure_capacity()
            self._cache[key] = {
                'value': value,
                'created': datetime.now()
            }
            self._access_times[key] = datetime.now()
            # Only add to weak refs if object supports it
            try:
                self._weak_refs[key] = value
            except TypeError:
                pass  # Strings and primitives can't be weakly referenced
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        entry = self._cache.get(key)
        if not entry:
            return True
        age = (datetime.now() - entry['created']).total_seconds()
        return age > self.ttl_seconds
    
    def _update_access_time(self, key: str) -> None:
        """Update last access time."""
        self._access_times[key] = datetime.now()
    
    def _remove_entry(self, key: str) -> None:
        """Remove cache entry."""
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
        sorted_keys = sorted(
            self._access_times.keys(),
            key=lambda k: self._access_times[k]
        )
        evict_count = len(self._cache) - self.max_size + 1
        for key in sorted_keys[:evict_count]:
            self._remove_entry(key)
            logger.debug(f"Evicted cache entry: {key}")
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._weak_refs.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'ttl_seconds': self.ttl_seconds,
                'weak_refs': len(self._weak_refs)
            }


class ResourceMonitor:
    """Monitors and manages LLM resource usage."""
    
    def __init__(self):
        self.request_pools: Dict[str, RequestPool] = {}
        self.cache_managers: Dict[str, CacheManager] = {}
        self._metrics: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
    
    def get_request_pool(self, config_name: str) -> RequestPool:
        """Get or create request pool for config."""
        if config_name not in self.request_pools:
            self.request_pools[config_name] = self._create_pool(config_name)
        return self.request_pools[config_name]
    
    def _create_pool(self, config_name: str) -> RequestPool:
        """Create request pool based on config type."""
        if 'fast' in config_name.lower():
            return RequestPool(max_concurrent=10, requests_per_minute=120)
        elif 'slow' in config_name.lower():
            return RequestPool(max_concurrent=3, requests_per_minute=30)
        return RequestPool(max_concurrent=5, requests_per_minute=60)
    
    def get_cache_manager(self, config_name: str) -> CacheManager:
        """Get or create cache manager for config."""
        if config_name not in self.cache_managers:
            self.cache_managers[config_name] = CacheManager()
        return self.cache_managers[config_name]
    
    async def record_request(self, config_name: str, 
                            success: bool, duration_ms: float) -> None:
        """Record request metrics."""
        async with self._lock:
            if config_name not in self._metrics:
                self._metrics[config_name] = self._init_metrics()
            metrics = self._metrics[config_name]
            metrics['total_requests'] += 1
            if success:
                metrics['successful_requests'] += 1
            else:
                metrics['failed_requests'] += 1
            metrics['total_duration_ms'] += duration_ms
    
    def _init_metrics(self) -> Dict:
        """Initialize metrics dictionary."""
        return {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_duration_ms': 0
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get resource usage metrics."""
        async with self._lock:
            return {
                'pools': {
                    name: {
                        'max_concurrent': pool.max_concurrent,
                        'requests_per_minute': pool.requests_per_minute
                    }
                    for name, pool in self.request_pools.items()
                },
                'caches': {
                    name: await cache.get_stats()
                    for name, cache in self.cache_managers.items()
                },
                'metrics': self._metrics.copy()
            }
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        for cache in self.cache_managers.values():
            await cache.clear()
        self._metrics.clear()
        logger.info("Resource manager cleaned up")


# Global resource monitor instance
resource_monitor = ResourceMonitor()
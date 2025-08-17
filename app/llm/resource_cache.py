"""Cache management for LLM operations.

Provides LLM cache with memory limits, TTL expiration,
and LRU eviction for optimal memory usage.
"""

import asyncio
import weakref
from typing import Any, Dict, Optional
from datetime import datetime
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CacheManager:
    """Manages LLM cache with memory limits."""
    
    def __init__(self, max_size: int = 1000, 
                 ttl_seconds: int = 3600):
        """Initialize cache manager with limits."""
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
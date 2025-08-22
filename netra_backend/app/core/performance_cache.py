"""Performance cache implementation for high-speed data access.

This module provides in-memory caching with TTL and LRU eviction
for optimizing repeated data access patterns.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL and hit tracking."""
    value: Any
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)


class MemoryCache:
    """High-performance in-memory cache with TTL and LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if datetime.now() > entry.expires_at:
                self._remove_expired_entry(key)
                return None
            
            self._update_access_tracking(key, entry)
            return entry.value
    
    def _remove_expired_entry(self, key: str) -> None:
        """Remove expired entry from cache."""
        del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)
    
    def _update_access_tracking(self, key: str, entry: CacheEntry) -> None:
        """Update access tracking for cache entry."""
        entry.hit_count += 1
        entry.last_accessed = datetime.now()
        
        # Move to end of access order (most recently used)
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        if ttl is None:
            ttl = self.default_ttl
        
        async with self._lock:
            now = datetime.now()
            expires_at = now + timedelta(seconds=ttl)
            
            # If at capacity, evict LRU item
            if len(self._cache) >= self.max_size and key not in self._cache:
                await self._evict_lru()
            
            self._cache[key] = CacheEntry(
                value=value,
                created_at=now,
                expires_at=expires_at
            )
            
            self._update_access_order(key)
    
    def _update_access_order(self, key: str) -> None:
        """Update access order for cache key."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    async def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if self._access_order:
            lru_key = self._access_order.pop(0)
            if lru_key in self._cache:
                del self._cache[lru_key]
    
    async def clear_expired(self) -> int:
        """Clear all expired entries."""
        expired_keys = self._find_expired_keys()
        
        for key in expired_keys:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
        
        return len(expired_keys)
    
    def _find_expired_keys(self) -> List[str]:
        """Find all expired cache keys."""
        expired_keys = []
        now = datetime.now()
        
        for key, entry in self._cache.items():
            if now > entry.expires_at:
                expired_keys.append(key)
        
        return expired_keys
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(entry.hit_count for entry in self._cache.values())
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
            "keys": list(self._cache.keys())
        }
"""Response Cache Service

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (performance optimization)
- Business Goal: Reduce API response times and resource usage
- Value Impact: Improves user experience and reduces infrastructure costs
- Strategic Impact: Essential for high-performance API operations

Provides intelligent response caching for API endpoints.
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field

from app.core.exceptions_base import NetraException
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached response entry."""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if the cache entry is expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        """Get the age of the cache entry in seconds."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_entries: int = 0
    memory_usage_bytes: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0


class ResponseCacheManager:
    """Manages response caching with TTL and LRU eviction."""
    
    def __init__(self, max_size: int = 10000, default_ttl_seconds: int = 300):
        """Initialize the cache manager."""
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self._stats = CacheStats()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                self._stats.misses += 1
                return None
            
            if entry.is_expired:
                await self._remove_entry(key)
                self._stats.misses += 1
                return None
            
            # Update access order for LRU
            self._update_access_order(key)
            entry.hit_count += 1
            self._stats.hits += 1
            
            logger.debug(f"Cache hit for key: {key}")
            return entry.value
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set a value in the cache."""
        async with self._lock:
            ttl = ttl_seconds or self.default_ttl_seconds
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(seconds=ttl)
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=expires_at
            )
            
            # Remove existing entry if present
            if key in self._cache:
                await self._remove_entry(key)
            
            # Evict entries if at capacity
            await self._ensure_capacity()
            
            self._cache[key] = entry
            self._access_order.append(key)
            self._stats.total_entries = len(self._cache)
            
            logger.debug(f"Cache set for key: {key}, TTL: {ttl}s")
    
    async def delete(self, key: str) -> bool:
        """Delete a specific cache entry."""
        async with self._lock:
            if key in self._cache:
                await self._remove_entry(key)
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._stats = CacheStats()
            logger.info("Cache cleared")
    
    async def get_stats(self) -> CacheStats:
        """Get cache performance statistics."""
        async with self._lock:
            self._stats.total_entries = len(self._cache)
            self._stats.memory_usage_bytes = self._estimate_memory_usage()
            return self._stats
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed."""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() 
                if entry.is_expired
            ]
            
            for key in expired_keys:
                await self._remove_entry(key)
            
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            return len(expired_keys)
    
    async def get_cache_key(self, request_data: Dict[str, Any]) -> str:
        """Generate a cache key from request data."""
        # Create deterministic hash from request data
        serialized = json.dumps(request_data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def _update_access_order(self, key: str) -> None:
        """Update LRU access order."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    async def _remove_entry(self, key: str) -> None:
        """Remove an entry from cache and access order."""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)
        self._stats.total_entries = len(self._cache)
    
    async def _ensure_capacity(self) -> None:
        """Ensure cache doesn't exceed max size."""
        while len(self._cache) >= self.max_size:
            # Remove least recently used entry
            if self._access_order:
                lru_key = self._access_order[0]
                await self._remove_entry(lru_key)
                self._stats.evictions += 1
            else:
                break
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage of cache entries."""
        # Simple estimation - would need more sophisticated calculation in production
        total_size = 0
        for entry in self._cache.values():
            # Rough estimate: key + value size
            total_size += len(str(entry.key)) + len(str(entry.value))
        return total_size


class ResponseCache:
    """High-level response cache interface."""
    
    def __init__(self, cache_manager: Optional[ResponseCacheManager] = None):
        """Initialize with optional cache manager."""
        self.cache_manager = cache_manager or ResponseCacheManager()
    
    async def get_cached_response(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached response for an endpoint."""
        cache_key = await self._build_cache_key(endpoint, params)
        return await self.cache_manager.get(cache_key)
    
    async def cache_response(self, endpoint: str, params: Dict[str, Any], 
                           response: Any, ttl_seconds: Optional[int] = None) -> None:
        """Cache a response for an endpoint."""
        cache_key = await self._build_cache_key(endpoint, params)
        await self.cache_manager.set(cache_key, response, ttl_seconds)
    
    async def invalidate_endpoint(self, endpoint: str) -> int:
        """Invalidate all cached responses for an endpoint."""
        # In a more sophisticated implementation, we'd maintain endpoint indexes
        # For now, this is a simplified version
        count = 0
        async with self.cache_manager._lock:
            keys_to_remove = [
                key for key in self.cache_manager._cache.keys()
                if key.startswith(f"endpoint:{endpoint}:")
            ]
            for key in keys_to_remove:
                await self.cache_manager.delete(key)
                count += 1
        return count
    
    async def _build_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Build a cache key for endpoint and parameters."""
        cache_data = {"endpoint": endpoint, "params": params}
        param_hash = await self.cache_manager.get_cache_key(cache_data)
        return f"endpoint:{endpoint}:{param_hash}"


# Global cache instance
response_cache = ResponseCache()
"""API Gateway Cache Manager implementation."""

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    hit_count: int = 0
    size_bytes: int = 0


class CacheStrategy(ABC):
    """Abstract base class for cache strategies."""
    
    @abstractmethod
    def should_cache(self, key: str, value: Any, metadata: Dict[str, Any]) -> bool:
        """Determine if item should be cached."""
        pass
    
    @abstractmethod
    def get_ttl(self, key: str, value: Any, metadata: Dict[str, Any]) -> Optional[int]:
        """Get time-to-live for cache entry in seconds."""
        pass


class DefaultCacheStrategy(CacheStrategy):
    """Default caching strategy."""
    
    def __init__(self, default_ttl: int = 300):
        self.default_ttl = default_ttl
    
    def should_cache(self, key: str, value: Any, metadata: Dict[str, Any]) -> bool:
        """Cache everything by default."""
        return True
    
    def get_ttl(self, key: str, value: Any, metadata: Dict[str, Any]) -> Optional[int]:
        """Return default TTL."""
        return self.default_ttl


class ApiCacheManager:
    """Manages API response caching."""
    
    def __init__(self, strategy: Optional[CacheStrategy] = None, max_size: int = 1000):
        self.strategy = strategy or DefaultCacheStrategy()
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.enabled = True
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
    
    def _generate_key(self, request_path: str, params: Dict[str, Any]) -> str:
        """Generate cache key from request."""
        key_data = f"{request_path}:{sorted(params.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, request_path: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached response."""
        if not self.enabled:
            return None
        
        key = self._generate_key(request_path, params)
        entry = self.cache.get(key)
        
        if entry is None:
            self.stats['misses'] += 1
            return None
        
        # Check expiration
        if entry.expires_at and time.time() > entry.expires_at:
            del self.cache[key]
            self.stats['misses'] += 1
            return None
        
        # Update hit count and stats
        entry.hit_count += 1
        self.stats['hits'] += 1
        return entry.value
    
    def set(self, request_path: str, params: Dict[str, Any], value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Cache a response."""
        if not self.enabled:
            return
        
        metadata = metadata or {}
        key = self._generate_key(request_path, params)
        
        if not self.strategy.should_cache(key, value, metadata):
            return
        
        # Calculate expiration time
        ttl = self.strategy.get_ttl(key, value, metadata)
        expires_at = time.time() + ttl if ttl else None
        
        # Create cache entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            expires_at=expires_at,
            size_bytes=len(str(value))  # Simple size estimation
        )
        
        # Evict if necessary
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        self.cache[key] = entry
        self.stats['size'] = len(self.cache)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.cache:
            return
        
        # Find LRU entry (lowest hit_count, then oldest)
        lru_key = min(self.cache.keys(), 
                     key=lambda k: (self.cache[k].hit_count, self.cache[k].created_at))
        
        del self.cache[lru_key]
        self.stats['evictions'] += 1
    
    def invalidate(self, pattern: Optional[str] = None) -> int:
        """Invalidate cache entries matching pattern."""
        if pattern is None:
            count = len(self.cache)
            self.cache.clear()
            self.stats['size'] = 0
            return count
        
        # Simple pattern matching
        keys_to_remove = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_remove:
            del self.cache[key]
        
        self.stats['size'] = len(self.cache)
        return len(keys_to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            **self.stats,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }
    
    def disable(self) -> None:
        """Disable caching."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable caching."""
        self.enabled = True

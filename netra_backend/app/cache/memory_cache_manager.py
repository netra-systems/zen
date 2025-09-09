"""Memory Cache Manager - SSOT for In-Memory Caching

This module provides in-memory caching capabilities for the Netra platform,
enabling fast local caching for frequently accessed data.

Business Value Justification (BVJ):
- Segment: All customer segments (Free -> Enterprise)
- Business Goal: Ultra-fast data access for hot data and session information
- Value Impact: Microsecond response times for cached data
- Strategic Impact: Enables real-time user experiences and reduces latency

SSOT Compliance:
- Integrates with distributed caching strategy
- Uses standardized cache patterns and interfaces
- Provides memory-efficient storage with automatic cleanup
"""

import asyncio
import time
import threading
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
import weakref
import gc

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class MemoryCacheEntry:
    """Individual memory cache entry."""
    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    size_estimate: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()


@dataclass
class MemoryCacheStats:
    """Memory cache statistics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    total_operations: int = 0
    current_size: int = 0
    max_size: int = 0
    memory_usage_bytes: int = 0
    start_time: Optional[datetime] = None
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total_reads = self.hits + self.misses
        if total_reads == 0:
            return 0.0
        return (self.hits / total_reads) * 100.0


class MemoryCacheManager:
    """SSOT Memory Cache Manager for in-memory caching.
    
    This class provides high-performance in-memory caching with automatic
    memory management, TTL support, and LRU eviction policies.
    
    Key Features:
    - Ultra-fast in-memory caching with O(1) access
    - Configurable size limits with LRU eviction
    - TTL (time-to-live) support with automatic cleanup
    - Thread-safe operations for concurrent access
    - Memory usage tracking and optimization
    - Automatic garbage collection integration
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        max_memory_mb: int = 100,
        default_ttl: Optional[int] = None,
        cleanup_interval: int = 300  # 5 minutes
    ):
        """Initialize memory cache manager.
        
        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
            default_ttl: Default TTL in seconds (None for no expiration)
            cleanup_interval: Interval for cleanup tasks in seconds
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        
        # Thread-safe storage using OrderedDict for LRU
        self._cache: OrderedDict[str, MemoryCacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = MemoryCacheStats(
            max_size=max_size,
            start_time=datetime.now(timezone.utc)
        )
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        logger.info(
            f"MemoryCacheManager initialized: max_size={max_size}, "
            f"max_memory={max_memory_mb}MB, default_ttl={default_ttl}s"
        )
    
    async def start(self):
        """Start background cleanup tasks."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.debug("Started memory cache cleanup task")
    
    async def stop(self):
        """Stop background tasks and cleanup."""
        self._shutdown = True
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.debug("Stopped memory cache manager")
    
    def _estimate_size(self, obj: Any) -> int:
        """Estimate memory size of an object.
        
        Args:
            obj: Object to estimate size for
            
        Returns:
            Estimated size in bytes
        """
        try:
            import sys
            
            # Basic size estimation
            if isinstance(obj, (str, bytes)):
                return len(obj)
            elif isinstance(obj, (int, float, bool)):
                return sys.getsizeof(obj)
            elif isinstance(obj, (list, tuple)):
                return sum(self._estimate_size(item) for item in obj)
            elif isinstance(obj, dict):
                return sum(
                    self._estimate_size(k) + self._estimate_size(v) 
                    for k, v in obj.items()
                )
            else:
                return sys.getsizeof(obj)
        except Exception:
            # Fallback estimation
            return 1024  # 1KB default
    
    def _evict_lru(self) -> int:
        """Evict least recently used entries to free space.
        
        Returns:
            Number of entries evicted
        """
        evicted = 0
        current_time = datetime.now(timezone.utc)
        
        # First, remove expired entries
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired
        ]
        
        for key in expired_keys:
            del self._cache[key]
            evicted += 1
            self._stats.evictions += 1
        
        # If still over limits, evict LRU entries
        while (
            (len(self._cache) > self.max_size or 
             self._stats.memory_usage_bytes > self.max_memory_bytes) and
            self._cache
        ):
            # Remove oldest entry (FIFO from OrderedDict)
            key, entry = self._cache.popitem(last=False)
            self._stats.memory_usage_bytes -= entry.size_estimate
            evicted += 1
            self._stats.evictions += 1
        
        if evicted > 0:
            logger.debug(f"Evicted {evicted} entries from memory cache")
        
        return evicted
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from memory cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        with self._lock:
            self._stats.total_operations += 1
            
            entry = self._cache.get(key)
            if entry is None:
                self._stats.misses += 1
                logger.debug(f"Memory cache miss for key: {key}")
                return default
            
            # Check expiration
            if entry.is_expired:
                del self._cache[key]
                self._stats.memory_usage_bytes -= entry.size_estimate
                self._stats.misses += 1
                self._stats.evictions += 1
                logger.debug(f"Memory cache expired for key: {key}")
                return default
            
            # Update access information and move to end (most recent)
            entry.accessed_at = datetime.now(timezone.utc)
            entry.access_count += 1
            self._cache.move_to_end(key)
            
            self._stats.hits += 1
            logger.debug(f"Memory cache hit for key: {key}")
            return entry.value
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in memory cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default_ttl if None)
            
        Returns:
            True if value was set successfully
        """
        with self._lock:
            try:
                current_time = datetime.now(timezone.utc)
                effective_ttl = ttl if ttl is not None else self.default_ttl
                
                expires_at = None
                if effective_ttl is not None:
                    expires_at = current_time + timedelta(seconds=effective_ttl)
                
                # Estimate size
                size_estimate = self._estimate_size(value)
                
                # Check if we need to evict first
                if key not in self._cache:
                    # Only check limits for new entries
                    if (len(self._cache) >= self.max_size or 
                        self._stats.memory_usage_bytes + size_estimate > self.max_memory_bytes):
                        self._evict_lru()
                
                # Remove existing entry if present
                if key in self._cache:
                    old_entry = self._cache[key]
                    self._stats.memory_usage_bytes -= old_entry.size_estimate
                
                # Create new entry
                entry = MemoryCacheEntry(
                    key=key,
                    value=value,
                    created_at=current_time,
                    accessed_at=current_time,
                    expires_at=expires_at,
                    size_estimate=size_estimate
                )
                
                # Add to cache (at end for LRU)
                self._cache[key] = entry
                self._stats.memory_usage_bytes += size_estimate
                self._stats.current_size = len(self._cache)
                
                self._stats.sets += 1
                self._stats.total_operations += 1
                
                logger.debug(f"Memory cache set for key: {key} (TTL: {effective_ttl}s)")
                return True
                
            except Exception as e:
                logger.error(f"Error setting memory cache key {key}: {e}")
                return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from memory cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if key didn't exist
        """
        with self._lock:
            self._stats.total_operations += 1
            
            entry = self._cache.pop(key, None)
            if entry is None:
                return False
            
            self._stats.memory_usage_bytes -= entry.size_estimate
            self._stats.current_size = len(self._cache)
            self._stats.deletes += 1
            
            logger.debug(f"Memory cache delete for key: {key}")
            return True
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists and not expired, False otherwise
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            
            if entry.is_expired:
                # Clean up expired entry
                del self._cache[key]
                self._stats.memory_usage_bytes -= entry.size_estimate
                self._stats.evictions += 1
                return False
            
            return True
    
    async def clear(self) -> int:
        """Clear all entries from memory cache.
        
        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.memory_usage_bytes = 0
            self._stats.current_size = 0
            self._stats.deletes += count
            self._stats.total_operations += 1
            
            logger.info(f"Cleared {count} entries from memory cache")
            return count
    
    async def get_stats(self) -> MemoryCacheStats:
        """Get current memory cache statistics.
        
        Returns:
            Current cache statistics
        """
        with self._lock:
            stats_copy = MemoryCacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                sets=self._stats.sets,
                deletes=self._stats.deletes,
                evictions=self._stats.evictions,
                total_operations=self._stats.total_operations,
                current_size=len(self._cache),
                max_size=self.max_size,
                memory_usage_bytes=self._stats.memory_usage_bytes,
                start_time=self._stats.start_time
            )
            return stats_copy
    
    async def get_size_info(self) -> Dict[str, Any]:
        """Get detailed size information.
        
        Returns:
            Dictionary with cache size details
        """
        with self._lock:
            return {
                "current_entries": len(self._cache),
                "max_entries": self.max_size,
                "memory_usage_bytes": self._stats.memory_usage_bytes,
                "memory_usage_mb": round(self._stats.memory_usage_bytes / (1024 * 1024), 2),
                "max_memory_mb": round(self.max_memory_bytes / (1024 * 1024), 2),
                "utilization_percent": round(
                    (len(self._cache) / self.max_size) * 100, 2
                ) if self.max_size > 0 else 0,
                "hit_rate_percent": round(self._stats.hit_rate, 2),
                "total_operations": self._stats.total_operations
            }
    
    async def cleanup_expired(self) -> int:
        """Clean up expired entries.
        
        Returns:
            Number of expired entries removed
        """
        with self._lock:
            current_time = datetime.now(timezone.utc)
            expired_keys = []
            
            for key, entry in self._cache.items():
                if entry.is_expired:
                    expired_keys.append(key)
            
            for key in expired_keys:
                entry = self._cache.pop(key)
                self._stats.memory_usage_bytes -= entry.size_estimate
                self._stats.evictions += 1
            
            self._stats.current_size = len(self._cache)
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired memory cache entries")
            
            return len(expired_keys)
    
    async def _cleanup_loop(self):
        """Background cleanup task loop."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.cleanup_interval)
                if not self._shutdown:
                    await self.cleanup_expired()
                    # Force garbage collection periodically
                    gc.collect()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory cache cleanup loop: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on memory cache.
        
        Returns:
            Health check results
        """
        try:
            start_time = time.time()
            
            # Test basic operations
            test_key = f"health_check_{int(time.time())}"
            test_value = {"timestamp": datetime.now(timezone.utc).isoformat()}
            
            # Test set
            set_success = await self.set(test_key, test_value, ttl=60)
            if not set_success:
                return {
                    "healthy": False,
                    "error": "Failed to set test key",
                    "stats": await self.get_stats()
                }
            
            # Test get
            retrieved_value = await self.get(test_key)
            if retrieved_value != test_value:
                return {
                    "healthy": False,
                    "error": "Retrieved value doesn't match set value",
                    "stats": await self.get_stats()
                }
            
            # Test delete
            delete_success = await self.delete(test_key)
            if not delete_success:
                return {
                    "healthy": False,
                    "error": "Failed to delete test key",
                    "stats": await self.get_stats()
                }
            
            end_time = time.time()
            
            return {
                "healthy": True,
                "response_time_ms": round((end_time - start_time) * 1000, 2),
                "stats": await self.get_stats(),
                "size_info": await self.get_size_info()
            }
            
        except Exception as e:
            logger.error(f"Memory cache health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "stats": await self.get_stats()
            }


# Create default instance for SSOT access
default_memory_cache_manager = MemoryCacheManager()

# Export for direct module access
__all__ = [
    "MemoryCacheManager",
    "MemoryCacheEntry",
    "MemoryCacheStats",
    "default_memory_cache_manager"
]
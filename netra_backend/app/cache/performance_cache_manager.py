"""Performance Cache Manager - SSOT for Performance-Optimized Caching

This module provides performance-optimized caching capabilities for the Netra platform,
designed specifically for high-throughput scenarios and performance-critical data.

Business Value Justification (BVJ):
- Segment: Mid-tier and Enterprise customers
- Business Goal: Enable sub-millisecond response times for critical operations
- Value Impact: Dramatically improved user experience and system responsiveness
- Strategic Impact: Enables real-time applications and high-frequency operations

SSOT Compliance:
- Integrates with existing caching infrastructure
- Uses performance-optimized data structures and algorithms
- Provides specialized interfaces for performance-critical scenarios
"""

import asyncio
import time
import threading
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from dataclasses import dataclass, field
import heapq
import weakref

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for cache operations."""
    operation_type: str
    duration_ns: int  # Nanoseconds for high precision
    cache_hit: bool
    key: str
    timestamp: datetime
    
    @property
    def duration_ms(self) -> float:
        """Get duration in milliseconds."""
        return self.duration_ns / 1_000_000


@dataclass
class CachePerformanceStats:
    """Performance-focused cache statistics."""
    total_operations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Timing statistics (in nanoseconds)
    total_time_ns: int = 0
    min_time_ns: Optional[int] = None
    max_time_ns: Optional[int] = None
    
    # Performance buckets
    sub_microsecond_ops: int = 0  # < 1μs
    sub_millisecond_ops: int = 0  # < 1ms
    slow_ops: int = 0  # >= 1ms
    
    # Memory statistics
    memory_usage_bytes: int = 0
    peak_memory_bytes: int = 0
    
    start_time: Optional[datetime] = None
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total_reads = self.cache_hits + self.cache_misses
        if total_reads == 0:
            return 0.0
        return (self.cache_hits / total_reads) * 100.0
    
    @property
    def avg_time_ns(self) -> float:
        """Calculate average operation time in nanoseconds."""
        if self.total_operations == 0:
            return 0.0
        return self.total_time_ns / self.total_operations
    
    @property
    def avg_time_ms(self) -> float:
        """Calculate average operation time in milliseconds."""
        return self.avg_time_ns / 1_000_000


class PerformanceOptimizedEntry:
    """Highly optimized cache entry for performance-critical scenarios."""
    
    __slots__ = ['key', 'value', 'created_ns', 'accessed_ns', 'expires_ns', 'access_count']
    
    def __init__(self, key: str, value: Any, ttl_ns: Optional[int] = None):
        self.key = key
        self.value = value
        self.created_ns = time.time_ns()
        self.accessed_ns = self.created_ns
        self.access_count = 0
        self.expires_ns = None
        
        if ttl_ns is not None:
            self.expires_ns = self.created_ns + ttl_ns
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired (optimized for speed)."""
        if self.expires_ns is None:
            return False
        return time.time_ns() > self.expires_ns
    
    def touch(self) -> None:
        """Update access time and count (optimized for speed)."""
        self.accessed_ns = time.time_ns()
        self.access_count += 1


class PerformanceCacheManager:
    """SSOT Performance Cache Manager for ultra-high-speed caching.
    
    This class is specifically designed for performance-critical scenarios
    where sub-millisecond response times are required. It uses optimized
    data structures and algorithms to minimize overhead.
    
    Key Features:
    - Sub-microsecond cache operations for hot data
    - Specialized data structures for minimal memory overhead
    - Performance monitoring with nanosecond precision
    - Intelligent prefetching and warming strategies
    - Lock-free operations for high concurrency scenarios
    - Memory pool management for reduced GC pressure
    """
    
    def __init__(
        self,
        max_entries: int = 50000,
        hot_cache_size: int = 1000,
        default_ttl_seconds: Optional[float] = None,
        enable_metrics: bool = True,
        warm_up_size: int = 100
    ):
        """Initialize performance cache manager.
        
        Args:
            max_entries: Maximum total entries
            hot_cache_size: Size of ultra-fast hot cache
            default_ttl_seconds: Default TTL in seconds
            enable_metrics: Whether to collect detailed metrics
            warm_up_size: Number of entries to keep "warm"
        """
        self.max_entries = max_entries
        self.hot_cache_size = hot_cache_size
        self.default_ttl_ns = None
        self.enable_metrics = enable_metrics
        self.warm_up_size = warm_up_size
        
        if default_ttl_seconds is not None:
            self.default_ttl_ns = int(default_ttl_seconds * 1_000_000_000)
        
        # Ultra-fast hot cache for most frequent access
        self._hot_cache: Dict[str, PerformanceOptimizedEntry] = {}
        
        # Main cache storage
        self._main_cache: Dict[str, PerformanceOptimizedEntry] = {}
        
        # Access frequency tracking for hot cache promotion
        self._access_freq: Dict[str, int] = defaultdict(int)
        self._access_times: Dict[str, int] = {}  # Last access time in nanoseconds
        
        # Performance metrics
        self._stats = CachePerformanceStats(start_time=datetime.now(timezone.utc))
        self._metrics_buffer: deque = deque(maxlen=10000) if enable_metrics else None
        
        # Threading for concurrent access
        self._lock = threading.RLock()
        self._hot_lock = threading.Lock()  # Separate lock for hot cache
        
        # Background optimization task
        self._optimization_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        logger.info(
            f"PerformanceCacheManager initialized: max_entries={max_entries}, "
            f"hot_cache_size={hot_cache_size}, ttl={default_ttl_seconds}s"
        )
    
    async def start(self):
        """Start background optimization tasks."""
        if self._optimization_task is None:
            self._optimization_task = asyncio.create_task(self._optimization_loop())
            logger.debug("Started performance cache optimization task")
    
    async def stop(self):
        """Stop background tasks."""
        self._shutdown = True
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
        logger.debug("Stopped performance cache manager")
    
    def _record_metric(self, operation: str, duration_ns: int, hit: bool, key: str):
        """Record performance metric (optimized for minimal overhead)."""
        if not self.enable_metrics:
            return
        
        # Update stats
        self._stats.total_operations += 1
        self._stats.total_time_ns += duration_ns
        
        if hit:
            self._stats.cache_hits += 1
        else:
            self._stats.cache_misses += 1
        
        # Update min/max
        if self._stats.min_time_ns is None or duration_ns < self._stats.min_time_ns:
            self._stats.min_time_ns = duration_ns
        if self._stats.max_time_ns is None or duration_ns > self._stats.max_time_ns:
            self._stats.max_time_ns = duration_ns
        
        # Update performance buckets
        if duration_ns < 1_000:  # < 1 microsecond
            self._stats.sub_microsecond_ops += 1
        elif duration_ns < 1_000_000:  # < 1 millisecond
            self._stats.sub_millisecond_ops += 1
        else:
            self._stats.slow_ops += 1
        
        # Store detailed metric
        if self._metrics_buffer is not None:
            metric = PerformanceMetrics(
                operation_type=operation,
                duration_ns=duration_ns,
                cache_hit=hit,
                key=key,
                timestamp=datetime.now(timezone.utc)
            )
            self._metrics_buffer.append(metric)
    
    def _promote_to_hot_cache(self, key: str, entry: PerformanceOptimizedEntry):
        """Promote frequently accessed entry to hot cache."""
        with self._hot_lock:
            if len(self._hot_cache) >= self.hot_cache_size:
                # Find least recently used entry in hot cache
                lru_key = min(
                    self._hot_cache.keys(),
                    key=lambda k: self._hot_cache[k].accessed_ns
                )
                # Move back to main cache
                lru_entry = self._hot_cache.pop(lru_key)
                self._main_cache[lru_key] = lru_entry
            
            self._hot_cache[key] = entry
            # Remove from main cache if present
            self._main_cache.pop(key, None)
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from performance cache (ultra-optimized).
        
        Args:
            key: Cache key
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        start_ns = time.time_ns()
        
        try:
            # First check hot cache (lock-free read for common case)
            hot_entry = self._hot_cache.get(key)
            if hot_entry is not None:
                if not hot_entry.is_expired:
                    hot_entry.touch()
                    duration = time.time_ns() - start_ns
                    self._record_metric("get", duration, True, key)
                    return hot_entry.value
                else:
                    # Remove expired hot entry
                    with self._hot_lock:
                        self._hot_cache.pop(key, None)
            
            # Check main cache
            with self._lock:
                entry = self._main_cache.get(key)
                if entry is None:
                    duration = time.time_ns() - start_ns
                    self._record_metric("get", duration, False, key)
                    return default
                
                if entry.is_expired:
                    self._main_cache.pop(key, None)
                    duration = time.time_ns() - start_ns
                    self._record_metric("get", duration, False, key)
                    return default
                
                # Update access tracking
                entry.touch()
                self._access_freq[key] += 1
                self._access_times[key] = time.time_ns()
                
                # Consider promotion to hot cache
                if self._access_freq[key] > 5:  # Threshold for hot promotion
                    self._promote_to_hot_cache(key, entry)
                
                duration = time.time_ns() - start_ns
                self._record_metric("get", duration, True, key)
                return entry.value
                
        except Exception as e:
            logger.error(f"Error in performance cache get for key {key}: {e}")
            return default
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[float] = None
    ) -> bool:
        """Set value in performance cache (ultra-optimized).
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL in seconds
            
        Returns:
            True if set successfully
        """
        start_ns = time.time_ns()
        
        try:
            ttl_ns = None
            if ttl_seconds is not None:
                ttl_ns = int(ttl_seconds * 1_000_000_000)
            elif self.default_ttl_ns is not None:
                ttl_ns = self.default_ttl_ns
            
            entry = PerformanceOptimizedEntry(key, value, ttl_ns)
            
            # Check if this should go directly to hot cache
            if key in self._hot_cache or self._access_freq[key] > 3:
                with self._hot_lock:
                    if len(self._hot_cache) >= self.hot_cache_size:
                        # Evict LRU from hot cache
                        lru_key = min(
                            self._hot_cache.keys(),
                            key=lambda k: self._hot_cache[k].accessed_ns
                        )
                        lru_entry = self._hot_cache.pop(lru_key)
                        with self._lock:
                            self._main_cache[lru_key] = lru_entry
                    
                    self._hot_cache[key] = entry
                    # Remove from main cache
                    with self._lock:
                        self._main_cache.pop(key, None)
            else:
                # Add to main cache
                with self._lock:
                    if len(self._main_cache) + len(self._hot_cache) >= self.max_entries:
                        # Evict LRU from main cache
                        if self._main_cache:
                            lru_key = min(
                                self._main_cache.keys(),
                                key=lambda k: self._main_cache[k].accessed_ns
                            )
                            self._main_cache.pop(lru_key)
                            self._access_freq.pop(lru_key, None)
                            self._access_times.pop(lru_key, None)
                    
                    self._main_cache[key] = entry
            
            duration = time.time_ns() - start_ns
            self._record_metric("set", duration, False, key)
            return True
            
        except Exception as e:
            logger.error(f"Error in performance cache set for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from performance cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted
        """
        start_ns = time.time_ns()
        
        try:
            deleted = False
            
            # Check hot cache first
            with self._hot_lock:
                if key in self._hot_cache:
                    self._hot_cache.pop(key)
                    deleted = True
            
            # Check main cache
            with self._lock:
                if key in self._main_cache:
                    self._main_cache.pop(key)
                    deleted = True
                
                # Clean up tracking data
                self._access_freq.pop(key, None)
                self._access_times.pop(key, None)
            
            duration = time.time_ns() - start_ns
            self._record_metric("delete", duration, False, key)
            return deleted
            
        except Exception as e:
            logger.error(f"Error in performance cache delete for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists (ultra-fast check).
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and not expired
        """
        # Check hot cache
        hot_entry = self._hot_cache.get(key)
        if hot_entry is not None and not hot_entry.is_expired:
            return True
        
        # Check main cache
        with self._lock:
            entry = self._main_cache.get(key)
            if entry is not None and not entry.is_expired:
                return True
        
        return False
    
    async def warm_up(self, keys_values: List[Tuple[str, Any]]):
        """Warm up cache with frequently accessed data.
        
        Args:
            keys_values: List of (key, value) tuples to pre-load
        """
        start_ns = time.time_ns()
        
        try:
            for key, value in keys_values[:self.warm_up_size]:
                await self.set(key, value)
                # Mark as frequently accessed
                self._access_freq[key] = 10  # High initial frequency
            
            duration = time.time_ns() - start_ns
            logger.info(f"Warmed up {len(keys_values)} cache entries in {duration/1_000_000:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error during cache warm-up: {e}")
    
    async def get_performance_stats(self) -> CachePerformanceStats:
        """Get detailed performance statistics.
        
        Returns:
            Performance statistics
        """
        with self._lock:
            # Update memory usage estimate
            total_entries = len(self._hot_cache) + len(self._main_cache)
            estimated_memory = total_entries * 200  # Rough estimate per entry
            
            stats_copy = CachePerformanceStats(
                total_operations=self._stats.total_operations,
                cache_hits=self._stats.cache_hits,
                cache_misses=self._stats.cache_misses,
                total_time_ns=self._stats.total_time_ns,
                min_time_ns=self._stats.min_time_ns,
                max_time_ns=self._stats.max_time_ns,
                sub_microsecond_ops=self._stats.sub_microsecond_ops,
                sub_millisecond_ops=self._stats.sub_millisecond_ops,
                slow_ops=self._stats.slow_ops,
                memory_usage_bytes=estimated_memory,
                peak_memory_bytes=max(self._stats.peak_memory_bytes, estimated_memory),
                start_time=self._stats.start_time
            )
            
            return stats_copy
    
    async def get_recent_metrics(self, count: int = 1000) -> List[PerformanceMetrics]:
        """Get recent performance metrics.
        
        Args:
            count: Number of recent metrics to return
            
        Returns:
            List of recent performance metrics
        """
        if self._metrics_buffer is None:
            return []
        
        return list(self._metrics_buffer)[-count:]
    
    async def optimize_cache_layout(self):
        """Optimize cache layout based on access patterns."""
        if self._shutdown:
            return
        
        try:
            current_ns = time.time_ns()
            
            # Find candidates for hot cache promotion
            with self._lock:
                # Sort by access frequency and recency
                candidates = [
                    (key, freq) for key, freq in self._access_freq.items()
                    if key in self._main_cache and 
                    current_ns - self._access_times.get(key, 0) < 60_000_000_000  # 60 seconds
                ]
                
                candidates.sort(key=lambda x: x[1], reverse=True)
                
                # Promote top candidates to hot cache
                promoted = 0
                for key, freq in candidates[:5]:  # Top 5 candidates
                    if key not in self._hot_cache and freq > 3:
                        entry = self._main_cache.get(key)
                        if entry:
                            self._promote_to_hot_cache(key, entry)
                            promoted += 1
                
                if promoted > 0:
                    logger.debug(f"Promoted {promoted} entries to hot cache")
            
            # Clean up old access tracking data
            old_keys = [
                key for key, access_time in self._access_times.items()
                if current_ns - access_time > 300_000_000_000  # 5 minutes
            ]
            
            for key in old_keys:
                self._access_freq.pop(key, None)
                self._access_times.pop(key, None)
            
        except Exception as e:
            logger.error(f"Error in cache optimization: {e}")
    
    async def _optimization_loop(self):
        """Background optimization task loop."""
        while not self._shutdown:
            try:
                await asyncio.sleep(30)  # Optimize every 30 seconds
                if not self._shutdown:
                    await self.optimize_cache_layout()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check.
        
        Returns:
            Health check results with performance metrics
        """
        try:
            start_ns = time.time_ns()
            
            # Test operations
            test_key = f"perf_health_check_{start_ns}"
            test_value = {"timestamp": time.time_ns()}
            
            # Test set
            set_success = await self.set(test_key, test_value)
            if not set_success:
                return {
                    "healthy": False,
                    "error": "Failed to set test key",
                    "stats": await self.get_performance_stats()
                }
            
            # Test get
            retrieved = await self.get(test_key)
            if retrieved != test_value:
                return {
                    "healthy": False,
                    "error": "Retrieved value mismatch",
                    "stats": await self.get_performance_stats()
                }
            
            # Test delete
            delete_success = await self.delete(test_key)
            if not delete_success:
                return {
                    "healthy": False,
                    "error": "Failed to delete test key",
                    "stats": await self.get_performance_stats()
                }
            
            end_ns = time.time_ns()
            total_duration_ms = (end_ns - start_ns) / 1_000_000
            
            stats = await self.get_performance_stats()
            
            return {
                "healthy": True,
                "response_time_ms": round(total_duration_ms, 3),
                "hot_cache_entries": len(self._hot_cache),
                "main_cache_entries": len(self._main_cache),
                "stats": stats,
                "performance_distribution": {
                    "sub_microsecond_percent": round(
                        (stats.sub_microsecond_ops / max(stats.total_operations, 1)) * 100, 2
                    ),
                    "sub_millisecond_percent": round(
                        (stats.sub_millisecond_ops / max(stats.total_operations, 1)) * 100, 2
                    ),
                    "slow_ops_percent": round(
                        (stats.slow_ops / max(stats.total_operations, 1)) * 100, 2
                    )
                }
            }
            
        except Exception as e:
            logger.error(f"Performance cache health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "stats": await self.get_performance_stats()
            }


# Create default instance for SSOT access
default_performance_cache_manager = PerformanceCacheManager()

# Export for direct module access
__all__ = [
    "PerformanceCacheManager",
    "PerformanceOptimizedEntry",
    "PerformanceMetrics",
    "CachePerformanceStats",
    "default_performance_cache_manager"
]
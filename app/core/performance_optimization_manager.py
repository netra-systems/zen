"""Performance optimization manager for comprehensive system optimization.

This module provides centralized performance optimization capabilities including:
- Database query optimization and caching
- Connection pool monitoring and tuning
- Memory usage optimization
- Async operation improvements
- WebSocket message batching
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
import weakref
import hashlib
import json

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL and hit tracking."""
    value: Any
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)


@dataclass
class QueryMetrics:
    """Database query performance metrics."""
    query_hash: str
    execution_count: int = 0
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    max_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    cache_hits: int = 0
    cache_misses: int = 0


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
                # Expired entry, remove it
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return None
            
            # Update access tracking
            entry.hit_count += 1
            entry.last_accessed = datetime.now()
            
            # Move to end of access order (most recently used)
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            return entry.value
    
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
            
            # Update access order
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
        expired_keys = []
        now = datetime.now()
        
        for key, entry in self._cache.items():
            if now > entry.expires_at:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(entry.hit_count for entry in self._cache.values())
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
            "keys": list(self._cache.keys())
        }


class QueryOptimizer:
    """Database query optimization and caching."""
    
    def __init__(self, cache_size: int = 500, cache_ttl: int = 300):
        self.cache = MemoryCache(max_size=cache_size, default_ttl=cache_ttl)
        self.query_metrics: Dict[str, QueryMetrics] = {}
        self._slow_query_threshold = 1.0  # seconds
    
    def _get_query_hash(self, query: str, params: Optional[Dict] = None) -> str:
        """Generate hash for query caching."""
        query_str = query.strip().lower()
        if params:
            param_str = json.dumps(params, sort_keys=True)
            combined = f"{query_str}|{param_str}"
        else:
            combined = query_str
        return hashlib.md5(combined.encode()).hexdigest()
    
    async def execute_with_cache(self, query: str, params: Optional[Dict], 
                                executor: Callable) -> Any:
        """Execute query with caching and metrics tracking."""
        query_hash = self._get_query_hash(query, params)
        
        # Check cache first for read queries
        if self._is_read_query(query):
            cached_result = await self.cache.get(query_hash)
            if cached_result is not None:
                self._update_cache_hit_metrics(query_hash)
                return cached_result
        
        # Execute query with timing
        start_time = time.time()
        try:
            result = await executor()
            execution_time = time.time() - start_time
            
            # Update metrics
            self._update_query_metrics(query_hash, execution_time)
            
            # Cache read query results
            if self._is_read_query(query) and result is not None:
                cache_ttl = self._determine_cache_ttl(query)
                await self.cache.set(query_hash, result, ttl=cache_ttl)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_query_metrics(query_hash, execution_time)
            logger.error(f"Query execution failed after {execution_time:.2f}s: {e}")
            raise
    
    def _is_read_query(self, query: str) -> bool:
        """Check if query is a read operation."""
        query_lower = query.strip().lower()
        return query_lower.startswith(('select', 'show', 'describe', 'explain'))
    
    def _determine_cache_ttl(self, query: str) -> int:
        """Determine appropriate cache TTL based on query type."""
        query_lower = query.strip().lower()
        
        if 'user' in query_lower or 'session' in query_lower:
            return 60  # User data: 1 minute
        elif 'config' in query_lower or 'setting' in query_lower:
            return 600  # Config data: 10 minutes
        elif 'audit' in query_lower or 'log' in query_lower:
            return 30   # Audit data: 30 seconds
        else:
            return 300  # Default: 5 minutes
    
    def _update_query_metrics(self, query_hash: str, execution_time: float):
        """Update query execution metrics."""
        if query_hash not in self.query_metrics:
            self.query_metrics[query_hash] = QueryMetrics(query_hash=query_hash)
        
        metrics = self.query_metrics[query_hash]
        metrics.execution_count += 1
        metrics.total_execution_time += execution_time
        metrics.avg_execution_time = metrics.total_execution_time / metrics.execution_count
        metrics.max_execution_time = max(metrics.max_execution_time, execution_time)
        metrics.min_execution_time = min(metrics.min_execution_time, execution_time)
        
        if execution_time > self._slow_query_threshold:
            logger.warning(f"Slow query detected: {execution_time:.2f}s (hash: {query_hash})")
    
    def _update_cache_hit_metrics(self, query_hash: str):
        """Update cache hit metrics."""
        if query_hash not in self.query_metrics:
            self.query_metrics[query_hash] = QueryMetrics(query_hash=query_hash)
        self.query_metrics[query_hash].cache_hits += 1
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance analysis report."""
        slow_queries = [
            m for m in self.query_metrics.values() 
            if m.avg_execution_time > self._slow_query_threshold
        ]
        
        cache_stats = self.cache.get_stats()
        
        return {
            "total_queries": len(self.query_metrics),
            "slow_queries": len(slow_queries),
            "cache_stats": cache_stats,
            "top_slow_queries": sorted(
                slow_queries, 
                key=lambda x: x.avg_execution_time, 
                reverse=True
            )[:10]
        }


class BatchProcessor:
    """Batch processor for efficient bulk operations."""
    
    def __init__(self, max_batch_size: int = 100, flush_interval: float = 1.0):
        self.max_batch_size = max_batch_size
        self.flush_interval = flush_interval
        self._batches: Dict[str, List[Any]] = {}
        self._timers: Dict[str, asyncio.Handle] = {}
        self._processors: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
    
    async def add_to_batch(self, batch_key: str, item: Any, 
                          processor: Callable[[List[Any]], Any]) -> None:
        """Add item to batch for processing."""
        async with self._lock:
            if batch_key not in self._batches:
                self._batches[batch_key] = []
                self._processors[batch_key] = processor
            
            self._batches[batch_key].append(item)
            
            # Cancel existing timer if any
            if batch_key in self._timers:
                self._timers[batch_key].cancel()
            
            # Check if batch is full
            if len(self._batches[batch_key]) >= self.max_batch_size:
                await self._flush_batch(batch_key)
            else:
                # Set timer to flush after interval
                loop = asyncio.get_event_loop()
                self._timers[batch_key] = loop.call_later(
                    self.flush_interval,
                    lambda: asyncio.create_task(self._flush_batch(batch_key))
                )
    
    async def _flush_batch(self, batch_key: str) -> None:
        """Flush a specific batch."""
        async with self._lock:
            if batch_key not in self._batches or not self._batches[batch_key]:
                return
            
            batch = self._batches[batch_key].copy()
            processor = self._processors[batch_key]
            
            # Clear batch
            self._batches[batch_key] = []
            
            # Cancel timer
            if batch_key in self._timers:
                self._timers[batch_key].cancel()
                del self._timers[batch_key]
        
        # Process batch outside of lock
        try:
            await processor(batch)
            logger.debug(f"Processed batch {batch_key} with {len(batch)} items")
        except Exception as e:
            logger.error(f"Error processing batch {batch_key}: {e}")
    
    async def flush_all(self) -> None:
        """Flush all pending batches."""
        batch_keys = list(self._batches.keys())
        for batch_key in batch_keys:
            await self._flush_batch(batch_key)


class PerformanceOptimizationManager:
    """Central performance optimization manager."""
    
    def __init__(self):
        self.query_optimizer = QueryOptimizer()
        self.batch_processor = BatchProcessor()
        self.connection_pool_monitor = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize performance optimization components."""
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("Performance optimization manager initialized")
    
    async def shutdown(self) -> None:
        """Shutdown performance optimization components."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        await self.batch_processor.flush_all()
        logger.info("Performance optimization manager shut down")
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of expired cache entries."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                expired_count = await self.query_optimizer.cache.clear_expired()
                if expired_count > 0:
                    logger.debug(f"Cleaned up {expired_count} expired cache entries")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error during periodic cleanup: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        return {
            "query_optimizer": self.query_optimizer.get_performance_report(),
            "cache_stats": self.query_optimizer.cache.get_stats(),
            "batch_processor_stats": {
                "active_batches": len(self.batch_processor._batches)
            }
        }


# Global instance
performance_manager = PerformanceOptimizationManager()
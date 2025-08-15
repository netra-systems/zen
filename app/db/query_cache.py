"""Database Query Caching System

Provides intelligent query result caching with TTL, invalidation,
and performance optimization.
"""

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import central_logger
from app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)


class CacheStrategy(Enum):
    """Cache strategy types."""
    LRU = "lru"  # Least Recently Used
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptive based on query patterns


@dataclass
class QueryCacheConfig:
    """Configuration for query caching."""
    enabled: bool = True
    default_ttl: int = 300  # 5 minutes
    max_cache_size: int = 1000
    strategy: CacheStrategy = CacheStrategy.ADAPTIVE
    cache_prefix: str = "db_query_cache:"
    metrics_enabled: bool = True
    
    # Adaptive caching thresholds
    frequent_query_threshold: int = 5  # Queries executed 5+ times
    frequent_query_ttl_multiplier: float = 2.0
    slow_query_threshold: float = 1.0  # Queries taking 1+ seconds
    slow_query_ttl_multiplier: float = 3.0


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = 0.0
    query_duration: float = 0.0
    tags: Set[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = set()
        if self.last_accessed == 0.0:
            self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return time.time() > self.expires_at
    
    def access(self) -> None:
        """Mark entry as accessed."""
        self.access_count += 1
        self.last_accessed = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'key': self.key,
            'value': self.value,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed,
            'query_duration': self.query_duration,
            'tags': list(self.tags)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create from dictionary."""
        return cls(
            key=data['key'],
            value=data['value'],
            created_at=data['created_at'],
            expires_at=data['expires_at'],
            access_count=data['access_count'],
            last_accessed=data['last_accessed'],
            query_duration=data['query_duration'],
            tags=set(data.get('tags', []))
        )


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_queries: int = 0
    total_cache_time: float = 0.0
    total_query_time: float = 0.0
    cache_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_queries == 0:
            return 0.0
        return self.hits / self.total_queries
    
    @property
    def avg_cache_time(self) -> float:
        """Average time to retrieve from cache."""
        if self.hits == 0:
            return 0.0
        return self.total_cache_time / self.hits
    
    @property
    def avg_query_time(self) -> float:
        """Average time for uncached queries."""
        if self.misses == 0:
            return 0.0
        return self.total_query_time / self.misses
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class QueryCache:
    """Intelligent database query cache."""
    
    def __init__(self, config: Optional[QueryCacheConfig] = None):
        """Initialize query cache."""
        self.config = config or QueryCacheConfig()
        self.redis = redis_manager
        self.metrics = CacheMetrics()
        self.query_patterns: Dict[str, int] = {}  # Track query frequencies
        self.query_durations: Dict[str, List[float]] = {}  # Track query performance
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self) -> None:
        """Start background tasks."""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())
        
        if self.config.metrics_enabled:
            self._metrics_task = asyncio.create_task(self._metrics_worker())
        
        logger.info("Query cache started")
    
    async def stop(self) -> None:
        """Stop background tasks."""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Query cache stopped")
    
    def _generate_cache_key(self, query: str, params: Optional[Dict] = None) -> str:
        """Generate cache key for query."""
        key_data = {
            'query': query.strip(),
            'params': params or {}
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        
        return f"{self.config.cache_prefix}{key_hash[:32]}"
    
    def _get_query_pattern(self, query: str) -> str:
        """Extract query pattern for frequency tracking."""
        # Normalize query for pattern matching
        pattern = query.strip().upper()
        
        # Remove parameter placeholders
        import re
        pattern = re.sub(r'\$\d+', '?', pattern)
        pattern = re.sub(r':\w+', '?', pattern)
        pattern = re.sub(r"'[^']*'", "'?'", pattern)
        pattern = re.sub(r'"[^"]*"', '"?"', pattern)
        pattern = re.sub(r'\d+', '?', pattern)
        
        return pattern
    
    def _calculate_ttl(self, query: str, duration: float) -> int:
        """Calculate adaptive TTL based on query characteristics."""
        if self.config.strategy != CacheStrategy.ADAPTIVE:
            return self.config.default_ttl
        
        base_ttl = self.config.default_ttl
        pattern = self._get_query_pattern(query)
        
        # Increase TTL for frequently accessed queries
        frequency = self.query_patterns.get(pattern, 0)
        if frequency >= self.config.frequent_query_threshold:
            base_ttl = int(base_ttl * self.config.frequent_query_ttl_multiplier)
        
        # Increase TTL for slow queries
        if duration >= self.config.slow_query_threshold:
            base_ttl = int(base_ttl * self.config.slow_query_ttl_multiplier)
        
        # Decrease TTL for time-sensitive queries
        time_sensitive_keywords = ['now()', 'current_timestamp', 'today']
        if any(keyword in query.lower() for keyword in time_sensitive_keywords):
            base_ttl = min(base_ttl, 60)  # Max 1 minute for time-sensitive
        
        return max(base_ttl, 30)  # Minimum 30 seconds
    
    def _should_cache_query(self, query: str, result: Any) -> bool:
        """Determine if query result should be cached."""
        if not self.config.enabled:
            return False
        
        query_lower = query.lower().strip()
        
        # Don't cache certain query types
        non_cacheable = [
            'insert', 'update', 'delete', 'drop', 'create', 'alter',
            'truncate', 'grant', 'revoke', 'begin', 'commit', 'rollback'
        ]
        
        if any(keyword in query_lower for keyword in non_cacheable):
            return False
        
        # Don't cache empty results
        if result is None:
            return False
        
        if isinstance(result, (list, tuple)) and len(result) == 0:
            return False
        
        # Don't cache very large results
        try:
            result_size = len(str(result))
            if result_size > 1_000_000:  # 1MB threshold
                return False
        except:
            pass
        
        return True
    
    async def get_cached_result(
        self,
        query: str,
        params: Optional[Dict] = None
    ) -> Optional[Any]:
        """Get cached query result."""
        if not self.config.enabled:
            return None
        
        start_time = time.time()
        cache_key = self._generate_cache_key(query, params)
        
        try:
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                try:
                    entry_data = json.loads(cached_data)
                    entry = CacheEntry.from_dict(entry_data)
                    
                    if not entry.is_expired():
                        entry.access()
                        
                        # Update cache with new access data
                        await self.redis.set(
                            cache_key,
                            json.dumps(entry.to_dict()),
                            ex=int(entry.expires_at - time.time())
                        )
                        
                        # Update metrics
                        self.metrics.hits += 1
                        self.metrics.total_cache_time += time.time() - start_time
                        
                        logger.debug(f"Cache hit for query pattern: {self._get_query_pattern(query)}")
                        return entry.value
                    else:
                        # Remove expired entry
                        await self.redis.delete(cache_key)
                        self.metrics.cache_size = max(0, self.metrics.cache_size - 1)
                
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.warning(f"Failed to deserialize cache entry: {e}")
                    await self.redis.delete(cache_key)
            
            self.metrics.misses += 1
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            self.metrics.misses += 1
            return None
    
    async def cache_result(
        self,
        query: str,
        result: Any,
        params: Optional[Dict] = None,
        duration: Optional[float] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Cache query result."""
        if not self._should_cache_query(query, result):
            return False
        
        try:
            cache_key = self._generate_cache_key(query, params)
            query_duration = duration or 0.0
            
            # Update query patterns and performance tracking
            pattern = self._get_query_pattern(query)
            self.query_patterns[pattern] = self.query_patterns.get(pattern, 0) + 1
            
            if pattern not in self.query_durations:
                self.query_durations[pattern] = []
            self.query_durations[pattern].append(query_duration)
            
            # Keep only recent durations
            if len(self.query_durations[pattern]) > 10:
                self.query_durations[pattern] = self.query_durations[pattern][-10:]
            
            # Calculate TTL
            ttl = self._calculate_ttl(query, query_duration)
            
            # Create cache entry
            now = time.time()
            entry = CacheEntry(
                key=cache_key,
                value=result,
                created_at=now,
                expires_at=now + ttl,
                query_duration=query_duration,
                tags=tags or set()
            )
            
            # Store in cache
            await self.redis.set(
                cache_key,
                json.dumps(entry.to_dict()),
                ex=ttl
            )
            
            # Update tag associations
            if tags:
                for tag in tags:
                    tag_key = f"{self.config.cache_prefix}tag:{tag}"
                    await self.redis.sadd(tag_key, cache_key)
                    await self.redis.expire(tag_key, ttl + 60)  # Slight buffer
            
            self.metrics.cache_size += 1
            
            # Trigger eviction if cache is too large
            if self.metrics.cache_size > self.config.max_cache_size:
                await self._trigger_eviction()
            
            logger.debug(f"Cached query result with TTL {ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Error caching query result: {e}")
            return False
    
    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cached entries with specific tag."""
        try:
            tag_key = f"{self.config.cache_prefix}tag:{tag}"
            cache_keys = await self.redis.smembers(tag_key)
            
            if cache_keys:
                await self.redis.delete(*cache_keys)
                await self.redis.delete(tag_key)
                
                self.metrics.cache_size = max(0, self.metrics.cache_size - len(cache_keys))
                
                logger.info(f"Invalidated {len(cache_keys)} entries with tag: {tag}")
                return len(cache_keys)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidating cache by tag {tag}: {e}")
            return 0
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cached entries matching pattern."""
        try:
            cache_keys = await self.redis.keys(f"{self.config.cache_prefix}*{pattern}*")
            
            if cache_keys:
                await self.redis.delete(*cache_keys)
                self.metrics.cache_size = max(0, self.metrics.cache_size - len(cache_keys))
                
                logger.info(f"Invalidated {len(cache_keys)} entries matching pattern: {pattern}")
                return len(cache_keys)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidating cache by pattern {pattern}: {e}")
            return 0
    
    async def clear_all(self) -> int:
        """Clear all cached entries."""
        try:
            cache_keys = await self.redis.keys(f"{self.config.cache_prefix}*")
            
            if cache_keys:
                await self.redis.delete(*cache_keys)
                cleared_count = len(cache_keys)
                self.metrics.cache_size = 0
                
                logger.info(f"Cleared {cleared_count} cached entries")
                return cleared_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0
    
    async def _trigger_eviction(self) -> None:
        """Trigger cache eviction based on strategy."""
        try:
            if self.config.strategy == CacheStrategy.LRU:
                await self._evict_lru()
            elif self.config.strategy == CacheStrategy.TTL:
                await self._evict_expired()
            elif self.config.strategy == CacheStrategy.ADAPTIVE:
                await self._evict_adaptive()
                
        except Exception as e:
            logger.error(f"Error during cache eviction: {e}")
    
    async def _evict_lru(self) -> None:
        """Evict least recently used entries."""
        # This is simplified - in production you'd want more sophisticated LRU
        evict_count = self.config.max_cache_size // 10  # Evict 10%
        
        cache_keys = await self.redis.keys(f"{self.config.cache_prefix}*")
        
        if len(cache_keys) > evict_count:
            keys_to_evict = cache_keys[:evict_count]
            await self.redis.delete(*keys_to_evict)
            
            self.metrics.evictions += len(keys_to_evict)
            self.metrics.cache_size -= len(keys_to_evict)
    
    async def _evict_expired(self) -> None:
        """Evict expired entries."""
        # Redis handles TTL automatically, but we can clean up our metrics
        actual_size = len(await self.redis.keys(f"{self.config.cache_prefix}*"))
        evicted = self.metrics.cache_size - actual_size
        
        if evicted > 0:
            self.metrics.evictions += evicted
            self.metrics.cache_size = actual_size
    
    async def _evict_adaptive(self) -> None:
        """Evict entries using adaptive strategy."""
        # Combine LRU and TTL strategies
        await self._evict_expired()
        
        if self.metrics.cache_size > self.config.max_cache_size:
            await self._evict_lru()
    
    async def _cleanup_worker(self) -> None:
        """Background worker for cache cleanup."""
        while self._running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await self._evict_expired()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup worker error: {e}")
    
    async def _metrics_worker(self) -> None:
        """Background worker for metrics collection."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Every minute
                
                # Update cache size metric
                actual_size = len(await self.redis.keys(f"{self.config.cache_prefix}*"))
                self.metrics.cache_size = actual_size
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache metrics worker error: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        metrics_dict = self.metrics.to_dict()
        
        # Add query pattern statistics
        metrics_dict['top_query_patterns'] = sorted(
            self.query_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Add performance statistics
        avg_durations = {}
        for pattern, durations in self.query_durations.items():
            if durations:
                avg_durations[pattern] = sum(durations) / len(durations)
        
        metrics_dict['avg_query_durations'] = sorted(
            avg_durations.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return metrics_dict


# Global query cache instance
query_cache = QueryCache()


async def cached_query(
    session: AsyncSession,
    query: str,
    params: Optional[Dict] = None,
    cache_tags: Optional[Set[str]] = None,
    force_refresh: bool = False
) -> Any:
    """Execute query with caching."""
    if not force_refresh:
        cached_result = await query_cache.get_cached_result(query, params)
        if cached_result is not None:
            return cached_result
    
    # Execute query
    start_time = time.time()
    
    try:
        if params:
            result = await session.execute(text(query), params)
        else:
            result = await session.execute(text(query))
        
        # Fetch results
        if result.returns_rows:
            rows = result.fetchall()
            result_data = [dict(row._mapping) for row in rows]
        else:
            result_data = result.rowcount
        
        duration = time.time() - start_time
        
        # Cache the result
        await query_cache.cache_result(
            query=query,
            result=result_data,
            params=params,
            duration=duration,
            tags=cache_tags
        )
        
        query_cache.metrics.total_queries += 1
        query_cache.metrics.total_query_time += duration
        
        return result_data
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise
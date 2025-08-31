"""Redis Caching Service for Analytics Service.

Provides high-level caching operations for:
- User session cache (TTL: 3600s)
- Real-time metrics cache (TTL: 86400s)  
- Hot prompts cache (TTL: 1800s)
- Cache invalidation methods
- Get/Set operations with automatic TTL management

This module follows the isolation pattern - no imports from other services.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
from enum import Enum

from analytics_core.database.redis_manager import get_redis_manager, RedisConnectionError

logger = logging.getLogger(__name__)


class CacheType(Enum):
    """Cache types with predefined TTL values."""
    USER_SESSION = "user_session"  # 3600 seconds (1 hour)
    REAL_TIME_METRICS = "real_time_metrics"  # 86400 seconds (24 hours)
    HOT_PROMPTS = "hot_prompts"  # 1800 seconds (30 minutes)


class CacheKeyPrefix:
    """Redis key prefixes for different cache types."""
    USER_SESSION = "analytics:session"
    REAL_TIME_METRICS = "analytics:metrics"
    HOT_PROMPTS = "analytics:prompts"


class RedisCacheService:
    """
    Redis-based caching service for Analytics Service.
    
    Features:
    - Type-specific caching with automatic TTL management
    - JSON serialization/deserialization
    - Bulk operations for performance
    - Cache invalidation patterns
    - Metrics and monitoring support
    """
    
    # TTL values in seconds
    TTL_VALUES = {
        CacheType.USER_SESSION: 3600,        # 1 hour
        CacheType.REAL_TIME_METRICS: 86400,  # 24 hours  
        CacheType.HOT_PROMPTS: 1800,         # 30 minutes
    }
    
    def __init__(self, redis_manager=None):
        """
        Initialize Redis cache service.
        
        Args:
            redis_manager: Optional Redis manager instance. If None, uses global manager.
        """
        self.redis_manager = redis_manager or get_redis_manager()
        
    async def set(
        self,
        cache_type: CacheType,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Set a value in the cache with automatic TTL.
        
        Args:
            cache_type: Type of cache (determines TTL and key prefix)
            key: Cache key (without prefix)
            value: Value to cache (will be JSON serialized)
            ttl: Override default TTL in seconds
            user_id: Optional user ID for user-specific caching
            
        Returns:
            True if successful, False otherwise
        """
        try:
            full_key = self._build_key(cache_type, key, user_id)
            cache_ttl = ttl or self.TTL_VALUES[cache_type]
            
            # Serialize value to JSON
            serialized_value = json.dumps(value, default=str)
            
            async with self.redis_manager.get_connection() as redis_conn:
                await redis_conn.setex(full_key, cache_ttl, serialized_value)
                
            logger.debug(
                f"Cached {cache_type.value}: {full_key} "
                f"(TTL: {cache_ttl}s, Size: {len(serialized_value)} bytes)"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache {cache_type.value}:{key}: {e}")
            return False
    
    async def get(
        self,
        cache_type: CacheType,
        key: str,
        user_id: Optional[str] = None,
        default: Any = None,
    ) -> Any:
        """
        Get a value from the cache.
        
        Args:
            cache_type: Type of cache
            key: Cache key (without prefix)
            user_id: Optional user ID for user-specific caching
            default: Default value if key not found
            
        Returns:
            Cached value (JSON deserialized) or default
        """
        try:
            full_key = self._build_key(cache_type, key, user_id)
            
            async with self.redis_manager.get_connection() as redis_conn:
                cached_value = await redis_conn.get(full_key)
                
            if cached_value is None:
                logger.debug(f"Cache miss: {full_key}")
                return default
                
            # Deserialize from JSON
            deserialized_value = json.loads(cached_value)
            logger.debug(f"Cache hit: {full_key}")
            return deserialized_value
            
        except Exception as e:
            logger.error(f"Failed to get cache {cache_type.value}:{key}: {e}")
            return default
    
    async def exists(
        self,
        cache_type: CacheType,
        key: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            cache_type: Type of cache
            key: Cache key (without prefix)
            user_id: Optional user ID for user-specific caching
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            full_key = self._build_key(cache_type, key, user_id)
            
            async with self.redis_manager.get_connection() as redis_conn:
                exists = await redis_conn.exists(full_key)
                
            return bool(exists)
            
        except Exception as e:
            logger.error(f"Failed to check cache existence {cache_type.value}:{key}: {e}")
            return False
    
    async def delete(
        self,
        cache_type: CacheType,
        key: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Delete a key from the cache.
        
        Args:
            cache_type: Type of cache
            key: Cache key (without prefix)
            user_id: Optional user ID for user-specific caching
            
        Returns:
            True if key was deleted, False otherwise
        """
        try:
            full_key = self._build_key(cache_type, key, user_id)
            
            async with self.redis_manager.get_connection() as redis_conn:
                deleted_count = await redis_conn.delete(full_key)
                
            success = deleted_count > 0
            if success:
                logger.debug(f"Cache deleted: {full_key}")
            else:
                logger.debug(f"Cache key not found for deletion: {full_key}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete cache {cache_type.value}:{key}: {e}")
            return False
    
    async def get_ttl(
        self,
        cache_type: CacheType,
        key: str,
        user_id: Optional[str] = None,
    ) -> Optional[int]:
        """
        Get the TTL (time to live) for a cache key.
        
        Args:
            cache_type: Type of cache
            key: Cache key (without prefix)
            user_id: Optional user ID for user-specific caching
            
        Returns:
            TTL in seconds, or None if key doesn't exist
        """
        try:
            full_key = self._build_key(cache_type, key, user_id)
            
            async with self.redis_manager.get_connection() as redis_conn:
                ttl = await redis_conn.ttl(full_key)
                
            # Redis returns -2 for non-existent keys, -1 for keys without expiry
            if ttl == -2:
                return None  # Key doesn't exist
            elif ttl == -1:
                return -1    # Key exists but has no expiry
            else:
                return ttl   # TTL in seconds
                
        except Exception as e:
            logger.error(f"Failed to get TTL for {cache_type.value}:{key}: {e}")
            return None
    
    async def invalidate_pattern(
        self,
        cache_type: CacheType,
        pattern: str,
        user_id: Optional[str] = None,
    ) -> int:
        """
        Invalidate cache keys matching a pattern.
        
        Args:
            cache_type: Type of cache
            pattern: Key pattern (supports Redis SCAN pattern matching)
            user_id: Optional user ID for user-specific invalidation
            
        Returns:
            Number of keys deleted
        """
        try:
            full_pattern = self._build_key(cache_type, pattern, user_id)
            
            async with self.redis_manager.get_connection() as redis_conn:
                # Use SCAN to find matching keys (memory-efficient for large datasets)
                keys_to_delete = []
                async for key in redis_conn.scan_iter(match=full_pattern):
                    keys_to_delete.append(key)
                
                # Delete matching keys in batches
                deleted_count = 0
                if keys_to_delete:
                    deleted_count = await redis_conn.delete(*keys_to_delete)
                    
            logger.info(
                f"Invalidated {deleted_count} keys matching pattern: {full_pattern}"
            )
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to invalidate pattern {cache_type.value}:{pattern}: {e}")
            return 0
    
    async def invalidate_user_cache(self, user_id: str) -> Dict[str, int]:
        """
        Invalidate all cache entries for a specific user.
        
        Args:
            user_id: User ID to invalidate cache for
            
        Returns:
            Dictionary with cache type as key and deleted count as value
        """
        results = {}
        
        for cache_type in CacheType:
            try:
                deleted_count = await self.invalidate_pattern(
                    cache_type, "*", user_id=user_id
                )
                results[cache_type.value] = deleted_count
                
            except Exception as e:
                logger.error(f"Failed to invalidate user cache {cache_type.value} for user {user_id}: {e}")
                results[cache_type.value] = 0
        
        total_deleted = sum(results.values())
        logger.info(f"Invalidated {total_deleted} cache entries for user {user_id}")
        return results
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            stats = {}
            
            async with self.redis_manager.get_connection() as redis_conn:
                # Get key counts for each cache type
                for cache_type in CacheType:
                    prefix = self._get_prefix(cache_type)
                    pattern = f"{prefix}:*"
                    
                    key_count = 0
                    async for _ in redis_conn.scan_iter(match=pattern):
                        key_count += 1
                    
                    stats[f"{cache_type.value}_keys"] = key_count
                
                # Get Redis info
                redis_info = await self.redis_manager.get_info()
                stats.update({
                    "redis_memory_used": redis_info.get("used_memory_human"),
                    "redis_connected_clients": redis_info.get("connected_clients"),
                    "redis_keyspace_hits": redis_info.get("keyspace_hits"),
                    "redis_keyspace_misses": redis_info.get("keyspace_misses"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}
    
    def _build_key(
        self,
        cache_type: CacheType,
        key: str,
        user_id: Optional[str] = None,
    ) -> str:
        """Build the full Redis key with appropriate prefix."""
        prefix = self._get_prefix(cache_type)
        
        if user_id:
            return f"{prefix}:user:{user_id}:{key}"
        else:
            return f"{prefix}:{key}"
    
    def _get_prefix(self, cache_type: CacheType) -> str:
        """Get the Redis key prefix for a cache type."""
        prefix_mapping = {
            CacheType.USER_SESSION: CacheKeyPrefix.USER_SESSION,
            CacheType.REAL_TIME_METRICS: CacheKeyPrefix.REAL_TIME_METRICS,
            CacheType.HOT_PROMPTS: CacheKeyPrefix.HOT_PROMPTS,
        }
        return prefix_mapping[cache_type]


# Convenience functions for common cache operations

async def cache_user_session(
    user_id: str,
    session_data: Dict[str, Any],
    ttl: Optional[int] = None,
) -> bool:
    """Cache user session data."""
    service = RedisCacheService()
    return await service.set(
        CacheType.USER_SESSION,
        "session_data",
        session_data,
        ttl=ttl,
        user_id=user_id,
    )


async def get_user_session(user_id: str) -> Optional[Dict[str, Any]]:
    """Get cached user session data."""
    service = RedisCacheService()
    return await service.get(
        CacheType.USER_SESSION,
        "session_data",
        user_id=user_id,
    )


async def cache_real_time_metrics(
    metric_key: str,
    metrics_data: Dict[str, Any],
    ttl: Optional[int] = None,
) -> bool:
    """Cache real-time metrics data."""
    service = RedisCacheService()
    return await service.set(
        CacheType.REAL_TIME_METRICS,
        metric_key,
        metrics_data,
        ttl=ttl,
    )


async def get_real_time_metrics(metric_key: str) -> Optional[Dict[str, Any]]:
    """Get cached real-time metrics data."""
    service = RedisCacheService()
    return await service.get(
        CacheType.REAL_TIME_METRICS,
        metric_key,
    )


async def cache_hot_prompt(
    prompt_id: str,
    prompt_data: Dict[str, Any],
    ttl: Optional[int] = None,
) -> bool:
    """Cache hot prompt data."""
    service = RedisCacheService()
    return await service.set(
        CacheType.HOT_PROMPTS,
        prompt_id,
        prompt_data,
        ttl=ttl,
    )


async def get_hot_prompt(prompt_id: str) -> Optional[Dict[str, Any]]:
    """Get cached hot prompt data."""
    service = RedisCacheService()
    return await service.get(
        CacheType.HOT_PROMPTS,
        prompt_id,
    )
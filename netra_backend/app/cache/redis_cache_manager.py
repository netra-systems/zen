"""Redis Cache Manager - SSOT Compatibility Layer

DEPRECATED: Use netra_backend.app.redis_manager.redis_manager directly

This module provides backward compatibility during Redis SSOT migration.
The primary SSOT Redis manager now includes all cache functionality.

Business Value Justification (BVJ):
- Segment: All customer segments (Free -> Enterprise)  
- Business Goal: Improve response times and reduce database load
- Value Impact: Faster user experiences and reduced infrastructure costs
- Strategic Impact: Enables scaling to support more concurrent users

SSOT Migration:
- All functionality has been consolidated into netra_backend.app.redis_manager
- This module provides compatibility wrappers during transition
- Future imports should use redis_manager directly
"""

import asyncio
import json
import pickle
import time
import warnings
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Set
from dataclasses import dataclass, field

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)

# Issue deprecation warning for this module
warnings.warn(
    "redis_cache_manager is deprecated. Use netra_backend.app.redis_manager.redis_manager directly",
    DeprecationWarning,
    stacklevel=2
)


@dataclass
class CacheStats:
    """Cache statistics tracking."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_operations: int = 0
    start_time: Optional[datetime] = None
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total_reads = self.hits + self.misses
        if total_reads == 0:
            return 0.0
        return (self.hits / total_reads) * 100.0


@dataclass
class CacheEntry:
    """Individual cache entry metadata."""
    key: str
    size_bytes: int
    created_at: datetime
    accessed_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


class RedisCacheManager:
    """Compatibility wrapper for existing cache manager usage.
    
    DEPRECATED: Use netra_backend.app.redis_manager.redis_manager directly
    
    This class provides backward compatibility during Redis SSOT migration.
    All operations are redirected to the primary SSOT Redis manager.
    """
    
    def __init__(self, redis_client=None, namespace: str = "netra"):
        """Initialize Redis cache manager wrapper.
        
        Args:
            redis_client: Optional Redis client instance (ignored, uses SSOT)
            namespace: Cache namespace for key isolation
        """
        self.redis_client = redis_manager  # Always use SSOT
        self.namespace = namespace
        self.stats = CacheStats(start_time=datetime.now(timezone.utc))
        logger.info(f"RedisCacheManager compatibility wrapper initialized with namespace: {namespace}")
    
    def _build_key(self, key: str) -> str:
        """Build namespaced cache key.
        
        Args:
            key: Original cache key
            
        Returns:
            Namespaced cache key
        """
        return f"{self.namespace}:cache:{key}"
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        try:
            redis_key = self._build_key(key)
            raw_value = await self.redis_client.get(redis_key)
            
            if raw_value is None:
                self.stats.misses += 1
                self.stats.total_operations += 1
                logger.debug(f"Cache miss for key: {key}")
                return default
            
            # Try JSON deserialization first, then pickle
            try:
                value = json.loads(raw_value)
            except (json.JSONDecodeError, TypeError):
                try:
                    value = pickle.loads(raw_value)
                except (pickle.PickleError, TypeError):
                    # If both fail, return raw value
                    value = raw_value.decode('utf-8') if isinstance(raw_value, bytes) else raw_value
            
            self.stats.hits += 1
            self.stats.total_operations += 1
            logger.debug(f"Cache hit for key: {key}")
            return value
            
        except Exception as e:
            self.stats.errors += 1
            self.stats.total_operations += 1
            logger.error(f"Error getting cache key {key}: {e}")
            return default
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None for no expiration)
            nx: Only set if key doesn't exist
            
        Returns:
            True if value was set, False otherwise
        """
        try:
            redis_key = self._build_key(key)
            
            # Serialize value
            try:
                serialized_value = json.dumps(value)
            except (TypeError, ValueError):
                try:
                    serialized_value = pickle.dumps(value)
                except (pickle.PickleError, TypeError):
                    # Fallback to string representation
                    serialized_value = str(value)
            
            # Set in Redis
            result = await self.redis_client.set(
                redis_key, 
                serialized_value, 
                ex=ttl, 
                nx=nx
            )
            
            if result:
                self.stats.sets += 1
                logger.debug(f"Cache set for key: {key} (TTL: {ttl}s)")
            else:
                logger.debug(f"Cache set failed for key: {key} (nx={nx})")
            
            self.stats.total_operations += 1
            return bool(result)
            
        except Exception as e:
            self.stats.errors += 1
            self.stats.total_operations += 1
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if key didn't exist
        """
        try:
            redis_key = self._build_key(key)
            result = await self.redis_client.delete(redis_key)
            
            if result > 0:
                self.stats.deletes += 1
                logger.debug(f"Cache delete for key: {key}")
            
            self.stats.total_operations += 1
            return result > 0
            
        except Exception as e:
            self.stats.errors += 1
            self.stats.total_operations += 1
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            redis_key = self._build_key(key)
            result = await self.redis_client.exists(redis_key)
            self.stats.total_operations += 1
            return result > 0
            
        except Exception as e:
            self.stats.errors += 1
            self.stats.total_operations += 1
            logger.error(f"Error checking cache key existence {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for a key.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            
        Returns:
            True if expiration was set, False otherwise
        """
        try:
            redis_key = self._build_key(key)
            result = await self.redis_client.expire(redis_key, ttl)
            self.stats.total_operations += 1
            
            if result:
                logger.debug(f"Set expiration for key: {key} (TTL: {ttl}s)")
            
            return bool(result)
            
        except Exception as e:
            self.stats.errors += 1
            self.stats.total_operations += 1
            logger.error(f"Error setting expiration for cache key {key}: {e}")
            return False
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining time to live for a key.
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds, None if key doesn't exist or has no expiration
        """
        try:
            redis_key = self._build_key(key)
            ttl = await self.redis_client.ttl(redis_key)
            self.stats.total_operations += 1
            
            if ttl == -2:  # Key doesn't exist
                return None
            elif ttl == -1:  # Key exists but has no expiration
                return None
            else:
                return ttl
                
        except Exception as e:
            self.stats.errors += 1
            self.stats.total_operations += 1
            logger.error(f"Error getting TTL for cache key {key}: {e}")
            return None
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary mapping keys to values (missing keys not included)
        """
        if not keys:
            return {}
        
        try:
            redis_keys = [self._build_key(key) for key in keys]
            raw_values = await self.redis_client.mget(redis_keys)
            
            result = {}
            for i, (key, raw_value) in enumerate(zip(keys, raw_values)):
                if raw_value is not None:
                    try:
                        # Try JSON first, then pickle
                        try:
                            value = json.loads(raw_value)
                        except (json.JSONDecodeError, TypeError):
                            try:
                                value = pickle.loads(raw_value)
                            except (pickle.PickleError, TypeError):
                                value = raw_value.decode('utf-8') if isinstance(raw_value, bytes) else raw_value
                        
                        result[key] = value
                        self.stats.hits += 1
                    except Exception as decode_error:
                        logger.warning(f"Error decoding cache value for key {key}: {decode_error}")
                        self.stats.errors += 1
                else:
                    self.stats.misses += 1
            
            self.stats.total_operations += len(keys)
            logger.debug(f"Bulk get: {len(result)}/{len(keys)} keys found")
            return result
            
        except Exception as e:
            self.stats.errors += len(keys)
            self.stats.total_operations += len(keys)
            logger.error(f"Error getting multiple cache keys: {e}")
            return {}
    
    async def set_many(
        self, 
        mapping: Dict[str, Any], 
        ttl: Optional[int] = None
    ) -> int:
        """Set multiple values in cache.
        
        Args:
            mapping: Dictionary of key-value pairs to set
            ttl: Time to live in seconds (applied to all keys)
            
        Returns:
            Number of keys successfully set
        """
        if not mapping:
            return 0
        
        success_count = 0
        
        try:
            # Use pipeline for better performance
            pipe = self.redis_client.pipeline()
            
            for key, value in mapping.items():
                try:
                    redis_key = self._build_key(key)
                    
                    # Serialize value
                    try:
                        serialized_value = json.dumps(value)
                    except (TypeError, ValueError):
                        try:
                            serialized_value = pickle.dumps(value)
                        except (pickle.PickleError, TypeError):
                            serialized_value = str(value)
                    
                    if ttl:
                        pipe.setex(redis_key, ttl, serialized_value)
                    else:
                        pipe.set(redis_key, serialized_value)
                    
                except Exception as serialize_error:
                    logger.warning(f"Error serializing value for key {key}: {serialize_error}")
                    continue
            
            # Execute pipeline
            results = await pipe.execute()
            success_count = sum(1 for result in results if result)
            
            self.stats.sets += success_count
            self.stats.total_operations += len(mapping)
            logger.debug(f"Bulk set: {success_count}/{len(mapping)} keys set")
            
        except Exception as e:
            self.stats.errors += len(mapping)
            self.stats.total_operations += len(mapping)
            logger.error(f"Error setting multiple cache keys: {e}")
        
        return success_count
    
    async def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys from cache.
        
        Args:
            keys: List of cache keys to delete
            
        Returns:
            Number of keys successfully deleted
        """
        if not keys:
            return 0
        
        try:
            redis_keys = [self._build_key(key) for key in keys]
            deleted_count = await self.redis_client.delete(*redis_keys)
            
            self.stats.deletes += deleted_count
            self.stats.total_operations += len(keys)
            logger.debug(f"Bulk delete: {deleted_count}/{len(keys)} keys deleted")
            return deleted_count
            
        except Exception as e:
            self.stats.errors += len(keys)
            self.stats.total_operations += len(keys)
            logger.error(f"Error deleting multiple cache keys: {e}")
            return 0
    
    async def clear_namespace(self) -> int:
        """Clear all keys in the current namespace.
        
        Returns:
            Number of keys deleted
        """
        try:
            pattern = f"{self.namespace}:cache:*"
            keys = await self.redis_client.scan_keys(pattern)
            
            if not keys:
                return 0
            
            deleted_count = await self.redis_client.delete(*keys)
            self.stats.deletes += deleted_count
            self.stats.total_operations += len(keys)
            logger.info(f"Cleared {deleted_count} keys from namespace: {self.namespace}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error clearing namespace {self.namespace}: {e}")
            return 0
    
    async def get_stats(self) -> CacheStats:
        """Get current cache statistics.
        
        Returns:
            Current cache statistics
        """
        return self.stats
    
    async def get_size_estimate(self) -> Dict[str, Any]:
        """Get estimated cache size information.
        
        Returns:
            Dictionary with cache size estimates
        """
        try:
            pattern = f"{self.namespace}:cache:*"
            keys = await self.redis_client.scan_keys(pattern)
            
            total_keys = len(keys)
            total_memory = 0
            
            # Sample a few keys to estimate memory usage
            sample_size = min(10, total_keys)
            if sample_size > 0:
                sample_keys = keys[:sample_size]
                sample_memory = 0
                
                for key in sample_keys:
                    try:
                        memory_usage = await self.redis_client.memory_usage(key)
                        if memory_usage:
                            sample_memory += memory_usage
                    except Exception:
                        pass  # Memory usage command might not be available
                
                if sample_memory > 0:
                    avg_key_size = sample_memory / sample_size
                    total_memory = avg_key_size * total_keys
            
            return {
                "namespace": self.namespace,
                "total_keys": total_keys,
                "estimated_memory_bytes": int(total_memory),
                "estimated_memory_mb": round(total_memory / (1024 * 1024), 2),
                "hit_rate_percent": round(self.stats.hit_rate, 2),
                "total_operations": self.stats.total_operations
            }
            
        except Exception as e:
            logger.error(f"Error getting cache size estimate: {e}")
            return {
                "namespace": self.namespace,
                "error": str(e),
                "hit_rate_percent": round(self.stats.hit_rate, 2),
                "total_operations": self.stats.total_operations
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the cache.
        
        Returns:
            Health check results
        """
        health = {
            "healthy": False,
            "namespace": self.namespace,
            "error": None,
            "response_time_ms": None,
            "stats": self.stats.__dict__.copy()
        }
        
        try:
            start_time = time.time()
            
            # Test basic operations
            test_key = f"health_check_{int(time.time())}"
            test_value = {"timestamp": datetime.now(timezone.utc).isoformat()}
            
            # Test set
            set_success = await self.set(test_key, test_value, ttl=60)
            if not set_success:
                health["error"] = "Failed to set test key"
                return health
            
            # Test get
            retrieved_value = await self.get(test_key)
            if retrieved_value != test_value:
                health["error"] = "Retrieved value doesn't match set value"
                return health
            
            # Test delete
            delete_success = await self.delete(test_key)
            if not delete_success:
                health["error"] = "Failed to delete test key"
                return health
            
            end_time = time.time()
            health["response_time_ms"] = round((end_time - start_time) * 1000, 2)
            health["healthy"] = True
            
        except Exception as e:
            health["error"] = str(e)
            logger.error(f"Cache health check failed: {e}")
        
        return health


# Create default instance for SSOT access
default_redis_cache_manager = RedisCacheManager()

# Export for direct module access
__all__ = [
    "RedisCacheManager",
    "CacheStats",
    "CacheEntry", 
    "default_redis_cache_manager"
]
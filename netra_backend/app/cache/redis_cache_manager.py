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
from netra_backend.app.core.serialization_sanitizer import (
    PickleValidator,
    ObjectSanitizer,
    is_safe_for_caching
)

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
        """Get value from cache - redirects to SSOT Redis manager."""
        try:
            redis_key = self._build_key(key)
            raw_value = await self.redis_client.get(redis_key)
            
            if raw_value is None:
                self.stats.misses += 1
                self.stats.total_operations += 1
                return default
            
            # Try JSON deserialization first, then pickle
            try:
                value = json.loads(raw_value)
            except (json.JSONDecodeError, TypeError):
                try:
                    value = pickle.loads(raw_value)
                except (pickle.PickleError, TypeError):
                    value = raw_value.decode('utf-8') if isinstance(raw_value, bytes) else raw_value
            
            self.stats.hits += 1
            self.stats.total_operations += 1
            return value
            
        except Exception as e:
            self.stats.errors += 1
            self.stats.total_operations += 1
            logger.error(f"Error getting cache key {key}: {e}")
            return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, nx: bool = False) -> bool:
        """Set value in cache - redirects to SSOT Redis manager with Issue #585 fix."""
        try:
            redis_key = self._build_key(key)
            
            # ISSUE #585 FIX: Pre-validate for caching and sanitize if needed
            serialized_value = None
            
            # Try JSON serialization first (fastest and most reliable)
            try:
                serialized_value = json.dumps(value, default=str)
                logger.debug(f"Cache key {key}: JSON serialization successful")
            except (TypeError, ValueError) as json_error:
                logger.debug(f"Cache key {key}: JSON failed ({json_error}), trying pickle with validation")
                
                # Check if safe for pickle before attempting
                is_safe, safety_error = PickleValidator.validate_for_caching(value)
                
                if is_safe:
                    # Try direct pickle
                    try:
                        serialized_value = pickle.dumps(value)
                        logger.debug(f"Cache key {key}: Direct pickle serialization successful")
                    except (pickle.PickleError, TypeError) as pickle_error:
                        logger.info(f"Cache key {key}: Direct pickle failed ({pickle_error}), attempting sanitization")
                        # Use safe pickle with sanitization
                        serialized_value = PickleValidator.safe_pickle_dumps(value)
                        if serialized_value:
                            logger.info(f"Cache key {key}: Sanitized pickle serialization successful")
                        else:
                            raise ValueError("Sanitized pickle serialization failed")
                else:
                    logger.info(f"Cache key {key}: Not safe for pickle ({safety_error}), sanitizing object")
                    
                    # Sanitize the object and try pickle
                    sanitized_value = ObjectSanitizer.sanitize_object(value)
                    serialized_value = PickleValidator.safe_pickle_dumps(sanitized_value)
                    
                    if serialized_value:
                        logger.info(f"Cache key {key}: Sanitized object pickle successful")
                    else:
                        # Final fallback: string representation
                        logger.warning(f"Cache key {key}: All serialization failed, using string fallback")
                        serialized_value = str(value)
            
            if serialized_value is None:
                # Absolute fallback
                serialized_value = f"<serialization_failed: {type(value).__name__}>"
                logger.error(f"Cache key {key}: All serialization methods failed, using fallback")
            
            # Set in Redis using SSOT manager
            result = await self.redis_client.set(redis_key, serialized_value, ex=ttl)
            
            if result:
                self.stats.sets += 1
            
            self.stats.total_operations += 1
            return bool(result)
            
        except Exception as e:
            self.stats.errors += 1
            self.stats.total_operations += 1
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache - redirects to SSOT Redis manager."""
        try:
            redis_key = self._build_key(key)
            result = await self.redis_client.delete(redis_key)
            
            if result > 0:
                self.stats.deletes += 1
            
            self.stats.total_operations += 1
            return result > 0
            
        except Exception as e:
            self.stats.errors += 1
            self.stats.total_operations += 1
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache - redirects to SSOT Redis manager."""
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
        """Set expiration time for a key - redirects to SSOT Redis manager."""
        try:
            redis_key = self._build_key(key)
            result = await self.redis_client.expire(redis_key, ttl)
            self.stats.total_operations += 1
            return bool(result)
        except Exception as e:
            self.stats.errors += 1
            self.stats.total_operations += 1
            logger.error(f"Error setting expiration for cache key {key}: {e}")
            return False
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining time to live for a key - redirects to SSOT Redis manager."""
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
        """Get multiple values from cache - redirects to SSOT Redis manager."""
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
            return result
            
        except Exception as e:
            self.stats.errors += len(keys)
            self.stats.total_operations += len(keys)
            logger.error(f"Error getting multiple cache keys: {e}")
            return {}
    
    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> int:
        """Set multiple values in cache - redirects to SSOT Redis manager."""
        if not mapping:
            return 0
        
        success_count = 0
        
        # Use individual sets for compatibility
        for key, value in mapping.items():
            try:
                if await self.set(key, value, ttl=ttl):
                    success_count += 1
            except Exception as e:
                logger.warning(f"Error setting cache key {key}: {e}")
                continue
        
        return success_count
    
    async def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys from cache - redirects to SSOT Redis manager."""
        if not keys:
            return 0
        
        try:
            redis_keys = [self._build_key(key) for key in keys]
            # Use SSOT Redis manager's delete method for each key
            deleted_count = 0
            for redis_key in redis_keys:
                if await self.redis_client.delete(redis_key):
                    deleted_count += 1
            
            self.stats.deletes += deleted_count
            self.stats.total_operations += len(keys)
            return deleted_count
            
        except Exception as e:
            self.stats.errors += len(keys)
            self.stats.total_operations += len(keys)
            logger.error(f"Error deleting multiple cache keys: {e}")
            return 0
    
    async def clear_namespace(self) -> int:
        """Clear all keys in the current namespace - redirects to SSOT Redis manager."""
        try:
            pattern = f"{self.namespace}:cache:*"
            keys = await self.redis_client.scan_keys(pattern)
            
            if not keys:
                return 0
            
            # Use individual deletes for compatibility
            deleted_count = 0
            for key in keys:
                if await self.redis_client.delete(key):
                    deleted_count += 1
            
            self.stats.deletes += deleted_count
            self.stats.total_operations += len(keys)
            logger.info(f"Cleared {deleted_count} keys from namespace: {self.namespace}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error clearing namespace {self.namespace}: {e}")
            return 0
    
    async def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        return self.stats
    
    async def get_size_estimate(self) -> Dict[str, Any]:
        """Get estimated cache size information - redirects to SSOT Redis manager."""
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
        """Perform a health check on the cache - redirects to SSOT Redis manager."""
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
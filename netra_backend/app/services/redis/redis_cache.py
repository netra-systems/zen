"""Redis Cache Service

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (performance optimization)
- Business Goal: High-performance caching with Redis backend
- Value Impact: Dramatically reduces response times and database load
- Strategic Impact: Essential for scalable enterprise applications

Provides Redis-based caching with advanced features and monitoring.
"""

import asyncio
import json
import pickle
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Union, List, Callable
from dataclasses import dataclass, field

import redis.asyncio as redis
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class CacheConfig:
    """Configuration for Redis cache."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    decode_responses: bool = True
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_operations: int = 0
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        return (self.errors / self.total_operations) if self.total_operations > 0 else 0.0


class RedisCache:
    """High-performance Redis cache implementation."""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """Initialize Redis cache with configuration."""
        self.config = config or CacheConfig()
        self.metrics = CacheMetrics()
        self._redis_pool: Optional[redis.ConnectionPool] = None
        self._redis_client: Optional[redis.Redis] = None
        self._is_connected = False
        self._lock = asyncio.Lock()
    
    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._redis_pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                decode_responses=self.config.decode_responses,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout
            )
            
            self._redis_client = redis.Redis(connection_pool=self._redis_pool)
            
            # Test connection
            await self._redis_client.ping()
            self._is_connected = True
            
            logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
            
        except Exception as e:
            self._is_connected = False
            self.metrics.errors += 1
            logger.error(f"Failed to connect to Redis: {e}")
            raise NetraException(f"Redis connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis_client:
            await self._redis_client.close()
        if self._redis_pool:
            await self._redis_pool.disconnect()
        
        self._is_connected = False
        logger.info("Disconnected from Redis")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from cache."""
        if not self._is_connected:
            raise NetraException("Redis not connected")
        
        try:
            self.metrics.total_operations += 1
            
            value = await self._redis_client.get(key)
            if value is None:
                self.metrics.misses += 1
                return default
            
            self.metrics.hits += 1
            
            # Try to deserialize JSON, fall back to string
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache get failed for key {key}: {e}")
            return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache with optional TTL."""
        if not self._is_connected:
            raise NetraException("Redis not connected")
        
        try:
            self.metrics.total_operations += 1
            self.metrics.sets += 1
            
            # Serialize value
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = str(value)
            
            if ttl:
                await self._redis_client.setex(key, ttl, serialized_value)
            else:
                await self._redis_client.set(key, serialized_value)
            
            return True
            
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache set failed for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self._is_connected:
            raise NetraException("Redis not connected")
        
        try:
            self.metrics.total_operations += 1
            self.metrics.deletes += 1
            
            result = await self._redis_client.delete(key)
            return result > 0
            
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        if not self._is_connected:
            raise NetraException("Redis not connected")
        
        try:
            self.metrics.total_operations += 1
            return bool(await self._redis_client.exists(key))
            
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache exists check failed for key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for an existing key."""
        if not self._is_connected:
            raise NetraException("Redis not connected")
        
        try:
            self.metrics.total_operations += 1
            return bool(await self._redis_client.expire(key, ttl))
            
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache expire failed for key {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get TTL for a key."""
        if not self._is_connected:
            raise NetraException("Redis not connected")
        
        try:
            self.metrics.total_operations += 1
            return await self._redis_client.ttl(key)
            
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache TTL check failed for key {key}: {e}")
            return -1
    
    async def clear(self, pattern: str = "*") -> int:
        """Clear cache keys matching pattern."""
        if not self._is_connected:
            raise NetraException("Redis not connected")
        
        try:
            self.metrics.total_operations += 1
            
            keys = await self._redis_client.keys(pattern)
            if keys:
                deleted = await self._redis_client.delete(*keys)
                self.metrics.deletes += deleted
                return deleted
            return 0
            
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache clear failed for pattern {pattern}: {e}")
            return 0
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        if not self._is_connected:
            raise NetraException("Redis not connected")
        
        try:
            self.metrics.total_operations += len(keys)
            
            values = await self._redis_client.mget(keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value is not None:
                    self.metrics.hits += 1
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = value
                else:
                    self.metrics.misses += 1
            
            return result
            
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache get_many failed: {e}")
            return {}
    
    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple key-value pairs."""
        if not self._is_connected:
            raise NetraException("Redis not connected")
        
        try:
            self.metrics.total_operations += len(mapping)
            self.metrics.sets += len(mapping)
            
            # Serialize all values
            serialized_mapping = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list, tuple)):
                    serialized_mapping[key] = json.dumps(value, default=str)
                else:
                    serialized_mapping[key] = str(value)
            
            # Use pipeline for atomic operation
            pipe = self._redis_client.pipeline()
            pipe.mset(serialized_mapping)
            
            if ttl:
                for key in mapping.keys():
                    pipe.expire(key, ttl)
            
            await pipe.execute()
            return True
            
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache set_many failed: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value."""
        if not self._is_connected:
            raise NetraException("Redis not connected")
        
        try:
            self.metrics.total_operations += 1
            return await self._redis_client.incrby(key, amount)
            
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache increment failed for key {key}: {e}")
            raise NetraException(f"Cache increment failed: {e}")
    
    async def get_metrics(self) -> CacheMetrics:
        """Get cache performance metrics."""
        return self.metrics
    
    async def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self.metrics = CacheMetrics()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Redis connection."""
        try:
            if not self._is_connected:
                return {"status": "unhealthy", "reason": "Not connected"}
            
            start_time = time.time()
            await self._redis_client.ping()
            response_time = (time.time() - start_time) * 1000
            
            info = await self._redis_client.info()
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown"),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
                "cache_metrics": {
                    "hit_rate": self.metrics.hit_rate,
                    "error_rate": self.metrics.error_rate,
                    "total_operations": self.metrics.total_operations
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "reason": str(e),
                "response_time_ms": -1
            }
    
    async def get_info(self) -> Dict[str, Any]:
        """Get Redis server information."""
        if not self._is_connected:
            raise NetraException("Redis not connected")
        
        try:
            return await self._redis_client.info()
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            raise NetraException(f"Failed to get Redis info: {e}")
    
    async def get_cache_size(self) -> int:
        """Get number of keys in cache."""
        if not self._is_connected:
            raise NetraException("Redis not connected")
        
        try:
            return await self._redis_client.dbsize()
        except Exception as e:
            logger.error(f"Failed to get cache size: {e}")
            return 0
    
    async def flush_db(self) -> bool:
        """Flush the current database."""
        if not self._is_connected:
            raise NetraException("Redis not connected")
        
        try:
            await self._redis_client.flushdb()
            logger.warning("Redis database flushed")
            return True
        except Exception as e:
            logger.error(f"Failed to flush database: {e}")
            return False


class RedisCacheManager:
    """Manager for multiple Redis cache instances."""
    
    def __init__(self):
        """Initialize the cache manager."""
        self._caches: Dict[str, RedisCache] = {}
        self._default_cache: Optional[RedisCache] = None
    
    async def add_cache(self, name: str, config: CacheConfig) -> RedisCache:
        """Add a new cache instance."""
        cache = RedisCache(config)
        await cache.connect()
        self._caches[name] = cache
        
        if not self._default_cache:
            self._default_cache = cache
        
        logger.info(f"Added Redis cache: {name}")
        return cache
    
    async def get_cache(self, name: str = "default") -> Optional[RedisCache]:
        """Get a cache instance by name."""
        if name == "default":
            return self._default_cache
        return self._caches.get(name)
    
    async def remove_cache(self, name: str) -> bool:
        """Remove a cache instance."""
        if name in self._caches:
            cache = self._caches[name]
            await cache.disconnect()
            del self._caches[name]
            
            if self._default_cache == cache:
                self._default_cache = None
            
            logger.info(f"Removed Redis cache: {name}")
            return True
        return False
    
    async def shutdown_all(self) -> None:
        """Shutdown all cache instances."""
        for cache in self._caches.values():
            await cache.disconnect()
        self._caches.clear()
        self._default_cache = None
        logger.info("All Redis caches shut down")


# Global cache manager instance
redis_cache_manager = RedisCacheManager()
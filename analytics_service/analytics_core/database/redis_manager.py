"""Redis Connection Manager for Analytics Service.

Provides Redis connection management with:
- Connection pooling
- Retry logic with exponential backoff
- Health checks
- Key expiration management
- Async/await support

This module follows the isolation pattern - no imports from other services.
"""

import asyncio
import logging
from typing import Optional, Any, Dict
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.exceptions import (
    ConnectionError,
    TimeoutError,
    RedisError,
    ResponseError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class RedisConnectionError(Exception):
    """Custom exception for Redis connection issues."""
    pass


class RedisManager:
    """
    Redis Connection Manager with pooling, retry logic, and health checks.
    
    Features:
    - Connection pooling for optimal performance
    - Exponential backoff retry logic
    - Health monitoring and connection recovery
    - TTL management for automatic key expiration
    - Async/await support throughout
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 20,
        retry_on_timeout: bool = True,
        socket_connect_timeout: int = 5,
        socket_timeout: int = 5,
        health_check_interval: int = 30,
    ):
        """
        Initialize Redis Manager.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Database number to use
            password: Redis password if auth required
            max_connections: Maximum connections in pool
            retry_on_timeout: Whether to retry on timeout
            socket_connect_timeout: Connection timeout in seconds
            socket_timeout: Socket timeout in seconds
            health_check_interval: Health check interval in seconds
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.retry_on_timeout = retry_on_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.socket_timeout = socket_timeout
        self.health_check_interval = health_check_interval
        
        self._pool: Optional[redis.ConnectionPool] = None
        self._redis: Optional[redis.Redis] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_connected = False
        
    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        try:
            # Create connection pool
            self._pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                retry_on_timeout=self.retry_on_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                socket_timeout=self.socket_timeout,
                decode_responses=True,  # Auto-decode bytes to strings
            )
            
            # Create Redis client
            self._redis = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self._test_connection()
            
            # Start health monitoring
            self._health_check_task = asyncio.create_task(
                self._health_monitor()
            )
            
            self._is_connected = True
            logger.info(
                f"Redis connection initialized successfully: "
                f"{self.host}:{self.port}/{self.db}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise RedisConnectionError(f"Redis initialization failed: {e}")
    
    async def close(self) -> None:
        """Close Redis connections and cleanup resources."""
        try:
            if self._health_check_task and not self._health_check_task.done():
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            if self._redis:
                await self._redis.aclose()
            
            if self._pool:
                await self._pool.aclose()
                
            self._is_connected = False
            logger.info("Redis connection closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Get a Redis connection from the pool.
        
        Usage:
            async with manager.get_connection() as redis_conn:
                await redis_conn.set("key", "value")
        """
        if not self._is_connected or not self._redis:
            raise RedisConnectionError("Redis not connected")
        
        try:
            yield self._redis
        except Exception as e:
            logger.error(f"Redis operation error: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    async def _test_connection(self) -> None:
        """Test Redis connection with retry logic."""
        if not self._redis:
            raise RedisConnectionError("Redis client not initialized")
        
        try:
            await self._redis.ping()
            logger.debug("Redis connection test successful")
        except Exception as e:
            logger.error(f"Redis connection test failed: {e}")
            raise RedisConnectionError(f"Connection test failed: {e}")
    
    async def _health_monitor(self) -> None:
        """Background task to monitor Redis health."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if self._redis:
                    # Perform health check
                    await self._redis.ping()
                    
                    # Log connection pool stats
                    if self._pool:
                        created_connections = self._pool.created_connections
                        available_connections = len(self._pool._available_connections)
                        in_use_connections = len(self._pool._in_use_connections)
                        
                        logger.debug(
                            f"Redis pool stats - Created: {created_connections}, "
                            f"Available: {available_connections}, "
                            f"In use: {in_use_connections}"
                        )
                        
            except asyncio.CancelledError:
                logger.info("Redis health monitor cancelled")
                break
            except Exception as e:
                logger.warning(f"Redis health check failed: {e}")
                self._is_connected = False
                
                # Attempt to reconnect
                try:
                    await self._test_connection()
                    self._is_connected = True
                    logger.info("Redis connection recovered")
                except Exception as reconnect_error:
                    logger.error(f"Failed to reconnect to Redis: {reconnect_error}")
    
    async def is_healthy(self) -> bool:
        """Check if Redis connection is healthy."""
        if not self._is_connected or not self._redis:
            return False
        
        try:
            await self._redis.ping()
            return True
        except Exception:
            return False
    
    async def get_info(self) -> Dict[str, Any]:
        """Get Redis server information."""
        if not self._redis:
            raise RedisConnectionError("Redis not connected")
        
        try:
            info = await self._redis.info()
            return {
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
            }
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            raise RedisConnectionError(f"Failed to get info: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._is_connected
    
    @property
    def redis(self) -> redis.Redis:
        """Get the Redis client instance."""
        if not self._redis:
            raise RedisConnectionError("Redis not connected")
        return self._redis


# Global Redis manager instance
_redis_manager: Optional[RedisManager] = None


def get_redis_manager(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
    **kwargs
) -> RedisManager:
    """
    Get or create a Redis manager instance.
    
    This follows the singleton pattern to ensure a single connection pool
    is used throughout the analytics service.
    """
    global _redis_manager
    
    if _redis_manager is None:
        _redis_manager = RedisManager(
            host=host,
            port=port,
            db=db,
            password=password,
            **kwargs
        )
    
    return _redis_manager


async def initialize_redis(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
    **kwargs
) -> RedisManager:
    """Initialize and return the global Redis manager."""
    manager = get_redis_manager(host, port, db, password, **kwargs)
    await manager.initialize()
    return manager


async def close_redis() -> None:
    """Close the global Redis manager."""
    global _redis_manager
    if _redis_manager:
        await _redis_manager.close()
        _redis_manager = None
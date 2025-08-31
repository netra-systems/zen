"""
Database Connection Management for Analytics Service

Provides real connection factories for ClickHouse and Redis.
Follows SPEC/unified_environment_management.xml patterns.

CRITICAL: Uses service-specific IsolatedEnvironment for independence.
"""
from typing import Optional, Any, Dict
import logging
import asyncio
from contextlib import asynccontextmanager

from analytics_service.analytics_core.config import get_config
from analytics_service.analytics_core.database.clickhouse_manager import ClickHouseManager
from analytics_service.analytics_core.database.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Global connection managers
_clickhouse_manager: Optional[ClickHouseManager] = None
_redis_manager: Optional[RedisManager] = None


def get_clickhouse_manager() -> ClickHouseManager:
    """Get or create ClickHouse manager singleton."""
    global _clickhouse_manager
    if _clickhouse_manager is None:
        config = get_config()
        params = config.get_clickhouse_connection_params()
        _clickhouse_manager = ClickHouseManager(
            host=params["host"],
            port=9000,  # Use native protocol port, not HTTP port
            database=params["database"],
            user=params["user"],
            password=params["password"],
            max_connections=config.connection_pool_size,
            query_timeout=config.query_timeout_seconds
        )
    return _clickhouse_manager


@asynccontextmanager
async def get_clickhouse_session():
    """Get ClickHouse session using connection manager.
    
    Returns an async context manager for ClickHouse connections.
    Ensures proper initialization and cleanup.
    """
    manager = get_clickhouse_manager()
    
    # Ensure manager is initialized
    if not manager._is_initialized:
        await manager.initialize()
    
    # Get connection from pool
    async with manager.get_connection() as connection:
        yield connection


def get_redis_manager() -> RedisManager:
    """Get or create Redis manager singleton."""
    global _redis_manager
    if _redis_manager is None:
        config = get_config()
        params = config.get_redis_connection_params()
        _redis_manager = RedisManager(
            host=params["host"],
            port=params["port"],
            db=params["db"],
            password=params.get("password"),
            max_connections=config.connection_pool_size
        )
    return _redis_manager


@asynccontextmanager
async def get_redis_connection():
    """Get Redis connection using connection manager.
    
    Returns an async context manager for Redis connections.
    Ensures proper initialization and cleanup.
    """
    manager = get_redis_manager()
    
    # Ensure manager is initialized
    if not hasattr(manager, '_is_connected') or not manager._is_connected:
        await manager.initialize()
    
    # Return the Redis client directly (it manages its own connections)
    yield manager._redis


async def get_clickhouse_session_async():
    """Get async ClickHouse session (delegates to main function).
    
    For backward compatibility - use get_clickhouse_session() instead.
    """
    async with get_clickhouse_session() as session:
        return session


async def get_redis_connection_async():
    """Get async Redis connection (delegates to main function).
    
    For backward compatibility - use get_redis_connection() instead.
    """
    async with get_redis_connection() as connection:
        return connection


class ClickHouseHealthChecker:
    """Health checker for ClickHouse database."""
    
    def __init__(self):
        """Initialize health checker."""
        self.manager = None
    
    async def check_health(self) -> Dict[str, Any]:
        """Check ClickHouse health status using real connection."""
        try:
            manager = get_clickhouse_manager()
            
            # Ensure manager is initialized
            if not manager._is_initialized:
                await manager.initialize()
            
            # Get health status from manager
            health_status = await manager.get_health_status()
            
            # Perform actual query test
            if health_status.get('is_healthy'):
                async with manager.get_connection() as client:
                    # Test with simple query
                    import time
                    start = time.time()
                    result = await asyncio.to_thread(
                        lambda: client.execute("SELECT 1")
                    )
                    latency_ms = (time.time() - start) * 1000
                    
                    if result == [(1,)]:
                        return {
                            "status": "healthy",
                            "connection": True,
                            "latency_ms": latency_ms,
                            "host": health_status.get('host'),
                            "port": health_status.get('port'),
                            "database": health_status.get('database'),
                            "pool_size": health_status.get('pool_size')
                        }
                    else:
                        raise ValueError("Unexpected query result")
            else:
                return {
                    "status": "unhealthy",
                    "connection": False,
                    "error": "Manager reports unhealthy status"
                }
                
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {e}")
            return {
                "status": "unhealthy",
                "connection": False,
                "error": str(e)
            }


class RedisHealthChecker:
    """Health checker for Redis cache."""
    
    def __init__(self):
        """Initialize health checker."""
        self.manager = None
    
    async def check_health(self) -> Dict[str, Any]:
        """Check Redis health status using real connection."""
        try:
            manager = get_redis_manager()
            
            # Ensure manager is initialized
            if not hasattr(manager, '_is_connected') or not manager._is_connected:
                await manager.initialize()
            
            # Perform actual ping test
            import time
            start = time.time()
            
            # Use the Redis client to ping
            if manager._redis:
                pong = await manager._redis.ping()
                latency_ms = (time.time() - start) * 1000
                
                if pong:
                    return {
                        "status": "healthy",
                        "connection": True,
                        "latency_ms": latency_ms,
                        "host": manager.host,
                        "port": manager.port,
                        "db": manager.db
                    }
                else:
                    raise ValueError("Ping failed")
            else:
                return {
                    "status": "unhealthy",
                    "connection": False,
                    "error": "Redis client not initialized"
                }
                
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "connection": False,
                "error": str(e)
            }
"""Redis Client Module - SSOT for Redis Client Access

Provides a centralized `get_redis_client` function following SSOT patterns for
integration tests and service dependencies. Delegates to existing Redis infrastructure
while maintaining consistent interface patterns.

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise) 
2. Business Goal: Reliable caching and session management
3. Value Impact: Enables scalable Redis operations for system lifecycle
4. Revenue Impact: Critical for system performance and reliability

This module follows the same pattern as get_database_manager() and other
SSOT service accessors in the codebase.
"""

import logging
from typing import Optional, Any
import redis

from netra_backend.app.services.redis_service import redis_service
from netra_backend.app.core.redis_connection_handler import RedisConnectionHandler

logger = logging.getLogger(__name__)


class RedisClientError(Exception):
    """Raised when Redis client operations fail."""
    pass


async def get_redis_client(user_context: Optional[Any] = None) -> redis.Redis:
    """Get Redis client instance following SSOT patterns.
    
    This function provides a consistent interface for accessing Redis clients
    across the application, particularly for integration tests and system
    lifecycle management.
    
    Args:
        user_context: Optional user context for user-specific operations.
                     Currently unused but maintained for API consistency.
    
    Returns:
        redis.Redis: Redis client instance ready for use
    
    Raises:
        RedisClientError: If Redis client cannot be created or connected
    
    Example:
        >>> redis_client = await get_redis_client()
        >>> await redis_client.ping()
        True
    """
    try:
        # First try to get the client from the existing redis_service
        # which handles user isolation and proper configuration
        if hasattr(redis_service, 'client') and redis_service.client:
            # Ensure the service is connected
            if not await redis_service.ping():
                await redis_service.connect()
            return redis_service.client
        
        # Fallback to RedisConnectionHandler for direct client creation
        logger.debug("Using RedisConnectionHandler fallback for Redis client")
        connection_handler = RedisConnectionHandler()
        redis_client = connection_handler.get_redis_client()
        
        # Validate the connection works
        redis_client.ping()
        logger.info("Redis client created successfully via RedisConnectionHandler")
        return redis_client
        
    except Exception as e:
        error_msg = f"Failed to create Redis client: {e}"
        logger.error(error_msg)
        raise RedisClientError(error_msg) from e


def get_redis_service() -> Any:
    """Get the global Redis service instance.
    
    Provides access to the full Redis service with user isolation support.
    
    Returns:
        RedisService: Global Redis service instance
    """
    return redis_service


# Synchronous wrapper for compatibility with existing patterns
def get_redis_client_sync() -> redis.Redis:
    """Get Redis client synchronously using RedisConnectionHandler.
    
    This is a synchronous version for compatibility with non-async contexts.
    Use get_redis_client() for async contexts when possible.
    
    Returns:
        redis.Redis: Redis client instance
    
    Raises:
        RedisClientError: If Redis client cannot be created
    """
    try:
        connection_handler = RedisConnectionHandler()
        redis_client = connection_handler.get_redis_client()
        logger.debug("Synchronous Redis client created successfully")
        return redis_client
    except Exception as e:
        error_msg = f"Failed to create synchronous Redis client: {e}"
        logger.error(error_msg)
        raise RedisClientError(error_msg) from e


# For backward compatibility and testing support
def validate_redis_connection() -> dict:
    """Validate Redis connection and return status information.
    
    Returns:
        dict: Connection status information including:
            - connected: bool
            - host: str  
            - port: int
            - response_time_ms: float
            - error: str (if any)
    """
    try:
        connection_handler = RedisConnectionHandler()
        return connection_handler.validate_connection()
    except Exception as e:
        return {
            "connected": False,
            "host": "unknown",
            "port": 0,
            "response_time_ms": None,
            "error": str(e)
        }
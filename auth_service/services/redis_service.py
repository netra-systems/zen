"""
Redis Service - Single Source of Truth for Redis Operations

This service provides a unified interface for Redis operations,
following SSOT principles and maintaining service independence.
"""

import logging
from typing import Any, Optional, List
from auth_service.auth_core.redis_manager import AuthRedisManager
from auth_service.auth_core.config import AuthConfig

logger = logging.getLogger(__name__)


class RedisService:
    """
    Single Source of Truth for Redis operations.
    
    This service wraps the existing RedisManager to provide a consistent interface.
    """
    
    def __init__(self, auth_config: AuthConfig):
        """Initialize Redis service with configuration."""
        self.auth_config = auth_config
        self._redis_manager = AuthRedisManager()
    
    async def connect(self):
        """Connect to Redis."""
        await self._redis_manager.connect()
    
    async def close(self):
        """Close Redis connection."""
        await self._redis_manager.close()
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a key-value pair in Redis."""
        return await self._redis_manager.set(key, value, ex=ex)
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key from Redis."""
        return await self._redis_manager.get(key)
    
    async def delete(self, *keys: str) -> int:
        """Delete keys from Redis."""
        return await self._redis_manager.delete(*keys)
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        return await self._redis_manager.keys(pattern)


__all__ = ["RedisService"]
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
        await self._redis_manager.disconnect()
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a key-value pair in Redis."""
        if not await self._redis_manager.ensure_connected():
            return False
        
        try:
            client = self._redis_manager.get_client()
            if not client:
                return False
            
            if ex is not None:
                await client.setex(key, ex, value)
            else:
                await client.set(key, value)
            return True
        except Exception:
            return False
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key from Redis."""
        if not await self._redis_manager.ensure_connected():
            return None
        
        try:
            client = self._redis_manager.get_client()
            if not client:
                return None
            
            result = await client.get(key)
            return result.decode('utf-8') if result else None
        except Exception:
            return None
    
    async def delete(self, *keys: str) -> int:
        """Delete keys from Redis."""
        if not await self._redis_manager.ensure_connected():
            return 0
        
        try:
            client = self._redis_manager.get_client()
            if not client:
                return 0
            
            return await client.delete(*keys)
        except Exception:
            return 0
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        if not await self._redis_manager.ensure_connected():
            return []
        
        try:
            client = self._redis_manager.get_client()
            if not client:
                return []
            
            result = await client.keys(pattern)
            return [key.decode('utf-8') if isinstance(key, bytes) else key for key in result]
        except Exception:
            return []


__all__ = ["RedisService"]
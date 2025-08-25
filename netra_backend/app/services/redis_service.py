"""Redis service wrapper - delegates to unified redis_manager.

Provides backward compatibility interface while consolidating Redis functionality.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Fast session and cache management
3. Value Impact: Enables scalable authentication and caching
4. Revenue Impact: Critical for performance and user experience
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from netra_backend.app.redis_manager import redis_manager

logger = logging.getLogger(__name__)


class RedisService:
    """Async Redis service wrapper - delegates to unified redis_manager."""
    
    def __init__(self, test_mode: bool = False):
        """Initialize Redis service."""
        self.test_mode = test_mode
        # Use shared redis_manager with test_mode if needed
        if test_mode:
            from netra_backend.app.redis_manager import RedisManager
            self._manager = RedisManager(test_mode=True)
        else:
            self._manager = redis_manager
            
    async def connect(self):
        """Connect to Redis."""
        await self._manager.connect()
            
    async def disconnect(self):
        """Disconnect from Redis."""
        await self._manager.disconnect()
            
    async def ping(self) -> bool:
        """Test Redis connection."""
        return await self._manager.ping()
            
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        return await self._manager.get(key)
            
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key-value pair."""
        result = await self._manager.set(key, value, ex=ex)
        return result is not None
            
    async def setex(self, key: str, time: int = None, value: str = None, ttl: int = None) -> bool:
        """Set key-value pair with expiration - support multiple parameter formats."""
        # Handle different parameter patterns that tests might use
        if ttl is not None:
            time = ttl
        if time is None:
            time = 60  # default TTL
        return await self._manager.setex(key, time, value)
            
    async def delete(self, *keys: str) -> int:
        """Delete keys."""
        return await self._manager.delete(*keys)
            
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        return await self._manager.keys(pattern)
            
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return await self._manager.exists(key)
            
    async def expire(self, key: str, time: int) -> bool:
        """Set key expiration."""
        return await self._manager.expire(key, time)
            
    async def acquire_leader_lock(self, instance_id: str, ttl: int = 30) -> bool:
        """
        Acquire distributed leader lock to prevent split-brain.
        
        Args:
            instance_id: Unique instance identifier
            ttl: Lock time-to-live in seconds
            
        Returns:
            True if lock acquired, False otherwise
        """
        return await self._manager.acquire_leader_lock(instance_id, ttl)
            
    async def release_leader_lock(self, instance_id: str) -> bool:
        """
        Release leader lock if held by this instance.
        
        Args:
            instance_id: Instance identifier that should hold the lock
            
        Returns:
            True if lock released, False otherwise
        """
        return await self._manager.release_leader_lock(instance_id)

    @property
    def client(self):
        """Get Redis client for backward compatibility."""
        return self._manager.redis_client
        
    # Additional methods required by tests and other components
    async def set_json(self, key: str, value: Dict[str, Any], ex: Optional[int] = None) -> bool:
        """Set JSON value in Redis."""
        json_str = json.dumps(value)
        result = await self._manager.set(key, json_str, ex=ex)
        return result is not None
        
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value from Redis."""
        json_str = await self._manager.get(key)
        if json_str:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return None
        return None
        
    async def incr(self, key: str) -> int:
        """Increment key value."""
        client = await self._manager.get_client()
        if client:
            try:
                return await client.incr(key)
            except Exception as e:
                logger.warning(f"Failed to incr {key}: {e}")
                return 0
        return 0
        
    async def decr(self, key: str) -> int:
        """Decrement key value."""
        client = await self._manager.get_client()
        if client:
            try:
                return await client.decr(key)
            except Exception as e:
                logger.warning(f"Failed to decr {key}: {e}")
                return 0
        return 0
        
    async def lpush(self, key: str, *values) -> int:
        """Push items to left side of list."""
        return await self._manager.lpush(key, *values)
        
    async def rpush(self, key: str, *values) -> int:
        """Push items to right side of list."""
        client = await self._manager.get_client()
        if client:
            try:
                return await client.rpush(key, *values)
            except Exception as e:
                logger.warning(f"Failed to rpush to {key}: {e}")
                return 0
        return 0
        
    async def lpop(self, key: str) -> Optional[str]:
        """Pop item from left side of list."""
        return await self._manager.lpop(key)
        
    async def rpop(self, key: str) -> Optional[str]:
        """Pop item from right side of list."""
        return await self._manager.rpop(key)
        
    async def llen(self, key: str) -> int:
        """Get length of list."""
        return await self._manager.llen(key)
        
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get range of items from list."""
        client = await self._manager.get_client()
        if client:
            try:
                return await client.lrange(key, start, end)
            except Exception as e:
                logger.warning(f"Failed to lrange {key}: {e}")
                return []
        return []
        
    async def sadd(self, key: str, *members) -> int:
        """Add members to set."""
        client = await self._manager.get_client()
        if client:
            try:
                return await client.sadd(key, *members)
            except Exception as e:
                logger.warning(f"Failed to sadd to {key}: {e}")
                return 0
        return 0
        
    async def srem(self, key: str, *members) -> int:
        """Remove members from set."""
        client = await self._manager.get_client()
        if client:
            try:
                return await client.srem(key, *members)
            except Exception as e:
                logger.warning(f"Failed to srem from {key}: {e}")
                return 0
        return 0
        
    async def smembers(self, key: str) -> List[str]:
        """Get all members of set."""
        client = await self._manager.get_client()
        if client:
            try:
                members = await client.smembers(key)
                return [m.decode() if isinstance(m, bytes) else m for m in members]
            except Exception as e:
                logger.warning(f"Failed to smembers {key}: {e}")
                return []
        return []
        
    async def hset(self, key: str, field_or_mapping: Union[str, Dict[str, Any]], value: Optional[str] = None) -> int:
        """Set hash field(s)."""
        return await self._manager.hset(key, field_or_mapping, value)
        
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field value."""
        return await self._manager.hget(key, field)
        
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """Get all hash fields and values."""
        return await self._manager.hgetall(key)
        
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        return await self._manager.ttl(key)


# Global Redis service instance
redis_service = RedisService()
"""Redis service wrapper - delegates to unified redis_manager.

Provides backward compatibility interface while consolidating Redis functionality.
All functions  <= 8 lines (MANDATORY). File  <= 300 lines (MANDATORY).

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
    
    def _namespace_key(self, user_id: Optional[str], key: str) -> str:
        """Namespace Redis key by user for isolation.
        
        Args:
            user_id: User identifier for namespacing. None uses 'system' namespace.
            key: Original Redis key
            
        Returns:
            Namespaced key in format 'user:{user_id}:{key}' or 'system:{key}'
        """
        namespace = user_id if user_id is not None else "system"
        return f"user:{namespace}:{key}"
            
    async def connect(self):
        """Connect to Redis."""
        await self._manager.connect()
            
    async def disconnect(self):
        """Disconnect from Redis."""
        await self._manager.disconnect()
            
    async def ping(self) -> bool:
        """Test Redis connection."""
        return await self._manager.ping()
            
    async def get(self, key: str, user_id: Optional[str] = None) -> Optional[str]:
        """Get value by key with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        return await self._manager.get(namespaced_key)
            
    async def set(self, key: str, value: str, ex: Optional[int] = None, user_id: Optional[str] = None) -> bool:
        """Set key-value pair with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        result = await self._manager.set(namespaced_key, value, ex=ex)
        return result is not None
            
    async def setex(self, key: str, time: int = None, value: str = None, ttl: int = None, user_id: Optional[str] = None) -> bool:
        """Set key-value pair with expiration - support multiple parameter formats."""
        # Handle different parameter patterns that tests might use
        if ttl is not None:
            time = ttl
        if time is None:
            time = 60  # default TTL
        namespaced_key = self._namespace_key(user_id, key)
        return await self._manager.setex(namespaced_key, time, value)
            
    async def delete(self, *keys: str, **kwargs) -> int:
        """Delete keys with optional user namespacing."""
        user_id = kwargs.get('user_id')
        if user_id is not None:
            namespaced_keys = [self._namespace_key(user_id, key) for key in keys]
            return await self._manager.delete(*namespaced_keys)
        return await self._manager.delete(*keys)
            
    async def keys(self, pattern: str, user_id: Optional[str] = None) -> List[str]:
        """Get keys matching pattern with optional user namespacing."""
        if user_id is not None:
            namespaced_pattern = self._namespace_key(user_id, pattern)
            keys = await self._manager.keys(namespaced_pattern)
            # Remove namespace prefix from returned keys
            namespace_prefix = f"user:{user_id}:"
            return [key.replace(namespace_prefix, "", 1) for key in keys if key.startswith(namespace_prefix)]
        return await self._manager.keys(pattern)
            
    async def exists(self, key: str, user_id: Optional[str] = None) -> bool:
        """Check if key exists with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        return await self._manager.exists(namespaced_key)
            
    async def expire(self, key: str, time: int, user_id: Optional[str] = None) -> bool:
        """Set key expiration with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        return await self._manager.expire(namespaced_key, time)
            
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
    async def set_json(self, key: str, value: Dict[str, Any], ex: Optional[int] = None, user_id: Optional[str] = None) -> bool:
        """Set JSON value in Redis with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        json_str = json.dumps(value)
        result = await self._manager.set(namespaced_key, json_str, ex=ex)
        return result is not None
        
    async def get_json(self, key: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get JSON value from Redis with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        json_str = await self._manager.get(namespaced_key)
        if json_str:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return None
        return None
        
    async def incr(self, key: str, user_id: Optional[str] = None) -> int:
        """Increment key value with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        client = await self._manager.get_client()
        if client:
            try:
                return await client.incr(namespaced_key)
            except Exception as e:
                logger.warning(f"Failed to incr {namespaced_key}: {e}")
                return 0
        return 0
        
    async def decr(self, key: str, user_id: Optional[str] = None) -> int:
        """Decrement key value with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        client = await self._manager.get_client()
        if client:
            try:
                return await client.decr(namespaced_key)
            except Exception as e:
                logger.warning(f"Failed to decr {namespaced_key}: {e}")
                return 0
        return 0
        
    async def lpush(self, key: str, *values, **kwargs) -> int:
        """Push items to left side of list with optional user namespacing."""
        user_id = kwargs.get('user_id')
        namespaced_key = self._namespace_key(user_id, key)
        return await self._manager.lpush(namespaced_key, *values)
        
    async def rpush(self, key: str, *values, **kwargs) -> int:
        """Push items to right side of list with optional user namespacing."""
        user_id = kwargs.get('user_id')
        namespaced_key = self._namespace_key(user_id, key)
        client = await self._manager.get_client()
        if client:
            try:
                return await client.rpush(namespaced_key, *values)
            except Exception as e:
                logger.warning(f"Failed to rpush to {namespaced_key}: {e}")
                return 0
        return 0
        
    async def lpop(self, key: str, user_id: Optional[str] = None) -> Optional[str]:
        """Pop item from left side of list with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        return await self._manager.lpop(namespaced_key)
        
    async def rpop(self, key: str, user_id: Optional[str] = None) -> Optional[str]:
        """Pop item from right side of list with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        return await self._manager.rpop(namespaced_key)
        
    async def llen(self, key: str, user_id: Optional[str] = None) -> int:
        """Get length of list with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        return await self._manager.llen(namespaced_key)
        
    async def lrange(self, key: str, start: int, end: int, user_id: Optional[str] = None) -> List[str]:
        """Get range of items from list with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        client = await self._manager.get_client()
        if client:
            try:
                return await client.lrange(namespaced_key, start, end)
            except Exception as e:
                logger.warning(f"Failed to lrange {namespaced_key}: {e}")
                return []
        return []
        
    async def sadd(self, key: str, *members, **kwargs) -> int:
        """Add members to set with optional user namespacing."""
        user_id = kwargs.get('user_id')
        namespaced_key = self._namespace_key(user_id, key)
        client = await self._manager.get_client()
        if client:
            try:
                return await client.sadd(namespaced_key, *members)
            except Exception as e:
                logger.warning(f"Failed to sadd to {namespaced_key}: {e}")
                return 0
        return 0
        
    async def srem(self, key: str, *members, **kwargs) -> int:
        """Remove members from set with optional user namespacing."""
        user_id = kwargs.get('user_id')
        namespaced_key = self._namespace_key(user_id, key)
        client = await self._manager.get_client()
        if client:
            try:
                return await client.srem(namespaced_key, *members)
            except Exception as e:
                logger.warning(f"Failed to srem from {namespaced_key}: {e}")
                return 0
        return 0
        
    async def smembers(self, key: str, user_id: Optional[str] = None) -> List[str]:
        """Get all members of set with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        client = await self._manager.get_client()
        if client:
            try:
                members = await client.smembers(namespaced_key)
                return [m.decode() if isinstance(m, bytes) else m for m in members]
            except Exception as e:
                logger.warning(f"Failed to smembers {namespaced_key}: {e}")
                return []
        return []
        
    async def hset(self, key: str, field_or_mapping: Union[str, Dict[str, Any]], value: Optional[str] = None, user_id: Optional[str] = None) -> int:
        """Set hash field(s) with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        return await self._manager.hset(namespaced_key, field_or_mapping, value)
        
    async def hget(self, key: str, field: str, user_id: Optional[str] = None) -> Optional[str]:
        """Get hash field value with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        return await self._manager.hget(namespaced_key, field)
        
    async def hgetall(self, key: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all hash fields and values with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        return await self._manager.hgetall(namespaced_key)
        
    async def ttl(self, key: str, user_id: Optional[str] = None) -> int:
        """Get time to live for key with optional user namespacing."""
        namespaced_key = self._namespace_key(user_id, key)
        return await self._manager.ttl(namespaced_key)
    
    # Compatibility aliases for tests
    async def initialize(self):
        """Initialize Redis service (alias for connect)."""
        await self.connect()
        
    async def shutdown(self):
        """Shutdown Redis service (alias for disconnect)."""
        await self.disconnect()


# Global Redis service instance
redis_service = RedisService()
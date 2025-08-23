"""Redis service for session and cache management.

Provides Redis connection and operations for auth and caching.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Fast session and cache management
3. Value Impact: Enables scalable authentication and caching
4. Revenue Impact: Critical for performance and user experience
"""

import json
import logging
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from netra_backend.app.core.configuration import get_configuration

logger = logging.getLogger(__name__)

class RedisService:
    """Async Redis service wrapper."""
    
    def __init__(self, test_mode: bool = False):
        """Initialize Redis service."""
        self.client: Optional[redis.Redis] = None
        config = get_configuration()
        self.url = config.redis_url or f"redis://{config.redis.host}:{config.redis.port}"
        self.test_mode = test_mode
        self.test_locks: Dict[str, str] = {}  # For test mode leader locks
        
    async def connect(self):
        """Connect to Redis."""
        try:
            self.client = redis.from_url(self.url, decode_responses=True)
            await self.client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
            
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.aclose()
            self.client = None
            
    async def ping(self) -> bool:
        """Test Redis connection."""
        if not self.client:
            return False
        try:
            await self.client.ping()
            return True
        except Exception:
            return False
            
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self.client:
            return None
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None
            
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key-value pair."""
        if not self.client:
            return False
        try:
            await self.client.set(key, value, ex=ex)
            return True
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False
            
    async def setex(self, key: str, time: int, value: str) -> bool:
        """Set key-value pair with expiration."""
        if not self.client:
            return False
        try:
            await self.client.setex(key, time, value)
            return True
        except Exception as e:
            logger.error(f"Redis SETEX error: {e}")
            return False
            
    async def delete(self, *keys: str) -> int:
        """Delete keys."""
        if not self.client or not keys:
            return 0
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return 0
            
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        if not self.client:
            return []
        try:
            return await self.client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS error: {e}")
            return []
            
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.client:
            return False
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False
            
    async def expire(self, key: str, time: int) -> bool:
        """Set key expiration."""
        if not self.client:
            return False
        try:
            return bool(await self.client.expire(key, time))
        except Exception as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False
            
    async def acquire_leader_lock(self, instance_id: str, ttl: int = 30) -> bool:
        """
        Acquire distributed leader lock to prevent split-brain.
        
        Args:
            instance_id: Unique instance identifier
            ttl: Lock time-to-live in seconds
            
        Returns:
            True if lock acquired, False otherwise
        """
        # Test mode - simulate lock behavior without Redis
        if self.test_mode:
            lock_key = "leader_lock"
            
            if lock_key not in self.test_locks:
                # No one has the lock, acquire it
                self.test_locks[lock_key] = instance_id
                logger.info(f"Leader lock acquired by {instance_id} (test mode)")
                return True
            else:
                # Someone else has the lock
                current_leader = self.test_locks[lock_key]
                logger.debug(f"Leader lock held by {current_leader}, {instance_id} failed to acquire (test mode)")
                return False
        
        # Normal mode - actual Redis
        if not self.client:
            return False
            
        lock_key = "leader_lock"
        
        try:
            # Use SET with NX (only if not exists) and EX (expiration)
            result = await self.client.set(
                lock_key, 
                instance_id, 
                nx=True,  # Only set if key doesn't exist
                ex=ttl    # Set expiration time
            )
            
            if result:
                logger.info(f"Leader lock acquired by {instance_id}")
                return True
            else:
                current_leader = await self.client.get(lock_key)
                logger.debug(f"Leader lock held by {current_leader}, {instance_id} failed to acquire")
                return False
                
        except Exception as e:
            logger.error(f"Redis leader lock error: {e}")
            return False
            
    async def release_leader_lock(self, instance_id: str) -> bool:
        """
        Release leader lock if held by this instance.
        
        Args:
            instance_id: Instance identifier that should hold the lock
            
        Returns:
            True if lock released, False otherwise
        """
        # Test mode - simulate lock behavior without Redis
        if self.test_mode:
            lock_key = "leader_lock"
            
            if lock_key in self.test_locks and self.test_locks[lock_key] == instance_id:
                del self.test_locks[lock_key]
                logger.info(f"Leader lock released by {instance_id} (test mode)")
                return True
            else:
                logger.warning(f"Lock not held by {instance_id}, cannot release (test mode)")
                return False
        
        # Normal mode - actual Redis
        if not self.client:
            return False
            
        lock_key = "leader_lock"
        
        try:
            # Lua script to atomically check and release
            lua_script = """
            if redis.call("GET", KEYS[1]) == ARGV[1] then
                return redis.call("DEL", KEYS[1])
            else
                return 0
            end
            """
            
            result = await self.client.eval(lua_script, 1, lock_key, instance_id)
            
            if result:
                logger.info(f"Leader lock released by {instance_id}")
                return True
            else:
                logger.warning(f"Lock not held by {instance_id}, cannot release")
                return False
                
        except Exception as e:
            logger.error(f"Redis leader lock release error: {e}")
            return False

# Global Redis service instance
redis_service = RedisService()
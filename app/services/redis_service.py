"""Redis service for session and cache management.

Provides Redis connection and operations for auth and caching.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Fast session and cache management
3. Value Impact: Enables scalable authentication and caching
4. Revenue Impact: Critical for performance and user experience
"""

import os
import redis.asyncio as redis
from typing import Optional, List, Any
import logging
import json

logger = logging.getLogger(__name__)

class RedisService:
    """Async Redis service wrapper."""
    
    def __init__(self):
        """Initialize Redis service."""
        self.client: Optional[redis.Redis] = None
        self.url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
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

# Global Redis service instance
redis_service = RedisService()
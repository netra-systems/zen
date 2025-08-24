"""
Auth Service Redis Manager - Independent Redis implementation for auth service

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Microservice independence and reliability
- Value Impact: Isolated auth service Redis operations, reduced coupling
- Strategic Impact: Enables independent scaling and deployment of auth service
"""
import os
import logging
import redis.asyncio as redis
from typing import Optional, Any

logger = logging.getLogger(__name__)


class AuthRedisManager:
    """Independent Redis manager for auth service"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = self._check_if_enabled()
        
    def _check_if_enabled(self) -> bool:
        """Check if Redis is enabled for auth service"""
        redis_url = os.getenv("REDIS_URL")
        return bool(redis_url and redis_url != "disabled")
    
    async def initialize(self) -> None:
        """Initialize Redis connection for auth service"""
        if not self.enabled:
            logger.info("Redis disabled for auth service")
            return
            
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Auth service Redis connection initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Redis for auth service: {e}")
            self.enabled = False
            self.redis_client = None
    
    def connect(self) -> bool:
        """Synchronous connect method for compatibility with session manager"""
        try:
            # For synchronous compatibility, just check if we're enabled
            # Actual connection will be established on first use
            return self.enabled
        except Exception as e:
            logger.warning(f"Redis connection check failed: {e}")
            return False
    
    async def async_connect(self) -> None:
        """Connect to Redis - async version"""
        await self.initialize()
    
    def get_client(self) -> Optional[redis.Redis]:
        """Get Redis client instance"""
        return self.redis_client
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        if not self.redis_client:
            return None
            
        try:
            return await self.redis_client.get(key)
        except Exception as e:
            logger.warning(f"Redis GET failed for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration"""
        if not self.redis_client:
            return False
            
        try:
            await self.redis_client.set(key, value, ex=ex)
            return True
        except Exception as e:
            logger.warning(f"Redis SET failed for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.redis_client:
            return False
            
        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Redis DELETE failed for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self.redis_client:
            return False
            
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Redis EXISTS check failed for key {key}: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for a key"""
        if not self.redis_client:
            return False
            
        try:
            return await self.redis_client.expire(key, seconds)
        except Exception as e:
            logger.warning(f"Redis EXPIRE failed for key {key}: {e}")
            return False
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Auth service Redis connection closed")
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
            finally:
                self.redis_client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        return self.enabled and self.redis_client is not None


# Global instance for auth service
auth_redis_manager = AuthRedisManager()
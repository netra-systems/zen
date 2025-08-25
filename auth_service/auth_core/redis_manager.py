"""
Auth Service Redis Manager - Delegates to shared redis_manager when possible

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Microservice independence with unified Redis management
- Value Impact: Consistent Redis operations across services
- Strategic Impact: Enables independent deployment while sharing Redis infrastructure
"""
import os
import logging
import redis.asyncio as redis
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Try to import shared redis manager for non-auth contexts
try:
    from netra_backend.app.redis_manager import redis_manager as shared_redis_manager
    SHARED_MANAGER_AVAILABLE = True
except ImportError:
    shared_redis_manager = None
    SHARED_MANAGER_AVAILABLE = False


class AuthRedisManager:
    """Redis manager for auth service - delegates to shared manager when available"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = self._check_if_enabled()
        self._is_auth_service_context = self._detect_auth_service_context()
        
    def _detect_auth_service_context(self) -> bool:
        """Detect if we're running in auth service context"""
        # Check if we're in auth_service directory or process
        import sys
        for path in sys.path:
            if 'auth_service' in path:
                return True
        return 'auth_service' in os.getcwd()
        
    def _check_if_enabled(self) -> bool:
        """Check if Redis is enabled for auth service"""
        redis_url = os.getenv("REDIS_URL")
        return bool(redis_url and redis_url != "disabled")
    
    async def initialize(self) -> None:
        """Initialize Redis connection for auth service"""
        if not self.enabled:
            logger.info("Redis disabled for auth service")
            return
            
        # If we're not in auth service context and shared manager is available, delegate
        if not self._is_auth_service_context and SHARED_MANAGER_AVAILABLE:
            logger.info("Using shared redis manager for auth operations")
            await shared_redis_manager.initialize()
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
        # If using shared manager, delegate
        if not self._is_auth_service_context and SHARED_MANAGER_AVAILABLE:
            return shared_redis_manager.redis_client
        return self.redis_client
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        # If using shared manager, delegate
        if not self._is_auth_service_context and SHARED_MANAGER_AVAILABLE:
            return await shared_redis_manager.get(key)
            
        if not self.redis_client:
            return None
            
        try:
            return await self.redis_client.get(key)
        except Exception as e:
            logger.warning(f"Redis GET failed for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration"""
        # If using shared manager, delegate
        if not self._is_auth_service_context and SHARED_MANAGER_AVAILABLE:
            result = await shared_redis_manager.set(key, value, ex=ex)
            return result is not None
            
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
        # If using shared manager, delegate
        if not self._is_auth_service_context and SHARED_MANAGER_AVAILABLE:
            result = await shared_redis_manager.delete(key)
            return result > 0
            
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
        # If using shared manager, delegate
        if not self._is_auth_service_context and SHARED_MANAGER_AVAILABLE:
            return await shared_redis_manager.exists(key)
            
        if not self.redis_client:
            return False
            
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Redis EXISTS check failed for key {key}: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for a key"""
        # If using shared manager, delegate
        if not self._is_auth_service_context and SHARED_MANAGER_AVAILABLE:
            return await shared_redis_manager.expire(key, seconds)
            
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
        # If using shared manager, check its availability
        if not self._is_auth_service_context and SHARED_MANAGER_AVAILABLE:
            return shared_redis_manager.enabled and shared_redis_manager.redis_client is not None
        return self.enabled and self.redis_client is not None


# Global instance for auth service
auth_redis_manager = AuthRedisManager()
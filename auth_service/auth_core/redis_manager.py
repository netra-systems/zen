"""
Auth Service Redis Manager - Independent Redis management for auth service

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Complete microservice independence 
- Value Impact: Enables auth service to operate independently
- Strategic Impact: Removes circular dependencies and enables independent deployment

CRITICAL: This is a completely independent Redis manager. NEVER import from netra_backend.
This ensures 100% microservice independence as required by architecture principles.
"""
import os
import logging
import asyncio
import redis.asyncio as redis
from typing import Optional, Any
from auth_service.auth_core.isolated_environment import get_env

logger = logging.getLogger(__name__)


class AuthRedisManager:
    """Completely independent Redis manager for auth service"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = True  # Will be set properly in initialize()
        
    def _check_if_enabled(self) -> bool:
        """Check if Redis is enabled for auth service"""
        # Check for explicit disable flags first
        if get_env().get("DISABLE_REDIS", "false").lower() == "true":
            return False
        
        # Check for test disable flags (for consistent test behavior)
        if get_env().get("TEST_DISABLE_REDIS", "false").lower() == "true":
            return False
        
        redis_url = get_env().get("REDIS_URL")
        if redis_url == "disabled":
            return False
            
        # For staging/production, we need more validation in initialize()
        # Just return True here to allow initialize() to do full checks
        return True
    
    async def initialize(self) -> None:
        """Initialize Redis connection for auth service"""
        # Re-check if Redis should be enabled
        self.enabled = self._check_if_enabled()
        if not self.enabled:
            logger.info("Redis disabled for auth service")
            return
            
        try:
            env = get_env().get("ENVIRONMENT", "development").lower()
            redis_url = get_env().get("REDIS_URL")
            
            # CRITICAL: Prevent localhost fallback in staging/production
            if not redis_url:
                if env in ["staging", "production"]:
                    # Check if Redis is required
                    redis_required = get_env().get("REDIS_REQUIRED", "false").lower() == "true"
                    if redis_required:
                        raise ValueError(f"REDIS_URL must be configured in {env} environment (REDIS_REQUIRED=true)")
                    else:
                        logger.warning(f"Redis not configured in {env} environment, disabling Redis support")
                        self.enabled = False
                        return
                else:
                    # Only allow localhost fallback in development
                    redis_url = "redis://localhost:6379"
                    logger.info("Using localhost Redis fallback for development environment")
            
            # Validate Redis URL doesn't contain localhost in staging/production
            if env in ["staging", "production"] and "localhost" in redis_url.lower():
                redis_fallback_enabled = get_env().get("REDIS_FALLBACK_ENABLED", "false").lower() == "true"
                if not redis_fallback_enabled:
                    raise ValueError(f"Localhost Redis URL not allowed in {env} environment (REDIS_FALLBACK_ENABLED=false)")
                logger.warning(f"Using localhost Redis in {env} - this should only be for testing!")
            
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection with timeout
            try:
                await asyncio.wait_for(self.redis_client.ping(), timeout=10)
                logger.info(f"Auth service Redis connection initialized successfully to {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
            except asyncio.TimeoutError:
                raise TimeoutError(f"Redis connection timeout after 10 seconds to {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
            
        except Exception as e:
            env = get_env().get("ENVIRONMENT", "development").lower()
            redis_required = get_env().get("REDIS_REQUIRED", "false").lower() == "true"
            
            if env in ["staging", "production"] and redis_required:
                # In staging/production with REDIS_REQUIRED=true, fail hard
                logger.error(f"Critical: Failed to initialize Redis in {env} environment: {e}")
                raise
            else:
                # In development or when Redis not required, allow graceful degradation
                logger.warning(f"Failed to initialize Redis for auth service: {e}")
                logger.warning(f"Redis disabled - running without Redis support (environment={env}, required={redis_required})")
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
                await self.redis_client.aclose()
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
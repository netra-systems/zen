import redis.asyncio as redis
from app.config import settings
from app.logging_config import central_logger as logger


class RedisManager:
    def __init__(self):
        self.redis_client = None
        self.enabled = self._check_if_enabled()

    def _check_if_enabled(self):
        """Check if Redis should be enabled based on service mode configuration."""
        import os
        
        # Check for test-specific disable flag
        if os.environ.get("TEST_DISABLE_REDIS", "").lower() == "true":
            logger.info("Redis is disabled for testing")
            return False
        
        # Check service mode from environment (set by dev launcher)
        redis_mode = os.environ.get("REDIS_MODE", "shared").lower()
        
        if redis_mode == "disabled":
            logger.info("Redis is disabled (mode: disabled)")
            return False
        elif redis_mode == "mock":
            logger.info("Redis is running in mock mode")
            # Still return True but the connection will use mock
            return True
            
        if settings.environment == "development":
            enabled = settings.dev_mode_redis_enabled
            if not enabled:
                logger.info("Redis is disabled in development configuration")
            return enabled
        # Redis is always enabled in production and testing
        return True

    async def connect(self):
        if not self.enabled:
            logger.info("Redis connection skipped - service is disabled in development mode")
            return
            
        try:
            self.redis_client = redis.Redis(
                host=settings.redis.host,
                port=settings.redis.port,
                decode_responses=True,
                username=settings.redis.username,
                password=settings.redis.password,
                socket_connect_timeout=10,  # 10 second connection timeout
                socket_timeout=5,  # 5 second socket timeout
            )
            await self.redis_client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Service will operate without Redis.")
            self.redis_client = None

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()

    async def get_client(self):
        """Get the Redis client instance. Returns None if not connected or disabled."""
        # Ensure we never return self, only the actual redis client or None
        if self.redis_client and hasattr(self.redis_client, 'get'):
            return self.redis_client
        return None
    
    async def get(self, key: str):
        """Get a value from Redis"""
        if self.redis_client:
            return await self.redis_client.get(key)
        return None
    
    async def set(self, key: str, value: str, ex: int = None, expire: int = None):
        """Set a value in Redis with optional expiration"""
        if self.redis_client:
            # Support both 'ex' and 'expire' for backward compatibility
            expiration = ex or expire
            return await self.redis_client.set(key, value, ex=expiration)
        return None
    
    async def delete(self, key: str):
        """Delete a key from Redis"""
        if self.redis_client:
            return await self.redis_client.delete(key)
        return None

redis_manager = RedisManager()

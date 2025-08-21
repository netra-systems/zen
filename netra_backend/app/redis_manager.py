import redis.asyncio as redis
from app.config import settings
from app.logging_config import central_logger as logger


class RedisManager:
    def __init__(self):
        self.redis_client = None
        self.enabled = self._check_if_enabled()

    def _is_redis_disabled_by_flag(self) -> bool:
        """Check if Redis is disabled by operational flag."""
        import os
        if os.environ.get("DISABLE_REDIS", "").lower() == "true":
            logger.info("Redis is disabled by configuration")
            return True
        return False

    def _get_redis_mode(self) -> str:
        """Get Redis mode from environment."""
        import os
        return os.environ.get("REDIS_MODE", "shared").lower()

    def _handle_redis_mode(self, redis_mode: str):
        """Handle Redis mode logic."""
        if redis_mode == "disabled":
            logger.info("Redis is disabled (mode: disabled)")
            return False
        elif redis_mode == "standalone":
            logger.info("Redis is running in standalone mode")
            return True
        return None

    def _check_development_redis(self) -> bool:
        """Check Redis availability in development mode."""
        if settings.environment == "development":
            enabled = settings.dev_mode_redis_enabled
            if not enabled:
                logger.info("Redis is disabled in development configuration")
            return enabled
        return True

    def _check_if_enabled(self):
        """Determine Redis service availability based on environment configuration."""
        if self._is_redis_disabled_by_flag():
            return False
        return self._check_redis_mode_and_development()

    def _check_redis_mode_and_development(self):
        """Check Redis mode and development settings."""
        redis_mode = self._get_redis_mode()
        mode_result = self._handle_redis_mode(redis_mode)
        if mode_result is not None:
            return mode_result
        return self._check_development_redis()

    def _create_redis_client(self):
        """Create Redis client with configuration."""
        return redis.Redis(
            host=settings.redis.host, port=settings.redis.port,
            decode_responses=True, username=settings.redis.username,
            password=settings.redis.password, socket_connect_timeout=10, socket_timeout=5
        )

    async def _test_redis_connection(self):
        """Test Redis connection."""
        await self.redis_client.ping()
        logger.info("Redis connected successfully")

    def _handle_connection_error(self, error: Exception):
        """Handle Redis connection errors."""
        logger.warning(f"Redis connection failed: {error}. Service will operate without Redis.")
        self.redis_client = None

    async def connect(self):
        """Connect to Redis if enabled."""
        if not self.enabled:
            logger.info("Redis connection skipped - service is disabled in development mode")
            return
            
        try:
            self.redis_client = self._create_redis_client()
            await self._test_redis_connection()
        except Exception as e:
            self._handle_connection_error(e)

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

    def _calculate_list_range(self, limit: int) -> int:
        """Calculate list range end index."""
        return limit - 1 if limit else -1

    async def _fetch_list_items(self, key: str, limit: int):
        """Fetch list items from Redis."""
        end_index = self._calculate_list_range(limit)
        return await self.redis_client.lrange(key, 0, end_index)

    async def get_list(self, key: str, limit: int = None):
        """Get list items from Redis"""
        if self.redis_client:
            return await self._get_list_with_error_handling(key, limit)
        return []

    async def _get_list_with_error_handling(self, key: str, limit: int):
        """Get list with error handling."""
        try:
            return await self._fetch_list_items(key, limit)
        except Exception as e:
            logger.warning(f"Failed to get list {key}: {e}")
            return []

    async def _push_and_trim_list(self, key: str, value: str, max_size: int):
        """Push item and trim list if needed."""
        await self.redis_client.lpush(key, value)
        if max_size:
            await self.redis_client.ltrim(key, 0, max_size - 1)

    async def add_to_list(self, key: str, value: str, max_size: int = None):
        """Add item to Redis list with optional size limit"""
        if self.redis_client:
            try:
                await self._push_and_trim_list(key, value, max_size)
                return True
            except Exception as e:
                logger.warning(f"Failed to add to list {key}: {e}")
                return False
        return False

redis_manager = RedisManager()

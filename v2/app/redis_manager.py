import redis.asyncio as redis
from app.config import settings

class RedisManager:
    def __init__(self):
        self.redis_client = None

    async def connect(self):
        self.redis_client = redis.Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            decode_responses=True,
            username=settings.redis.username,
            password=settings.redis.password,
        )
        await self.redis_client.ping()

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()

    async def get_client(self):
        """Get the Redis client instance. Returns None if not connected."""
        # Ensure we never return self, only the actual redis client or None
        if self.redis_client and hasattr(self.redis_client, 'get'):
            return self.redis_client
        return None
    
    async def get(self, key: str):
        """Get a value from Redis"""
        if self.redis_client:
            return await self.redis_client.get(key)
        return None
    
    async def set(self, key: str, value: str, ex: int = None):
        """Set a value in Redis with optional expiration"""
        if self.redis_client:
            return await self.redis_client.set(key, value, ex=ex)
        return None

redis_manager = RedisManager()

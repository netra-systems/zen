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
        return self.redis_client
    
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

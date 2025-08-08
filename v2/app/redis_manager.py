import redis.asyncio as redis
from app.config import settings

class RedisManager:
    def __init__(self):
        self.redis_client = None

    async def connect(self):
        self.redis_client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        await self.redis_client.ping()

    async def disconnect(self):
        await self.redis_client.close()

    async def get_client(self):
        return self.redis_client

redis_manager = RedisManager()
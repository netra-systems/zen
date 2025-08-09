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

redis_manager = RedisManager()

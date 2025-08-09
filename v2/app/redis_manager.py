import redis.asyncio as redis
from app.config import settings

class RedisManager:
    def __init__(self):
        self.redis_client = None

    async def connect(self):
        self.redis_client = redis.Redis(
            host='redis-10504.fcrce190.us-east-1-1.ec2.redns.redis-cloud.com',
            port=10504,
            decode_responses=True,
            username="default",
            password=settings.redis_password,
        )
        await self.redis_client.ping()

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()

    async def get_client(self):
        return self.redis_client

redis_manager = RedisManager()
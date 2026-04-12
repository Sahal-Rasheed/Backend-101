from redis.asyncio import Redis, ConnectionPool

from app.core.config import settings


class RedisClient:
    def __init__(self):
        self.pool = ConnectionPool.from_url(settings.REDIS_URL)
        self.client = None

    async def connect(self):
        if self.client is None:
            self.client = Redis(connection_pool=self.pool, decode_responses=True)
        if not await self.client.ping():
            raise ConnectionError(f"Failed to connect to Redis at {settings.REDIS_URL}")

    async def close(self):
        if self.client is not None:
            await self.client.aclose()
            self.client = None


redis_client = RedisClient()

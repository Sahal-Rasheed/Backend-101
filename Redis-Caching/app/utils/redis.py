import orjson  # > for faster JSON serialization/deserialization than json module
from typing import Any

from app.core.redis import redis_client as redis


class CacheService:
    async def get(self, key: str) -> Any | None:
        data_json = await redis.client.get(key)
        if data_json is None:
            return None
        return orjson.loads(data_json)

    async def set(self, key: str, value: Any, expire: int = 60) -> None:
        await redis.client.set(key, orjson.dumps(value), ex=expire)

    async def delete(self, key: str) -> None:
        await redis.client.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        async for key in redis.client.scan_iter(pattern):
            await redis.client.delete(key)


cache = CacheService()

import orjson  # > for faster JSON serialization/deserialization than json module
from typing import Any

from app.core.redis import redis_client as redis


class RedisService:
    def get(self, key: str) -> Any | None:
        data_json = redis.client.get(key)
        if data_json is None:
            return None
        return orjson.loads(data_json)

    def set(self, key: str, value: Any, expire: int = 60) -> None:
        redis.client.set(key, orjson.dumps(value), ex=expire)

    def delete(self, key: str) -> None:
        redis.client.delete(key)

    def delete_pattern(self, pattern: str) -> None:
        for key in redis.client.scan_iter(pattern):
            redis.client.delete(key)

    def acquire_lock(self, lock_key: str, timeout: int = 10) -> bool:
        return redis.client.set(lock_key, "1", ex=timeout, nx=True)


redis_service = RedisService()

import time

from app.core.redis import redis_client as redis
from app.rate_limiter.base import BaseRateLimiter
from app.rate_limiter.schemas import FixedWindowRateLimitConfig, RateLimitResult


class FixedWindowRateLimiter(BaseRateLimiter):
    def __init__(
        self, config: FixedWindowRateLimitConfig = FixedWindowRateLimitConfig()
    ):
        self.limit = config.limit
        self.window = config.window

    async def allow_request(self, key: str) -> RateLimitResult:
        current = await redis.client.incr(key)

        if current == 1:
            await redis.client.expire(key, self.window)

        ttl = await redis.client.ttl(key)
        ttl = ttl if ttl > 0 else self.window

        remaining = max(self.limit - current, 0)

        return RateLimitResult(
            allowed=current <= self.limit,
            remaining=remaining,
            reset_at=int(time.time()) + ttl,
        )

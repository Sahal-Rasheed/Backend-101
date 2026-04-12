import time
import uuid

from app.core.redis import redis_client as redis
from app.rate_limiter.base import BaseRateLimiter
from app.rate_limiter.schemas import SlidingWindowRateLimitConfig, RateLimitResult


class SlidingWindowRateLimiter(BaseRateLimiter):
    def __init__(
        self, config: SlidingWindowRateLimitConfig = SlidingWindowRateLimitConfig()
    ):
        self.limit = config.limit
        self.window = config.window

    async def allow_request(self, key: str) -> RateLimitResult:
        now = int(time.time() * 1000)
        window_ms = self.window * 1000
        window_start = now - window_ms

        # remove old timestamps outside the window
        await redis.client.zremrangebyscore(key, 0, window_start)

        # add current timestamp as a unique member
        member = f"{now}-{uuid.uuid4()}"
        await redis.client.zadd(key, {member: now})

        # get the count of requests in the current window
        current = await redis.client.zcard(key)

        # set expiration in ms for the new member
        await redis.client.pexpire(key, window_ms)

        # get the oldest timestamp in the current window to calculate reset time
        oldest = await redis.client.zrange(key, 0, 0, withscores=True)
        oldest_score = oldest[0][1] if oldest else now

        remaining = max(self.limit - current, 0)
        reset_at = int((oldest_score + window_ms) / 1000)

        return RateLimitResult(
            allowed=current <= self.limit,
            remaining=remaining,
            reset_at=reset_at,
        )

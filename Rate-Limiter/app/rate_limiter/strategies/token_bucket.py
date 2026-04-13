import time
import math

from app.core.redis import redis_client as redis
from app.rate_limiter.base import BaseRateLimiter
from app.rate_limiter.schemas import TokenBucketRateLimitConfig, RateLimitResult


class TokenBucketRateLimiter(BaseRateLimiter):
    def __init__(self, config: TokenBucketRateLimitConfig | None = None):
        config = config or TokenBucketRateLimitConfig()
        self.capacity = config.capacity
        self.refill_rate = config.refill_rate

    async def allow_request(self, key: str) -> RateLimitResult:
        now = int(time.time() * 1000)
        state = await redis.client.hgetall(key)

        prev_tokens = float(state.get("tokens", self.capacity))
        last_refill = int(state.get("last_refill", now))

        elapsed = max((now - last_refill) / 1000, 0)
        new_tokens = min(self.capacity, prev_tokens + elapsed * self.refill_rate)

        allowed = new_tokens >= 1
        token_after_request = new_tokens - 1 if allowed else new_tokens
        remaining = max(int(token_after_request), 0)

        time_until_next_token = (
            0
            if token_after_request >= 0
            else math.ceil(((1 - token_after_request) / self.refill_rate) * 1000)
        )

        reset_at = int(now + time_until_next_token)

        await redis.client.hset(
            key,
            mapping={
                "tokens": token_after_request,
                "last_refill": now,
            },
        )
        ttl = max(int((self.capacity / self.refill_rate) * 2), 1)
        await redis.client.expire(key, ttl)

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_at=reset_at,
        )

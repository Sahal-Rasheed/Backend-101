import time

from app.core.redis import redis_client as redis
from app.rate_limiter.base import BaseRateLimiter
from app.rate_limiter.schemas import TokenBucketRateLimitConfig, RateLimitResult


class TokenBucketRateLimiter(BaseRateLimiter):
    """
    Token Bucket Rate Limiting:
    - Maintains a "bucket" that fills with tokens at a constant rate (refill_rate) up to a maximum capacity (capacity) over time.
    - Each request consumes one token from the bucket. If the bucket is empty (no tokens), the request is rejected.
    - Tokens are added to the bucket at a steady rate, allowing for bursts of traffic up to the capacity, while enforcing an average rate over time.
    - More flexible than fixed or sliding window, as it allows for bursts while still enforcing an overall rate limit.
    - Suitable for scenarios where you want to allow short bursts of traffic but still enforce a long-term average rate limit, such as API rate limiting or controlling access to resources.
    - Uses Redis hash to store the current token count and last refill time, and updates them on each request.
    """

    def __init__(self, config: TokenBucketRateLimitConfig | None = None):
        config = config or TokenBucketRateLimitConfig()
        self.capacity = config.capacity
        self.refill_rate = config.refill_rate
        self.token_bucket_script = redis.client.register_script(
            """
            local key = KEYS[1]

            local now = tonumber(ARGV[1])
            local capacity = tonumber(ARGV[2])
            local refill_rate = tonumber(ARGV[3])

            -- fetch current state
            local data = redis.call("HMGET", key, "tokens", "last_refill")

            local tokens = tonumber(data[1])
            local last_refill = tonumber(data[2])

            -- defaults
            if tokens == nil then
                tokens = capacity
            end

            if last_refill == nil then
                last_refill = now
            end

            -- refill logic
            local elapsed = (now - last_refill) / 1000
            tokens = math.min(capacity, tokens + elapsed * refill_rate)

            local allowed = 0

            if tokens >= 1 then
                tokens = tokens - 1
                allowed = 1
            end

            -- update state
            redis.call("HSET", key,
                "tokens", tokens,
                "last_refill", now
            )

            -- cleanup stale keys
            redis.call("EXPIRE", key, math.ceil(capacity / refill_rate) * 2)

            return {allowed, tokens}
            """
        )

    # non atomic approach for token bucket rate limiting
    async def allow_request(self, key: str) -> RateLimitResult:
        now = int(time.time() * 1000)
        state = await redis.client.hgetall(key)

        # get current tokens and last refill time since last update
        tokens = float(state.get("tokens", self.capacity))
        last_refill = int(state.get("last_refill", now))

        # how many seconds have passed since last refill
        elapsed = max((now - last_refill) / 1000, 0)

        # tokens generated during elapsed time
        new_tokens = elapsed * self.refill_rate

        # add new tokens to the bucket, ensuring it doesn't exceed capacity or max cap
        tokens = min(self.capacity, tokens + new_tokens)

        # check if we have enough tokens for the request
        # if tokens >= 1, allow request and consume 1 token, else reject request
        allowed = tokens >= 1
        tokens = tokens - 1 if allowed else tokens

        # update bucket state
        await redis.client.hset(
            key,
            mapping={
                "tokens": tokens,  # current bucket level
                "last_refill": now,  # timestamp of last token refill
            },
        )

        # set expiration for the key to avoid stale data,
        # as if the key is not accessed for a long time it will automatically get deleted from Redis
        await redis.client.expire(key, int((self.capacity / self.refill_rate) * 2))

        remaining = max(int(tokens), 0)

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_at=None,  # token bucket has no fixed reset
        )

    # atomic approach for token bucket rate limiting using Lua script
    # async def allow_request(self, key: str) -> RateLimitResult:
    #     now = int(time.time() * 1000)

    #     allowed, tokens = await self.token_bucket_script(
    #         keys=[key],
    #         args=[
    #             now,
    #             self.capacity,
    #             self.refill_rate,
    #         ],
    #     )

    #     remaining = max(int(tokens), 0)

    #     return RateLimitResult(
    #         allowed=bool(allowed),
    #         remaining=remaining,
    #         reset_at=None,  # token bucket has no fixed reset
    #     )

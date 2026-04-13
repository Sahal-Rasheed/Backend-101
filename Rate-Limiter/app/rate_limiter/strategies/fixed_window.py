import time

from app.core.redis import redis_client as redis
from app.rate_limiter.base import BaseRateLimiter
from app.rate_limiter.schemas import FixedWindowRateLimitConfig, RateLimitResult


class FixedWindowRateLimiter(BaseRateLimiter):
    """
    Fixed Window Rate Limiting:
    - Divide time into fixed intervals (windows) and allow up to N (limit) requests per window.
    - Counts requests in fixed time intervals (windows) and resets counts at the end of each window.
    - Simple to implement but can lead to burstiness at window boundaries.
    - Uses Redis INCR and EXPIRE to track counts and reset windows.
    - Suitable for basic rate limiting needs where strict accuracy is not critical.
    """

    def __init__(
        self, config: FixedWindowRateLimitConfig = FixedWindowRateLimitConfig()
    ):
        self.limit = config.limit
        self.window = config.window

    async def allow_request(self, key: str) -> RateLimitResult:
        # INCR + EXPIRE approach for fixed window counting (not atomic altogether)
        current = await redis.client.incr(key)
        if current == 1:
            await redis.client.expire(key, self.window)

        # LUA script based INCR + EXPIRE approach for fixed window counting (atomic altogether)
        # incr_expire_script = redis.client.register_script(
        #     """
        #     local current = redis.call("INCR", KEYS[1])
        #     if current == 1 then
        #         redis.call("EXPIRE", KEYS[1], ARGV[1])
        #     end
        #     return current
        #     """
        # )
        # current = await incr_expire_script(keys=[key], args=[self.window])

        ttl = await redis.client.ttl(key)
        ttl = ttl if ttl > 0 else self.window

        remaining = max(self.limit - current, 0)

        return RateLimitResult(
            allowed=current <= self.limit,
            remaining=remaining,
            reset_at=int(time.time()) + ttl,
        )


## Note on thread-safety and atomicity:
# - The `INCR + EXPIRE` approach is simple and works well for many use cases, but it has a potential issue:
# - if the process crashes after INCR but before EXPIRE, the key will never expire, leading to a "leaked" key that stays in Redis indefinitely. This can cause memory issues over time if many keys are leaked.
# - Even though logic is thread-safe because Redis is single-threaded (only one request gets current == 1).
# - However, it is not atomic. Atomic in db terms means all operations succeed or fail together.
# - Here INCR and EXPIRE are two separate o/p calls. We need to execute them together atomically to ensure that if one succeeds, the other does too.
# - If the process crashes after INCR but before EXPIRE, the key will leak (stay in Redis forever).
# - Use Lua to wrap these into a single, indivisible operation to execute them together atomically. This way, if the process crashes during execution, either both operations succeed or neither does, preventing leaks and ensuring consistent state.

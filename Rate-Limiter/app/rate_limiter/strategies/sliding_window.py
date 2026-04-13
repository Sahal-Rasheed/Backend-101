import time
import uuid

from app.core.redis import redis_client as redis
from app.rate_limiter.base import BaseRateLimiter
from app.rate_limiter.schemas import SlidingWindowRateLimitConfig, RateLimitResult


class SlidingWindowRateLimiter(BaseRateLimiter):
    """
    Sliding Window Rate Limiting:
    - Allows up to N (limit) requests in any continuous time window of size W (window).
    - Uses a sorted set in Redis to store each request (member) and its timestamp as the (score).
    - On each request, it removes timestamps outside the current window and counts the remaining ones.
    - More accurate than fixed window, as it allows a "sliding" view of the request history.
    - Handles burstiness better, as it doesn't reset counts at fixed intervals.
    - Suitable for scenarios where more precise rate limiting is required, but may have higher overhead due to managing sorted sets and timestamps.
    """

    def __init__(self, config: SlidingWindowRateLimitConfig | None = None):
        config = config or SlidingWindowRateLimitConfig()
        self.limit = config.limit
        self.window = config.window
        self.sliding_window_script = redis.client.register_script(
            """
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local window = tonumber(ARGV[2])
            local limit = tonumber(ARGV[3])
            local member = ARGV[4]

            local window_start = now - window

            redis.call("ZREMRANGEBYSCORE", key, 0, window_start)

            local current = redis.call("ZCARD", key)

            if current < limit then
                redis.call("ZADD", key, now, member)
                redis.call("PEXPIRE", key, window)
                return {1, current + 1}
            else
                return {0, current}
            end
            """
        )

    # non atomic approach for sliding window rate limiting
    # (not atomic because of multiple related Redis calls)
    async def allow_request(self, key: str) -> RateLimitResult:
        now = int(time.time() * 1000)
        window_ms = self.window * 1000
        window_start = now - window_ms

        member = f"{now}-{uuid.uuid4()}"

        # remove old timestamps outside the window from the sorted set
        await redis.client.zremrangebyscore(key, 0, window_start)

        # count requests in the current window
        current = await redis.client.zcard(key)

        # allow or reject request based on current count and limit
        if current < self.limit:
            await redis.client.zadd(
                key, {member: now}
            )  # add current request timestamp to sorted set
            current += 1
            allowed = True
        else:
            allowed = False

        # set expiration for the key to avoid stale data,
        # as if the key is not accessed for a long time
        # it will automatically get deleted from Redis
        await redis.client.pexpire(key, window_ms)

        remaining = max(self.limit - current, 0)
        reset_at = int(time.time()) + self.window

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_at=reset_at,
        )

    # atomic approach for sliding window rate limiting using Lua script
    # (atomic because all related Redis operations are executed together in a single Lua script)
    # async def allow_request(self, key: str) -> RateLimitResult:
    #     now = int(time.time() * 1000)
    #     window_ms = self.window * 1000
    #     member = f"{now}-{uuid.uuid4()}"

    #     allowed, current = await self.sliding_window_script(
    #         keys=[key],
    #         args=[now, window_ms, self.limit, member],
    #     )

    #     remaining = max(self.limit - current, 0)

    #     reset_at = int(time.time()) + self.window

    #     return RateLimitResult(
    #         allowed=bool(allowed),
    #         remaining=remaining,
    #         reset_at=reset_at,
    #     )


## Note on thread-safety and atomicity:
# - The sliding window approach uses multiple Redis commands.
# - Each Redis command is atomic individually because Redis is single-threaded.
#   However, the overall rate-limiting logic is NOT atomic because it spans multiple commands.

# - This creates a race condition under concurrency:
#   Multiple requests can interleave between these commands and observe the same state.

# - Example race condition:
#   limit = 5, current count = 4
#   Two requests execute concurrently:
#     - Both call ZCARD and see count = 4
#     - Both decide they are allowed
#     - Both call ZADD
#   Result: count becomes 6 (limit exceeded)

# - This happens because the sequence:
#     "check count → decide → insert"
#   is not atomic.

# - Redis guarantees atomicity per command, NOT across multiple commands.

# - To solve this, we need atomic execution of the full logic:
#     remove old → count → check → insert

# - Using Redis transactions (MULTI/EXEC) does not solve this fully,
#   because they do not support conditional branching (cannot do "if count < limit then insert").

# - Using distributed locks (SET NX) can enforce correctness, but:
#   - introduces additional latency
#   - reduces concurrency (requests must wait for lock)
#   - adds complexity (lock expiry, retries, failure handling)
#   - is generally overkill for this use case

# - The recommended approach is to use a Lua script:
#   - Executes entirely inside Redis as a single atomic operation
#   - Prevents interleaving of commands
#   - Ensures correctness under concurrency
#   - Avoids lock overhead and extra network round-trips

# - Atomicity here ensures that:
#   - The check (count < limit) and the insert (ZADD) happen together
#   - No other request can modify the state in between
#   - Race conditions are eliminated for this logic

# - Note on expiration:
#   - Sliding window logic does not require key expiration for correctness
#   - Expiration (PEXPIRE) is used for memory cleanup
#   - It ensures inactive keys are eventually removed from Redis

# - Summary:
#   - Non-atomic multi-command logic → prone to race conditions
#   - Locks → correct but heavy and reduces concurrency
#   - Lua script → atomic, efficient, and preferred solution

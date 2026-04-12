from app.rate_limiter.schemas import RateLimitStrategy
from app.rate_limiter.strategies import TokenBucketRateLimiter
from app.rate_limiter.strategies import FixedWindowRateLimiter
from app.rate_limiter.strategies import SlidingWindowRateLimiter


def get_rate_limiter(strategy: RateLimitStrategy):
    if strategy == RateLimitStrategy.SLIDING_WINDOW:
        return SlidingWindowRateLimiter()

    elif strategy == RateLimitStrategy.FIXED_WINDOW:
        return FixedWindowRateLimiter()

    elif strategy == RateLimitStrategy.TOKEN_BUCKET:
        return TokenBucketRateLimiter()

    else:
        raise ValueError("Unknown strategy")

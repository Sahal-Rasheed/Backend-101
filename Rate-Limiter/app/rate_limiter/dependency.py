import time
from typing import Annotated

from fastapi import Depends, Request, Response, HTTPException

from app.rate_limiter.factory import get_rate_limiter
from app.rate_limiter.schemas import RateLimitStrategy


async def rate_limiter_dependency(
    request: Request,
    response: Response,
    strategy: RateLimitStrategy = RateLimitStrategy.FIXED_WINDOW,
    prefix: str = "global",
) -> None:
    limiter = get_rate_limiter(strategy)

    client_host = request.client.host if request.client else "unknown"
    key = f"rate_limit:{prefix}:{client_host}"

    result = await limiter.allow_request(key)

    limit_value = (
        limiter.capacity if strategy == RateLimitStrategy.TOKEN_BUCKET else limiter.limit
    )
    response.headers["X-RateLimit-Limit"] = str(limit_value)
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    response.headers["X-RateLimit-Reset"] = str(result.reset_at)

    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests",
            headers={
                "Retry-After": str(max(int(result.reset_at - time.time()), 1)),
                "X-RateLimit-Reset": str(result.reset_at),
            },
        )


rate_limiter_dep = Annotated[None, Depends(rate_limiter_dependency)]

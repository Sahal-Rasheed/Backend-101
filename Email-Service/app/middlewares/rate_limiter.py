import time
from typing import Annotated

from fastapi.exceptions import HTTPException
from fastapi import Depends, Request, Response, status

from app.utils.redis import redis_service

LIMIT = 10
WINDOW_SECONDS = 60


def rate_limiter_dependency_middleware(request: Request, response: Response):
    """
    Middleware dependency to enforce fixed window rate limiting based on tenant-id, on Email-Service endpoint.
    Rate limit is 10 requests per minute per tenant-id.
    """
    tenant_id = request.headers.get("x-tenant-id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing tenant id header"
        )

    key = f"rate_limit:{tenant_id}"
    # LUA script based INCR + EXPIRE approach for fixed window counting (atomic altogether)
    req_count = redis_service.run_lua_script(
        script="""
        local current = redis.call("INCR", KEYS[1])
        if current == 1 then
            redis.call("EXPIRE", KEYS[1], ARGV[1])
        end
        return current
        """,
        keys=[key],
        args=[WINDOW_SECONDS],
    )
    ttl = redis_service.get_ttl(key)
    ttl = ttl if ttl > 0 else WINDOW_SECONDS
    remaining = max(LIMIT - req_count, 0)
    reset_at = int(time.time()) + ttl

    response.headers["X-RateLimit-Limit"] = str(LIMIT)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_at)

    if req_count > LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too Many Requests",
            headers={
                "Retry-After": str(max(int(reset_at - time.time()), 1)),
                "X-RateLimit-Reset": str(reset_at),
            },
        )


RateLimiterDep = Annotated[None, Depends(rate_limiter_dependency_middleware)]

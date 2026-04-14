from functools import partial

from fastapi import APIRouter, Depends

from app.rate_limiter.dependency import rate_limiter_dependency
from app.rate_limiter.schemas import RateLimitStrategy

router = APIRouter(prefix="/rate-limit", tags=["rate-limit"])


@router.get("/fixed-window")
async def fixed_window_probe(
    _: None = Depends(
        partial(
            rate_limiter_dependency,
            strategy=RateLimitStrategy.FIXED_WINDOW,
            prefix="fixed-window",
        )
    ),
):
    return {"strategy": RateLimitStrategy.FIXED_WINDOW, "status": "allowed"}


@router.get("/sliding-window")
async def sliding_window_probe(
    _: None = Depends(
        partial(
            rate_limiter_dependency,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            prefix="sliding-window",
        )
    ),
):
    return {"strategy": RateLimitStrategy.SLIDING_WINDOW, "status": "allowed"}


@router.get("/token-bucket")
async def token_bucket_probe(
    _: None = Depends(
        partial(
            rate_limiter_dependency,
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            prefix="token-bucket",
        )
    ),
):
    return {"strategy": RateLimitStrategy.TOKEN_BUCKET, "status": "allowed"}


# NOTE:

# We use `functools.partial` with FastAPI dependencies to pre-bind
# configuration arguments (e.g., rate limit strategy, prefix) while
# still allowing FastAPI to inject request-scoped parameters like `Request` and `Response`.

# Why not call the dependency function directly with args inside Depends ?
# Calling the dependency (e.g., rate_limiter_dependency(...)) would
# execute it at import time and pass its result to Depends, which is incorrect.
# FastAPI expects a `callable`, not the result of a function call as a dependency as FastAPI will automatically call the dependency function.

# Why `partial`?
# `partial` returns a new `callable` with some arguments pre-filled,
# making it a concise and readable way to pass parameterized dependencies
# This makes it easy to use parameterized dependencies in FastAPI.

# When to refactor?
# If the dependency requires additional logic (logging, branching, complex configuration)
# prefer a dependency factory (wrapper function) instead of `partial` for better readability and maintainability.

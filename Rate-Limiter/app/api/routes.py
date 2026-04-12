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

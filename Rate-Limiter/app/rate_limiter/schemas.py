from enum import StrEnum

from pydantic import BaseModel, Field


class RateLimitStrategy(StrEnum):
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


class RateLimitBaseConfig(BaseModel):
    limit: int = Field(gt=0)
    window: int = Field(gt=0)


class FixedWindowRateLimitConfig(RateLimitBaseConfig):
    limit: int = Field(default=100, gt=0, description="Max requests per window")
    window: int = Field(default=60, gt=0, description="Window (time) size in seconds")


class SlidingWindowRateLimitConfig(RateLimitBaseConfig):
    limit: int = Field(default=100, gt=0, description="Max requests per window")
    window: int = Field(default=60, gt=0, description="Window (time) size in seconds")


class TokenBucketRateLimitConfig(BaseModel):
    capacity: int = Field(default=100, gt=0, description="Maximum number of tokens")
    refill_rate: int = Field(default=10, gt=0, description="Tokens added per second")


class RateLimitResult(BaseModel):
    allowed: bool
    remaining: int
    reset_at: int | None

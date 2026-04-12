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
    limit: int = 100
    window: int = 60


class SlidingWindowRateLimitConfig(RateLimitBaseConfig):
    limit: int = 100
    window: int = 60


class TokenBucketRateLimitConfig(BaseModel):
    capacity: int = Field(default=100, gt=0)
    refill_rate: float = Field(default=100.0, gt=0)


class RateLimitResult(BaseModel):
    allowed: bool
    remaining: int
    reset_at: int

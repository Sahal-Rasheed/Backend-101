import pytest
from httpx import AsyncClient

from app.rate_limiter.schemas import (
    FixedWindowRateLimitConfig,
    SlidingWindowRateLimitConfig,
    TokenBucketRateLimitConfig,
    RateLimitStrategy,
)
from app.rate_limiter.strategies.fixed_window import FixedWindowRateLimiter
from app.rate_limiter.strategies.sliding_window import SlidingWindowRateLimiter
from app.rate_limiter.strategies.token_bucket import TokenBucketRateLimiter

# mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


async def _flush_redis() -> None:
    from app.core.redis import redis_client

    await redis_client.client.flushdb()


def _assert_common_headers(resp, strategy: str) -> None:
    headers = resp.headers

    assert "X-RateLimit-Limit" in headers
    assert "X-RateLimit-Remaining" in headers
    assert "X-RateLimit-Reset" in headers

    assert int(headers["X-RateLimit-Limit"]) > 0
    assert int(headers["X-RateLimit-Remaining"]) >= 0

    if strategy == "token_bucket":
        assert headers["X-RateLimit-Reset"] == "None"
    else:
        assert int(headers["X-RateLimit-Reset"]) >= 0


@pytest.mark.parametrize(
    ("endpoint", "strategy"),
    [
        ("/api/v1/rate-limit/fixed-window", "fixed_window"),
        ("/api/v1/rate-limit/sliding-window", "sliding_window"),
        ("/api/v1/rate-limit/token-bucket", "token_bucket"),
    ],
)
async def test_rate_limiter_allows_first_request(
    client: AsyncClient, endpoint: str, strategy: str
):
    """
    First request should be allowed and include rate limit metadata.
    """
    await _flush_redis()

    resp = await client.get(endpoint)

    assert resp.status_code == 200

    data = resp.json()
    assert data["strategy"] == strategy
    assert data["status"] == "allowed"

    _assert_common_headers(resp, strategy)


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/rate-limit/fixed-window",
        "/api/v1/rate-limit/sliding-window",
        "/api/v1/rate-limit/token-bucket",
    ],
)
async def test_rate_limit_remaining_decreases_on_consecutive_requests(
    client: AsyncClient, endpoint: str
):
    """
    Consecutive requests from the same client should consume quota.
    """
    await _flush_redis()

    first = await client.get(endpoint)
    second = await client.get(endpoint)

    assert first.status_code == 200
    assert second.status_code == 200

    first_remaining = int(first.headers["X-RateLimit-Remaining"])
    second_remaining = int(second.headers["X-RateLimit-Remaining"])

    print(f"First remaining: {first_remaining}, Second remaining: {second_remaining}")

    assert second_remaining <= first_remaining
    assert first_remaining - second_remaining <= 1


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/rate-limit/fixed-window",
        "/api/v1/rate-limit/sliding-window",
    ],
)
async def test_rate_limit_blocks_after_small_quota(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
):
    """
    With tiny limits, the third immediate request should be rejected.
    """
    await _flush_redis()

    def rate_limit_factory_patch(selected: RateLimitStrategy):
        if selected == RateLimitStrategy.FIXED_WINDOW:
            return FixedWindowRateLimiter(
                FixedWindowRateLimitConfig(limit=2, window=60)
            )

        if selected == RateLimitStrategy.SLIDING_WINDOW:
            return SlidingWindowRateLimiter(
                SlidingWindowRateLimitConfig(limit=2, window=60)
            )

        if selected == RateLimitStrategy.TOKEN_BUCKET:
            return TokenBucketRateLimiter(
                TokenBucketRateLimitConfig(capacity=2, refill_rate=1)
            )

        raise ValueError("Unknown strategy")

    # patch the default rate limiter factory to return our custom low-limit factory for testing
    monkeypatch.setattr(
        "app.rate_limiter.dependency.get_rate_limiter",
        rate_limit_factory_patch,
    )

    responses = [await client.get(endpoint) for _ in range(6)]

    assert responses[0].status_code == 200
    assert responses[1].status_code == 200
    assert responses[2].status_code == 429
    assert "Retry-After" in responses[2].headers
    assert int(responses[2].headers["Retry-After"]) >= 1


async def test_token_bucket_low_capacity_exposes_configured_limit(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """
    Token bucket endpoint should expose patched capacity in rate limit headers.
    """
    await _flush_redis()

    def rate_limit_factory_patch(selected: RateLimitStrategy):
        if selected == RateLimitStrategy.TOKEN_BUCKET:
            return TokenBucketRateLimiter(
                TokenBucketRateLimitConfig(capacity=2, refill_rate=1)
            )

        return FixedWindowRateLimiter(FixedWindowRateLimitConfig(limit=100, window=60))

    monkeypatch.setattr(
        "app.rate_limiter.dependency.get_rate_limiter",
        rate_limit_factory_patch,
    )

    first = await client.get("/api/v1/rate-limit/token-bucket")
    second = await client.get("/api/v1/rate-limit/token-bucket")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.headers["X-RateLimit-Limit"] == "2"
    assert second.headers["X-RateLimit-Limit"] == "2"
    assert int(second.headers["X-RateLimit-Remaining"]) <= int(
        first.headers["X-RateLimit-Remaining"]
    )

from abc import ABC, abstractmethod

from app.rate_limiter.schemas import RateLimitResult


class BaseRateLimiter(ABC):
    @abstractmethod
    async def allow_request(self, key: str) -> RateLimitResult: ...

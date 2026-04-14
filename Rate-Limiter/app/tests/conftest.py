import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    """
    A test client for the FastAPI app.
    """
    from app.main import app
    from app.core.redis import redis_client

    await redis_client.connect()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await redis_client.close()

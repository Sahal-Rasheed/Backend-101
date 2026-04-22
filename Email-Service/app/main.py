import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.redis import redis_client
from app.api import router as api_router
from app.db.async_session import init_models, async_engine


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    https://fastapi.tiangolo.com/advanced/events/
    """
    await init_models()
    logger.info("Database models initialized")
    redis_client.connect()
    logger.info("Connected to Redis")

    yield

    await async_engine.dispose()
    logger.info("Database engine disposed")
    redis_client.close()
    logger.info("Disconnected from Redis")


app = FastAPI(
    debug=settings.DEBUG,
    title=settings.PROJECT_NAME,
    docs_url=f"{settings.API_V1_STR}/docs" if settings.DEBUG else None,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    redoc_url=None,
    lifespan=lifespan,
)


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Email Service API!"}


app.include_router(api_router, prefix=settings.API_V1_STR)

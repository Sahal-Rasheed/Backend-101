import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.redis import redis_client


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    https://fastapi.tiangolo.com/advanced/events/
    """
    await redis_client.connect()
    yield
    await redis_client.close()


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
    logger.info("Hello World")
    return {"message": "Hello World"}


app.include_router(api_router, prefix=settings.API_V1_STR)

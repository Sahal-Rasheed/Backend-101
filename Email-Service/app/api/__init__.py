from fastapi import APIRouter

from app.api.email import email_router
from app.api.webhook import webhook_router


router = APIRouter()
router.include_router(email_router, prefix="/email", tags=["emails"])
router.include_router(webhook_router, prefix="/webhook", tags=["webhooks"])

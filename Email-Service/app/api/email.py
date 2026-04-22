from uuid import UUID

from celery.result import AsyncResult
from fastapi import APIRouter, Header, Query, status
from fastapi.exceptions import HTTPException

from app.utils.redis import redis_service  # noqa
from app.db.async_session import AsyncSessionDep
from app.repository.email import email_repository
from app.middlewares.rate_limiter import RateLimiterDep
from app.tasks.email_tasks import (
    send_welcome_email,
    send_pwd_reset_email,
    send_notification_email,
)
from app.schemas.email import (
    EmailType,
    EmailStatus,
    EmailSendPayload,
    EmailLogResponse,
    EmailSendResponse,
    EmailBlacklistResponse,
    EmailTaskStatusResponse,
)

email_router = APIRouter()


@email_router.post(
    "/send", status_code=status.HTTP_200_OK, response_model=EmailSendResponse
)
async def send_email(
    _: RateLimiterDep,
    db: AsyncSessionDep,
    email_data: EmailSendPayload,
    x_tenant_id: str = Header(..., alias="x-tenant-id"),
) -> EmailSendResponse:
    """Endpoint to dispatch email sending tasks."""
    is_blacklisted = await email_repository.is_email_blacklisted(
        db, email_data.to_email
    )
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address is blacklisted",
        )
    
    # return EmailSendResponse(task_id="", email_log_id="", status=EmailStatus.QUEUED)

    # create initial email log entry in the database
    email_log = await email_repository.create_email_log(db, email_data)

    # trigger celery task based on email type and it will route to appropriate queue as defined in global config
    if email_data.email_type == EmailType.WELCOME:
        task = send_welcome_email.delay(
            data={
                "id": str(email_log.id),
                "to_email": email_data.to_email,
                "subject": email_data.subject,
                "html_content": f"<h1>Welcome, {email_data.to_email}!</h1><p>Thank you for joining our platform.</p>",
            }
        )

    if email_data.email_type == EmailType.PASSWORD_RESET:
        task = send_pwd_reset_email.delay(
            data={
                "id": str(email_log.id),
                "to_email": email_data.to_email,
                "subject": email_data.subject,
                "html_content": f"<h1>Password Reset Request for {email_data.to_email}</h1><p>Click <a href='https://example.com/reset?token=abc123'>here</a> to reset your password.</p>",
            }
        )

    if email_data.email_type == EmailType.NOTIFICATION:
        task = send_notification_email.delay(
            data={
                "id": str(email_log.id),
                "to_email": email_data.to_email,
                "subject": email_data.subject,
                "html_content": "<h1>Notification</h1><p>This is a notification email.</p>",
            }
        )

    return EmailSendResponse(
        task_id=task.id, email_log_id=str(email_log.id), status=EmailStatus.QUEUED
    )


@email_router.get(
    "/tasks/{task_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=EmailTaskStatusResponse,
)
async def get_email_task_status(task_id: str) -> EmailTaskStatusResponse:
    """Endpoint to check the status of a email task inside celery."""
    task_result = AsyncResult(task_id)
    if not task_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    response = {
        "task_id": task_id,
        "state": task_result.state,
        "status": task_result.status,
        "result": None,
        "error": None,
        "trace": None,
    }

    if task_result.ready():
        if task_result.successful():
            response["result"] = task_result.get()
        else:
            response["error"] = str(task_result.result)
            response["trace"] = str(task_result.traceback)

    return EmailTaskStatusResponse(**response)


@email_router.get(
    "/logs", status_code=status.HTTP_200_OK, response_model=list[EmailLogResponse]
)
async def list_email_logs(
    db: AsyncSessionDep,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[EmailLogResponse]:
    """Endpoint to list email logs with pagination."""
    email_logs = await email_repository.get_all_email_logs(db, limit, offset)
    return email_logs


@email_router.get(
    "/logs/{id}",
    status_code=status.HTTP_200_OK,
    response_model=EmailLogResponse,
)
async def get_email_log(db: AsyncSessionDep, id: UUID) -> EmailLogResponse:
    """Endpoint to get details of a specific email log."""
    email_log = await email_repository.get_email_log(db, id)
    if not email_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email log not found"
        )
    return email_log


@email_router.get(
    "/blacklists",
    status_code=status.HTTP_200_OK,
    response_model=list[EmailBlacklistResponse],
)
async def list_blacklisted_emails(
    db: AsyncSessionDep,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[EmailBlacklistResponse]:
    """Endpoint to list blacklisted emails with pagination."""
    blacklisted_emails = await email_repository.list_blacklisted_emails(
        db, limit, offset
    )
    return blacklisted_emails

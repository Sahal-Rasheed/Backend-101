from sqlalchemy import select
from celery.exceptions import MaxRetriesExceededError

from app.models.email import EmailLog
from app.core.celery import celery_app
from app.utils.email import send_email
from app.db.sync_session import get_sync_session
from app.schemas.email import EmailStatus, EmailProvider


@celery_app.task(
    bind=True,
    name="send_welcome_email_task",  # custom task name
    autoretry_for=(Exception, ConnectionError),  # retry on these exceptions
    retry_backoff=True,  # exponential backoff: 2, 4, 8, 16 seconds...
    retry_backoff_max=600,  # maximum 10 minutes between retries
    retry_jitter=True,  # add randomness to prevent thundering herd
    max_retries=5,  # give up after 5 attempts
)
def send_welcome_email(self, data: dict) -> dict:
    """
    Celery task to send welcome email to users.
    """
    try:
        # update email log status to processing before sending email
        with get_sync_session() as db:
            email_log = db.execute(
                select(EmailLog).where(EmailLog.id == data["id"])
            ).scalar_one_or_none()
            email_log.status = EmailStatus.PROCESSING
            db.commit()
            db.refresh(email_log)

        result = send_email(
            to_email=data["to_email"],
            subject=data["subject"],
            html_content=data["html_content"],
        )

        # update email log with provider info and mark as sent
        with get_sync_session() as db:
            email_log = db.execute(
                select(EmailLog).where(EmailLog.id == data["id"])
            ).scalar_one_or_none()
            email_log.provider = (
                EmailProvider.RESEND
                if result["provider"] == "resend"
                else EmailProvider.SMTP
            )
            email_log.status = EmailStatus.SENT
            db.commit()
            db.refresh(email_log)

        return {"success": True, "email_log_id": str(data["id"]), "error": None}
    except Exception as ex:
        print(f"Error in send_welcome_email task: {ex}")
        raise self.retry(exc=ex)

    except MaxRetriesExceededError:
        # update email log status to failed after max retries exceeded
        with get_sync_session() as db:
            email_log = db.execute(
                select(EmailLog).where(EmailLog.id == data["id"])
            ).scalar_one_or_none()
            email_log.status = EmailStatus.FAILED
            email_log.error = "Max retries exceeded"
            db.commit()
            db.refresh(email_log)
        return {
            "success": False,
            "email_log_id": str(data["id"]),
            "error": "Max retries exceeded",
        }


# references:
# https://docs.celeryq.dev/en/main/_modules/celery/app/task.html#Task
# https://docs.celeryq.dev/en/main/userguide/tasks.html

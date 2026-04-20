from typing import Literal, Any
from enum import StrEnum

from pydantic import BaseModel, EmailStr


class EmailType(StrEnum):
    WELCOME = "welcome_email"
    PASSWORD_RESET = "password_reset_email"
    NOTIFICATION = "notification_email"


class EmailProvider(StrEnum):
    RESEND = "resend"
    SMTP = "smtp"


class EmailStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"


class EmailSendPayload(BaseModel):
    to_email: EmailStr
    subject: str
    email_type: EmailType


class EmailSendResponse(BaseModel):
    task_id: str
    email_log_id: str
    status: Literal[EmailStatus.QUEUED]


class EmailTaskStatusResponse(BaseModel):
    task_id: str
    state: str | Any
    status: str | Any
    result: Any | None = None
    error: Any | None = None
    trace: Any | None = None

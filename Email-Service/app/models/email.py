from uuid import uuid4

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimeStampMixin
from app.schemas.email import EmailType, EmailProvider, EmailStatus


class EmailLog(Base, TimeStampMixin):
    __tablename__ = "email_logs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid4
    )
    to_email: Mapped[str] = mapped_column(index=True)
    subject: Mapped[str]
    email_type: Mapped[EmailType]
    status: Mapped[EmailStatus] = mapped_column(default=EmailStatus.QUEUED)
    provider: Mapped[EmailProvider | None] = mapped_column(nullable=True)
    error: Mapped[str | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"EmailLog(id={self.id}, to_email='{self.to_email}', type='{self.email_type}')"


class EmailBlacklist(Base):
    __tablename__ = "email_blacklist"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        index=True, unique=True
    )  # unique constraint needed for upsert operation
    reason: Mapped[str | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"EmailBlacklist(id={self.id}, email='{self.email}')"

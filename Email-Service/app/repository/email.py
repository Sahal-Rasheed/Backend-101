from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import EmailLog, EmailBlacklist
from app.schemas.email import EmailSendPayload


class EmailRepository:
    def __init__(self):
        self.email_log_model = EmailLog
        self.email_blacklist_model = EmailBlacklist

    async def create_email_log(
        self, db: AsyncSession, email_create: EmailSendPayload
    ) -> EmailLog:
        email = self.email_log_model(**email_create.model_dump())
        db.add(email)
        await db.commit()
        await db.refresh(email)
        return email

    async def get_email_log(self, db: AsyncSession, email_id: int) -> EmailLog | None:
        result = await db.execute(
            select(self.email_log_model).where(self.email_log_model.id == email_id)
        )
        return result.scalar_one_or_none()

    async def get_all_email_logs(
        self, db: AsyncSession, limit: int = 100, offset: int = 0
    ) -> list[EmailLog]:

        query = (
            select(self.email_log_model)
            .offset(offset)
            .limit(limit)
            .order_by(self.email_log_model.id)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create_email_blacklist(
        self, db: AsyncSession, email: str, reason: str | None = None
    ) -> EmailBlacklist:
        blacklist_entry = self.email_blacklist_model(email=email, reason=reason)
        db.add(blacklist_entry)
        await db.commit()
        await db.refresh(blacklist_entry)
        return blacklist_entry

    async def is_email_blacklisted(self, db: AsyncSession, email: str) -> bool:
        result = await db.execute(
            select(func.count())
            .select_from(self.email_blacklist_model)
            .where(self.email_blacklist_model.email == email)
        )
        count = result.scalar_one()
        return count > 0

    async def list_blacklisted_emails(
        self, db: AsyncSession, limit: int = 100, offset: int = 0
    ) -> list[EmailBlacklist]:
        query = (
            select(self.email_blacklist_model)
            .offset(offset)
            .limit(limit)
            .order_by(self.email_blacklist_model.id)
        )
        result = await db.execute(query)
        return list(result.scalars().all())


email_repository = EmailRepository()


# quick note:
# - use .execute() always for db o/p its the sqlalchemy 2.0 style
# - .query() is the old 1.x style and should be avoided possible
# - .scalars() call unwraps the Row wrapper and gives you the model object directly,
#   without it you get a Row tuple which you then have to index into. so always chain .scalars() when selecting ORM models.

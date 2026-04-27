from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

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

    async def update_email_log_status(
        self, db: AsyncSession, id: str, status: str, error: str | None = None
    ) -> EmailLog | None:
        stmt = (
            update(self.email_log_model)
            .where(self.email_log_model.id == id)
            .values(status=status, error=error)
            .returning(self.email_log_model)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()

    async def get_email_log(self, db: AsyncSession, id: UUID) -> EmailLog | None:
        result = await db.execute(
            select(self.email_log_model).where(self.email_log_model.id == id)
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

    async def upsert_email_blacklist(
        self, db: AsyncSession, email: str, reason: str | None = None
    ) -> EmailBlacklist:
        stmt = (
            insert(self.email_blacklist_model)
            .values(email=email, reason=reason)
            .on_conflict_do_update(
                index_elements=[
                    self.email_blacklist_model.email
                ],  # target the unique email column for conflict detection for upsert
                set_={"reason": reason},
            )
            .returning(self.email_blacklist_model)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one()

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

from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

sync_engine = create_engine(
    settings.SQLITE_DATABASE_URL.replace("sqlite+aiosqlite", "sqlite"),
    echo=False,
    connect_args={"check_same_thread": False},
)

sync_session_maker = sessionmaker(bind=sync_engine, expire_on_commit=False)


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    session = sync_session_maker()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

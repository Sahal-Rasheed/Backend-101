from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Email Service API"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    REDIS_URL: str = "redis://localhost:6379/1"
    SQLITE_DATABASE_URL: str = "sqlite+aiosqlite:///./database.db"

    RESEND_API_KEY: str
    RESEND_SENDER_EMAIL: str = "onboarding@resend.dev"

    SMTP_USER: str
    SMTP_PASS: str
    SMTP_HOST: str
    SMTP_PORT: int

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

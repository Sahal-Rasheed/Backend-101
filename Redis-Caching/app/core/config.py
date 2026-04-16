from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Redis Caching API"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    REDIS_URL: str = "redis://localhost:6379/2"
    SQLITE_DATABASE_URL: str = "sqlite+aiosqlite:///./database.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

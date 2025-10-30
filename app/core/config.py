from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    APP_ENV: str = "development"
    # 是否启用测试模式，用于控制 DEBUG 级别日志的输出
    APP_TEST_MODE: bool = False
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PromptWorks"
    DATABASE_URL: str = (
        "postgresql+psycopg://promptworks:promptworks@localhost:5432/promptworks"
    )
    REDIS_URL: str = "redis://localhost:6379/0"
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    BACKEND_CORS_ORIGINS: list[str] | str = ["http://localhost:5173"]
    BACKEND_CORS_ALLOW_CREDENTIALS: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value:
            msg = "DATABASE_URL must be provided"
            raise ValueError(msg)
        return value

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, (list, tuple)):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        raise TypeError(
            "BACKEND_CORS_ORIGINS must be a list or a comma separated string"
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached application settings instance."""

    return Settings()


settings = get_settings()

"""Environment-based configuration. No secrets are hardcoded; see .env.example."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./attendance.db"
    JWT_SECRET: str = "dev-only-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    ATTENDANCE_THRESHOLD: float = 75.0
    CORS_ORIGINS: str = "http://localhost:5173"
    UPLOAD_DIR: str = "./uploads"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-5-5"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "attendance@example.com"

    IMAP_HOST: str = ""
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""
    IMAP_POLL_SECONDS: int = 120

    COUNSELLING_AUTO_SEND: bool = False
    COUNSELLING_DEADLINE_HOURS: int = 24


@lru_cache
def get_settings() -> Settings:
    return Settings()

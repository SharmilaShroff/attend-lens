"""Environment-based configuration. No secrets are hardcoded; see .env.example."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "mysql+pymysql://root:root@localhost:3306/attendlens_db"
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
    SMTP_PASS: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "attendance@attendlens.edu"
    EMAIL_FROM: str = "attendance@attendlens.edu"

    GMAIL_USER: str = ""
    GMAIL_APP_PASSWORD: str = ""
    EMAIL_FROM_NAME: str = "Attend Lens"
    N8N_WEBHOOK_URL: str = ""

    # n8n Absence-Email Webhook (Part B integration)
    N8N_ABSENCE_WEBHOOK_URL: str = ""
    N8N_WEBHOOK_SECRET: str = ""

    EMAIL_AUTOMATION_ENABLED: bool = True
    EMAIL_DRY_RUN: bool = False
    FOLLOWUP_WAIT_HOURS: int = 24
    QUIET_HOURS_START: int = 21
    QUIET_HOURS_END: int = 7
    APP_BASE_URL: str = "http://localhost:5173"

    IMAP_HOST: str = ""
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""
    IMAP_POLL_SECONDS: int = 120

    COUNSELLING_AUTO_SEND: bool = False
    COUNSELLING_DEADLINE_HOURS: int = 24
    ML_MODEL_DIR: str = "../ml/models"
    ML_CONFIDENCE_THRESHOLD: float = 0.5
    ML_CRISIS_KEYWORDS: str = "suicide,self-harm,kill myself,end it all,don't want to live,hopeless"

@lru_cache
def get_settings() -> Settings:
    return Settings()


from __future__ import annotations

from pathlib import Path

from pydantic import AnyUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    app_env: str = "local"
    app_base_url: AnyUrl = "http://localhost:3000"
    api_v1_prefix: str = "/api/v1"
    cors_allowed_origins: list[str] = ["http://localhost:3000"]

    # Auth (default cho local dev; production phải set JWT_SECRET)
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_issuer: str = "smart-ielts-mentor"
    jwt_audience: str = "smart-ielts-mentor-web"
    access_token_expire_minutes: int = 60
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300

    # Quota / limits
    free_trial_daily_submissions: int = 3
    max_writing_words: int = 650
    max_audio_seconds: int = 240
    feature_speaking_enabled: bool = False

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-large"
    openai_timeout_seconds: float = 45.0

    # Pinecone
    pinecone_api_key: str | None = None
    pinecone_index_name: str = "smart-ielts-mentor"
    pinecone_namespace: str = "default"

    # Postgres
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "smart_ielts"
    postgres_user: str = "smart_ielts"
    postgres_password: str = "smart_ielts"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # S3
    s3_bucket: str = "smart-ielts-mentor"
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None

    # Observability
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "smart-ielts-mentor"

    # Worker reliability
    job_reclaim_running_after_seconds: int = 1800

    @model_validator(mode="after")
    def _validate_security_defaults(self) -> "Settings":
        production_like = self.app_env.lower() in {"prod", "production", "staging"}
        if production_like and self.jwt_secret == "dev-secret-change-in-production":
            raise ValueError("JWT_SECRET must be set to a strong value in production/staging")
        return self

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()  # singleton


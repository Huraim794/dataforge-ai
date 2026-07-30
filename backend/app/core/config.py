from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    project_name: str = "DataForge AI"
    version: str = "1.0.0"
    debug: bool = False
    environment: str = Field(default="production")

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_workers: int = Field(default=4)
    allowed_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"]
    )
    root_path: str = Field(default="")

    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://dataforge:dataforge@localhost:5432/dataforge"
    )
    database_sync_url: str = Field(
        default="postgresql://dataforge:dataforge@localhost:5432/dataforge"
    )
    database_pool_size: int = Field(default=20)
    database_max_overflow: int = Field(default=10)

    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")
    redis_queue_url: RedisDsn = Field(default="redis://localhost:6379/1")
    redis_cache_url: RedisDsn = Field(default="redis://localhost:6379/2")

    secret_key: str = Field(default="")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "dataforge-ai"

    registration_enabled: bool = Field(default=True)
    default_user_role: str = Field(default="user")

    max_concurrent_browsers: int = Field(default=10, ge=1, le=100)
    default_timeout_ms: int = Field(default=30000)
    browser_headless: bool = Field(default=True)
    browser_viewport_width: int = 1920
    browser_viewport_height: int = 1080
    browser_launch_args: List[str] = Field(
        default=["--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    )

    proxy_pool_size: int = Field(default=50)
    proxy_check_interval_seconds: int = Field(default=300)
    proxy_check_timeout_seconds: int = Field(default=10)
    proxy_max_failures: int = Field(default=3)
    proxy_ban_threshold: int = Field(default=5)
    proxy_check_url: str = Field(default="https://httpbin.org/ip")

    queue_max_retries: int = Field(default=3)
    queue_default_priority: int = Field(default=5)
    queue_retry_delay_seconds: int = Field(default=60)
    queue_retry_backoff_multiplier: float = Field(default=2.0)
    queue_max_concurrent_jobs: int = Field(default=20)
    queue_result_ttl: int = Field(default=86400)

    rate_limit_requests_per_second: int = Field(default=10)
    rate_limit_burst_size: int = Field(default=20)
    rate_limit_domain_based: bool = Field(default=True)

    browser_pool_min: int = Field(default=2)
    browser_pool_max: int = Field(default=10)
    browser_pool_idle_timeout_seconds: int = Field(default=300)
    browser_pool_health_check_seconds: int = Field(default=30)
    browser_pool_max_uses_per_context: int = Field(default=50)

    captcha_service_api_key: Optional[str] = Field(default=None)
    captcha_service_url: str = Field(default="https://api.2captcha.com")
    captcha_auto_solve: bool = Field(default=False)
    captcha_timeout_seconds: int = Field(default=120)

    llm_provider: str = Field(default="openai")
    llm_api_key: Optional[str] = Field(default=None)
    llm_model: str = Field(default="gpt-4o")
    llm_temperature: float = Field(default=0.1)
    llm_max_tokens: int = Field(default=4096)
    llm_endpoint: Optional[str] = Field(default=None)

    storage_backend: str = Field(default="local")
    storage_local_path: str = Field(default="./data/storage")
    storage_s3_bucket: Optional[str] = Field(default=None)
    storage_s3_region: Optional[str] = Field(default=None)

    sentry_dsn: Optional[str] = Field(default=None)
    prometheus_enabled: bool = Field(default=True)
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    log_file: Optional[str] = Field(default=None)

    scheduler_enabled: bool = Field(default=True)
    scheduler_timezone: str = Field(default="UTC")
    scheduler_max_instances: int = Field(default=3)
    scheduler_job_defaults_coalesce: bool = Field(default=True)
    scheduler_job_defaults_max_instances: int = Field(default=1)

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def assemble_allowed_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and v:
            return [item.strip() for item in v.split(",")]
        return v or ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("secret_key", mode="before")
    @classmethod
    def check_secret_key(cls, v: str) -> str:
        if not v or v in ("", "dataforge-secret-key-change-in-production"):
            import os

            env = os.getenv("ENVIRONMENT", "development")
            if env == "production":
                raise ValueError(
                    "SECRET_KEY must be set to a secure value in production. "
                    "Generate one with: openssl rand -hex 32"
                )
            return f"dev-{os.urandom(16).hex()}"
        return v

    @property
    def database_url_str(self) -> str:
        return str(self.database_url)


settings = Settings()

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent

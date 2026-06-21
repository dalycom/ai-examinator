from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.enums import AppEnv, Locale


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: AppEnv = AppEnv.LOCAL
    secret_key: str = Field(min_length=32)
    database_url: str
    migration_database_url: str | None = None
    redis_url: str = "redis://localhost:6379/0"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 1_209_600
    default_locale: Locale = Locale.EN
    supported_locales: str = "en,ar,fr"
    ai_allow_external_phi: bool = False
    ai_use_celery_extraction: bool = False
    export_use_celery: bool = False
    rate_limit_enabled: bool = False
    rate_limit_auth_per_minute: int = 30
    rate_limit_api_per_minute: int = 300
    llm_provider: str = "stub"
    llm_model_id: str = "stub-clinical-v1"
    llm_model_preset: str | None = None
    llm_endpoint_url: str | None = None
    llm_api_key: str | None = None
    llm_timeout_seconds: int = 120
    llm_temperature: float = 0.1
    llm_prompt_version: str = "extraction-v1"
    mfa_issuer: str = "AI-Examinator"
    cors_origins: str = "http://localhost:3000"
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_bucket: str = "ai-examinator"
    object_storage_access_key: str = "minioadmin"
    object_storage_secret_key: str = "minioadmin"

    @field_validator("supported_locales", mode="before")
    @classmethod
    def validate_supported_locales(cls, value: str) -> str:
        locales = [part.strip() for part in value.split(",") if part.strip()]
        if not locales:
            raise ValueError("supported_locales must not be empty")
        return ",".join(locales)

    @property
    def supported_locale_list(self) -> list[Locale]:
        return [Locale(code) for code in self.supported_locales.split(",")]

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def alembic_database_url(self) -> str:
        return self.migration_database_url or self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()

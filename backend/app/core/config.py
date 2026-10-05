"""Ilova sozlamalari — barcha qiymatlar environment o'zgaruvchilaridan o'qiladi."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Ombor AI API"
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # --- Database --------------------------------------------------------------
    # Supabase: postgresql+asyncpg://postgres.<ref>:<password>@<pooler-host>:6543/postgres
    database_url: str = Field(..., description="SQLAlchemy async DSN (postgresql+asyncpg://...)")
    db_pool_size: int = 10
    db_max_overflow: int = 10
    db_echo: bool = False
    # Supabase transaction pooler (pgbouncer, 6543-port) prepared statement'larni
    # qo'llab-quvvatlamaydi — bu holda True qiling.
    db_use_pgbouncer: bool = False

    # --- CORS --------------------------------------------------------------------
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # --- Auth: Supabase JWT --------------------------------------------------------
    supabase_url: str | None = None
    # Legacy HS256 JWT secret. Bo'sh bo'lsa, JWKS (asimmetrik kalitlar) ishlatiladi.
    supabase_jwt_secret: SecretStr | None = None
    supabase_jwt_audience: str = "authenticated"

    # --- Auth: AI agent API kalitlari ----------------------------------------------
    ai_agent_api_keys: Annotated[list[SecretStr], NoDecode] = []
    ai_agent_role: Literal["admin", "manager", "viewer"] = "manager"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("ai_agent_api_keys", mode="before")
    @classmethod
    def _split_keys(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("ai_agent_api_keys")
    @classmethod
    def _validate_key_strength(cls, keys: list[SecretStr]) -> list[SecretStr]:
        for key in keys:
            if len(key.get_secret_value()) < 32:
                raise ValueError("AI_AGENT_API_KEYS: har bir kalit kamida 32 belgidan iborat bo'lishi kerak")
        return keys

    @property
    def jwks_url(self) -> str | None:
        if not self.supabase_url:
            return None
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

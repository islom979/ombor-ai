from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # FastAPI backend
    ombor_api_url: str = "http://localhost:8000/api/v1"
    ombor_api_key: SecretStr = Field(..., description="Backend AI_AGENT_API_KEYS dan biri")
    ombor_api_timeout: float = 30.0

    # Claude (Anthropic API). ANTHROPIC_API_KEY SDK tomonidan avtomatik o'qiladi.
    claude_model: str = "claude-opus-5-5"
    claude_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    claude_max_tokens: int = 16000
    agent_max_turns: int = Field(15, ge=1, le=50)
    # Refusal holatida server tomonidagi zaxira modelga o'tish (Claude API'da qo'llab-quvvatlanadi).
    claude_server_fallbacks: bool = True

    # Xavfsizlik: false bo'lsa agent faqat o'qiy oladi.
    agent_allow_writes: bool = True

    # Worker
    worker_id: str = "ai-worker-1"
    worker_poll_interval: float = Field(2.0, gt=0)
    worker_concurrency: int = Field(2, ge=1, le=16)

    log_level: str = "INFO"


@lru_cache
def get_settings() -> AgentSettings:
    return AgentSettings()  # type: ignore[call-arg]

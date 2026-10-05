from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.domain.enums import AiCommandStatus
from app.schemas.common import Schema


class AiCommandCreate(Schema):
    prompt: str = Field(min_length=1, max_length=4000)


class AiCommandClaim(Schema):
    worker_id: str = Field(min_length=1, max_length=100)


class AiToolCall(Schema):
    name: str
    input: dict[str, Any]
    output: Any | None = None
    is_error: bool = False
    duration_ms: int | None = None


class AiCommandUpdate(Schema):
    """Agent ishchi (worker) natijani shu sxema orqali yozadi."""

    status: AiCommandStatus
    response: str | None = Field(None, max_length=20000)
    error: str | None = Field(None, max_length=4000)
    tool_calls: list[AiToolCall] | None = None
    model: str | None = Field(None, max_length=100)
    input_tokens: int | None = Field(None, ge=0)
    output_tokens: int | None = Field(None, ge=0)


class AiCommandRead(Schema):
    id: UUID
    user_id: UUID | None
    user_email: str | None = None
    prompt: str
    status: AiCommandStatus
    response: str | None
    error: str | None
    tool_calls: list[AiToolCall]
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

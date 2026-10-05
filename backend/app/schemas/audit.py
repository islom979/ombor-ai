from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.domain.enums import UserRole
from app.schemas.common import Schema

AuditCategory = Literal["auth", "write", "read", "error"]


class AuditLogRead(Schema):
    id: int
    created_at: datetime
    actor_kind: str
    user_id: UUID | None
    user_email: str | None
    user_role: UserRole | None
    action: str
    method: str
    path: str
    path_params: dict[str, Any]
    query: str | None
    request_body: Any | None
    status_code: int
    duration_ms: int
    ip: str | None
    user_agent: str | None
    country: str | None
    region: str | None
    city: str | None
    latitude: float | None
    longitude: float | None
    request_id: str | None

    @field_validator("ip", mode="before")
    @classmethod
    def _ip_to_str(cls, value: object) -> object:
        return str(value) if value is not None else None


class AuditFilters(Schema):
    user_id: UUID | None = None
    category: AuditCategory | None = Field(
        None, description="auth — kirish/chiqish, write — o'zgartirishlar, read — o'qish, error — xatolar (4xx/5xx)"
    )
    action: str | None = Field(None, max_length=100)
    ip: str | None = Field(None, max_length=64)
    search: str | None = Field(None, max_length=100, description="email, yo'l yoki shahar bo'yicha")
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def _check_dates(self) -> "AuditFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from date_to dan katta bo'lishi mumkin emas")
        return self


class AuthEvent(Schema):
    event: Literal["login", "logout"]

from datetime import datetime
from uuid import UUID

from app.domain.enums import UserRole
from app.schemas.common import Schema


class ProfileRead(Schema):
    id: UUID
    email: str
    full_name: str | None
    role: UserRole
    created_at: datetime


class RoleUpdate(Schema):
    role: UserRole


class MeRead(Schema):
    kind: str
    role: UserRole
    user_id: UUID | None
    email: str | None
    full_name: str | None

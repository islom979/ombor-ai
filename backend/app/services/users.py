from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.security import Principal
from app.repositories.profiles import ProfileRepository
from app.schemas.users import MeRead, ProfileRead, RoleUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._profiles = ProfileRepository(session)

    async def me(self, principal: Principal) -> MeRead:
        profile = await self._profiles.get(principal.user_id) if principal.user_id else None
        return MeRead(
            kind=principal.kind,
            role=principal.role,
            user_id=principal.user_id,
            email=profile.email if profile else principal.email,
            full_name=profile.full_name if profile else "AI Agent",
        )

    async def list(self) -> list[ProfileRead]:
        return [ProfileRead.model_validate(p) for p in await self._profiles.list()]

    async def update_role(self, profile_id: UUID, data: RoleUpdate, principal: Principal) -> ProfileRead:
        if profile_id == principal.user_id:
            raise ConflictError("O'z rolingizni o'zgartira olmaysiz")
        profile = await self._profiles.get(profile_id)
        if not profile:
            raise NotFoundError("Foydalanuvchi topilmadi")
        profile.role = data.role
        await self._session.flush()
        await self._session.refresh(profile)
        return ProfileRead.model_validate(profile)

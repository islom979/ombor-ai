from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Profile


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, profile_id: UUID) -> Profile | None:
        return await self._session.get(Profile, profile_id)

    async def list(self) -> list[Profile]:
        return list(await self._session.scalars(select(Profile).order_by(Profile.created_at)))

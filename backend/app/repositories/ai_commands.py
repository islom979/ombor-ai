from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import AiCommand
from app.domain.enums import AiCommandStatus


class AiCommandRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, command: AiCommand) -> None:
        self._session.add(command)

    async def flush(self) -> None:
        await self._session.flush()

    async def get(self, command_id: UUID) -> AiCommand | None:
        return await self._session.scalar(
            select(AiCommand)
            .where(AiCommand.id == command_id)
            .options(joinedload(AiCommand.user))
            .execution_options(populate_existing=True)
        )

    async def list(self, *, user_id: UUID | None, offset: int, limit: int) -> tuple[list[AiCommand], int]:
        stmt = select(AiCommand)
        if user_id:
            stmt = stmt.where(AiCommand.user_id == user_id)
        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = await self._session.scalars(
            stmt.options(joinedload(AiCommand.user))
            .order_by(AiCommand.created_at.desc(), AiCommand.id)
            .offset(offset)
            .limit(limit)
        )
        return list(rows), int(total)

    async def claim_next(self, worker_id: str) -> UUID | None:
        """Navbatdagi 'pending' buyruqni atomar ravishda egallaydi.

        FOR UPDATE SKIP LOCKED — bir nechta worker parallel ishlasa ham,
        bitta buyruq faqat bittasiga tushadi.
        """
        next_id = (
            select(AiCommand.id)
            .where(AiCommand.status == AiCommandStatus.PENDING)
            .order_by(AiCommand.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        return await self._session.scalar(
            update(AiCommand)
            .where(AiCommand.id == next_id)
            .values(status=AiCommandStatus.RUNNING, claimed_by=worker_id, started_at=func.now())
            .returning(AiCommand.id)
        )

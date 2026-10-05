from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Counterparty
from app.domain.enums import CounterpartyKind
from app.repositories.products import ilike_pattern


class CounterpartyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, counterparty_id: UUID) -> Counterparty | None:
        entity = await self._session.get(Counterparty, counterparty_id)
        return entity if entity and entity.is_active else None

    async def get_for_update(self, counterparty_id: UUID) -> Counterparty | None:
        entity = await self._session.scalar(
            select(Counterparty)
            .where(Counterparty.id == counterparty_id, Counterparty.is_active)
            .with_for_update()
        )
        return entity

    def add(self, entity: Counterparty) -> None:
        self._session.add(entity)

    async def list(
        self, *, kind: CounterpartyKind | None, search: str | None, offset: int, limit: int
    ) -> tuple[list[Counterparty], int]:
        stmt = select(Counterparty).where(Counterparty.is_active)
        if kind:
            stmt = stmt.where(Counterparty.kind == kind)
        if search:
            pattern = ilike_pattern(search)
            stmt = stmt.where(
                Counterparty.name.ilike(pattern)
                | Counterparty.phone.ilike(pattern)
                | Counterparty.address.ilike(pattern)
            )
        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = await self._session.scalars(
            stmt.order_by(Counterparty.created_at.desc(), Counterparty.id).offset(offset).limit(limit)
        )
        return list(rows), int(total)

    async def adjust_balance(self, counterparty_id: UUID, delta: Decimal) -> None:
        await self._session.execute(
            update(Counterparty)
            .where(Counterparty.id == counterparty_id)
            .values(balance=Counterparty.balance + delta)
        )

    async def count(self, kind: CounterpartyKind) -> int:
        return int(
            await self._session.scalar(
                select(func.count()).where(Counterparty.kind == kind, Counterparty.is_active)
            )
            or 0
        )

    async def balance_totals(self) -> tuple[Decimal, Decimal]:
        """(klientlar bizga qarzi, bizning ta'minotchilarga qarzimiz) — ikkalasi ham musbat son."""
        receivables = await self._session.scalar(
            select(func.coalesce(func.sum(-Counterparty.balance), 0)).where(
                Counterparty.is_active, Counterparty.balance < 0
            )
        )
        payables = await self._session.scalar(
            select(func.coalesce(func.sum(Counterparty.balance), 0)).where(
                Counterparty.is_active, Counterparty.balance > 0
            )
        )
        return Decimal(receivables or 0), Decimal(payables or 0)

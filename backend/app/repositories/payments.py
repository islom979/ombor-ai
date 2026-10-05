from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models import CashRegister, Payment, PaymentAllocation


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, payment: Payment) -> None:
        self._session.add(payment)

    def add_allocation(self, allocation: PaymentAllocation) -> None:
        self._session.add(allocation)

    async def flush(self) -> None:
        await self._session.flush()

    def _with_relations(self):
        return (
            joinedload(Payment.cash_register),
            joinedload(Payment.creator),
            selectinload(Payment.allocations).joinedload(PaymentAllocation.invoice),
        )

    async def get(self, payment_id: UUID) -> Payment | None:
        return await self._session.scalar(
            select(Payment)
            .where(Payment.id == payment_id)
            .options(*self._with_relations())
            .execution_options(populate_existing=True)
        )

    async def list(self, *, counterparty_id: UUID | None, offset: int, limit: int) -> tuple[list[Payment], int]:
        stmt = select(Payment)
        if counterparty_id:
            stmt = stmt.where(Payment.counterparty_id == counterparty_id)
        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = await self._session.scalars(
            stmt.options(*self._with_relations())
            .order_by(Payment.created_at.desc(), Payment.id)
            .offset(offset)
            .limit(limit)
        )
        return list(rows.unique()), int(total)


class CashRegisterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, register: CashRegister) -> None:
        self._session.add(register)

    async def get(self, register_id: UUID) -> CashRegister | None:
        register = await self._session.get(CashRegister, register_id)
        return register if register and register.is_active else None

    async def first_active(self) -> CashRegister | None:
        return await self._session.scalar(
            select(CashRegister)
            .where(CashRegister.is_active)
            .order_by(CashRegister.created_at, CashRegister.name)
            .limit(1)
        )

    async def list_active(self) -> list[CashRegister]:
        return list(
            await self._session.scalars(
                select(CashRegister).where(CashRegister.is_active).order_by(CashRegister.created_at, CashRegister.name)
            )
        )

    async def name_taken(self, name: str) -> bool:
        return (await self._session.scalar(select(CashRegister.id).where(CashRegister.name == name))) is not None

    async def adjust_balance(self, register_id: UUID, delta: Decimal) -> None:
        await self._session.execute(
            update(CashRegister)
            .where(CashRegister.id == register_id)
            .values(balance=CashRegister.balance + delta)
        )

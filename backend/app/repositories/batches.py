from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from app.db.models import Batch, Product
from app.repositories.products import ilike_pattern

# pg_advisory_xact_lock kaliti: partiya kodlarini ketma-ket generatsiya qilish uchun.
_BATCH_CODE_LOCK_KEY = 7_340_001


class BatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, batch: Batch) -> None:
        self._session.add(batch)

    async def lock_for_update(self, batch_ids: list[UUID]) -> dict[UUID, Batch]:
        """Partiyalarni qulflaydi (deadlock bo'lmasligi uchun id bo'yicha tartibda)."""
        if not batch_ids:
            return {}
        rows = await self._session.scalars(
            select(Batch).where(Batch.id.in_(batch_ids)).order_by(Batch.id).with_for_update()
        )
        return {batch.id: batch for batch in rows}

    async def lock_fifo(self, product_id: UUID) -> list[Batch]:
        """Mahsulotning qoldig'i bor partiyalari, eng eskisidan boshlab, qulflangan holda."""
        rows = await self._session.scalars(
            select(Batch)
            .where(Batch.product_id == product_id, Batch.quantity > 0)
            .order_by(Batch.received_at, Batch.id)
            .with_for_update()
        )
        return list(rows)

    async def next_sequence(self, day: datetime) -> int:
        """Shu kun uchun keyingi partiya tartib raqami (tranzaksiya oxirigacha qulflangan)."""
        await self._session.execute(text("select pg_advisory_xact_lock(:key)"), {"key": _BATCH_CODE_LOCK_KEY})
        count = await self._session.scalar(
            select(func.count()).where(Batch.code.like(f"{day:%Y%m%d}-%"))
        )
        return int(count or 0) + 1

    async def available(self, *, search: str | None, limit: int) -> list[Batch]:
        stmt = (
            select(Batch)
            .join(Batch.product)
            .options(contains_eager(Batch.product))
            .where(Batch.quantity > 0, Product.is_active)
        )
        if search:
            stmt = stmt.where(
                Product.name.ilike(ilike_pattern(search))
                | Batch.code.ilike(ilike_pattern(search))
                | (Product.barcode == search.strip())
            )
        rows = await self._session.scalars(stmt.order_by(Product.name, Batch.received_at).limit(limit))
        return list(rows)

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models import Invoice, InvoiceItem
from app.domain.enums import InvoiceStatus, InvoiceType, PaymentStatus
from app.repositories.products import ilike_pattern
from app.schemas.invoices import InvoiceFilters

# Hisobotlar uchun mahalliy vaqt zonasi (sana chegaralari shu bo'yicha olinadi).
LOCAL_TZ = ZoneInfo("Asia/Tashkent")


def day_start(value) -> datetime:
    return datetime.combine(value, time.min, tzinfo=LOCAL_TZ)


def day_end(value) -> datetime:
    return datetime.combine(value, time.max, tzinfo=LOCAL_TZ)


class InvoiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, invoice: Invoice) -> None:
        self._session.add(invoice)

    async def flush(self) -> None:
        await self._session.flush()

    async def get_detail(self, invoice_id: UUID) -> Invoice | None:
        return await self._session.scalar(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .options(
                joinedload(Invoice.counterparty),
                selectinload(Invoice.items).joinedload(InvoiceItem.product),
                selectinload(Invoice.items).joinedload(InvoiceItem.batch),
            )
            # Shu tranzaksiyada yaratilgan obyektlar uchun server default'larni ham yangilaydi.
            .execution_options(populate_existing=True)
        )

    async def list(self, filters: InvoiceFilters, *, offset: int, limit: int) -> tuple[list[Invoice], int]:
        stmt = select(Invoice)
        if filters.type:
            stmt = stmt.where(Invoice.type == filters.type)
        if filters.counterparty_id:
            stmt = stmt.where(Invoice.counterparty_id == filters.counterparty_id)
        if filters.status:
            stmt = stmt.where(Invoice.status == filters.status)
        if filters.payment_status:
            stmt = stmt.where(Invoice.payment_status == filters.payment_status)
        if filters.date_from:
            stmt = stmt.where(Invoice.created_at >= day_start(filters.date_from))
        if filters.date_to:
            stmt = stmt.where(Invoice.created_at <= day_end(filters.date_to))
        if filters.search:
            stmt = stmt.where(Invoice.number.ilike(ilike_pattern(filters.search)))

        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = await self._session.scalars(
            stmt.options(joinedload(Invoice.counterparty))
            .order_by(Invoice.created_at.desc(), Invoice.id)
            .offset(offset)
            .limit(limit)
        )
        return list(rows), int(total)

    async def lock_open_invoices(
        self, *, counterparty_id: UUID, invoice_type: InvoiceType, only_ids: list[UUID] | None
    ) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .where(
                Invoice.counterparty_id == counterparty_id,
                Invoice.type == invoice_type,
                Invoice.status == InvoiceStatus.ACCEPTED,
                Invoice.payment_status != PaymentStatus.PAID,
            )
            .order_by(Invoice.created_at, Invoice.id)
            .with_for_update()
        )
        if only_ids is not None:
            stmt = stmt.where(Invoice.id.in_(only_ids))
        invoices = list(await self._session.scalars(stmt))
        if only_ids is not None:
            order = {invoice_id: index for index, invoice_id in enumerate(only_ids)}
            invoices.sort(key=lambda invoice: order[invoice.id])
        return invoices

    async def operation_stats(
        self, date_from: datetime | None, date_to: datetime | None
    ) -> list[tuple[InvoiceType, int, Decimal]]:
        stmt = select(Invoice.type, func.count(), func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.status == InvoiceStatus.ACCEPTED
        )
        if date_from:
            stmt = stmt.where(Invoice.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Invoice.created_at <= date_to)
        rows = await self._session.execute(stmt.group_by(Invoice.type))
        return [(row[0], int(row[1]), Decimal(row[2])) for row in rows.all()]

    async def sales_totals(self, date_from: datetime | None, date_to: datetime | None) -> tuple[Decimal, Decimal]:
        """(tushum chegirmadan keyin, sotilgan tovar tannarxi) — faqat chiqimlar bo'yicha."""
        base = select(Invoice.id).where(
            Invoice.type == InvoiceType.CHIQIM, Invoice.status == InvoiceStatus.ACCEPTED
        )
        if date_from:
            base = base.where(Invoice.created_at >= date_from)
        if date_to:
            base = base.where(Invoice.created_at <= date_to)
        ids = base.subquery()

        revenue = await self._session.scalar(
            select(func.coalesce(func.sum(Invoice.total), 0)).where(Invoice.id.in_(select(ids.c.id)))
        )
        cost = await self._session.scalar(
            select(func.coalesce(func.sum(InvoiceItem.cost_price * InvoiceItem.quantity), 0)).where(
                InvoiceItem.invoice_id.in_(select(ids.c.id))
            )
        )
        return Decimal(revenue or 0), Decimal(cost or 0)

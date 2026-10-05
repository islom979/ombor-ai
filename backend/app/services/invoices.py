"""Ombor operatsiyalari: kirim, chiqim, utilizatsiya.

Har bir operatsiya bitta tranzaksiyada bajariladi (so'rov sessiyasi = UoW):
partiyalar ``SELECT ... FOR UPDATE`` bilan qulflanadi, shuning uchun parallel
chiqimlar qoldiqni manfiyga tushira olmaydi (oxirgi himoya — CHECK quantity >= 0).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InsufficientStockError, NotFoundError, ValidationFailed
from app.core.security import Principal
from app.db.models import Batch, Counterparty, Invoice, InvoiceItem, Product
from app.domain import rules
from app.domain.enums import CounterpartyKind, InvoiceSource, InvoiceType, PaymentStatus
from app.repositories.batches import BatchRepository
from app.repositories.counterparties import CounterpartyRepository
from app.repositories.invoices import LOCAL_TZ, InvoiceRepository
from app.repositories.products import ProductRepository
from app.schemas.common import Page, PageParams
from app.schemas.invoices import (
    ChiqimCreate,
    InvoiceDetail,
    InvoiceFilters,
    InvoiceItemRead,
    InvoiceRead,
    KirimCreate,
    UtilizatsiyaCreate,
)


class InvoiceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._invoices = InvoiceRepository(session)
        self._batches = BatchRepository(session)
        self._products = ProductRepository(session)
        self._counterparties = CounterpartyRepository(session)

    # ------------------------------------------------------------------ queries
    async def list(self, filters: InvoiceFilters, page: PageParams) -> Page[InvoiceRead]:
        items, total = await self._invoices.list(filters, offset=page.offset, limit=page.size)
        return Page.build([InvoiceRead.model_validate(i) for i in items], total, page.page, page.size)

    async def get(self, invoice_id: UUID) -> InvoiceDetail:
        invoice = await self._invoices.get_detail(invoice_id)
        if not invoice:
            raise NotFoundError("Invoice topilmadi")
        return self._to_detail(invoice)

    # ------------------------------------------------------------------ commands
    async def create_kirim(self, data: KirimCreate, principal: Principal) -> InvoiceDetail:
        supplier = await self._require_counterparty(data.supplier_id, CounterpartyKind.SUPPLIER)
        products = await self._require_products({item.product_id for item in data.items})

        now = datetime.now(UTC)
        local_now = now.astimezone(LOCAL_TZ)
        invoice = self._new_invoice(InvoiceType.KIRIM, supplier.id, data.note, principal, local_now)
        self._invoices.add(invoice)
        await self._invoices.flush()

        sequence = await self._batches.next_sequence(local_now)
        lines: list[InvoiceItem] = []
        for offset, item in enumerate(data.items):
            batch = Batch(
                id=uuid4(),
                product_id=item.product_id,
                invoice_id=invoice.id,
                code=rules.batch_code(local_now, item.purchase_price, sequence + offset),
                purchase_price=item.purchase_price,
                sale_price=item.sale_price,
                initial_quantity=item.quantity,
                quantity=item.quantity,
                received_at=now,
            )
            self._batches.add(batch)
            products[item.product_id].default_sale_price = item.sale_price
            lines.append(
                InvoiceItem(
                    invoice_id=invoice.id,
                    product_id=item.product_id,
                    batch_id=batch.id,
                    quantity=item.quantity,
                    unit_price=item.purchase_price,
                    cost_price=item.purchase_price,
                    line_total=rules.line_total(item.quantity, item.purchase_price),
                )
            )
        await self._session.flush()  # partiyalar invoice qatorlaridan oldin yozilishi shart

        await self._finalize(invoice, lines, discount_percent=Decimal(0))
        await self._counterparties.adjust_balance(supplier.id, rules.invoice_balance_delta(invoice.type, invoice.total))
        return await self.get(invoice.id)

    async def create_chiqim(self, data: ChiqimCreate, principal: Principal) -> InvoiceDetail:
        client = await self._require_counterparty(data.client_id, CounterpartyKind.CLIENT)
        products = await self._require_products({item.product_id for item in data.items})

        explicit_ids = sorted({item.batch_id for item in data.items if item.batch_id})
        locked = await self._batches.lock_for_update(explicit_ids)
        if missing := set(explicit_ids) - locked.keys():
            raise NotFoundError("Partiya topilmadi", details={"batch_ids": [str(i) for i in missing]})

        local_now = datetime.now(UTC).astimezone(LOCAL_TZ)
        invoice = self._new_invoice(InvoiceType.CHIQIM, client.id, data.note, principal, local_now)
        self._invoices.add(invoice)
        await self._invoices.flush()

        lines: list[InvoiceItem] = []
        for item in data.items:
            product = products[item.product_id]
            if item.batch_id:
                batch = locked[item.batch_id]
                if batch.product_id != product.id:
                    raise ValidationFailed(f"Partiya {batch.code} '{product.name}' mahsulotiga tegishli emas")
                portions = self._take_from([batch], item.quantity, product)
            else:
                portions = self._take_from(await self._batches.lock_fifo(product.id), item.quantity, product)

            for batch, taken in portions:
                batch.quantity -= taken
                price = item.unit_price if item.unit_price is not None else batch.sale_price
                lines.append(
                    InvoiceItem(
                        invoice_id=invoice.id,
                        product_id=product.id,
                        batch_id=batch.id,
                        quantity=taken,
                        unit_price=price,
                        cost_price=batch.purchase_price,
                        line_total=rules.line_total(taken, price),
                    )
                )

        await self._finalize(invoice, lines, discount_percent=data.discount_percent)
        await self._counterparties.adjust_balance(client.id, rules.invoice_balance_delta(invoice.type, invoice.total))
        return await self.get(invoice.id)

    async def create_utilizatsiya(self, data: UtilizatsiyaCreate, principal: Principal) -> InvoiceDetail:
        batch_ids = sorted({item.batch_id for item in data.items})
        locked = await self._batches.lock_for_update(batch_ids)
        if missing := set(batch_ids) - locked.keys():
            raise NotFoundError("Partiya topilmadi", details={"batch_ids": [str(i) for i in missing]})
        products = await self._require_products({batch.product_id for batch in locked.values()})

        local_now = datetime.now(UTC).astimezone(LOCAL_TZ)
        invoice = self._new_invoice(InvoiceType.UTILIZATSIYA, None, data.note, principal, local_now)
        self._invoices.add(invoice)
        await self._invoices.flush()

        lines: list[InvoiceItem] = []
        for item in data.items:
            batch = locked[item.batch_id]
            self._take_from([batch], item.quantity, products[batch.product_id])
            batch.quantity -= item.quantity
            lines.append(
                InvoiceItem(
                    invoice_id=invoice.id,
                    product_id=batch.product_id,
                    batch_id=batch.id,
                    quantity=item.quantity,
                    unit_price=batch.purchase_price,
                    cost_price=batch.purchase_price,
                    line_total=rules.line_total(item.quantity, batch.purchase_price),
                )
            )

        await self._finalize(invoice, lines, discount_percent=Decimal(0))
        # Hisobdan chiqarishda hech kim hech kimga qarzdor emas.
        invoice.paid_amount = invoice.total
        invoice.payment_status = PaymentStatus.PAID
        await self._session.flush()
        return await self.get(invoice.id)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _new_invoice(
        invoice_type: InvoiceType,
        counterparty_id: UUID | None,
        note: str | None,
        principal: Principal,
        local_now: datetime,
    ) -> Invoice:
        return Invoice(
            id=uuid4(),
            number=rules.invoice_number(local_now),
            type=invoice_type,
            counterparty_id=counterparty_id,
            subtotal=Decimal(0),
            total=Decimal(0),
            discount_percent=Decimal(0),
            discount_amount=Decimal(0),
            paid_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID,
            note=note,
            source=InvoiceSource.AI if principal.is_agent else InvoiceSource.WEB,
            created_by=principal.user_id,
        )

    async def _finalize(self, invoice: Invoice, lines: list[InvoiceItem], *, discount_percent: Decimal) -> None:
        for position, line in enumerate(lines):
            line.position = position
        self._session.add_all(lines)
        totals = rules.calculate_totals([line.line_total for line in lines], discount_percent)
        invoice.subtotal = totals.subtotal
        invoice.discount_percent = discount_percent
        invoice.discount_amount = totals.discount_amount
        invoice.total = totals.total
        invoice.payment_status = rules.payment_status_for(totals.total, invoice.paid_amount)
        await self._session.flush()

    @staticmethod
    def _take_from(batches: list[Batch], requested: Decimal, product: Product) -> list[tuple[Batch, Decimal]]:
        """So'ralgan miqdorni partiyalardan (berilgan tartibda) yig'adi yoki xato beradi."""
        available = sum((batch.quantity for batch in batches), Decimal(0))
        if available < requested:
            raise InsufficientStockError(
                f"'{product.name}' yetarli emas: omborda {rules.qty(available)} {product.unit}, "
                f"so'ralgan {rules.qty(requested)} {product.unit}",
                details={"product_id": str(product.id), "available": str(available), "requested": str(requested)},
            )
        portions: list[tuple[Batch, Decimal]] = []
        remaining = requested
        for batch in batches:
            if remaining <= 0:
                break
            taken = min(batch.quantity, remaining)
            if taken > 0:
                portions.append((batch, taken))
                remaining -= taken
        return portions

    async def _require_counterparty(self, counterparty_id: UUID, kind: CounterpartyKind) -> Counterparty:
        entity = await self._counterparties.get_for_update(counterparty_id)
        if not entity or entity.kind != kind:
            label = "Ta'minotchi" if kind == CounterpartyKind.SUPPLIER else "Klient"
            raise NotFoundError(f"{label} topilmadi")
        return entity

    async def _require_products(self, ids: set[UUID]) -> dict[UUID, Product]:
        products = await self._products.get_many(ids)
        if missing := ids - products.keys():
            raise NotFoundError("Mahsulot topilmadi", details={"product_ids": [str(i) for i in missing]})
        return products

    @staticmethod
    def _to_detail(invoice: Invoice) -> InvoiceDetail:
        base = InvoiceRead.model_validate(invoice).model_dump()
        items = [
            InvoiceItemRead(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product.name,
                unit=item.product.unit,
                batch_id=item.batch_id,
                batch_code=item.batch.code,
                quantity=item.quantity,
                unit_price=item.unit_price,
                cost_price=item.cost_price,
                line_total=item.line_total,
            )
            for item in invoice.items
        ]
        return InvoiceDetail(**base, items=items)

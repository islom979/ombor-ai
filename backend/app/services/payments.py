from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationFailed
from app.core.security import Principal
from app.db.models import CashRegister, Payment, PaymentAllocation
from app.domain import rules
from app.repositories.counterparties import CounterpartyRepository
from app.repositories.invoices import InvoiceRepository
from app.repositories.payments import CashRegisterRepository, PaymentRepository
from app.schemas.common import Page, PageParams
from app.schemas.payments import (
    CashRegisterCreate,
    CashRegisterRead,
    PaymentAllocationRead,
    PaymentCreate,
    PaymentRead,
)


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self._payments = PaymentRepository(session)
        self._registers = CashRegisterRepository(session)
        self._invoices = InvoiceRepository(session)
        self._counterparties = CounterpartyRepository(session)

    async def list(self, *, counterparty_id: UUID | None, page: PageParams) -> Page[PaymentRead]:
        items, total = await self._payments.list(
            counterparty_id=counterparty_id, offset=page.offset, limit=page.size
        )
        return Page.build([self._to_read(p) for p in items], total, page.page, page.size)

    async def create(self, data: PaymentCreate, principal: Principal) -> PaymentRead:
        counterparty = await self._counterparties.get_for_update(data.counterparty_id)
        if not counterparty:
            raise NotFoundError("Kontragent topilmadi")

        register = (
            await self._registers.get(data.cash_register_id)
            if data.cash_register_id
            else await self._registers.first_active()
        )
        if not register:
            raise ValidationFailed("Faol kassa topilmadi — avval kassa yarating")

        direction = rules.payment_direction_for(counterparty.kind)
        invoice_ids = list(dict.fromkeys(data.invoice_ids)) if data.invoice_ids else None
        open_invoices = await self._invoices.lock_open_invoices(
            counterparty_id=counterparty.id,
            invoice_type=rules.invoice_type_for_counterparty(counterparty.kind),
            only_ids=invoice_ids,
        )
        if invoice_ids is not None and len(open_invoices) != len(invoice_ids):
            raise ValidationFailed("Ba'zi invoicelar topilmadi, boshqa kontragentga tegishli yoki to'liq to'langan")

        payment = Payment(
            counterparty_id=counterparty.id,
            cash_register_id=register.id,
            direction=direction,
            method=data.method,
            amount=data.amount,
            note=data.note,
            created_by=principal.user_id,
        )
        self._payments.add(payment)
        await self._payments.flush()

        by_id = {invoice.id: invoice for invoice in open_invoices}
        allocations = rules.allocate_payment(
            data.amount,
            [rules.OpenInvoice(i.id, i.total, i.paid_amount) for i in open_invoices],
        )
        for invoice_id, share in allocations:
            invoice = by_id[invoice_id]
            invoice.paid_amount += share
            invoice.payment_status = rules.payment_status_for(invoice.total, invoice.paid_amount)
            self._payments.add_allocation(PaymentAllocation(payment_id=payment.id, invoice_id=invoice_id, amount=share))

        await self._counterparties.adjust_balance(counterparty.id, rules.payment_balance_delta(direction, data.amount))
        await self._registers.adjust_balance(register.id, rules.cash_register_delta(direction, data.amount))
        await self._payments.flush()

        created = await self._payments.get(payment.id)
        if created is None:  # pragma: no cover — shu tranzaksiyada yaratilgan
            raise NotFoundError("To'lov topilmadi")
        return self._to_read(created)

    # ------------------------------------------------------------- cash registers
    async def list_registers(self) -> list[CashRegisterRead]:
        return [CashRegisterRead.model_validate(r) for r in await self._registers.list_active()]

    async def create_register(self, data: CashRegisterCreate) -> CashRegisterRead:
        if await self._registers.name_taken(data.name):
            raise ConflictError(f"'{data.name}' nomli kassa allaqachon mavjud")
        register = CashRegister(name=data.name)
        self._registers.add(register)
        await self._payments.flush()
        return CashRegisterRead.model_validate(await self._registers.get(register.id))

    @staticmethod
    def _to_read(payment: Payment) -> PaymentRead:
        return PaymentRead(
            id=payment.id,
            counterparty_id=payment.counterparty_id,
            cash_register_id=payment.cash_register_id,
            cash_register_name=payment.cash_register.name,
            direction=payment.direction,
            method=payment.method,
            amount=payment.amount,
            note=payment.note,
            created_by_name=(payment.creator.full_name or payment.creator.email) if payment.creator else None,
            allocations=[
                PaymentAllocationRead(invoice_id=a.invoice_id, invoice_number=a.invoice.number, amount=a.amount)
                for a in payment.allocations
            ],
            created_at=payment.created_at,
        )

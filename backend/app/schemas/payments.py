from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import PaymentDirection, PaymentMethod
from app.schemas.common import Money, PositiveMoney, Schema


class PaymentCreate(Schema):
    counterparty_id: UUID
    amount: PositiveMoney
    method: PaymentMethod = PaymentMethod.CASH
    # Ko'rsatilmasa — birinchi faol kassa.
    cash_register_id: UUID | None = None
    # Ko'rsatilsa — faqat shu invoicelar (berilgan tartibda) yopiladi, aks holda eng eskisidan.
    invoice_ids: list[UUID] | None = Field(None, max_length=200)
    note: str | None = Field(None, max_length=1000)


class PaymentAllocationRead(Schema):
    invoice_id: UUID
    invoice_number: str
    amount: Money


class PaymentRead(Schema):
    id: UUID
    counterparty_id: UUID
    cash_register_id: UUID
    cash_register_name: str
    direction: PaymentDirection
    method: PaymentMethod
    amount: Money
    note: str | None
    created_by_name: str | None
    allocations: list[PaymentAllocationRead]
    created_at: datetime


class CashRegisterCreate(Schema):
    name: str = Field(min_length=1, max_length=100)


class CashRegisterRead(Schema):
    id: UUID
    name: str
    balance: Money
    is_active: bool

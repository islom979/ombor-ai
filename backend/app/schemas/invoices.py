from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, model_validator

from app.domain.enums import InvoiceSource, InvoiceStatus, InvoiceType, PaymentStatus
from app.schemas.common import Money, NonNegativeMoney, PositiveQuantity, Quantity, Schema
from app.schemas.counterparties import CounterpartyBrief

# ---------------------------------------------------------------------------
# Kirish (create) sxemalari
# ---------------------------------------------------------------------------


class KirimItemIn(Schema):
    product_id: UUID
    quantity: PositiveQuantity
    purchase_price: NonNegativeMoney
    sale_price: NonNegativeMoney


class KirimCreate(Schema):
    supplier_id: UUID
    note: str | None = Field(None, max_length=1000)
    items: list[KirimItemIn] = Field(min_length=1, max_length=200)


class ChiqimItemIn(Schema):
    product_id: UUID
    quantity: PositiveQuantity
    # Partiya ko'rsatilmasa — FIFO (eng eski partiyadan) bo'yicha avtomatik tanlanadi.
    batch_id: UUID | None = None
    # Narx ko'rsatilmasa — partiyaning sotuv narxi olinadi.
    unit_price: NonNegativeMoney | None = None


class ChiqimCreate(Schema):
    client_id: UUID
    note: str | None = Field(None, max_length=1000)
    discount_percent: Decimal = Field(Decimal(0), ge=0, le=100, max_digits=5, decimal_places=2)
    items: list[ChiqimItemIn] = Field(min_length=1, max_length=200)


class UtilizatsiyaItemIn(Schema):
    batch_id: UUID
    quantity: PositiveQuantity


class UtilizatsiyaCreate(Schema):
    note: str = Field(min_length=1, max_length=1000, description="Hisobdan chiqarish sababi")
    items: list[UtilizatsiyaItemIn] = Field(min_length=1, max_length=200)


class InvoiceFilters(Schema):
    type: InvoiceType | None = None
    counterparty_id: UUID | None = None
    status: InvoiceStatus | None = None
    payment_status: PaymentStatus | None = None
    date_from: date | None = None
    date_to: date | None = None
    search: str | None = Field(None, max_length=100)

    @model_validator(mode="after")
    def _check_dates(self) -> "InvoiceFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from date_to dan katta bo'lishi mumkin emas")
        return self


# ---------------------------------------------------------------------------
# Chiqish (read) sxemalari
# ---------------------------------------------------------------------------


class InvoiceItemRead(Schema):
    id: UUID
    product_id: UUID
    product_name: str
    unit: str
    batch_id: UUID
    batch_code: str
    quantity: Quantity
    unit_price: Money
    cost_price: Money
    line_total: Money


class InvoiceRead(Schema):
    id: UUID
    number: str
    type: InvoiceType
    status: InvoiceStatus
    payment_status: PaymentStatus
    counterparty: CounterpartyBrief | None
    subtotal: Money
    discount_percent: Money
    discount_amount: Money
    total: Money
    paid_amount: Money
    note: str | None
    source: InvoiceSource
    created_at: datetime


class InvoiceDetail(InvoiceRead):
    items: list[InvoiceItemRead]

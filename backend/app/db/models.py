"""ORM modellari. Sxemaning yagona manbai — database/migrations/*.sql;
bu modellar o'sha jadvallarni aynan aks ettiradi (create_all ishlatilmaydi)."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Identity, Integer, Numeric, Text, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import (
    AiCommandStatus,
    CounterpartyKind,
    InvoiceStatus,
    InvoiceType,
    PaymentDirection,
    PaymentMethod,
    PaymentStatus,
    ProductUnit,
    UserRole,
)


def pg_enum(enum_cls: type[StrEnum], name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        create_type=False,
        values_callable=lambda members: [member.value for member in members],
    )


class Base(DeclarativeBase):
    pass


def uuid_pk() -> Mapped[UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))


def created_at_col() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(Text)
    full_name: Mapped[str | None] = mapped_column(Text)
    role: Mapped[UserRole] = mapped_column(pg_enum(UserRole, "user_role"))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = created_at_col()


class Product(Base):
    __tablename__ = "products"

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text)
    unit: Mapped[ProductUnit] = mapped_column(pg_enum(ProductUnit, "product_unit"))
    barcode: Mapped[str | None] = mapped_column(Text)
    min_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal(0))
    default_sale_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal(0))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = created_at_col()


class Counterparty(Base):
    __tablename__ = "counterparties"

    id: Mapped[UUID] = uuid_pk()
    kind: Mapped[CounterpartyKind] = mapped_column(pg_enum(CounterpartyKind, "counterparty_kind"))
    name: Mapped[str] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    balance: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal(0))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = created_at_col()


class CashRegister(Base):
    __tablename__ = "cash_registers"

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text)
    balance: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal(0))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = created_at_col()


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[UUID] = uuid_pk()
    number: Mapped[str] = mapped_column(Text)
    type: Mapped[InvoiceType] = mapped_column(pg_enum(InvoiceType, "invoice_type"))
    counterparty_id: Mapped[UUID | None] = mapped_column(ForeignKey("counterparties.id"))
    status: Mapped[InvoiceStatus] = mapped_column(
        pg_enum(InvoiceStatus, "invoice_status"), default=InvoiceStatus.ACCEPTED
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        pg_enum(PaymentStatus, "payment_status"), default=PaymentStatus.UNPAID
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal(0))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal(0))
    total: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal(0))
    note: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, default="web")
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("profiles.id"))
    created_at: Mapped[datetime] = created_at_col()

    counterparty: Mapped[Counterparty | None] = relationship(lazy="raise")
    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice", lazy="raise", order_by="InvoiceItem.position"
    )


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[UUID] = uuid_pk()
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    invoice_id: Mapped[UUID | None] = mapped_column(ForeignKey("invoices.id"))
    code: Mapped[str] = mapped_column(Text)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    sale_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    initial_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    received_at: Mapped[datetime] = created_at_col()
    created_at: Mapped[datetime] = created_at_col()

    product: Mapped[Product] = relationship(lazy="raise")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[UUID] = uuid_pk()
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("batches.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    cost_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(16, 2))

    invoice: Mapped[Invoice] = relationship(back_populates="items", lazy="raise")
    product: Mapped[Product] = relationship(lazy="raise")
    batch: Mapped[Batch] = relationship(lazy="raise")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = uuid_pk()
    counterparty_id: Mapped[UUID] = mapped_column(ForeignKey("counterparties.id"))
    cash_register_id: Mapped[UUID] = mapped_column(ForeignKey("cash_registers.id"))
    direction: Mapped[PaymentDirection] = mapped_column(pg_enum(PaymentDirection, "payment_direction"))
    method: Mapped[PaymentMethod] = mapped_column(pg_enum(PaymentMethod, "payment_method"))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("profiles.id"))
    created_at: Mapped[datetime] = created_at_col()

    cash_register: Mapped[CashRegister] = relationship(lazy="raise")
    creator: Mapped[Profile | None] = relationship(lazy="raise")
    allocations: Mapped[list["PaymentAllocation"]] = relationship(lazy="raise")


class PaymentAllocation(Base):
    __tablename__ = "payment_allocations"

    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), primary_key=True)
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))

    invoice: Mapped[Invoice] = relationship(lazy="raise")


class AiCommand(Base):
    __tablename__ = "ai_commands"

    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("profiles.id"))
    prompt: Mapped[str] = mapped_column(Text)
    status: Mapped[AiCommandStatus] = mapped_column(
        pg_enum(AiCommandStatus, "ai_command_status"), default=AiCommandStatus.PENDING
    )
    response: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    model: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    claimed_by: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()

    user: Mapped[Profile | None] = relationship(lazy="raise")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    created_at: Mapped[datetime] = created_at_col()
    actor_kind: Mapped[str] = mapped_column(Text)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("profiles.id"))
    user_email: Mapped[str | None] = mapped_column(Text)
    user_role: Mapped[UserRole | None] = mapped_column(pg_enum(UserRole, "user_role"))
    action: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text)
    path_params: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    query: Mapped[str | None] = mapped_column(Text)
    request_body: Mapped[Any | None] = mapped_column(JSONB)
    status_code: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer)
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    request_id: Mapped[str | None] = mapped_column(Text)

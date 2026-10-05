"""Sof biznes qoidalari — hech qanday I/O yo'q, shuning uchun to'liq unit-test qilinadi.

Balans konvensiyasi (counterparties.balance):
    musbat  → BIZ kontragentga qarzdormiz (masalan, ta'minotchidan tovar oldik)
    manfiy  → KONTRAGENT bizga qarzdor (masalan, klientga tovar berdik)
"""

import secrets
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import CounterpartyKind, InvoiceType, PaymentDirection, PaymentStatus

MONEY_QUANT = Decimal("0.01")
QTY_QUANT = Decimal("0.001")
ZERO = Decimal("0")


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def qty(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(QTY_QUANT, rounding=ROUND_HALF_UP)


def line_total(quantity: Decimal, unit_price: Decimal) -> Decimal:
    return money(quantity * unit_price)


@dataclass(frozen=True, slots=True)
class Totals:
    subtotal: Decimal
    discount_amount: Decimal
    total: Decimal


def calculate_totals(line_totals: list[Decimal], discount_percent: Decimal = ZERO) -> Totals:
    if not ZERO <= discount_percent <= Decimal(100):
        raise ValueError("Chegirma 0 dan 100 gacha bo'lishi kerak")
    subtotal = money(sum(line_totals, ZERO))
    discount_amount = money(subtotal * discount_percent / Decimal(100))
    return Totals(subtotal=subtotal, discount_amount=discount_amount, total=subtotal - discount_amount)


def payment_status_for(total: Decimal, paid: Decimal) -> PaymentStatus:
    if paid <= ZERO:
        return PaymentStatus.UNPAID if total > ZERO else PaymentStatus.PAID
    if paid >= total:
        return PaymentStatus.PAID
    return PaymentStatus.PARTIAL


def batch_code(received_at: datetime, purchase_price: Decimal, sequence: int) -> str:
    """Partiya kodi: ``YYYYMMDD-<xarid narxi>-<tartib raqami>``, masalan ``20260803-37500-002``."""
    return f"{received_at:%Y%m%d}-{int(purchase_price)}-{sequence:03d}"


def invoice_number(created_at: datetime) -> str:
    """Invoice raqami: ``INV-<8 hex>-YYYYMM``, masalan ``INV-3ba27d6a-202609``."""
    return f"INV-{secrets.token_hex(4)}-{created_at:%Y%m}"


def invoice_balance_delta(invoice_type: InvoiceType, total: Decimal) -> Decimal:
    """Invoice kontragent balansiga qanday ta'sir qiladi."""
    match invoice_type:
        case InvoiceType.KIRIM:
            return total  # ta'minotchiga qarzimiz oshdi
        case InvoiceType.CHIQIM:
            return -total  # klient bizga qarzdor bo'ldi
        case InvoiceType.UTILIZATSIYA:
            return ZERO


def payment_direction_for(kind: CounterpartyKind) -> PaymentDirection:
    return PaymentDirection.OUTGOING if kind == CounterpartyKind.SUPPLIER else PaymentDirection.INCOMING


def payment_balance_delta(direction: PaymentDirection, amount: Decimal) -> Decimal:
    """To'lov kontragent balansini nolga yaqinlashtiradi."""
    return -amount if direction == PaymentDirection.OUTGOING else amount


def cash_register_delta(direction: PaymentDirection, amount: Decimal) -> Decimal:
    return amount if direction == PaymentDirection.INCOMING else -amount


def invoice_type_for_counterparty(kind: CounterpartyKind) -> InvoiceType:
    return InvoiceType.KIRIM if kind == CounterpartyKind.SUPPLIER else InvoiceType.CHIQIM


@dataclass(frozen=True, slots=True)
class OpenInvoice:
    id: object
    total: Decimal
    paid_amount: Decimal

    @property
    def outstanding(self) -> Decimal:
        return self.total - self.paid_amount


def allocate_payment(amount: Decimal, invoices: list[OpenInvoice]) -> list[tuple[object, Decimal]]:
    """To'lovni ochiq invoicelarga berilgan tartibda (odatda eng eskisidan) taqsimlaydi.

    Ortib qolgan summa avans sifatida kontragent balansida qoladi.
    """
    allocations: list[tuple[object, Decimal]] = []
    remaining = amount
    for invoice in invoices:
        if remaining <= ZERO:
            break
        share = min(remaining, invoice.outstanding)
        if share > ZERO:
            allocations.append((invoice.id, share))
            remaining -= share
    return allocations

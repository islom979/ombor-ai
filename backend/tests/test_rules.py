from datetime import datetime
from decimal import Decimal

import pytest

from app.domain import rules
from app.domain.enums import CounterpartyKind, InvoiceType, PaymentDirection, PaymentStatus

D = Decimal


def test_batch_code_format() -> None:
    assert rules.batch_code(datetime(2026, 8, 3), D("37500.00"), 2) == "20260803-37500-002"


def test_invoice_number_format() -> None:
    number = rules.invoice_number(datetime(2026, 9, 12))
    assert number.startswith("INV-") and number.endswith("-202609") and len(number) == 19


def test_totals_with_discount() -> None:
    totals = rules.calculate_totals([D("100000"), D("50000.50")], D("10"))
    assert totals.subtotal == D("150000.50")
    assert totals.discount_amount == D("15000.05")
    assert totals.total == D("135000.45")


def test_totals_reject_bad_discount() -> None:
    with pytest.raises(ValueError):
        rules.calculate_totals([D("1")], D("101"))


@pytest.mark.parametrize(
    ("total", "paid", "expected"),
    [
        (D("100"), D("0"), PaymentStatus.UNPAID),
        (D("100"), D("40"), PaymentStatus.PARTIAL),
        (D("100"), D("100"), PaymentStatus.PAID),
        (D("0"), D("0"), PaymentStatus.PAID),
    ],
)
def test_payment_status(total: Decimal, paid: Decimal, expected: PaymentStatus) -> None:
    assert rules.payment_status_for(total, paid) == expected


def test_balance_conventions() -> None:
    # Kirim: ta'minotchiga qarzimiz oshadi (+), to'lov uni kamaytiradi (-)
    assert rules.invoice_balance_delta(InvoiceType.KIRIM, D("10")) == D("10")
    supplier_dir = rules.payment_direction_for(CounterpartyKind.SUPPLIER)
    assert supplier_dir == PaymentDirection.OUTGOING
    assert rules.payment_balance_delta(supplier_dir, D("10")) == D("-10")
    assert rules.cash_register_delta(supplier_dir, D("10")) == D("-10")

    # Chiqim: klient bizga qarzdor (-), to'lovi balansni oshiradi (+), kassaga pul kiradi
    assert rules.invoice_balance_delta(InvoiceType.CHIQIM, D("10")) == D("-10")
    client_dir = rules.payment_direction_for(CounterpartyKind.CLIENT)
    assert rules.payment_balance_delta(client_dir, D("10")) == D("10")
    assert rules.cash_register_delta(client_dir, D("10")) == D("10")


def test_allocate_payment_oldest_first_with_advance() -> None:
    invoices = [
        rules.OpenInvoice("a", D("100"), D("30")),
        rules.OpenInvoice("b", D("50"), D("0")),
        rules.OpenInvoice("c", D("40"), D("0")),
    ]
    assert rules.allocate_payment(D("100"), invoices) == [("a", D("70")), ("b", D("30"))]
    # Barcha qarzdan ko'p to'lov — ortig'i avans bo'lib qoladi
    assert sum(share for _, share in rules.allocate_payment(D("1000"), invoices)) == D("160")

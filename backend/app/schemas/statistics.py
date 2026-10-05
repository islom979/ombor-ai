from datetime import date

from app.domain.enums import InvoiceType
from app.schemas.common import Money, Schema
from app.schemas.payments import CashRegisterRead


class OperationStat(Schema):
    type: InvoiceType
    count: int
    total: Money


class Statistics(Schema):
    date_from: date | None
    date_to: date | None
    suppliers_count: int
    clients_count: int
    products_count: int
    revenue: Money
    cost_of_goods: Money
    profit: Money
    receivables: Money  # klientlarning bizga qarzi
    payables: Money  # bizning ta'minotchilarga qarzimiz
    cash_registers: list[CashRegisterRead]
    operations: list[OperationStat]

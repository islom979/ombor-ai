from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import InvoiceType
from app.repositories.counterparties import CounterpartyRepository
from app.repositories.invoices import InvoiceRepository, day_end, day_start
from app.repositories.payments import CashRegisterRepository
from app.repositories.products import ProductRepository
from app.schemas.payments import CashRegisterRead
from app.schemas.statistics import OperationStat, Statistics


class StatisticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._invoices = InvoiceRepository(session)
        self._counterparties = CounterpartyRepository(session)
        self._products = ProductRepository(session)
        self._registers = CashRegisterRepository(session)

    async def get(self, date_from: date | None, date_to: date | None) -> Statistics:
        start = day_start(date_from) if date_from else None
        end = day_end(date_to) if date_to else None

        by_type = {t: (count, total) for t, count, total in await self._invoices.operation_stats(start, end)}
        operations = [
            OperationStat(type=t, count=by_type.get(t, (0, 0))[0], total=by_type.get(t, (0, 0))[1])
            for t in InvoiceType
        ]
        revenue, cost = await self._invoices.sales_totals(start, end)
        parties = await self._counterparties.summary()

        return Statistics(
            date_from=date_from,
            date_to=date_to,
            suppliers_count=parties.suppliers,
            clients_count=parties.clients,
            products_count=await self._products.count_active(),
            revenue=revenue,
            cost_of_goods=cost,
            profit=revenue - cost,
            receivables=parties.receivables,
            payables=parties.payables,
            cash_registers=[CashRegisterRead.model_validate(r) for r in await self._registers.list_active()],
            operations=operations,
        )

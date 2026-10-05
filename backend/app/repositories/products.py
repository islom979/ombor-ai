from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Batch, Product


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def ilike_pattern(term: str) -> str:
    return f"%{_escape_like(term.strip())}%"


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, product_id: UUID) -> Product | None:
        product = await self._session.get(Product, product_id)
        return product if product and product.is_active else None

    async def get_many(self, ids: set[UUID]) -> dict[UUID, Product]:
        if not ids:
            return {}
        rows = await self._session.scalars(select(Product).where(Product.id.in_(ids), Product.is_active))
        return {product.id: product for product in rows}

    async def name_taken(self, name: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(Product.id).where(func.lower(Product.name) == name.strip().lower(), Product.is_active)
        if exclude_id:
            stmt = stmt.where(Product.id != exclude_id)
        return (await self._session.scalar(stmt.limit(1))) is not None

    async def barcode_taken(self, barcode: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(Product.id).where(Product.barcode == barcode)
        if exclude_id:
            stmt = stmt.where(Product.id != exclude_id)
        return (await self._session.scalar(stmt.limit(1))) is not None

    def add(self, product: Product) -> None:
        self._session.add(product)

    def _stock_subquery(self):
        return (
            select(
                Batch.product_id.label("product_id"),
                func.coalesce(func.sum(Batch.quantity), 0).label("stock"),
                func.count().filter(Batch.quantity > 0).label("batches_count"),
            )
            .group_by(Batch.product_id)
            .subquery()
        )

    async def list_with_stock(
        self, *, search: str | None, offset: int, limit: int
    ) -> tuple[list[tuple[Product, Decimal, int, Decimal | None]], int]:
        stock = self._stock_subquery()
        last_price = (
            select(Batch.purchase_price)
            .where(Batch.product_id == Product.id)
            .order_by(Batch.received_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        stmt: Select = (
            select(
                Product,
                func.coalesce(stock.c.stock, 0),
                func.coalesce(stock.c.batches_count, 0),
                last_price,
            )
            .outerjoin(stock, stock.c.product_id == Product.id)
            .where(Product.is_active)
        )
        if search:
            stmt = stmt.where(Product.name.ilike(ilike_pattern(search)) | (Product.barcode == search.strip()))
        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = await self._session.execute(stmt.order_by(Product.name).offset(offset).limit(limit))
        return [tuple(row) for row in rows.all()], total  # type: ignore[misc]

    async def stock_rows(self, *, search: str | None, low_only: bool) -> list[tuple[Batch, Product, bool]]:
        """Qoldig'i bor partiyalar + mahsulot kam qolganmi belgisi."""
        stock = self._stock_subquery()
        is_low = (func.coalesce(stock.c.stock, 0) < Product.min_stock).label("is_low")
        stmt = (
            select(Batch, Product, is_low)
            .join(Product, Product.id == Batch.product_id)
            .outerjoin(stock, stock.c.product_id == Product.id)
            .where(Batch.quantity > 0, Product.is_active)
        )
        if search:
            stmt = stmt.where(
                Product.name.ilike(ilike_pattern(search))
                | (Product.barcode == search.strip())
                | Batch.code.ilike(ilike_pattern(search))
            )
        if low_only:
            stmt = stmt.where(is_low)
        rows = await self._session.execute(stmt.order_by(Product.name, Batch.received_at))
        return [tuple(row) for row in rows.all()]  # type: ignore[misc]

    async def stock_summary(self) -> tuple[int, int, Decimal, int]:
        totals = (
            await self._session.execute(
                select(
                    func.count(func.distinct(Batch.product_id)),
                    func.count(),
                    func.coalesce(func.sum(Batch.quantity * Batch.purchase_price), 0),
                ).where(Batch.quantity > 0)
            )
        ).one()
        stock = self._stock_subquery()
        low_count = await self._session.scalar(
            select(func.count())
            .select_from(Product)
            .outerjoin(stock, stock.c.product_id == Product.id)
            .where(Product.is_active, func.coalesce(stock.c.stock, 0) < Product.min_stock)
        )
        return int(totals[0]), int(totals[1]), Decimal(totals[2]), int(low_count or 0)

    async def has_stock(self, product_id: UUID) -> bool:
        stmt = select(Batch.id).where(Batch.product_id == product_id, Batch.quantity > 0).limit(1)
        return (await self._session.scalar(stmt)) is not None

    async def count_active(self) -> int:
        return int(await self._session.scalar(select(func.count()).where(Product.is_active)) or 0)

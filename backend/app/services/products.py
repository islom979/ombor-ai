from __future__ import annotations

import csv
import io
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.db.models import Product
from app.repositories.batches import BatchRepository
from app.repositories.products import ProductRepository
from app.schemas.common import Page, PageParams
from app.schemas.products import (
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ProductWithStock,
    StockRow,
    StockSummary,
)

UNIT_LABELS = {"kg": "kg", "dona": "dona", "litr": "litr", "metr": "metr", "quti": "quti"}


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._products = ProductRepository(session)
        self._batches = BatchRepository(session)

    async def list(self, *, search: str | None, page: PageParams) -> Page[ProductWithStock]:
        rows, total = await self._products.list_with_stock(search=search, offset=page.offset, limit=page.size)
        items = [
            ProductWithStock(
                **ProductRead.model_validate(product).model_dump(),
                stock=stock,
                batches_count=batches_count,
                last_purchase_price=last_price,
            )
            for product, stock, batches_count, last_price in rows
        ]
        return Page.build(items, total, page.page, page.size)

    async def get(self, product_id: UUID) -> ProductRead:
        return ProductRead.model_validate(await self._require(product_id))

    async def create(self, data: ProductCreate) -> ProductRead:
        await self._ensure_unique(name=data.name, barcode=data.barcode)
        product = Product(**data.model_dump())
        self._products.add(product)
        await self._flush_refresh(product)
        return ProductRead.model_validate(product)

    async def update(self, product_id: UUID, data: ProductUpdate) -> ProductRead:
        product = await self._require(product_id)
        changes = data.model_dump(exclude_unset=True)
        await self._ensure_unique(name=changes.get("name"), barcode=changes.get("barcode"), exclude_id=product_id)
        for field, value in changes.items():
            setattr(product, field, value)
        await self._flush_refresh(product)
        return ProductRead.model_validate(product)

    async def deactivate(self, product_id: UUID) -> None:
        product = await self._require(product_id)
        if await self._products.has_stock(product_id):
            raise ConflictError("Omborda qoldig'i bor mahsulotni o'chirib bo'lmaydi")
        product.is_active = False

    async def stock(self, *, search: str | None, low_only: bool) -> list[StockRow]:
        rows = await self._products.stock_rows(search=search, low_only=low_only)
        return [self._to_stock_row(batch, product, is_low) for batch, product, is_low in rows]

    async def stock_summary(self) -> StockSummary:
        products, batches, value, low = await self._products.stock_summary()
        return StockSummary(total_products=products, total_batches=batches, total_value=value, low_stock_count=low)

    async def available_batches(self, *, search: str | None, limit: int) -> list[StockRow]:
        batches = await self._batches.available(search=search, limit=limit)
        return [self._to_stock_row(batch, batch.product, False) for batch in batches]

    async def export_stock_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["Mahsulot", "Birlik", "Partiya", "Xarid narxi", "Sotuv narxi", "Miqdor", "Umumiy qiymat", "Barcode"]
        )
        for row in await self.stock(search=None, low_only=False):
            writer.writerow(
                [
                    row.product_name,
                    UNIT_LABELS[row.unit],
                    row.batch_code,
                    row.purchase_price,
                    row.sale_price,
                    row.quantity,
                    row.total_value,
                    row.barcode or "",
                ]
            )
        # BOM — Excel UTF-8 (kirill/o'zbek harflari) ni to'g'ri ochishi uchun.
        return "﻿" + buffer.getvalue()

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _to_stock_row(batch, product: Product, is_low: bool) -> StockRow:
        return StockRow(
            batch_id=batch.id,
            batch_code=batch.code,
            product_id=product.id,
            product_name=product.name,
            unit=product.unit,
            barcode=product.barcode,
            purchase_price=batch.purchase_price,
            sale_price=batch.sale_price,
            quantity=batch.quantity,
            total_value=batch.quantity * batch.purchase_price,
            is_low=is_low,
            received_at=batch.received_at,
        )

    async def _require(self, product_id: UUID) -> Product:
        product = await self._products.get(product_id)
        if not product:
            raise NotFoundError("Mahsulot topilmadi")
        return product

    async def _ensure_unique(self, *, name: str | None, barcode: str | None, exclude_id: UUID | None = None) -> None:
        if name and await self._products.name_taken(name, exclude_id=exclude_id):
            raise ConflictError(f"'{name}' nomli mahsulot allaqachon mavjud")
        if barcode and await self._products.barcode_taken(barcode, exclude_id=exclude_id):
            raise ConflictError(f"'{barcode}' barcode allaqachon ishlatilgan")

    async def _flush_refresh(self, product: Product) -> None:
        await self._session.flush()
        await self._session.refresh(product)

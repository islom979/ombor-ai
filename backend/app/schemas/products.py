from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.domain.enums import ProductUnit
from app.schemas.common import Money, NonNegativeMoney, Quantity, Schema


class ProductCreate(Schema):
    name: str = Field(min_length=1, max_length=200)
    unit: ProductUnit = ProductUnit.DONA
    barcode: str | None = Field(None, max_length=64)
    min_stock: Quantity = Field(default=Decimal(0), ge=0)
    default_sale_price: NonNegativeMoney = Decimal(0)


class ProductUpdate(Schema):
    name: str | None = Field(None, min_length=1, max_length=200)
    unit: ProductUnit | None = None
    barcode: str | None = Field(None, max_length=64)
    min_stock: Quantity | None = Field(None, ge=0)
    default_sale_price: NonNegativeMoney | None = None


class ProductRead(Schema):
    id: UUID
    name: str
    unit: ProductUnit
    barcode: str | None
    min_stock: Quantity
    default_sale_price: Money
    is_active: bool
    created_at: datetime


class ProductWithStock(ProductRead):
    stock: Quantity
    batches_count: int
    last_purchase_price: Money | None


class StockRow(Schema):
    """Ombor qoldig'i jadvalidagi bitta qator = bitta partiya."""

    batch_id: UUID
    batch_code: str
    product_id: UUID
    product_name: str
    unit: ProductUnit
    barcode: str | None
    purchase_price: Money
    sale_price: Money
    quantity: Quantity
    total_value: Money
    is_low: bool
    received_at: datetime


class StockSummary(Schema):
    total_products: int
    total_batches: int
    total_value: Money
    low_stock_count: int

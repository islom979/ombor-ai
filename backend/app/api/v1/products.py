from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import AnyRole, Paging, SessionDep, Staff
from app.schemas.common import Page
from app.schemas.products import (
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ProductWithStock,
    StockRow,
    StockSummary,
)
from app.services.products import ProductService


def get_service(session: SessionDep) -> ProductService:
    return ProductService(session)


Service = Annotated[ProductService, Depends(get_service)]
Search = Annotated[str | None, Query(max_length=100)]

products_router = APIRouter(prefix="/products", tags=["products"])
stock_router = APIRouter(prefix="/stock", tags=["stock"])


@products_router.get("", response_model=Page[ProductWithStock], summary="Mahsulotlar ro'yxati (qoldiq bilan)")
async def list_products(_: AnyRole, service: Service, page: Paging, search: Search = None):
    return await service.list(search=search, page=page)


@products_router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, _: Staff, service: Service):
    return await service.create(data)


@products_router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: UUID, _: AnyRole, service: Service):
    return await service.get(product_id)


@products_router.patch("/{product_id}", response_model=ProductRead)
async def update_product(product_id: UUID, data: ProductUpdate, _: Staff, service: Service):
    return await service.update(product_id, data)


@products_router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: UUID, _: Staff, service: Service) -> Response:
    await service.deactivate(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@stock_router.get("", response_model=list[StockRow], summary="Ombordagi tovarlar qoldig'i (partiyalar kesimida)")
async def list_stock(_: AnyRole, service: Service, search: Search = None, low_only: bool = False):
    return await service.stock(search=search, low_only=low_only)


@stock_router.get("/summary", response_model=StockSummary)
async def stock_summary(_: AnyRole, service: Service):
    return await service.stock_summary()


@stock_router.get("/available", response_model=list[StockRow], summary="Chiqim uchun mavjud partiyalar")
async def available_batches(
    _: AnyRole, service: Service, search: Search = None, limit: Annotated[int, Query(ge=1, le=200)] = 30
):
    return await service.available_batches(search=search, limit=limit)


@stock_router.get("/export", summary="Qoldiqni CSV formatda yuklab olish")
async def export_stock(_: AnyRole, service: Service) -> Response:
    content = await service.export_stock_csv()
    filename = f"ombor-qoldiq-{date.today():%Y-%m-%d}.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

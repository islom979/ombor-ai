from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import AnyRole, Paging, SessionDep, Staff
from app.schemas.common import Page
from app.schemas.invoices import (
    ChiqimCreate,
    InvoiceDetail,
    InvoiceFilters,
    InvoiceRead,
    KirimCreate,
    UtilizatsiyaCreate,
)
from app.services.invoices import InvoiceService


def get_service(session: SessionDep) -> InvoiceService:
    return InvoiceService(session)


Service = Annotated[InvoiceService, Depends(get_service)]

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=Page[InvoiceRead], summary="Operatsiyalar tarixi (filtrlar bilan)")
async def list_invoices(_: AnyRole, service: Service, page: Paging, filters: Annotated[InvoiceFilters, Query()]):
    return await service.list(filters, page)


@router.get("/{invoice_id}", response_model=InvoiceDetail)
async def get_invoice(invoice_id: UUID, _: AnyRole, service: Service):
    return await service.get(invoice_id)


@router.post("/kirim", response_model=InvoiceDetail, status_code=status.HTTP_201_CREATED, summary="Omborga kirim")
async def create_kirim(data: KirimCreate, principal: Staff, service: Service):
    return await service.create_kirim(data, principal)


@router.post("/chiqim", response_model=InvoiceDetail, status_code=status.HTTP_201_CREATED, summary="Ombordan chiqim")
async def create_chiqim(data: ChiqimCreate, principal: Staff, service: Service):
    return await service.create_chiqim(data, principal)


@router.post(
    "/utilizatsiya", response_model=InvoiceDetail, status_code=status.HTTP_201_CREATED, summary="Hisobdan chiqarish"
)
async def create_utilizatsiya(data: UtilizatsiyaCreate, principal: Staff, service: Service):
    return await service.create_utilizatsiya(data, principal)

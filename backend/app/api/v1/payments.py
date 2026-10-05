from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import Admin, AnyRole, Paging, SessionDep, Staff
from app.schemas.common import Page
from app.schemas.payments import CashRegisterCreate, CashRegisterRead, PaymentCreate, PaymentRead
from app.services.payments import PaymentService


def get_service(session: SessionDep) -> PaymentService:
    return PaymentService(session)


Service = Annotated[PaymentService, Depends(get_service)]

payments_router = APIRouter(prefix="/payments", tags=["payments"])
registers_router = APIRouter(prefix="/cash-registers", tags=["cash-registers"])


@payments_router.get("", response_model=Page[PaymentRead], summary="To'lovlar tarixi")
async def list_payments(_: AnyRole, service: Service, page: Paging, counterparty_id: UUID | None = None):
    return await service.list(counterparty_id=counterparty_id, page=page)


@payments_router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED, summary="To'lov qilish")
async def create_payment(data: PaymentCreate, principal: Staff, service: Service):
    return await service.create(data, principal)


@registers_router.get("", response_model=list[CashRegisterRead], summary="Kassalar")
async def list_registers(_: AnyRole, service: Service):
    return await service.list_registers()


@registers_router.post("", response_model=CashRegisterRead, status_code=status.HTTP_201_CREATED)
async def create_register(data: CashRegisterCreate, _: Admin, service: Service):
    return await service.create_register(data)

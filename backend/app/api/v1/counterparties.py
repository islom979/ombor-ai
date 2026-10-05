from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import AnyRole, Paging, SessionDep, Staff
from app.domain.enums import CounterpartyKind
from app.schemas.common import Page
from app.schemas.counterparties import CounterpartyCreate, CounterpartyRead, CounterpartyUpdate
from app.services.counterparties import CounterpartyService


def get_service(session: SessionDep) -> CounterpartyService:
    return CounterpartyService(session)


Service = Annotated[CounterpartyService, Depends(get_service)]

router = APIRouter(prefix="/counterparties", tags=["counterparties"])


@router.get("", response_model=Page[CounterpartyRead], summary="Ta'minotchilar / klientlar ro'yxati")
async def list_counterparties(
    _: AnyRole,
    service: Service,
    page: Paging,
    kind: CounterpartyKind | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
):
    return await service.list(kind=kind, search=search, page=page)


@router.post("", response_model=CounterpartyRead, status_code=status.HTTP_201_CREATED)
async def create_counterparty(data: CounterpartyCreate, _: Staff, service: Service):
    return await service.create(data)


@router.get("/{counterparty_id}", response_model=CounterpartyRead)
async def get_counterparty(counterparty_id: UUID, _: AnyRole, service: Service):
    return await service.get(counterparty_id)


@router.patch("/{counterparty_id}", response_model=CounterpartyRead)
async def update_counterparty(counterparty_id: UUID, data: CounterpartyUpdate, _: Staff, service: Service):
    return await service.update(counterparty_id, data)


@router.delete("/{counterparty_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_counterparty(counterparty_id: UUID, _: Staff, service: Service) -> Response:
    await service.deactivate(counterparty_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

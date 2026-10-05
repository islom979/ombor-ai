from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import AnyRole, CurrentPrincipal, Paging, SessionDep, Staff
from app.schemas.ai_commands import AiCommandClaim, AiCommandCreate, AiCommandRead, AiCommandUpdate
from app.schemas.common import Page
from app.services.ai_commands import AiCommandService, ensure_agent


def get_service(session: SessionDep) -> AiCommandService:
    return AiCommandService(session)


Service = Annotated[AiCommandService, Depends(get_service)]

router = APIRouter(prefix="/ai/commands", tags=["ai"])


@router.post("", response_model=AiCommandRead, status_code=status.HTTP_201_CREATED, summary="AI'ga buyruq berish")
async def create_command(data: AiCommandCreate, principal: Staff, service: Service):
    return await service.create(data, principal)


@router.get("", response_model=Page[AiCommandRead], summary="AI buyruqlar tarixi")
async def list_commands(principal: AnyRole, service: Service, page: Paging):
    return await service.list(principal, page)


@router.get("/{command_id}", response_model=AiCommandRead)
async def get_command(command_id: UUID, principal: AnyRole, service: Service):
    return await service.get(command_id, principal)


@router.post(
    "/claim",
    response_model=AiCommandRead,
    responses={204: {"description": "Navbatda buyruq yo'q"}},
    summary="[Agent] navbatdagi buyruqni egallash",
)
async def claim_command(data: AiCommandClaim, principal: CurrentPrincipal, service: Service):
    ensure_agent(principal)
    command = await service.claim(data.worker_id)
    return command if command else Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{command_id}", response_model=AiCommandRead, summary="[Agent] natijani yozish")
async def update_command(command_id: UUID, data: AiCommandUpdate, principal: CurrentPrincipal, service: Service):
    ensure_agent(principal)
    return await service.update(command_id, data)

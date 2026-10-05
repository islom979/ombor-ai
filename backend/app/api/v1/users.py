from uuid import UUID

from fastapi import APIRouter

from app.api.deps import Admin, CurrentPrincipal, SessionDep
from app.schemas.users import MeRead, ProfileRead, RoleUpdate
from app.services.users import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=MeRead)
async def me(principal: CurrentPrincipal, session: SessionDep):
    return await UserService(session).me(principal)


@router.get("", response_model=list[ProfileRead], summary="Foydalanuvchilar (faqat admin)")
async def list_users(_: Admin, session: SessionDep):
    return await UserService(session).list()


@router.patch("/{profile_id}/role", response_model=ProfileRead, summary="Rolni o'zgartirish (faqat admin)")
async def update_role(profile_id: UUID, data: RoleUpdate, principal: Admin, session: SessionDep):
    return await UserService(session).update_role(profile_id, data, principal)

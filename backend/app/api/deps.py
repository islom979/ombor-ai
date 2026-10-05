"""FastAPI dependency'lari: DB sessiya (UoW), autentifikatsiya va rol tekshiruvi."""

from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import ApiKeyVerifier, Principal, SupabaseTokenVerifier
from app.db.session import session_scope
from app.domain.enums import UserRole
from app.repositories.profiles import ProfileRepository
from app.schemas.common import PageParams

bearer_scheme = HTTPBearer(auto_error=False, description="Supabase access token")
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False, description="AI agent API kaliti")


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in session_scope(request.app.state.session_factory):
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_principal(
    request: Request,
    session: SessionDep,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    api_key: Annotated[str | None, Security(api_key_scheme)],
) -> Principal:
    if api_key:
        verifier: ApiKeyVerifier = request.app.state.api_key_verifier
        principal = verifier.verify(api_key)
        request.state.principal = principal  # audit jurnali uchun
        return principal

    if bearer is None or bearer.scheme.lower() != "bearer":
        raise AuthenticationError("Autentifikatsiya talab qilinadi")

    token_verifier: SupabaseTokenVerifier = request.app.state.token_verifier
    claims = await token_verifier.verify(bearer.credentials)
    profile = await ProfileRepository(session).get(claims.user_id)
    if profile is None:
        raise PermissionDeniedError("Foydalanuvchi profili topilmadi")
    principal = Principal(kind="user", role=profile.role, user_id=profile.id, email=profile.email)
    request.state.principal = principal  # audit jurnali uchun
    return principal


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


def require_roles(*roles: UserRole) -> Callable[..., Coroutine[Any, Any, Principal]]:
    allowed = set(roles)

    async def dependency(principal: CurrentPrincipal) -> Principal:
        if principal.role not in allowed:
            raise PermissionDeniedError("Bu amal uchun ruxsat yo'q")
        return principal

    return dependency


AnyRole = Annotated[Principal, Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.VIEWER))]
Staff = Annotated[Principal, Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))]
Admin = Annotated[Principal, Depends(require_roles(UserRole.ADMIN))]
Paging = Annotated[PageParams, Depends()]

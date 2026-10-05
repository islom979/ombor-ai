from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status

from app.api.deps import Admin, AnyRole, Paging, SessionDep
from app.repositories.audit_logs import AuditLogRepository
from app.schemas.audit import AuditFilters, AuditLogRead, AuthEvent
from app.schemas.common import Page

router = APIRouter(tags=["audit"])


@router.get("/audit-logs", response_model=Page[AuditLogRead], summary="Audit jurnali (faqat admin)")
async def list_audit_logs(
    _: Admin, session: SessionDep, page: Paging, filters: Annotated[AuditFilters, Query()]
) -> Page[AuditLogRead]:
    items, total = await AuditLogRepository(session).list(filters, offset=page.offset, limit=page.size)
    return Page.build([AuditLogRead.model_validate(i) for i in items], total, page.page, page.size)


@router.post(
    "/auth/events",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Kirish/chiqish voqeasini qayd etish",
    description="Frontend Supabase'ga muvaffaqiyatli kirgandan keyin va chiqishdan oldin chaqiradi. "
    "Yozuvni audit middleware IP va joylashuv bilan birga saqlaydi.",
)
async def record_auth_event(data: AuthEvent, request: Request, _: AnyRole) -> Response:
    request.state.audit_action = f"auth.{data.event}"
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog
from app.repositories.invoices import day_end, day_start
from app.repositories.products import ilike_pattern
from app.schemas.audit import AuditFilters

AUTH_ACTIONS = ("auth.login", "auth.logout")
WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, filters: AuditFilters, *, offset: int, limit: int) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog)
        if filters.user_id:
            stmt = stmt.where(AuditLog.user_id == filters.user_id)
        if filters.action:
            stmt = stmt.where(AuditLog.action == filters.action)
        if filters.ip:
            # Noto'g'ri IP matni so'rovni yiqitmasligi uchun matn sifatida solishtiramiz.
            stmt = stmt.where(func.host(AuditLog.ip) == filters.ip.strip())
        if filters.search:
            pattern = ilike_pattern(filters.search)
            stmt = stmt.where(
                or_(AuditLog.user_email.ilike(pattern), AuditLog.path.ilike(pattern), AuditLog.city.ilike(pattern))
            )
        if filters.date_from:
            stmt = stmt.where(AuditLog.created_at >= day_start(filters.date_from))
        if filters.date_to:
            stmt = stmt.where(AuditLog.created_at <= day_end(filters.date_to))
        match filters.category:
            case "auth":
                stmt = stmt.where(AuditLog.action.in_(AUTH_ACTIONS))
            case "write":
                stmt = stmt.where(AuditLog.method.in_(WRITE_METHODS), AuditLog.action.not_in(AUTH_ACTIONS))
            case "read":
                stmt = stmt.where(AuditLog.method == "GET")
            case "error":
                stmt = stmt.where(AuditLog.status_code >= 400)

        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = await self._session.scalars(
            stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(offset).limit(limit)
        )
        return list(rows), int(total)



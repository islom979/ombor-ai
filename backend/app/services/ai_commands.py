"""AI buyruqlar navbati.

Oqim: foydalanuvchi buyruq yuboradi (pending) → ai_agent worker uni ``claim`` qiladi
(running) → Claude tool'lar orqali shu API bilan ishlaydi → natijani ``PATCH`` qiladi
(completed/failed). Dashboard holatni jonli kuzatadi.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationFailed
from app.core.security import Principal
from app.db.models import AiCommand
from app.domain.enums import AiCommandStatus, UserRole
from app.repositories.ai_commands import AiCommandRepository
from app.schemas.ai_commands import AiCommandCreate, AiCommandRead, AiCommandUpdate
from app.schemas.common import Page, PageParams

_FINAL_STATUSES = {AiCommandStatus.COMPLETED, AiCommandStatus.FAILED}


class AiCommandService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AiCommandRepository(session)

    async def create(self, data: AiCommandCreate, principal: Principal) -> AiCommandRead:
        if principal.user_id is None:
            raise ValidationFailed("Buyruqni faqat tizim foydalanuvchisi yaratishi mumkin")
        command = AiCommand(user_id=principal.user_id, prompt=data.prompt, status=AiCommandStatus.PENDING, tool_calls=[])
        self._repo.add(command)
        await self._repo.flush()
        return await self._read(command.id)

    async def list(self, principal: Principal, page: PageParams) -> Page[AiCommandRead]:
        user_filter = None if self._sees_all(principal) else principal.user_id
        items, total = await self._repo.list(user_id=user_filter, offset=page.offset, limit=page.size)
        return Page.build([self._to_read(c) for c in items], total, page.page, page.size)

    async def get(self, command_id: UUID, principal: Principal) -> AiCommandRead:
        command = await self._require(command_id)
        if not self._sees_all(principal) and command.user_id != principal.user_id:
            raise NotFoundError("Buyruq topilmadi")
        return self._to_read(command)

    async def claim(self, worker_id: str) -> AiCommandRead | None:
        command_id = await self._repo.claim_next(worker_id)
        return await self._read(command_id) if command_id else None

    async def update(self, command_id: UUID, data: AiCommandUpdate) -> AiCommandRead:
        command = await self._require(command_id)
        if command.status in _FINAL_STATUSES:
            raise ConflictError("Yakunlangan buyruqni o'zgartirib bo'lmaydi")
        if data.status == AiCommandStatus.PENDING:
            raise ValidationFailed("Buyruqni qayta 'pending' holatiga o'tkazib bo'lmaydi")

        command.status = data.status
        for field in ("response", "error", "model", "input_tokens", "output_tokens"):
            value = getattr(data, field)
            if value is not None:
                setattr(command, field, value)
        if data.tool_calls is not None:
            command.tool_calls = [call.model_dump(mode="json") for call in data.tool_calls]
        if data.status in _FINAL_STATUSES:
            command.finished_at = datetime.now(UTC)
        await self._repo.flush()
        return await self._read(command.id)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _sees_all(principal: Principal) -> bool:
        return principal.is_agent or principal.role == UserRole.ADMIN

    async def _require(self, command_id: UUID) -> AiCommand:
        command = await self._repo.get(command_id)
        if not command:
            raise NotFoundError("Buyruq topilmadi")
        return command

    async def _read(self, command_id: UUID) -> AiCommandRead:
        command = await self._repo.get(command_id)
        if not command:
            raise NotFoundError("Buyruq topilmadi")
        return self._to_read(command)

    @staticmethod
    def _to_read(command: AiCommand) -> AiCommandRead:
        data = AiCommandRead.model_validate(command)
        data.user_email = command.user.email if command.user else None
        return data


def ensure_agent(principal: Principal) -> None:
    if not principal.is_agent:
        raise PermissionDeniedError("Bu amal faqat AI agent uchun")

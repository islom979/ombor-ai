from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.db.models import Counterparty
from app.domain.enums import CounterpartyKind
from app.repositories.counterparties import CounterpartyRepository
from app.schemas.common import Page, PageParams
from app.schemas.counterparties import CounterpartyCreate, CounterpartyRead, CounterpartyUpdate


class CounterpartyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CounterpartyRepository(session)

    async def list(
        self, *, kind: CounterpartyKind | None, search: str | None, page: PageParams
    ) -> Page[CounterpartyRead]:
        items, total = await self._repo.list(kind=kind, search=search, offset=page.offset, limit=page.size)
        return Page.build([CounterpartyRead.model_validate(i) for i in items], total, page.page, page.size)

    async def get(self, counterparty_id: UUID) -> CounterpartyRead:
        return CounterpartyRead.model_validate(await self._require(counterparty_id))

    async def create(self, data: CounterpartyCreate) -> CounterpartyRead:
        entity = Counterparty(**data.model_dump())
        self._repo.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return CounterpartyRead.model_validate(entity)

    async def update(self, counterparty_id: UUID, data: CounterpartyUpdate) -> CounterpartyRead:
        entity = await self._require(counterparty_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        await self._session.flush()
        await self._session.refresh(entity)
        return CounterpartyRead.model_validate(entity)

    async def deactivate(self, counterparty_id: UUID) -> None:
        entity = await self._require(counterparty_id)
        if entity.balance != 0:
            raise ConflictError("Balansi nolga teng bo'lmagan kontragentni o'chirib bo'lmaydi")
        entity.is_active = False

    async def _require(self, counterparty_id: UUID) -> Counterparty:
        entity = await self._repo.get(counterparty_id)
        if not entity:
            raise NotFoundError("Kontragent topilmadi")
        return entity

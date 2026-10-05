from datetime import date

from fastapi import APIRouter

from app.api.deps import AnyRole, SessionDep
from app.core.errors import ValidationFailed
from app.schemas.statistics import Statistics
from app.services.statistics import StatisticsService

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("", response_model=Statistics, summary="Hisobotlar / statistika")
async def get_statistics(
    _: AnyRole, session: SessionDep, date_from: date | None = None, date_to: date | None = None
):
    if date_from and date_to and date_from > date_to:
        raise ValidationFailed("date_from date_to dan katta bo'lishi mumkin emas")
    return await StatisticsService(session).get(date_from, date_to)

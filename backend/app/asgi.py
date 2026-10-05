"""ASGI entrypoint (Vercel va boshqa serverless platformalar uchun): ``app.asgi:app``.

Sozlamalar to'liq bo'lmasa ilova "yiqilmaydi" — o'rniga 503 bilan nima yetishmayotganini aytadi.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.config import get_settings
from app.main import create_app


def _misconfigured_app(error: ValidationError) -> FastAPI:
    missing = sorted({str(e["loc"][0]).upper() for e in error.errors()})
    fallback = FastAPI(title="Ombor AI API (sozlanmagan)", docs_url=None, redoc_url=None)

    @fallback.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"])
    async def not_configured(path: str) -> JSONResponse:
        return JSONResponse(
            {
                "error": {
                    "code": "not_configured",
                    "message": "Backend environment o'zgaruvchilari to'ldirilmagan",
                    "details": {"invalid_or_missing": missing},
                }
            },
            status_code=503,
        )

    return fallback


try:
    get_settings()
    app = create_app()
except ValidationError as exc:
    app = _misconfigured_app(exc)

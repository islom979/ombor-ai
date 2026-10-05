"""FastAPI ilova fabrikasi.

Ishga tushirish: ``uvicorn app.main:create_app --factory --reload``
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.router import api_router
from app.core.audit_middleware import AuditMiddleware
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.core.security import ApiKeyVerifier, SupabaseTokenVerifier
from app.db.session import create_engine, create_session_factory

logger = logging.getLogger("app")


def _error_body(code: str, message: str, details: object = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            _error_body(exc.code, exc.message, exc.details), status_code=exc.status_code, headers=headers
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(p) for p in err["loc"][1:]), "message": err["msg"]} for err in exc.errors()
        ]
        return JSONResponse(
            _error_body("validation_failed", "So'rov ma'lumotlari noto'g'ri", {"errors": errors}), status_code=422
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity(_: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Integrity error: %s", exc.orig)
        return JSONResponse(
            _error_body("conflict", "Ma'lumotlar yaxlitligi buzildi (takroriy yoki bog'langan yozuv)"),
            status_code=409,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Kutilmagan xato", exc_info=exc)
        return JSONResponse(_error_body("internal_error", "Ichki server xatosi"), status_code=500)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    # Engine "dangasa" — ulanish birinchi so'rovda ochiladi. Holat lifespan'dan tashqarida
    # yaratiladi, shuning uchun lifespan ishlamaydigan serverless muhitda ham ilova ishlaydi.
    engine = create_engine(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("%s ishga tushdi (%s)", settings.app_name, settings.environment)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.token_verifier = SupabaseTokenVerifier(settings)
    app.state.api_key_verifier = ApiKeyVerifier(settings)
    if settings.audit_enabled:
        # CORS'dan oldin qo'shiladi → CORS tashqi qatlam bo'ladi, audit esa yakuniy status kodini ko'radi.
        app.add_middleware(
            AuditMiddleware,
            session_factory=app.state.session_factory,
            trust_proxy=settings.trust_proxy,
            log_reads=settings.audit_log_reads,
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
        expose_headers=["Content-Disposition"],
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/health", tags=["health"])
    async def health(request: Request) -> dict:
        async with request.app.state.engine.connect() as connection:
            await connection.execute(text("select 1"))
        return {"status": "ok"}

    return app

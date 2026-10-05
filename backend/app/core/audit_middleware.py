"""Audit middleware — har bir API so'rovini ``audit_logs`` jadvaliga yozadi.

Sof ASGI middleware (BaseHTTPMiddleware emas): so'rov tanasini o'qib qo'yish
keyingi qatlamlarga xalaqit bermaydi va javob oqimiga aralashmaydi.
Jurnalga yozishdagi xato hech qachon foydalanuvchi so'rovini buzmaydi.
"""

import json
import logging
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.client_info import extract_client_info
from app.core.security import Principal
from app.db.models import AuditLog

logger = logging.getLogger("app.audit")

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
MAX_BODY_BYTES = 8 * 1024
SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/favicon.ico"}
SENSITIVE_KEYS = {"password", "token", "access_token", "refresh_token", "api_key", "secret", "authorization"}


def redact(value: Any) -> Any:
    """Maxfiy kalitlarni ``***`` bilan almashtiradi (ichma-ich obyektlarda ham)."""
    if isinstance(value, dict):
        return {k: "***" if k.lower() in SENSITIVE_KEYS else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def parse_body(raw: bytes) -> Any:
    if not raw:
        return None
    if len(raw) > MAX_BODY_BYTES:
        return {"truncated": True, "size": len(raw)}
    try:
        return redact(json.loads(raw))
    except (ValueError, UnicodeDecodeError):
        return {"raw": raw[:500].decode("utf-8", "replace")}


def path_template(path: str, params: dict[str, str]) -> str:
    """``/api/v1/products/3fa8…`` → ``/api/v1/products/{product_id}`` (guruhlash va filtrlash uchun)."""
    segments = path.split("/")
    by_value = {value: name for name, value in params.items()}
    return "/".join(f"{{{by_value[s]}}}" if s in by_value else s for s in segments)


class AuditMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        trust_proxy: bool,
        log_reads: bool,
    ) -> None:
        self.app = app
        self._session_factory = session_factory
        self._trust_proxy = trust_proxy
        self._log_reads = log_reads

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        method = scope.get("method", "")
        if scope["type"] != "http" or method == "OPTIONS" or scope.get("path") in SKIP_PATHS:
            await self.app(scope, receive, send)
            return
        if method not in WRITE_METHODS and not self._log_reads:
            await self.app(scope, receive, send)
            return

        # Request.state shu lug'atni ishlatadi — get_principal yozgan foydalanuvchi bizga ko'rinadi.
        scope.setdefault("state", {})
        started = time.perf_counter()
        body_chunks: list[bytes] = []
        captured = 0
        status_code = 500

        async def receive_wrapper() -> Message:
            nonlocal captured
            message = await receive()
            if method in WRITE_METHODS and message["type"] == "http.request" and captured <= MAX_BODY_BYTES:
                chunk = message.get("body", b"")
                body_chunks.append(chunk)
                captured += len(chunk)
            return message

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            await self._write(scope, status_code, duration_ms, b"".join(body_chunks) if captured else b"")

    async def _write(self, scope: Scope, status_code: int, duration_ms: int, raw_body: bytes) -> None:
        try:
            state = scope.get("state") or {}
            principal: Principal | None = state.get("principal")
            endpoint = scope.get("endpoint")
            path_params = {k: str(v) for k, v in (scope.get("path_params") or {}).items()}
            headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
            client = extract_client_info(
                headers, (scope.get("client") or (None,))[0], trust_proxy=self._trust_proxy
            )

            entry = AuditLog(
                actor_kind=principal.kind if principal else "anonymous",
                user_id=principal.user_id if principal else None,
                user_email=principal.email if principal else None,
                user_role=principal.role if principal else None,
                action=state.get("audit_action") or (endpoint.__name__ if endpoint else "unmatched_route"),
                method=scope["method"],
                path=path_template(scope["path"], path_params)[:300],
                path_params=path_params,
                query=scope.get("query_string", b"").decode("latin-1")[:1000] or None,
                request_body=parse_body(raw_body) if scope["method"] in WRITE_METHODS else None,
                status_code=status_code,
                duration_ms=duration_ms,
                ip=client.ip,
                user_agent=client.user_agent,
                country=client.country,
                region=client.region,
                city=client.city,
                latitude=client.latitude,
                longitude=client.longitude,
                request_id=client.request_id,
            )
            async with self._session_factory() as session, session.begin():
                session.add(entry)
        except Exception:
            logger.exception("Audit jurnaliga yozib bo'lmadi")

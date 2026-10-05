"""Autentifikatsiya primitivlari: Supabase JWT tekshiruvi va AI agent API kaliti."""

import hmac
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

import jwt
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.domain.enums import UserRole

PrincipalKind = Literal["user", "agent"]


@dataclass(frozen=True, slots=True)
class Principal:
    """So'rov kimdan kelganini ifodalaydi (foydalanuvchi yoki AI agent)."""

    kind: PrincipalKind
    role: UserRole
    user_id: UUID | None = None
    email: str | None = None

    @property
    def is_agent(self) -> bool:
        return self.kind == "agent"


@dataclass(frozen=True, slots=True)
class TokenClaims:
    user_id: UUID
    email: str | None


class SupabaseTokenVerifier:
    """Supabase access token'ini tekshiradi.

    * ``SUPABASE_JWT_SECRET`` berilgan bo'lsa — HS256 (legacy secret).
    * Aks holda — ``SUPABASE_URL`` dagi JWKS orqali (RS256/ES256 asimmetrik kalitlar).
    """

    _ASYMMETRIC_ALGORITHMS = ["RS256", "ES256"]

    def __init__(self, settings: Settings) -> None:
        self._audience = settings.supabase_jwt_audience
        self._secret = settings.supabase_jwt_secret.get_secret_value() if settings.supabase_jwt_secret else None
        self._jwks_client = (
            jwt.PyJWKClient(settings.jwks_url, cache_keys=True, lifespan=3600)
            if not self._secret and settings.jwks_url
            else None
        )

    async def verify(self, token: str) -> TokenClaims:
        try:
            if self._secret:
                payload = jwt.decode(token, self._secret, algorithms=["HS256"], audience=self._audience)
            elif self._jwks_client:
                signing_key = await run_in_threadpool(self._jwks_client.get_signing_key_from_jwt, token)
                payload = jwt.decode(
                    token, signing_key.key, algorithms=self._ASYMMETRIC_ALGORITHMS, audience=self._audience
                )
            else:
                raise AuthenticationError("JWT tekshiruvi sozlanmagan (SUPABASE_JWT_SECRET yoki SUPABASE_URL)")
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Token muddati tugagan") from exc
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Token yaroqsiz") from exc

        try:
            user_id = UUID(str(payload["sub"]))
        except (KeyError, ValueError) as exc:
            raise AuthenticationError("Token'da foydalanuvchi identifikatori yo'q") from exc
        return TokenClaims(user_id=user_id, email=payload.get("email"))


class ApiKeyVerifier:
    """AI agent API kalitlarini doimiy vaqtda (timing-safe) solishtiradi."""

    def __init__(self, settings: Settings) -> None:
        self._keys = [key.get_secret_value().encode() for key in settings.ai_agent_api_keys]
        self._role = UserRole(settings.ai_agent_role)

    def verify(self, presented: str) -> Principal:
        candidate = presented.encode()
        # Barcha kalitlar bilan solishtiramiz — qaysi biri mos kelgani vaqtdan bilinmasin.
        matched = False
        for key in self._keys:
            matched |= hmac.compare_digest(candidate, key)
        if not matched:
            raise AuthenticationError("API kalit yaroqsiz")
        return Principal(kind="agent", role=self._role)

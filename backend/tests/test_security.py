"""Autentifikatsiya primitivlari — bazasiz, sof unit testlar."""

import base64
import json
import time
import uuid

import jwt
import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.core.security import ApiKeyVerifier, SupabaseTokenVerifier
from app.domain.enums import UserRole

SECRET = "unit-test-secret-0123456789-abcdefghijklmnopqrstuvwxyz"
AGENT_KEY = "k" * 40


def settings(**overrides) -> Settings:
    base = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "supabase_jwt_secret": SECRET,
        "ai_agent_api_keys": [AGENT_KEY],
    }
    return Settings(**(base | overrides))


def token(**claims) -> str:
    now = int(time.time())
    payload = {"sub": str(uuid.uuid4()), "aud": "authenticated", "iat": now, "exp": now + 60} | claims
    return jwt.encode(payload, claims.pop("_secret", SECRET), algorithm="HS256")


# ------------------------------------------------------------------- JWT
async def test_valid_token_returns_claims() -> None:
    user_id = uuid.uuid4()
    claims = await SupabaseTokenVerifier(settings()).verify(token(sub=str(user_id), email="a@b.uz"))
    assert claims.user_id == user_id and claims.email == "a@b.uz"


@pytest.mark.parametrize(
    ("bad_token", "message"),
    [
        (lambda: token(exp=int(time.time()) - 10), "muddati"),
        (lambda: token(aud="anon"), "yaroqsiz"),
        (lambda: jwt.encode({"sub": "x", "aud": "authenticated"}, "wrong-secret-" * 4, algorithm="HS256"), "yaroqsiz"),
        (lambda: token(sub="not-a-uuid"), "identifikatori"),
        (lambda: "not.a.jwt", "yaroqsiz"),
    ],
)
async def test_invalid_tokens_are_rejected(bad_token, message: str) -> None:
    with pytest.raises(AuthenticationError, match=message):
        await SupabaseTokenVerifier(settings()).verify(bad_token())


async def test_alg_none_token_is_rejected() -> None:
    unsigned = jwt.encode({"sub": str(uuid.uuid4()), "aud": "authenticated"}, key=None, algorithm="none")
    with pytest.raises(AuthenticationError):
        await SupabaseTokenVerifier(settings()).verify(unsigned)


async def test_asymmetric_token_without_jwks_is_rejected() -> None:
    # ES256 sarlavhali token, lekin SUPABASE_URL (JWKS) sozlanmagan — qabul qilinmasligi kerak.
    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    forged = f"{b64({'alg': 'ES256', 'typ': 'JWT'})}.{b64({'sub': str(uuid.uuid4())})}.c2lnbmF0dXJl"
    with pytest.raises(AuthenticationError):
        await SupabaseTokenVerifier(settings(supabase_url=None)).verify(forged)


async def test_hs256_token_rejected_when_no_secret_configured() -> None:
    with pytest.raises(AuthenticationError):
        await SupabaseTokenVerifier(settings(supabase_jwt_secret=None)).verify(token())


# ------------------------------------------------------------------- API key
def test_api_key_accepts_configured_key_with_configured_role() -> None:
    principal = ApiKeyVerifier(settings(ai_agent_role="viewer")).verify(AGENT_KEY)
    assert principal.is_agent and principal.role == UserRole.VIEWER and principal.user_id is None


@pytest.mark.parametrize("presented", ["", "k" * 39, "k" * 41, AGENT_KEY.upper()])
def test_api_key_rejects_anything_else(presented: str) -> None:
    with pytest.raises(AuthenticationError):
        ApiKeyVerifier(settings()).verify(presented)


def test_api_key_with_no_keys_configured_rejects_everything() -> None:
    with pytest.raises(AuthenticationError):
        ApiKeyVerifier(settings(ai_agent_api_keys=[])).verify(AGENT_KEY)


# ------------------------------------------------------------------- config
def test_short_api_keys_are_refused_at_startup() -> None:
    with pytest.raises(ValidationError, match="32"):
        settings(ai_agent_api_keys=["short"])


def test_comma_separated_env_values_are_split(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://a.uz, https://b.uz ,")
    monkeypatch.setenv("AI_AGENT_API_KEYS", f"{'a' * 32},{'b' * 32}")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    loaded = Settings(_env_file=None)
    assert loaded.cors_origins == ["https://a.uz", "https://b.uz"]
    assert [k.get_secret_value() for k in loaded.ai_agent_api_keys] == ["a" * 32, "b" * 32]


def test_jwks_url_is_derived_from_supabase_url() -> None:
    assert settings(supabase_url="https://x.supabase.co/").jwks_url == "https://x.supabase.co/auth/v1/.well-known/jwks.json"
    assert settings(supabase_url=None).jwks_url is None


def test_secrets_are_not_leaked_in_repr() -> None:
    text = repr(settings())
    assert SECRET not in text and AGENT_KEY not in text
    assert isinstance(settings().supabase_jwt_secret, SecretStr)

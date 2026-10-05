"""Integratsion testlar uchun fixture'lar.

Talab: ``TEST_DATABASE_URL`` — migratsiyalar qo'llangan alohida test bazasi
(lokal Postgres uchun avval database/local/000_supabase_stubs.sql ni ishga tushiring).
Bazadagi ma'lumotlar har sessiya boshida TOZALANADI — production bazani bermang!
"""

import os
import time
import uuid
from collections.abc import AsyncIterator

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.main import create_app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
JWT_SECRET = "test-jwt-secret-for-integration-tests-only-0123456789"
AGENT_KEY = "test-agent-key-0123456789-abcdefghijklmnopqrstuvwxyz"

requires_db = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL o'rnatilmagan")


def make_token(user_id: uuid.UUID, email: str) -> str:
    now = int(time.time())
    payload = {"sub": str(user_id), "email": email, "aud": "authenticated", "iat": now, "exp": now + 3600}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(
        database_url=TEST_DATABASE_URL or "postgresql+asyncpg://unused/unused",
        supabase_jwt_secret=JWT_SECRET,
        ai_agent_api_keys=[AGENT_KEY],
        ai_agent_role="manager",
        environment="development",
    )


@pytest.fixture(scope="session")
async def users(settings: Settings) -> dict[str, dict]:
    """Toza baza + 3 ta foydalanuvchi: admin (birinchi), manager, viewer."""
    engine = create_async_engine(settings.database_url)
    accounts = {name: {"id": uuid.uuid4(), "email": f"{name}@test.uz"} for name in ("admin", "manager", "viewer")}
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "truncate public.payment_allocations, public.payments, public.invoice_items, public.batches,"
                " public.invoices, public.ai_commands, public.counterparties, public.products,"
                " public.cash_registers, public.profiles, auth.users cascade"
            )
        )
        for name in ("admin", "manager", "viewer"):  # tartib muhim: birinchisi admin bo'ladi
            await conn.execute(
                text("insert into auth.users (id, email) values (:id, :email)"), accounts[name]
            )
        await conn.execute(
            text("update public.profiles set role = 'manager' where id = :id"), {"id": accounts["manager"]["id"]}
        )
        await conn.execute(text("insert into public.cash_registers (name) values ('Kassa Ombor')"))
    await engine.dispose()
    for account in accounts.values():
        account["headers"] = {"Authorization": f"Bearer {make_token(account['id'], account['email'])}"}
    return accounts


@pytest.fixture(scope="module")
async def clean_business_data(settings: Settings, users: dict) -> None:
    """Global yig'indilarni tekshiradigan modullar uchun: biznes jadvallarini tozalaydi
    (foydalanuvchilar va kassa saqlanadi, kassa balansi nolga qaytariladi)."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "truncate public.payment_allocations, public.payments, public.invoice_items, public.batches,"
                " public.invoices, public.ai_commands, public.counterparties, public.products cascade"
            )
        )
        await conn.execute(text("update public.cash_registers set balance = 0"))
    await engine.dispose()


@pytest.fixture(scope="session")
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test/api/v1") as http:
            yield http


@pytest.fixture(scope="session")
def agent_headers() -> dict[str, str]:
    return {"X-API-Key": AGENT_KEY}

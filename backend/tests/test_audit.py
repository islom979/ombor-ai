"""Audit jurnali: har bir so'rov kim/nima/qayerdan bilan yoziladi, admin ko'ra oladi."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.main import create_app
from tests.conftest import requires_db

pytestmark = [requires_db, pytest.mark.asyncio(loop_scope="session")]

GEO_HEADERS = {
    "x-real-ip": "213.230.100.7",
    "x-vercel-ip-country": "UZ",
    "x-vercel-ip-city": "Tashkent",
    "x-vercel-ip-latitude": "41.3",
    "x-vercel-ip-longitude": "69.24",
    "user-agent": "pytest-browser",
}


async def latest(settings: Settings, where: str = "true") -> dict | None:
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        row = (
            await conn.execute(text(f"select * from public.audit_logs where {where} order by id desc limit 1"))
        ).mappings().first()
    await engine.dispose()
    return dict(row) if row else None


@pytest.fixture(scope="module")
async def proxied(settings: Settings, users: dict) -> AsyncIterator[AsyncClient]:
    """Vercel ortidagi kabi: proxy sarlavhalariga ishonadigan ilova."""
    app = create_app(settings.model_copy(update={"trust_proxy_headers": True}))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as http:
            yield http


async def test_write_request_is_logged_with_user_ip_location_and_body(
    proxied: AsyncClient, users: dict, settings: Settings
) -> None:
    h = users["manager"]["headers"] | GEO_HEADERS
    response = await proxied.post("/products", json={"name": "Audit mahsulot", "unit": "kg"}, headers=h)
    assert response.status_code == 201

    row = await latest(settings, "action = 'create_product'")
    assert row is not None
    assert row["actor_kind"] == "user" and row["user_email"] == "manager@test.uz" and row["user_role"] == "manager"
    assert (row["method"], row["path"], row["status_code"]) == ("POST", "/api/v1/products", 201)
    assert row["request_body"] == {"name": "Audit mahsulot", "unit": "kg"}
    assert str(row["ip"]) == "213.230.100.7"
    assert (row["country"], row["city"], row["latitude"], row["longitude"]) == ("UZ", "Tashkent", 41.3, 69.24)
    assert row["user_agent"] == "pytest-browser" and row["duration_ms"] >= 0


async def test_path_template_and_params_are_stored(proxied: AsyncClient, users: dict, settings: Settings) -> None:
    product_id = (await latest(settings, "action = 'create_product'")) and (
        await proxied.get("/products", params={"search": "Audit mahsulot"}, headers=users["viewer"]["headers"])
    ).json()["items"][0]["id"]
    await proxied.get(f"/products/{product_id}", headers=users["viewer"]["headers"])
    row = await latest(settings, "action = 'get_product'")
    assert row["path"] == "/api/v1/products/{product_id}"
    assert row["path_params"] == {"product_id": product_id}
    assert row["request_body"] is None  # o'qish so'rovlarida tana saqlanmaydi


async def test_unauthenticated_and_forbidden_attempts_are_logged(
    proxied: AsyncClient, users: dict, settings: Settings
) -> None:
    await proxied.get("/stock", headers={"x-real-ip": "203.0.113.9"})
    row = await latest(settings, "host(ip) = '203.0.113.9'")
    assert row["actor_kind"] == "anonymous" and row["status_code"] == 401 and row["user_id"] is None

    await proxied.post("/products", json={"name": "x"}, headers=users["viewer"]["headers"])
    row = await latest(settings, "user_email = 'viewer@test.uz' and method = 'POST'")
    assert row["status_code"] == 403


async def test_agent_requests_are_attributed_to_agent(
    proxied: AsyncClient, agent_headers: dict, settings: Settings
) -> None:
    await proxied.get("/stock/summary", headers=agent_headers)
    row = await latest(settings, "action = 'stock_summary'")
    assert row["actor_kind"] == "agent" and row["user_id"] is None


async def test_login_and_logout_events(proxied: AsyncClient, users: dict, settings: Settings) -> None:
    h = users["admin"]["headers"] | GEO_HEADERS
    for event in ("login", "logout"):
        assert (await proxied.post("/auth/events", json={"event": event}, headers=h)).status_code == 204
        row = await latest(settings, f"action = 'auth.{event}'")
        assert row["user_email"] == "admin@test.uz" and row["city"] == "Tashkent"
    assert (await proxied.post("/auth/events", json={"event": "hack"}, headers=h)).status_code == 422


async def test_health_and_preflight_are_not_logged(proxied: AsyncClient, settings: Settings) -> None:
    before = await latest(settings)
    await proxied.get("http://test/health")
    await proxied.options("/stock", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert (await latest(settings))["id"] == before["id"]


async def test_spoofed_geo_headers_ignored_without_trust(client: AsyncClient, users: dict, settings: Settings) -> None:
    await client.get("/cash-registers", headers=users["viewer"]["headers"] | GEO_HEADERS)
    row = await latest(settings, "action = 'list_registers'")
    assert str(row["ip"]) == "127.0.0.1" and row["city"] is None


async def test_only_admin_reads_audit_log_with_filters(proxied: AsyncClient, users: dict) -> None:
    assert (await proxied.get("/audit-logs", headers=users["manager"]["headers"])).status_code == 403

    h = users["admin"]["headers"]
    auth = (await proxied.get("/audit-logs", params={"category": "auth"}, headers=h)).json()
    assert auth["total"] >= 2 and {i["action"] for i in auth["items"]} <= {"auth.login", "auth.logout"}

    by_ip = (await proxied.get("/audit-logs", params={"ip": "203.0.113.9"}, headers=h)).json()
    assert by_ip["total"] >= 1 and all(i["ip"] == "203.0.113.9" for i in by_ip["items"])

    errors = (await proxied.get("/audit-logs", params={"category": "error"}, headers=h)).json()
    assert all(i["status_code"] >= 400 for i in errors["items"])

    assert (await proxied.get("/audit-logs", params={"ip": "garbage"}, headers=h)).status_code == 200
    bad_range = await proxied.get("/audit-logs", params={"date_from": "2026-02-02", "date_to": "2026-02-01"}, headers=h)
    assert bad_range.status_code == 422


async def test_audit_failure_never_breaks_the_request(settings: Settings, users: dict) -> None:
    app = create_app(settings)

    class BrokenFactory:
        def __call__(self):
            raise RuntimeError("db down")

    # Middleware'ning sessiya fabrikasini buzamiz — so'rov baribir muvaffaqiyatli bo'lishi kerak.
    from app.core.audit_middleware import AuditMiddleware

    audit = next(m for m in app.user_middleware if m.cls is AuditMiddleware)
    audit.kwargs["session_factory"] = BrokenFactory()
    app.middleware_stack = None
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as http:
            response = await http.get("/cash-registers", headers=users["viewer"]["headers"])
    assert response.status_code == 200

"""API chegaraviy holatlari: validatsiya, ruxsatlar, biznes qoidalari buzilishi, xato formati."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import requires_db

pytestmark = [requires_db, pytest.mark.asyncio(loop_scope="session")]


def uniq(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def make_stock(client: AsyncClient, h: dict, quantity: str = "10") -> dict:
    product = (await client.post("/products", json={"name": uniq("P"), "min_stock": "2"}, headers=h)).json()
    supplier = (await client.post("/counterparties", json={"kind": "supplier", "name": uniq("S")}, headers=h)).json()
    customer = (await client.post("/counterparties", json={"kind": "client", "name": uniq("C")}, headers=h)).json()
    kirim = (
        await client.post(
            "/invoices/kirim",
            json={
                "supplier_id": supplier["id"],
                "items": [{"product_id": product["id"], "quantity": quantity, "purchase_price": "100", "sale_price": "150"}],
            },
            headers=h,
        )
    ).json()
    return {"product": product, "supplier": supplier, "customer": customer, "kirim": kirim}


# ------------------------------------------------------------ xato formati
async def test_validation_error_has_uniform_shape(client: AsyncClient, users: dict) -> None:
    response = await client.post("/products", json={"name": "", "unit": "tonna"}, headers=users["manager"]["headers"])
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert {e["field"] for e in error["details"]["errors"]} >= {"name", "unit"}


async def test_unknown_resource_returns_404(client: AsyncClient, users: dict) -> None:
    h = users["viewer"]["headers"]
    for path in (f"/products/{uuid.uuid4()}", f"/invoices/{uuid.uuid4()}", f"/counterparties/{uuid.uuid4()}"):
        response = await client.get(path, headers=h)
        assert response.status_code == 404, path
        assert response.json()["error"]["code"] == "not_found"


async def test_malformed_uuid_is_422_not_500(client: AsyncClient, users: dict) -> None:
    assert (await client.get("/invoices/not-a-uuid", headers=users["viewer"]["headers"])).status_code == 422


# ------------------------------------------------------------ ruxsatlar
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/products", {"name": "x"}),
        ("POST", "/counterparties", {"kind": "client", "name": "x"}),
        ("POST", "/invoices/kirim", {"supplier_id": str(uuid.uuid4()), "items": []}),
        ("POST", "/payments", {"counterparty_id": str(uuid.uuid4()), "amount": "1"}),
        ("POST", "/ai/commands", {"prompt": "salom"}),
        ("POST", "/cash-registers", {"name": "x"}),
    ],
)
async def test_viewer_cannot_write(client: AsyncClient, users: dict, method: str, path: str, body: dict) -> None:
    response = await client.request(method, path, json=body, headers=users["viewer"]["headers"])
    assert response.status_code == 403


async def test_manager_cannot_manage_users_or_registers(client: AsyncClient, users: dict) -> None:
    h = users["manager"]["headers"]
    assert (await client.post("/cash-registers", json={"name": uniq("K")}, headers=h)).status_code == 403
    target = users["viewer"]["id"]
    assert (await client.patch(f"/users/{target}/role", json={"role": "admin"}, headers=h)).status_code == 403


async def test_admin_cannot_demote_self(client: AsyncClient, users: dict) -> None:
    admin = users["admin"]
    response = await client.patch(f"/users/{admin['id']}/role", json={"role": "viewer"}, headers=admin["headers"])
    assert response.status_code == 409


async def test_token_for_user_without_profile_is_forbidden(client: AsyncClient) -> None:
    from tests.conftest import make_token

    response = await client.get("/stock", headers={"Authorization": f"Bearer {make_token(uuid.uuid4(), 'x@y.uz')}"})
    assert response.status_code == 403


# ------------------------------------------------------------ biznes qoidalari
async def test_kirim_rejects_wrong_counterparty_kind(client: AsyncClient, users: dict) -> None:
    h = users["manager"]["headers"]
    data = await make_stock(client, h)
    response = await client.post(
        "/invoices/kirim",
        json={
            "supplier_id": data["customer"]["id"],  # klient, ta'minotchi emas
            "items": [{"product_id": data["product"]["id"], "quantity": "1", "purchase_price": "1", "sale_price": "1"}],
        },
        headers=h,
    )
    assert response.status_code == 404


async def test_chiqim_rejects_batch_of_other_product(client: AsyncClient, users: dict) -> None:
    h = users["manager"]["headers"]
    first, second = await make_stock(client, h), await make_stock(client, h)
    response = await client.post(
        "/invoices/chiqim",
        json={
            "client_id": first["customer"]["id"],
            "items": [
                {
                    "product_id": first["product"]["id"],
                    "batch_id": second["kirim"]["items"][0]["batch_id"],
                    "quantity": "1",
                }
            ],
        },
        headers=h,
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "item_patch",
    [{"quantity": "0"}, {"quantity": "-1"}, {"unit_price": "-5"}, {"quantity": "1.0001"}],
)
async def test_chiqim_rejects_invalid_numbers(client: AsyncClient, users: dict, item_patch: dict) -> None:
    h = users["manager"]["headers"]
    data = await make_stock(client, h)
    item = {"product_id": data["product"]["id"], "quantity": "1"} | item_patch
    response = await client.post("/invoices/chiqim", json={"client_id": data["customer"]["id"], "items": [item]}, headers=h)
    assert response.status_code == 422


async def test_discount_over_100_is_rejected(client: AsyncClient, users: dict) -> None:
    h = users["manager"]["headers"]
    data = await make_stock(client, h)
    response = await client.post(
        "/invoices/chiqim",
        json={
            "client_id": data["customer"]["id"],
            "discount_percent": "100.5",
            "items": [{"product_id": data["product"]["id"], "quantity": "1"}],
        },
        headers=h,
    )
    assert response.status_code == 422


async def test_utilizatsiya_cannot_exceed_batch(client: AsyncClient, users: dict) -> None:
    h = users["manager"]["headers"]
    data = await make_stock(client, h, quantity="3")
    batch_id = data["kirim"]["items"][0]["batch_id"]
    response = await client.post(
        "/invoices/utilizatsiya", json={"note": "test", "items": [{"batch_id": batch_id, "quantity": "4"}]}, headers=h
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"


async def test_cannot_delete_product_with_stock_or_party_with_balance(client: AsyncClient, users: dict) -> None:
    h = users["manager"]["headers"]
    data = await make_stock(client, h)
    assert (await client.delete(f"/products/{data['product']['id']}", headers=h)).status_code == 409
    assert (await client.delete(f"/counterparties/{data['supplier']['id']}", headers=h)).status_code == 409
    # Balansi nol bo'lgan klientni o'chirish mumkin va u ro'yxatdan yo'qoladi
    assert (await client.delete(f"/counterparties/{data['customer']['id']}", headers=h)).status_code == 204
    assert (await client.get(f"/counterparties/{data['customer']['id']}", headers=h)).status_code == 404


async def test_payment_for_foreign_invoice_is_rejected(client: AsyncClient, users: dict) -> None:
    h = users["manager"]["headers"]
    first, second = await make_stock(client, h), await make_stock(client, h)
    response = await client.post(
        "/payments",
        json={
            "counterparty_id": first["supplier"]["id"],
            "amount": "10",
            "invoice_ids": [second["kirim"]["id"]],  # boshqa ta'minotchining invoysi
        },
        headers=h,
    )
    assert response.status_code == 422


async def test_supplier_payment_reduces_debt_and_cash(client: AsyncClient, users: dict) -> None:
    h = users["manager"]["headers"]
    data = await make_stock(client, h)  # kirim: 10 x 100 = 1000
    registers_before = {r["id"]: r["balance"] for r in (await client.get("/cash-registers", headers=h)).json()}
    payment = (await client.post("/payments", json={"counterparty_id": data["supplier"]["id"], "amount": "400"}, headers=h)).json()
    assert payment["direction"] == "outgoing"
    supplier = (await client.get(f"/counterparties/{data['supplier']['id']}", headers=h)).json()
    assert supplier["balance"] == 600.0
    registers_after = {r["id"]: r["balance"] for r in (await client.get("/cash-registers", headers=h)).json()}
    assert registers_after[payment["cash_register_id"]] == registers_before[payment["cash_register_id"]] - 400


# ------------------------------------------------------------ so'rov parametrlari
async def test_invoice_filters_validate_date_range(client: AsyncClient, users: dict) -> None:
    h = users["viewer"]["headers"]
    response = await client.get("/invoices", params={"date_from": "2026-05-02", "date_to": "2026-05-01"}, headers=h)
    assert response.status_code == 422
    assert (await client.get("/statistics", params={"date_from": "2026-05-02", "date_to": "2026-05-01"}, headers=h)).status_code == 422


@pytest.mark.parametrize("params", [{"size": 0}, {"size": 500}, {"page": 0}])
async def test_pagination_bounds(client: AsyncClient, users: dict, params: dict) -> None:
    assert (await client.get("/products", params=params, headers=users["viewer"]["headers"])).status_code == 422


async def test_search_escapes_like_wildcards(client: AsyncClient, users: dict) -> None:
    h = users["manager"]["headers"]
    await client.post("/products", json={"name": uniq("100% sharbat")}, headers=h)
    found = (await client.get("/products", params={"search": "100%"}, headers=h)).json()
    assert found["total"] >= 1
    # '%' oddiy belgi sifatida qidiriladi — hamma narsaga mos kelmaydi
    nothing = (await client.get("/products", params={"search": "%%%"}, headers=h)).json()
    assert nothing["total"] == 0


async def test_stock_export_is_csv_with_bom(client: AsyncClient, users: dict) -> None:
    response = await client.get("/stock/export", headers=users["viewer"]["headers"])
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert response.text.startswith("﻿Mahsulot,")


async def test_ai_command_cannot_be_reset_to_pending(client: AsyncClient, users: dict, agent_headers: dict) -> None:
    created = (await client.post("/ai/commands", json={"prompt": "test"}, headers=users["manager"]["headers"])).json()
    response = await client.patch(f"/ai/commands/{created['id']}", json={"status": "pending"}, headers=agent_headers)
    assert response.status_code == 422

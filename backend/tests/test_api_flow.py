"""To'liq biznes oqimi: kirim → qoldiq → chiqim (FIFO) → to'lov → statistika → AI navbat."""

import asyncio

import pytest
from httpx import AsyncClient

from tests.conftest import requires_db

pytestmark = [requires_db, pytest.mark.asyncio(loop_scope="session")]


async def test_auth_is_required(client: AsyncClient) -> None:
    response = await client.get("/stock")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"

    response = await client.get("/stock", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


async def test_me_and_roles(client: AsyncClient, users: dict) -> None:
    me = (await client.get("/users/me", headers=users["admin"]["headers"])).json()
    assert me["role"] == "admin"

    viewer = users["viewer"]["headers"]
    response = await client.post("/products", json={"name": "X"}, headers=viewer)
    assert response.status_code == 403
    assert (await client.get("/users", headers=users["manager"]["headers"])).status_code == 403


async def test_full_warehouse_flow(client: AsyncClient, users: dict, agent_headers: dict) -> None:
    h = users["manager"]["headers"]

    product = (await client.post("/products", json={"name": "Burger", "unit": "dona", "min_stock": 5}, headers=h)).json()
    dup = await client.post("/products", json={"name": "burger"}, headers=h)
    assert dup.status_code == 409

    supplier = (
        await client.post("/counterparties", json={"kind": "supplier", "name": "Sof food"}, headers=h)
    ).json()
    customer = (
        await client.post("/counterparties", json={"kind": "client", "name": "Elbek Baxt uyi"}, headers=h)
    ).json()

    # --- Kirim: ikki partiya (FIFO tekshirish uchun turli narxda)
    for price, quantity in (("24000", "3"), ("25000", "10")):
        response = await client.post(
            "/invoices/kirim",
            json={
                "supplier_id": supplier["id"],
                "items": [
                    {"product_id": product["id"], "quantity": quantity, "purchase_price": price, "sale_price": "32000"}
                ],
            },
            headers=h,
        )
        assert response.status_code == 201, response.text
        kirim = response.json()
        assert kirim["type"] == "kirim" and kirim["payment_status"] == "unpaid"
        assert kirim["items"][0]["batch_code"].endswith(f"-{price}-00{1 if price == '24000' else 2}")

    summary = (await client.get("/stock/summary", headers=h)).json()
    assert summary == {"total_products": 1, "total_batches": 2, "total_value": 322000.0, "low_stock_count": 0}
    assert (await client.get(f"/counterparties/{supplier['id']}", headers=h)).json()["balance"] == 322000.0

    # --- Chiqim: 5 dona, FIFO → 3 ta birinchi partiyadan, 2 ta ikkinchisidan; 10% chegirma
    response = await client.post(
        "/invoices/chiqim",
        json={"client_id": customer["id"], "discount_percent": "10", "items": [{"product_id": product["id"], "quantity": "5"}]},
        headers=h,
    )
    assert response.status_code == 201, response.text
    chiqim = response.json()
    assert [(i["quantity"], i["cost_price"]) for i in chiqim["items"]] == [(3.0, 24000.0), (2.0, 25000.0)]
    assert chiqim["subtotal"] == 160000.0 and chiqim["total"] == 144000.0

    # --- Yetarli bo'lmagan qoldiq — 409 va hech narsa o'zgarmaydi
    response = await client.post(
        "/invoices/chiqim",
        json={"client_id": customer["id"], "items": [{"product_id": product["id"], "quantity": "999"}]},
        headers=h,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"
    stock = (await client.get("/stock", headers=h)).json()
    assert [row["quantity"] for row in stock] == [8.0]
    assert stock[0]["is_low"] is False

    # --- Klient to'lovi: qisman → keyin to'liq
    payment = (
        await client.post("/payments", json={"counterparty_id": customer["id"], "amount": "100000"}, headers=h)
    ).json()
    assert payment["direction"] == "incoming"
    assert payment["allocations"][0]["amount"] == 100000.0
    invoice = (await client.get(f"/invoices/{chiqim['id']}", headers=h)).json()
    assert invoice["payment_status"] == "partial"

    await client.post(
        "/payments",
        json={"counterparty_id": customer["id"], "amount": "44000", "method": "card", "invoice_ids": [chiqim["id"]]},
        headers=h,
    )
    invoice = (await client.get(f"/invoices/{chiqim['id']}", headers=h)).json()
    assert invoice["payment_status"] == "paid" and invoice["paid_amount"] == 144000.0
    assert (await client.get(f"/counterparties/{customer['id']}", headers=h)).json()["balance"] == 0.0

    history = (await client.get("/payments", params={"counterparty_id": customer["id"]}, headers=h)).json()
    assert history["total"] == 2

    # --- Filtrlar
    page = (await client.get("/invoices", params={"type": "kirim", "size": 1}, headers=h)).json()
    assert page["total"] == 2 and page["pages"] == 2 and len(page["items"]) == 1

    # --- Statistika: foyda = 144000 - (3*24000 + 2*25000) = 22000
    stats = (await client.get("/statistics", headers=h)).json()
    assert stats["profit"] == 22000.0 and stats["revenue"] == 144000.0
    assert stats["cash_registers"][0]["balance"] == 144000.0
    assert {op["type"]: op["count"] for op in stats["operations"]} == {"kirim": 2, "chiqim": 1, "utilizatsiya": 0}

    # --- AI agent: API kalit bilan o'qiy oladi va yozuvlar 'ai' manbasi bilan belgilanadi
    agent_stock = await client.get("/stock", headers=agent_headers)
    assert agent_stock.status_code == 200
    response = await client.post(
        "/invoices/utilizatsiya",
        json={"note": "Muddati o'tgan", "items": [{"batch_id": stock[0]["batch_id"], "quantity": "1"}]},
        headers=agent_headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["source"] == "ai" and response.json()["payment_status"] == "paid"

    # --- CSV eksport
    export = await client.get("/stock/export", headers=h)
    assert export.status_code == 200 and "Burger" in export.text


async def test_concurrent_chiqim_never_oversells(client: AsyncClient, users: dict) -> None:
    h = users["manager"]["headers"]
    product = (await client.post("/products", json={"name": "Chips", "unit": "kg"}, headers=h)).json()
    supplier = (await client.post("/counterparties", json={"kind": "supplier", "name": "S2"}, headers=h)).json()
    customer = (await client.post("/counterparties", json={"kind": "client", "name": "C2"}, headers=h)).json()
    await client.post(
        "/invoices/kirim",
        json={
            "supplier_id": supplier["id"],
            "items": [{"product_id": product["id"], "quantity": "10", "purchase_price": "100", "sale_price": "150"}],
        },
        headers=h,
    )

    async def sell() -> int:
        response = await client.post(
            "/invoices/chiqim",
            json={"client_id": customer["id"], "items": [{"product_id": product["id"], "quantity": "4"}]},
            headers=h,
        )
        return response.status_code

    results = await asyncio.gather(*(sell() for _ in range(5)))
    assert sorted(results) == [201, 201, 409, 409, 409]
    stock = (await client.get("/stock", params={"search": "Chips"}, headers=h)).json()
    assert sum(row["quantity"] for row in stock) == 2.0


async def test_ai_command_queue(client: AsyncClient, users: dict, agent_headers: dict) -> None:
    h = users["manager"]["headers"]
    created = (await client.post("/ai/commands", json={"prompt": "Kam qolgan tovarlar?"}, headers=h)).json()
    assert created["status"] == "pending"

    # Foydalanuvchi claim qila olmaydi
    assert (await client.post("/ai/commands/claim", json={"worker_id": "w"}, headers=h)).status_code == 403

    claimed = await client.post("/ai/commands/claim", json={"worker_id": "worker-1"}, headers=agent_headers)
    assert claimed.status_code == 200 and claimed.json()["id"] == created["id"]
    assert claimed.json()["status"] == "running"
    empty = await client.post("/ai/commands/claim", json={"worker_id": "worker-1"}, headers=agent_headers)
    assert empty.status_code == 204

    done = await client.patch(
        f"/ai/commands/{created['id']}",
        json={
            "status": "completed",
            "response": "Kam qolgan tovar yo'q.",
            "tool_calls": [{"name": "get_stock_summary", "input": {}, "output": {"low_stock_count": 0}}],
            "model": "claude-opus-5-5",
        },
        headers=agent_headers,
    )
    assert done.status_code == 200 and done.json()["finished_at"]

    again = await client.patch(
        f"/ai/commands/{created['id']}", json={"status": "failed"}, headers=agent_headers
    )
    assert again.status_code == 409

    # Viewer boshqa foydalanuvchining buyrug'ini ko'rmaydi
    assert (await client.get(f"/ai/commands/{created['id']}", headers=users["viewer"]["headers"])).status_code == 404
    listing = (await client.get("/ai/commands", headers=h)).json()
    assert listing["items"][0]["tool_calls"][0]["name"] == "get_stock_summary"

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from ai_agent.agent import OmborAgent
from ai_agent.api_client import OmborApiClient
from ai_agent.config import AgentSettings
from ai_agent.tools import TOOLS, ToolExecutor, anthropic_tool_definitions, openai_function_definitions

SUPPLIER_ID = "11111111-1111-1111-1111-111111111111"
PRODUCT_ID = "22222222-2222-2222-2222-222222222222"


def make_api(handler) -> OmborApiClient:
    return OmborApiClient("http://api.test/api/v1", "k" * 40, transport=httpx.MockTransport(handler))


# ----------------------------------------------------------------- schemas
def test_schemas_are_self_contained_objects() -> None:
    definitions = anthropic_tool_definitions()
    assert len(definitions) == len(TOOLS)
    for tool in definitions:
        dumped = json.dumps(tool["input_schema"])
        assert "$ref" not in dumped and "$defs" not in dumped
        assert tool["input_schema"]["type"] == "object"
        assert tool["description"]

    kirim = next(t for t in definitions if t["name"] == "create_kirim")["input_schema"]
    assert set(kirim["required"]) == {"supplier_id", "items"}
    assert kirim["properties"]["items"]["items"]["required"] == ["product_id", "quantity", "purchase_price", "sale_price"]


def test_read_only_mode_hides_write_tools() -> None:
    names = {t["name"] for t in anthropic_tool_definitions(allow_writes=False)}
    assert "create_chiqim" not in names and "search_stock" in names
    assert all(f["type"] == "function" for f in openai_function_definitions())


# ----------------------------------------------------------------- executor
async def test_executor_validates_before_calling_api() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    async with make_api(handler) as api:
        outcome = await ToolExecutor(api).execute("create_kirim", {"supplier_id": "not-a-uuid", "items": []})
    assert outcome.is_error and not called
    fields = {p["field"] for p in outcome.output["problems"]}
    assert {"supplier_id", "items"} <= fields


async def test_executor_blocks_writes_when_disabled() -> None:
    async with make_api(lambda r: httpx.Response(500)) as api:
        outcome = await ToolExecutor(api, allow_writes=False).execute(
            "create_product", {"name": "Test"}
        )
    assert outcome.is_error and "o'chirilgan" in outcome.output["error"]


async def test_executor_maps_api_call_and_errors() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/invoices/kirim"):
            return httpx.Response(201, json={"number": "INV-1"})
        return httpx.Response(
            409, json={"error": {"code": "insufficient_stock", "message": "Burger yetarli emas", "details": {}}}
        )

    async with make_api(handler) as api:
        executor = ToolExecutor(api)
        ok = await executor.execute(
            "create_kirim",
            {
                "supplier_id": SUPPLIER_ID,
                "items": [{"product_id": PRODUCT_ID, "quantity": 2, "purchase_price": 24000, "sale_price": 32000}],
            },
        )
        failed = await executor.execute("create_chiqim", {"client_id": SUPPLIER_ID, "items": [{"product_id": PRODUCT_ID, "quantity": 5}]})

    assert ok.output == {"number": "INV-1"} and not ok.is_error
    assert seen[0].headers["X-API-Key"] == "k" * 40
    body = json.loads(seen[0].content)
    assert body["items"][0]["purchase_price"] == 24000 and "note" not in body
    assert failed.is_error and failed.output["code"] == "insufficient_stock"


async def test_unknown_tool_is_error() -> None:
    async with make_api(lambda r: httpx.Response(200, json={})) as api:
        outcome = await ToolExecutor(api).execute("drop_database", {})
    assert outcome.is_error


# ----------------------------------------------------------------- agent loop
class FakeMessages:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = responses
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self._responses.pop(0)


def block(**kwargs: Any) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


def response(content: list, stop_reason: str) -> SimpleNamespace:
    return SimpleNamespace(content=content, stop_reason=stop_reason, usage=SimpleNamespace(input_tokens=10, output_tokens=5))


@pytest.fixture
def settings() -> AgentSettings:
    return AgentSettings(ombor_api_key="k" * 40, claude_server_fallbacks=True)


async def test_agent_runs_parallel_tools_and_returns_text(settings: AgentSettings) -> None:
    fake = FakeMessages(
        [
            response(
                [
                    block(type="text", text="Tekshiraman"),
                    block(type="tool_use", id="t1", name="get_stock_summary", input={}),
                    block(type="tool_use", id="t2", name="search_stock", input={"low_only": True}),
                ],
                "tool_use",
            ),
            response([block(type="text", text="Kam qolgan tovar: 1 ta.")], "end_turn"),
        ]
    )
    client = SimpleNamespace(beta=SimpleNamespace(messages=fake))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/stock/summary"):
            return httpx.Response(200, json={"low_stock_count": 1})
        assert request.url.params["low_only"] == "true"
        return httpx.Response(200, json=[{"product_name": "Bedro"}])

    progress: list[str] = []

    async def on_tool(outcome) -> None:
        progress.append(outcome.name)

    async with make_api(handler) as api:
        agent = OmborAgent(client, ToolExecutor(api), settings)  # type: ignore[arg-type]
        result = await agent.run("Nima kam qoldi?", on_tool_call=on_tool)

    assert result.text == "Kam qolgan tovar: 1 ta." and result.succeeded
    assert progress == ["get_stock_summary", "search_stock"]
    assert result.input_tokens == 20

    first, second = fake.calls
    assert first["betas"] == ["server-side-fallback-2026-07-01"] and first["fallbacks"] == "default"
    assert first["output_config"] == {"effort": "medium"}
    # Ikkinchi so'rovda: user → assistant(tool_use) → user(ikkala tool_result bitta xabarda)
    tool_results = second["messages"][2]["content"]
    assert [r["tool_use_id"] for r in tool_results] == ["t1", "t2"]
    assert json.loads(tool_results[1]["content"])["count"] == 1


async def test_agent_handles_refusal(settings: AgentSettings) -> None:
    fake = FakeMessages([response([], "refusal")])
    client = SimpleNamespace(beta=SimpleNamespace(messages=fake))
    async with make_api(lambda r: httpx.Response(200, json={})) as api:
        result = await OmborAgent(client, ToolExecutor(api), settings).run("...")  # type: ignore[arg-type]
    assert not result.succeeded

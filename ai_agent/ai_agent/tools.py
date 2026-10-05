"""AI agent tool'lari (Function Calling / Tool Use).

Yagona haqiqat manbai — har bir tool uchun Pydantic kirish modeli:
  * undan JSON Schema avtomatik yasaladi (Anthropic ``input_schema`` va OpenAI/Open WebUI
    ``parameters`` formatlarida),
  * model yuborgan argumentlar ishga tushirishdan OLDIN shu model bilan tekshiriladi,
  * handler tekshirilgan argumentlarni FastAPI endpoint'iga aylantiradi.

Yangi tool qo'shish: kirish modelini yozing → handler yozing → ``TOOLS`` ga ``ToolSpec`` qo'shing.
"""

import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai_agent.api_client import OmborApiClient, OmborApiError

MAX_TOOL_OUTPUT_CHARS = 40_000

Unit = Literal["kg", "dona", "litr", "metr", "quti"]
CounterpartyKind = Literal["supplier", "client"]
InvoiceType = Literal["kirim", "chiqim", "utilizatsiya"]
PaymentStatus = Literal["unpaid", "partial", "paid"]
PaymentMethod = Literal["cash", "card", "transfer"]


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# =============================================================================
# Kirish modellari
# =============================================================================


class NoInput(ToolInput):
    pass


class SearchStockInput(ToolInput):
    search: str | None = Field(None, description="Mahsulot nomi, barcode yoki partiya kodi bo'yicha qidiruv")
    low_only: bool = Field(False, description="Faqat kam qolgan (min_stock dan past) mahsulotlar")


class ListProductsInput(ToolInput):
    search: str | None = Field(None, description="Mahsulot nomi yoki barcode")
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


class CreateProductInput(ToolInput):
    name: str = Field(min_length=1, max_length=200, description="Mahsulot nomi (takrorlanmas)")
    unit: Unit = Field("dona", description="O'lchov birligi")
    barcode: str | None = Field(None, max_length=64)
    min_stock: float = Field(0, ge=0, description="Shu miqdordan kam qolsa 'KAM QOLGAN' deb belgilanadi")
    default_sale_price: float = Field(0, ge=0, description="Standart sotuv narxi (so'm)")


class FindBatchesInput(ToolInput):
    search: str = Field(min_length=1, description="Mahsulot nomi yoki partiya kodi")
    limit: int = Field(20, ge=1, le=100)


class ListCounterpartiesInput(ToolInput):
    kind: CounterpartyKind | None = Field(None, description="supplier = ta'minotchi, client = klient")
    search: str | None = Field(None, description="Nom, telefon yoki manzil bo'yicha qidiruv")
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


class CounterpartyIdInput(ToolInput):
    counterparty_id: UUID


class CreateCounterpartyInput(ToolInput):
    kind: CounterpartyKind
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(None, max_length=32, description="Masalan: +998 90 123 45 67")
    address: str | None = Field(None, max_length=300)


class ListInvoicesInput(ToolInput):
    type: InvoiceType | None = None
    payment_status: PaymentStatus | None = None
    counterparty_id: UUID | None = None
    date_from: date | None = Field(None, description="YYYY-MM-DD, shu kun ham kiradi")
    date_to: date | None = Field(None, description="YYYY-MM-DD, shu kun ham kiradi")
    search: str | None = Field(None, description="Invoice raqami bo'yicha qidiruv")
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


class InvoiceIdInput(ToolInput):
    invoice_id: UUID


class KirimItem(ToolInput):
    product_id: UUID
    quantity: float = Field(gt=0)
    purchase_price: float = Field(ge=0, description="Xarid narxi, 1 birlik uchun (so'm)")
    sale_price: float = Field(ge=0, description="Sotuv narxi, 1 birlik uchun (so'm)")


class CreateKirimInput(ToolInput):
    supplier_id: UUID = Field(description="Ta'minotchi id (list_counterparties kind=supplier orqali toping)")
    items: list[KirimItem] = Field(min_length=1, max_length=100)
    note: str | None = Field(None, max_length=1000)


class ChiqimItem(ToolInput):
    product_id: UUID
    quantity: float = Field(gt=0)
    batch_id: UUID | None = Field(None, description="Aniq partiya. Berilmasa — FIFO (eng eski partiyadan)")
    unit_price: float | None = Field(None, ge=0, description="Sotuv narxi. Berilmasa — partiya sotuv narxi")


class CreateChiqimInput(ToolInput):
    client_id: UUID = Field(description="Klient id (list_counterparties kind=client orqali toping)")
    items: list[ChiqimItem] = Field(min_length=1, max_length=100)
    discount_percent: float = Field(0, ge=0, le=100)
    note: str | None = Field(None, max_length=1000)


class CreatePaymentInput(ToolInput):
    counterparty_id: UUID
    amount: float = Field(gt=0, description="To'lov summasi (so'm)")
    method: PaymentMethod = "cash"
    cash_register_id: UUID | None = Field(None, description="Berilmasa — birinchi faol kassa")
    invoice_ids: list[UUID] | None = Field(None, description="Faqat shu invoicelarni yopish. Berilmasa — eng eskisidan")
    note: str | None = Field(None, max_length=1000)


class ListPaymentsInput(ToolInput):
    counterparty_id: UUID | None = None
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


class StatisticsInput(ToolInput):
    date_from: date | None = Field(None, description="YYYY-MM-DD")
    date_to: date | None = Field(None, description="YYYY-MM-DD")


# =============================================================================
# Handlerlar — har biri bitta FastAPI endpoint'iga mos keladi
# =============================================================================

Handler = Callable[[OmborApiClient, Any], Awaitable[Any]]


def _body(args: BaseModel) -> dict[str, Any]:
    return args.model_dump(mode="json", exclude_none=True)


async def _get_stock_summary(api: OmborApiClient, _: NoInput) -> Any:
    return await api.get("/stock/summary")


async def _search_stock(api: OmborApiClient, a: SearchStockInput) -> Any:
    rows = await api.get("/stock", search=a.search, low_only=a.low_only)
    return {"count": len(rows), "rows": rows}


async def _list_products(api: OmborApiClient, a: ListProductsInput) -> Any:
    return await api.get("/products", search=a.search, page=a.page, size=a.size)


async def _create_product(api: OmborApiClient, a: CreateProductInput) -> Any:
    return await api.post("/products", _body(a))


async def _find_available_batches(api: OmborApiClient, a: FindBatchesInput) -> Any:
    return await api.get("/stock/available", search=a.search, limit=a.limit)


async def _list_counterparties(api: OmborApiClient, a: ListCounterpartiesInput) -> Any:
    return await api.get("/counterparties", kind=a.kind, search=a.search, page=a.page, size=a.size)


async def _get_counterparty(api: OmborApiClient, a: CounterpartyIdInput) -> Any:
    return await api.get(f"/counterparties/{a.counterparty_id}")


async def _create_counterparty(api: OmborApiClient, a: CreateCounterpartyInput) -> Any:
    return await api.post("/counterparties", _body(a))


async def _list_invoices(api: OmborApiClient, a: ListInvoicesInput) -> Any:
    return await api.get("/invoices", **a.model_dump(mode="json", exclude_none=True))


async def _get_invoice(api: OmborApiClient, a: InvoiceIdInput) -> Any:
    return await api.get(f"/invoices/{a.invoice_id}")


async def _create_kirim(api: OmborApiClient, a: CreateKirimInput) -> Any:
    return await api.post("/invoices/kirim", _body(a))


async def _create_chiqim(api: OmborApiClient, a: CreateChiqimInput) -> Any:
    return await api.post("/invoices/chiqim", _body(a))


async def _create_payment(api: OmborApiClient, a: CreatePaymentInput) -> Any:
    return await api.post("/payments", _body(a))


async def _list_payments(api: OmborApiClient, a: ListPaymentsInput) -> Any:
    return await api.get("/payments", counterparty_id=a.counterparty_id, page=a.page, size=a.size)


async def _list_cash_registers(api: OmborApiClient, _: NoInput) -> Any:
    return await api.get("/cash-registers")


async def _get_statistics(api: OmborApiClient, a: StatisticsInput) -> Any:
    return await api.get("/statistics", **a.model_dump(mode="json", exclude_none=True))


# =============================================================================
# Ro'yxat
# =============================================================================


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    input_model: type[ToolInput]
    handler: Handler
    mutating: bool = False


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "get_stock_summary",
        "Ombor bo'yicha umumiy ko'rsatkichlar: mahsulotlar soni, partiyalar soni, umumiy qiymat (so'm) "
        "va kam qolgan mahsulotlar soni. Ombor holati haqidagi umumiy savollarda birinchi navbatda ishlating.",
        NoInput,
        _get_stock_summary,
    ),
    ToolSpec(
        "search_stock",
        "Ombordagi qoldiqni partiyalar kesimida qaytaradi (mahsulot, partiya kodi, xarid/sotuv narxi, miqdor, "
        "umumiy qiymat, is_low). Muayyan mahsulot qoldig'ini yoki kam qolganlarni topish uchun.",
        SearchStockInput,
        _search_stock,
    ),
    ToolSpec(
        "list_products",
        "Mahsulotlar katalogi (umumiy qoldiq bilan). Kirim/chiqim qilishdan oldin product_id ni topish uchun.",
        ListProductsInput,
        _list_products,
    ),
    ToolSpec(
        "create_product",
        "Katalogga yangi mahsulot qo'shadi. Avval list_products bilan bunday mahsulot yo'qligini tekshiring.",
        CreateProductInput,
        _create_product,
        mutating=True,
    ),
    ToolSpec(
        "find_available_batches",
        "Qoldig'i bor partiyalarni qidiradi (chiqim uchun aniq partiya va uning sotuv narxini tanlashda).",
        FindBatchesInput,
        _find_available_batches,
    ),
    ToolSpec(
        "list_counterparties",
        "Ta'minotchilar (supplier) yoki klientlar (client) ro'yxati balans bilan. balance > 0 — biz ularga "
        "qarzdormiz; balance < 0 — ular bizga qarzdor.",
        ListCounterpartiesInput,
        _list_counterparties,
    ),
    ToolSpec(
        "get_counterparty",
        "Bitta ta'minotchi yoki klient ma'lumoti va joriy balansi.",
        CounterpartyIdInput,
        _get_counterparty,
    ),
    ToolSpec(
        "create_counterparty",
        "Yangi ta'minotchi yoki klient qo'shadi. Avval list_counterparties bilan dublikat yo'qligini tekshiring.",
        CreateCounterpartyInput,
        _create_counterparty,
        mutating=True,
    ),
    ToolSpec(
        "list_invoices",
        "Operatsiyalar tarixi (kirim/chiqim/utilizatsiya) filtrlar bilan: tur, to'lov holati, kontragent, "
        "sana oralig'i, invoice raqami. Natija sahifalangan (total, pages).",
        ListInvoicesInput,
        _list_invoices,
    ),
    ToolSpec(
        "get_invoice",
        "Bitta invoice tafsilotlari: mahsulotlar, partiyalar, narxlar, jami va to'lov holati.",
        InvoiceIdInput,
        _get_invoice,
    ),
    ToolSpec(
        "create_kirim",
        "Omborga KIRIM (ta'minotchidan tovar qabul qilish). Har bir qator uchun yangi partiya yaratiladi va "
        "ta'minotchi balansi oshadi. supplier_id va product_id larni oldindan aniqlang.",
        CreateKirimInput,
        _create_kirim,
        mutating=True,
    ),
    ToolSpec(
        "create_chiqim",
        "Ombordan CHIQIM (klientga tovar berish/sotish). Qoldiq yetarli bo'lmasa xato qaytadi. "
        "Klient balansi kamayadi (qarzga yoziladi), to'lov alohida create_payment bilan qilinadi.",
        CreateChiqimInput,
        _create_chiqim,
        mutating=True,
    ),
    ToolSpec(
        "create_payment",
        "To'lov qayd etish: klientdan pul olish yoki ta'minotchiga pul berish (yo'nalish kontragent turidan "
        "aniqlanadi). Summa eng eski ochiq invoicelarga taqsimlanadi.",
        CreatePaymentInput,
        _create_payment,
        mutating=True,
    ),
    ToolSpec(
        "list_payments",
        "To'lovlar tarixi (kassa, usul, summa, qaysi invoicelarga taqsimlangani).",
        ListPaymentsInput,
        _list_payments,
    ),
    ToolSpec("list_cash_registers", "Kassalar va ularning joriy balansi.", NoInput, _list_cash_registers),
    ToolSpec(
        "get_statistics",
        "Hisobot: ta'minotchilar/klientlar/mahsulotlar soni, tushum, tannarx, foyda, debitor/kreditor qarzlar, "
        "kassalar va operatsiyalar statistikasi (sana oralig'i bo'yicha).",
        StatisticsInput,
        _get_statistics,
    ),
)

TOOLS_BY_NAME: dict[str, ToolSpec] = {tool.name: tool for tool in TOOLS}


# =============================================================================
# JSON Schema eksport (Anthropic / OpenAI-mos Open WebUI)
# =============================================================================


def _inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Pydantic ``$defs``/``$ref`` larni ichiga joylaydi va keraksiz ``title`` larni olib tashlaydi."""
    defs = schema.get("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return resolve(defs[node["$ref"].split("/")[-1]])
            return {key: resolve(value) for key, value in node.items() if key not in ("title", "$defs")}
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    return resolve(schema)


def input_schema(spec: ToolSpec) -> dict[str, Any]:
    schema = _inline_refs(spec.input_model.model_json_schema())
    schema.setdefault("properties", {})
    schema["type"] = "object"
    return schema


def anthropic_tool_definitions(*, allow_writes: bool = True) -> list[dict[str, Any]]:
    """Claude Messages API ``tools`` parametri uchun."""
    return [
        {"name": spec.name, "description": spec.description, "input_schema": input_schema(spec)}
        for spec in TOOLS
        if allow_writes or not spec.mutating
    ]


def openai_function_definitions(*, allow_writes: bool = True) -> list[dict[str, Any]]:
    """OpenAI-mos format (Open WebUI, LiteLLM va boshqa function-calling klientlar uchun)."""
    return [
        {
            "type": "function",
            "function": {"name": spec.name, "description": spec.description, "parameters": input_schema(spec)},
        }
        for spec in TOOLS
        if allow_writes or not spec.mutating
    ]


# =============================================================================
# Ijrochi
# =============================================================================


@dataclass(slots=True)
class ToolOutcome:
    name: str
    input: dict[str, Any]
    output: Any
    is_error: bool
    duration_ms: int

    def as_text(self) -> str:
        """Model uchun tool_result matni (juda katta javoblar qisqartiriladi)."""
        text = json.dumps(self.output, ensure_ascii=False, default=str)
        if len(text) > MAX_TOOL_OUTPUT_CHARS:
            text = text[:MAX_TOOL_OUTPUT_CHARS] + '..." [javob qisqartirildi — filtr yoki sahifalashdan foydalaning]'
        return text

    def as_record(self) -> dict[str, Any]:
        """Bazaga (ai_commands.tool_calls) yoziladigan qisqa yozuv."""
        output = self.output
        if len(json.dumps(output, ensure_ascii=False, default=str)) > 4000:
            output = {"truncated": True, "preview": self.as_text()[:2000]}
        return {
            "name": self.name,
            "input": self.input,
            "output": output,
            "is_error": self.is_error,
            "duration_ms": self.duration_ms,
        }


class ToolExecutor:
    def __init__(self, api: OmborApiClient, *, allow_writes: bool = True) -> None:
        self._api = api
        self._allow_writes = allow_writes

    def definitions(self) -> list[dict[str, Any]]:
        return anthropic_tool_definitions(allow_writes=self._allow_writes)

    async def execute(self, name: str, raw_input: Any) -> ToolOutcome:
        started = time.perf_counter()
        raw = raw_input if isinstance(raw_input, dict) else {}

        def done(output: Any, *, is_error: bool) -> ToolOutcome:
            elapsed = int((time.perf_counter() - started) * 1000)
            return ToolOutcome(name=name, input=raw, output=output, is_error=is_error, duration_ms=elapsed)

        spec = TOOLS_BY_NAME.get(name)
        if spec is None:
            return done({"error": f"Noma'lum tool: {name}"}, is_error=True)
        if spec.mutating and not self._allow_writes:
            return done({"error": "Yozish amallari o'chirilgan (AGENT_ALLOW_WRITES=false)"}, is_error=True)

        try:
            args = spec.input_model.model_validate(raw)
        except ValidationError as exc:
            problems = [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]
            return done({"error": "Argumentlar noto'g'ri", "problems": problems}, is_error=True)

        try:
            return done(await spec.handler(self._api, args), is_error=False)
        except OmborApiError as exc:
            return done({"error": exc.message, "code": exc.code, "details": exc.details}, is_error=True)
        except httpx.HTTPError as exc:
            return done({"error": f"Backend bilan aloqa xatosi: {exc.__class__.__name__}"}, is_error=True)

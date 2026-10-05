"""Claude tool-use sikli: model → tool chaqiruvlari → FastAPI → natija → model ... → yakuniy javob."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from anthropic import AsyncAnthropic

from ai_agent.config import AgentSettings
from ai_agent.tools import ToolExecutor, ToolOutcome

logger = logging.getLogger("ai_agent")

SERVER_FALLBACK_BETA = "server-side-fallback-2026-07-01"

SYSTEM_PROMPT = """\
Sen "Ombor AI" — oziq-ovqat ulgurji omborini boshqarish tizimining yordamchisisan.
Foydalanuvchilar ombor xodimlari; ular bilan o'zbek tilida (lotin yozuvida), qisqa va aniq gaplash.

Tizim haqida:
- Kirim: ta'minotchidan tovar qabul qilish; har bir qator yangi partiya (batch) yaratadi.
- Chiqim: klientga tovar berish; partiya ko'rsatilmasa eng eski partiyadan (FIFO) olinadi.
- Kontragent balansi: musbat — biz unga qarzdormiz, manfiy — u bizga qarzdor.
- To'lov kontragent turiga qarab yo'naladi: klientdan kirim, ta'minotchiga chiqim.
- Barcha summalar so'mda.

Ish tartibi:
- Ma'lumotni faqat tool'lar orqali ol; hech qachon id, narx yoki qoldiqni o'ylab topma.
- Yozish amalidan (kirim, chiqim, to'lov, yangi mahsulot/kontragent) oldin kerakli id larni qidiruv
  tool'lari bilan aniqla. Nom bo'yicha bir nechta mos keladigan yozuv chiqsa yoki muhim ma'lumot
  (miqdor, narx, kontragent) yetishmasa — amalni bajarma, nima aniqlashtirilishi kerakligini yoz.
- Bir-biriga bog'liq bo'lmagan o'qish amallarini parallel chaqir.
- Tool xato qaytarsa, sababini tushuntir; mantiqiy bo'lsa boshqa yo'l bilan qayta urin.

Javob formati: avval natija (bajarilgan amal yoki savolga javob), keyin kerak bo'lsa qisqa jadval yoki
ro'yxat. Pul summalarini 1 234 567 so'm ko'rinishida yoz. Yaratilgan hujjatlarning raqamini ko'rsat.
"""

ToolCallback = Callable[[ToolOutcome], Awaitable[None]]


@dataclass(slots=True)
class AgentResult:
    text: str
    tool_calls: list[ToolOutcome] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    stop_reason: str | None = None
    succeeded: bool = True


class OmborAgent:
    def __init__(self, client: AsyncAnthropic, executor: ToolExecutor, settings: AgentSettings) -> None:
        self._client = client
        self._executor = executor
        self._settings = settings
        self._tools = executor.definitions()

    async def run(self, prompt: str, *, on_tool_call: ToolCallback | None = None) -> AgentResult:
        today = datetime.now(ZoneInfo("Asia/Tashkent")).strftime("%Y-%m-%d (%A)")
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": f"Bugungi sana: {today}\n\n{prompt}"},
        ]
        result = AgentResult(text="", model=self._settings.claude_model)

        for turn in range(self._settings.agent_max_turns):
            response = await self._create(messages)
            result.input_tokens += response.usage.input_tokens
            result.output_tokens += response.usage.output_tokens
            result.stop_reason = response.stop_reason
            logger.debug("turn=%s stop_reason=%s", turn, response.stop_reason)

            if response.stop_reason == "refusal":
                result.text = "So'rov xavfsizlik siyosati sababli bajarilmadi."
                result.succeeded = False
                return result

            # Assistant javobini o'zgartirmasdan qo'shamiz (thinking bloklari ham saqlanadi).
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "pause_turn":
                continue

            tool_uses = [block for block in response.content if block.type == "tool_use"]
            if response.stop_reason != "tool_use" or not tool_uses:
                result.text = self._final_text(response.content)
                if response.stop_reason == "max_tokens":
                    result.text += "\n\n[Javob uzunlik chegarasida to'xtadi]"
                return result

            outcomes = await asyncio.gather(
                *(self._executor.execute(block.name, block.input) for block in tool_uses)
            )
            for outcome in outcomes:
                result.tool_calls.append(outcome)
                if on_tool_call:
                    await on_tool_call(outcome)

            # Barcha tool natijalari BITTA user xabarida qaytariladi.
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": outcome.as_text(),
                            "is_error": outcome.is_error,
                        }
                        for block, outcome in zip(tool_uses, outcomes, strict=True)
                    ],
                }
            )

        result.text = "Amallar soni chegarasiga yetildi — so'rovni kichikroq qismlarga bo'lib bering."
        result.succeeded = False
        return result

    async def _create(self, messages: list[dict[str, Any]]):
        params: dict[str, Any] = {
            "model": self._settings.claude_model,
            "max_tokens": self._settings.claude_max_tokens,
            "system": SYSTEM_PROMPT,
            "tools": self._tools,
            "messages": messages,
            "output_config": {"effort": self._settings.claude_effort},
        }
        if self._settings.claude_server_fallbacks:
            return await self._client.beta.messages.create(
                **params, betas=[SERVER_FALLBACK_BETA], fallbacks="default"
            )
        return await self._client.beta.messages.create(**params)

    @staticmethod
    def _final_text(content: list[Any]) -> str:
        texts = [block.text for block in content if block.type == "text"]
        return "\n".join(texts).strip() or "(bo'sh javob)"

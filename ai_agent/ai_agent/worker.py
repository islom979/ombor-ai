"""AI buyruqlar navbatini qayta ishlovchi worker.

    python -m ai_agent.worker

Dashboard'dan yuborilgan buyruqlarni backend'dan ``claim`` qiladi, Claude bilan bajaradi,
har bir tool chaqiruvidan keyin oraliq natijani yozadi (dashboard jonli kuzatadi) va
yakuniy javobni saqlaydi.
"""

import asyncio
import contextlib
import logging
import signal
from typing import Any

import anthropic
import httpx

from ai_agent.agent import OmborAgent
from ai_agent.api_client import OmborApiClient, OmborApiError
from ai_agent.config import AgentSettings, get_settings
from ai_agent.tools import ToolExecutor, ToolOutcome

logger = logging.getLogger("ai_agent.worker")


class CommandWorker:
    def __init__(self, api: OmborApiClient, agent: OmborAgent, settings: AgentSettings) -> None:
        self._api = api
        self._agent = agent
        self._settings = settings
        self._stopping = asyncio.Event()

    def stop(self) -> None:
        self._stopping.set()

    async def run(self) -> None:
        loops = [
            asyncio.create_task(self._loop(f"{self._settings.worker_id}-{index}"))
            for index in range(self._settings.worker_concurrency)
        ]
        logger.info("Worker ishga tushdi: %s ta parallel oqim", len(loops))
        await asyncio.gather(*loops)

    async def _loop(self, worker_id: str) -> None:
        while not self._stopping.is_set():
            try:
                command = await self._api.claim_command(worker_id)
            except (OmborApiError, httpx.HTTPError) as exc:
                logger.warning("[%s] claim xatosi: %s", worker_id, exc)
                command = None
            if command is None:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self._stopping.wait(), timeout=self._settings.worker_poll_interval)
                continue
            await self.process(command)

    async def process(self, command: dict[str, Any]) -> None:
        command_id = command["id"]
        logger.info("Buyruq %s: %s", command_id, command["prompt"][:120])
        records: list[dict[str, Any]] = []

        async def report_progress(outcome: ToolOutcome) -> None:
            records.append(outcome.as_record())
            with contextlib.suppress(OmborApiError, httpx.HTTPError):
                await self._api.update_command(command_id, {"status": "running", "tool_calls": records})

        try:
            result = await self._agent.run(command["prompt"], on_tool_call=report_progress)
            payload = {
                "status": "completed" if result.succeeded else "failed",
                "response": result.text,
                "error": None if result.succeeded else result.text,
                "tool_calls": [call.as_record() for call in result.tool_calls],
                "model": result.model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            }
        except anthropic.RateLimitError:
            logger.warning("Buyruq %s: Claude rate limit", command_id)
            payload = self._failure(records, "Claude API so'rovlar chegarasi oshdi — birozdan so'ng qayta urining")
        except anthropic.APIStatusError as exc:
            logger.error("Buyruq %s: Claude API xatosi %s", command_id, exc.status_code)
            payload = self._failure(records, f"Claude API xatosi ({exc.status_code})")
        except anthropic.APIConnectionError:
            payload = self._failure(records, "Claude API bilan aloqa yo'q")
        except Exception:
            logger.exception("Buyruq %s: kutilmagan xato", command_id)
            payload = self._failure(records, "Agentda kutilmagan xato")

        try:
            await self._api.update_command(command_id, payload)
        except (OmborApiError, httpx.HTTPError):
            logger.exception("Buyruq %s natijasini saqlab bo'lmadi", command_id)

    @staticmethod
    def _failure(records: list[dict[str, Any]], message: str) -> dict[str, Any]:
        return {"status": "failed", "error": message, "tool_calls": records}


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")

    async with OmborApiClient(
        settings.ombor_api_url, settings.ombor_api_key.get_secret_value(), timeout=settings.ombor_api_timeout
    ) as api:
        executor = ToolExecutor(api, allow_writes=settings.agent_allow_writes)
        agent = OmborAgent(anthropic.AsyncAnthropic(), executor, settings)
        worker = CommandWorker(api, agent, settings)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):  # Windows'da add_signal_handler yo'q
                loop.add_signal_handler(sig, worker.stop)
        await worker.run()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())

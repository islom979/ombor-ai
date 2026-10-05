"""Terminaldan agent bilan ishlash.

    python -m ai_agent.cli "Kam qolgan tovarlarni ko'rsat"
    python -m ai_agent.cli            # interaktiv rejim
    python -m ai_agent.cli --export-tools openai > tools.json   # Open WebUI uchun
"""

import argparse
import asyncio
import json
import sys

import anthropic

from ai_agent.agent import OmborAgent
from ai_agent.api_client import OmborApiClient
from ai_agent.config import get_settings
from ai_agent.tools import ToolExecutor, ToolOutcome, anthropic_tool_definitions, openai_function_definitions


async def _print_tool(outcome: ToolOutcome) -> None:
    mark = "✗" if outcome.is_error else "✓"
    print(f"  {mark} {outcome.name}({json.dumps(outcome.input, ensure_ascii=False)}) — {outcome.duration_ms} ms")


async def run(prompts: list[str]) -> None:
    settings = get_settings()
    async with OmborApiClient(
        settings.ombor_api_url, settings.ombor_api_key.get_secret_value(), timeout=settings.ombor_api_timeout
    ) as api:
        agent = OmborAgent(
            anthropic.AsyncAnthropic(), ToolExecutor(api, allow_writes=settings.agent_allow_writes), settings
        )

        async def ask(prompt: str) -> None:
            result = await agent.run(prompt, on_tool_call=_print_tool)
            print(f"\n{result.text}\n")
            print(f"[{result.model} · {result.input_tokens} in / {result.output_tokens} out tokens]\n")

        if prompts:
            await ask(" ".join(prompts))
            return
        print("Ombor AI — savolingizni yozing (chiqish: Ctrl+C)")
        while True:
            try:
                prompt = (await asyncio.to_thread(input, "> ")).strip()
            except EOFError:
                return
            if prompt:
                await ask(prompt)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ombor AI agent")
    parser.add_argument("prompt", nargs="*", help="Buyruq matni (bo'sh bo'lsa — interaktiv rejim)")
    parser.add_argument("--export-tools", choices=["anthropic", "openai"], help="Tool JSON Schema'larini chiqarish")
    args = parser.parse_args()

    if args.export_tools:
        definitions = anthropic_tool_definitions() if args.export_tools == "anthropic" else openai_function_definitions()
        json.dump(definitions, sys.stdout, ensure_ascii=False, indent=2)
        return
    try:
        asyncio.run(run(args.prompt))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

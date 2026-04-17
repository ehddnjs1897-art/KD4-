import os
import asyncio
from typing import AsyncIterator
import anthropic
from tools import TOOL_DEFINITIONS, execute_tool

MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-7")
MAX_TURNS = 30


async def run_agent(
    prompt: str,
    system: str = "",
    progress_callback=None
) -> str:
    """
    Run a full autonomous agent loop until Claude decides to stop.
    Yields progress updates via progress_callback(str).
    Returns the final text response.
    """
    client = anthropic.AsyncAnthropic()
    messages = [{"role": "user", "content": prompt}]

    default_system = (
        "You are an autonomous agent running on the user's Mac. "
        "Use the provided tools to complete the task fully. "
        "After finishing, summarize what you did in Korean."
    )

    for turn in range(MAX_TURNS):
        response = await client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system or default_system,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b.text for b in response.content if b.type == "text" and b.text]

        if progress_callback and text_blocks:
            await progress_callback("\n".join(text_blocks))

        if response.stop_reason == "end_turn":
            return "\n".join(text_blocks) or "(작업 완료)"

        if not tool_calls:
            return "\n".join(text_blocks) or "(응답 없음)"

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for call in tool_calls:
            if progress_callback:
                await progress_callback(f"🔧 {call.name}({_summarize(call.input)})")
            result = await execute_tool(call.name, call.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

    return "최대 실행 횟수 초과 — 작업이 너무 복잡합니다."


def _summarize(d: dict) -> str:
    s = str(d)
    return s[:60] + "..." if len(s) > 60 else s

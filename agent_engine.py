import os
import re
import json
import asyncio
import subprocess
from tools import TOOL_DEFINITIONS, execute_tool
from memory import get_memory_context

MAX_TURNS = 20

_TOOL_DOCS = "\n".join(
    f"- {t['name']}: {t['description']}\n  params: {json.dumps(t['input_schema']['properties'])}"
    for t in TOOL_DEFINITIONS
)

AGENT_SYSTEM = f"""당신은 맥에서 실행되는 자율 에이전트입니다.
주어진 작업을 완료하기 위해 아래 도구들을 사용하세요.

사용 가능한 도구:
{_TOOL_DOCS}

도구를 사용할 때는 반드시 아래 형식으로 응답하세요:
<tool_call>
{{"name": "도구이름", "input": {{...}}}}
</tool_call>

도구 결과를 보고 추가 작업이 필요하면 다시 tool_call을 사용하세요.

최종 결과 응답 규칙 (반드시 지킬 것):
- 마크다운 문법 절대 사용 금지 (##, **, *,  `, ---, > 등 없이)
- 핸드폰에서 읽기 쉽게 짧고 간결하게
- 이모지로 항목 구분
- 한국어로 작성
- 기술적 용어 대신 누구나 이해할 수 있는 말로"""


def _parse_tool_calls(text: str) -> list[dict]:
    pattern = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
    calls = []
    for m in pattern.finditer(text):
        try:
            calls.append(json.loads(m.group(1)))
        except json.JSONDecodeError:
            pass
    return calls


def _strip_tool_calls(text: str) -> str:
    return re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL).strip()


_FORMAT_RULE = """

[출력 형식 규칙 - 반드시 따를 것]
- ## ** ` --- > 같은 마크다운 기호 절대 사용 금지
- 짧고 간결하게, 이모지로 항목 구분
- 누구나 읽기 쉬운 한국어로만 작성"""


def _run_claude_cli(prompt: str, system: str, model: str = "claude-sonnet-4-6") -> str:
    """claude CLI를 subprocess로 호출. system 프롬프트는 본문에 포함."""
    full = f"{system}\n\n---\n\n{prompt}{_FORMAT_RULE}" if system else f"{prompt}{_FORMAT_RULE}"
    try:
        result = subprocess.run(
            ["claude", "-p", full, "--model", model, "--dangerously-skip-permissions"],
            capture_output=True, text=True, timeout=600
        )
        if result.returncode != 0 and result.stderr:
            return f"[CLI 오류] {result.stderr[:500]}"
        return result.stdout.strip()
    except FileNotFoundError:
        return "[오류] claude CLI가 설치되지 않았습니다."
    except subprocess.TimeoutExpired:
        return "[오류] 응답 시간 초과 (600초)"


def _is_failure(text: str) -> bool:
    if not text or len(text.strip()) < 10:
        return True
    markers = ["[CLI 오류]", "[오류]", "최대 실행 횟수 초과"]
    return any(m in text for m in markers)


async def _run_agent_with_model(
    prompt: str,
    system: str,
    model: str,
    progress_callback
) -> str:
    mem_ctx = get_memory_context()
    mem_prefix = f"[장기 메모리]\n{mem_ctx}\n\n" if mem_ctx else ""
    conversation_parts = [f"{mem_prefix}작업: {prompt}"]

    for turn in range(MAX_TURNS):
        full_prompt = "\n\n".join(conversation_parts)
        sys_prompt = system or AGENT_SYSTEM

        response = await asyncio.get_event_loop().run_in_executor(
            None, _run_claude_cli, full_prompt, sys_prompt, model
        )

        tool_calls = _parse_tool_calls(response)
        clean_text = _strip_tool_calls(response)

        if progress_callback and clean_text:
            await progress_callback(clean_text)

        if not tool_calls:
            return clean_text or "(작업 완료)"

        conversation_parts.append(f"[에이전트 응답]\n{response}")

        tool_results = []
        for call in tool_calls:
            name = call.get("name", "")
            inp = call.get("input", {})
            if progress_callback:
                await progress_callback(f"🔧 {name}({str(inp)[:60]})")
            result = await execute_tool(name, inp)
            tool_results.append(f"[{name} 결과]\n{result}")

        conversation_parts.append("\n".join(tool_results))

    return "최대 실행 횟수 초과."


async def run_agent(
    prompt: str,
    system: str = "",
    progress_callback=None
) -> str:
    result = await _run_agent_with_model(prompt, system, "claude-sonnet-4-6", progress_callback)
    if _is_failure(result):
        if progress_callback:
            await progress_callback("⚙️ Sonnet 실패 — Opus 4.7로 재시도...")
        result = await _run_agent_with_model(prompt, system, "claude-opus-4-7", progress_callback)
    return result

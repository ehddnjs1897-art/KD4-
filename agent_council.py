from __future__ import annotations
import asyncio
import logging
from datetime import datetime
from typing import Optional, Callable
from agent_engine import run_agent

logger = logging.getLogger(__name__)

LABELS = {
    "analyst":     "🔵 분석가",
    "executor":    "🟠 실행자",
    "validator":   "🟢 검증자",
    "facilitator": "🎯 진행자",
}

ANALYST_SYSTEM = """당신은 AI 에이전트 팀의 분석 전문가입니다.

맡은 역할:
- 작업 전체를 파악하고 위험·고려사항을 먼저 짚어냅니다
- 실행 방향과 우선순위를 구체적으로 제안합니다
- 다른 팀원 발언을 보고 빠진 관점이 있으면 짚어줍니다

발언 스타일: 간결하게, 이모지로 항목 구분, 한국어, 마크다운 금지."""

EXECUTOR_SYSTEM = """당신은 AI 에이전트 팀의 실행 전문가입니다.
사용 가능한 도구(파일읽기/쓰기, 터미널, 브라우저 등)를 실제로 활용합니다.

맡은 역할:
- 분석가의 방향을 바탕으로 실제 도구를 사용해 작업을 수행합니다
- 무엇을 했는지, 결과가 어떤지 구체적으로 보고합니다
- 검증자의 피드백을 받으면 즉시 수정 작업에 들어갑니다
- 막히는 부분은 솔직하게 공유합니다

발언 스타일: 단계별로, 이모지로 항목 구분, 한국어, 마크다운 금지."""

VALIDATOR_SYSTEM = """당신은 AI 에이전트 팀의 검증 전문가입니다.

맡은 역할:
- 실행 결과의 품질을 엄격하게 검증합니다
- 테스트·확인 결과를 구체적으로 제시합니다
- 통과 / 재작업 중 하나를 명확히 판정합니다
- 완전히 완료됐다고 판단하면 반드시 첫 줄에 "✅ 검증 완료" 를 씁니다

발언 스타일: 명확한 판정, 이모지로 항목 구분, 한국어, 마크다운 금지."""

FACILITATOR_SYSTEM = """당신은 회의 진행자입니다.
현재 회의 상황을 보고 다음 발언자를 결정하세요.

반드시 아래 단어 중 하나만 답하세요 (다른 말 없이):
analyst
executor
validator
done

기준:
- analyst: 전략 재검토나 추가 분석이 필요할 때
- executor: 실행·수정 작업이 필요할 때
- validator: 결과 검증이 필요할 때
- done: 검증자가 "✅ 검증 완료" 판정을 내렸을 때"""


def _build_prompt(topic: str, transcript: list[dict], role: str) -> str:
    parts = [f"작업 주제: {topic}"]
    if transcript:
        parts.append("\n지금까지 회의 내용:")
        for turn in transcript:
            label = LABELS.get(turn["role"], turn["role"])
            parts.append(f"\n[{label}]\n{turn['message']}")
    parts.append(f"\n이제 {LABELS[role]} 차례입니다. 발언해주세요.")
    return "\n".join(parts)


async def _speak(role: str, topic: str, transcript: list[dict]) -> str:
    system = {"analyst": ANALYST_SYSTEM, "executor": EXECUTOR_SYSTEM, "validator": VALIDATOR_SYSTEM}[role]
    prompt = _build_prompt(topic, transcript, role)
    return await run_agent(prompt=prompt, system=system)


async def _next_speaker(topic: str, transcript: list[dict]) -> str:
    if not transcript:
        return "analyst"
    # Check if last validator message approved
    for turn in reversed(transcript):
        if turn["role"] == "validator" and "✅ 검증 완료" in turn["message"]:
            return "done"
        break

    summary_parts = [f"작업: {topic[:100]}\n\n회의 요약:"]
    for turn in transcript[-6:]:  # Last 6 turns for context
        label = LABELS.get(turn["role"], turn["role"])
        summary_parts.append(f"[{label}] {turn['message'][:200]}")

    prompt = "\n".join(summary_parts)
    result = await run_agent(prompt=prompt, system=FACILITATOR_SYSTEM)
    result = result.strip().lower().split()[0] if result.strip() else ""
    if result in ("analyst", "executor", "validator", "done"):
        return result

    # Fallback: structured cycle
    last_role = transcript[-1]["role"]
    cycle = {"analyst": "executor", "executor": "validator", "validator": "executor"}
    return cycle.get(last_role, "executor")


async def run_council(
    topic: str,
    project_name: str = "",
    progress_callback: Optional[Callable] = None,
    max_turns: int = 12,
) -> tuple[str, list[dict]]:
    """
    에이전트 회의 실행.
    반환: (최종결과, 회의록 리스트)
    회의록 형식: [{"role": str, "message": str, "timestamp": str}, ...]
    """
    transcript: list[dict] = []

    async def send(msg: str):
        if progress_callback:
            try:
                await progress_callback(msg)
            except Exception:
                pass

    label = f" | {project_name}" if project_name else ""
    await send(f"🏛 에이전트 회의 시작{label}\n📌 {topic[:80]}")

    # Structured opening: analyst → executor → validator (first 3 turns)
    opening = ["analyst", "executor", "validator"]

    for turn_idx in range(max_turns):
        if turn_idx < 3:
            role = opening[turn_idx]
        else:
            role = await _next_speaker(topic, transcript)

        if role == "done":
            break

        await send(f"\n{LABELS[role]} 발언 중...")

        message = await _speak(role, topic, transcript)
        transcript.append({
            "role": role,
            "message": message,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })

        # Send abbreviated view of the message
        preview = message[:600] + ("..." if len(message) > 600 else "")
        await send(f"{LABELS[role]}:\n{preview}")

        # Early exit if validator approved
        if role == "validator" and "✅ 검증 완료" in message:
            break

    # Final result = last validator or executor message
    final = ""
    for turn in reversed(transcript):
        if turn["role"] in ("validator", "executor"):
            final = turn["message"]
            break

    await send(f"🏁 회의 완료 ({len(transcript)}턴)")
    return final or "(회의 완료)", transcript

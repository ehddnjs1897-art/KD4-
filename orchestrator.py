import os
from agent_engine import run_agent
from agents.analyst import SYSTEM_PROMPT as ANALYST_PROMPT
from agents.executor import SYSTEM_PROMPT as EXECUTOR_PROMPT
from agents.validator import SYSTEM_PROMPT as VALIDATOR_PROMPT

MAX_RETRY_CYCLES = 3


async def run_orchestrated_task(task: str, progress_callback=None) -> str:
    """
    멀티 에이전트 루프:
    분석 → 실행 → 검증 → (재실행 필요시 반복) → 최종 보고
    """

    async def progress(msg: str):
        if progress_callback:
            await progress_callback(msg)

    await progress("🧠 [분석 에이전트] 태스크 분석 시작...")

    analyst_result = await run_agent(
        prompt=f"다음 태스크를 분석하세요: {task}",
        system=ANALYST_PROMPT,
        progress_callback=None,
    )

    await progress(f"📊 [분석 결과]\n{analyst_result[:500]}")

    execution_result = ""
    validation_result = ""

    for cycle in range(1, MAX_RETRY_CYCLES + 1):
        await progress(f"⚙️ [실행 에이전트] 실행 중 (시도 {cycle}/{MAX_RETRY_CYCLES})...")

        exec_prompt = (
            f"원래 태스크: {task}\n\n"
            f"분석 에이전트 지시사항:\n{analyst_result}"
        )
        if validation_result:
            exec_prompt += f"\n\n검증 에이전트 피드백:\n{validation_result}"

        execution_result = await run_agent(
            prompt=exec_prompt,
            system=EXECUTOR_PROMPT,
            progress_callback=None,
        )

        await progress(f"✏️ [실행 완료]\n{execution_result[:400]}")
        await progress("🔍 [검증 에이전트] 결과 검증 중...")

        validation_result = await run_agent(
            prompt=(
                f"원래 태스크: {task}\n\n"
                f"실행된 작업:\n{execution_result}"
            ),
            system=VALIDATOR_PROMPT,
            progress_callback=None,
        )

        await progress(f"🔎 [검증 결과]\n{validation_result[:400]}")

        if "APPROVED" in validation_result:
            await progress("✅ 검증 통과! 작업 완료.")
            break
        elif cycle < MAX_RETRY_CYCLES:
            await progress(f"♻️ 재작업 요청됨. {cycle + 1}번째 시도 준비...")
        else:
            await progress("⚠️ 최대 재시도 횟수 도달.")

    final = (
        f"📋 최종 보고\n\n"
        f"태스크: {task}\n\n"
        f"실행 결과:\n{execution_result}\n\n"
        f"검증:\n{validation_result}"
    )
    return final

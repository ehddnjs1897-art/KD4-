import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from telegram import Bot
from daily_scout import run_daily_scout
from agent_engine import run_agent
from task_queue import next_task, complete_task, list_tasks, start_task
from memory import memory_write

logger = logging.getLogger(__name__)

DAILY_HOUR = int(os.getenv("DAILY_REPORT_HOUR", "9"))

def _parse_ids() -> list[int]:
    raw = os.getenv("TELEGRAM_ALLOWED_USER_IDS") or os.getenv("TELEGRAM_ALLOWED_USER_ID", "")
    return [int(p) for p in raw.split(",") if p.strip().isdigit()]

ALLOWED_IDS = _parse_ids()
ALLOWED_USER_ID = ALLOWED_IDS[0] if ALLOWED_IDS else 0  # 관리자 = 첫 번째

# 일반 자율 실행 시간 (오전10, 오후12, 오후6)
AUTO_WORK_HOURS = [int(h) for h in os.getenv("AUTO_WORK_HOURS", "8,10,12,14,16,18,20,22").split(",")]

# 새벽 심층 작업 시간
NIGHT_WORK_HOUR = int(os.getenv("NIGHT_WORK_HOUR", "2"))

DAYTIME_PROMPT = """
맥 전체를 스캔해서 가장 중요한 미완성 작업 하나를 찾아 직접 처리해줘.

스캔 대상:
- ~/Desktop, ~/Documents, ~/Downloads
- ~/.claude/projects (Claude 대화 기록)

처리 기준:
1. 오늘 수정됐거나 최근 대화에서 언급된 작업 우선
2. 파일이 있으면 직접 수정/완성
3. 처리 후 무엇을 했는지 한국어로 보고

한 번에 한 가지만 처리하고 결과를 명확히 보고해줘.
"""

NIGHT_PROMPT = """
지금은 새벽이라 사용자가 자고 있습니다. 방해 없이 깊이 있는 작업을 할 수 있는 최적의 시간입니다.

다음을 순서대로 처리해줘:

1. 전체 스캔
   - ~/.claude/projects 에서 미완성 대화/작업 전부 찾기
   - ~/Desktop, ~/Documents, ~/Downloads 최근 파일 분석
   - 중요도 순으로 작업 목록 작성

2. 심층 작업 (최대 3가지)
   - 미완성 코드/문서 완성
   - 정리가 필요한 파일 구조 개선
   - README나 문서가 없는 프로젝트에 문서 추가

3. 정리
   - Downloads 폴더 오래된 파일 목록화
   - 중복/불필요한 파일 목록화 (삭제는 사용자 확인 후)

모든 작업 완료 후 아침에 사용자가 일어났을 때 볼 수 있게
"새벽 작업 보고서" 형식으로 한국어로 정리해서 보고해줘.
"""

HEARTBEAT_FILE = os.path.expanduser("~/claude-agent/HEARTBEAT.md")

HEARTBEAT_PROMPT = """HEARTBEAT.md 파일에 새 요청이 있습니다. 내용을 읽고 처리하세요.

처리 후:
1. 완료된 항목 앞에 ✅ 표시
2. 처리 결과를 HEARTBEAT.md 하단에 추가
3. 텔레그램으로 결과 보고

파일 경로: ~/claude-agent/HEARTBEAT.md
"""

CHECKOUT_PROMPT = """
사용자가 퇴근했습니다. 오늘 하루 작업을 정리하고 내일을 준비해줘.

할 일:
1. 오늘 수정된 파일들 정리 및 백업 확인
2. ~/.claude/projects 에서 오늘 대화 요약
3. 미완성으로 남은 작업 목록 파악
4. 내일 해야 할 일 우선순위 정리
5. 가능한 작업은 지금 바로 처리 (자동화 가능한 것들)

퇴근 보고서 형식으로 정리해서 보내줘:
- 오늘 완료한 것
- 미완성 남은 것
- 내일 우선순위
- 지금 자동 처리한 것
"""


async def _send(bot: Bot, text: str, admin_only: bool = False):
    """관리자 또는 전체 허용 사용자에게 메시지 전송."""
    targets = [ALLOWED_USER_ID] if admin_only else ALLOWED_IDS
    if not targets:
        return
    for uid in targets:
        if not uid:
            continue
        try:
            for i in range(0, len(text), 4000):
                await bot.send_message(chat_id=uid, text=text[i:i+4000])
        except Exception as e:
            logger.warning(f"_send uid={uid} 실패: {e}")


async def send_daily_report(bot: Bot):
    try:
        await _send(bot, "📋 오늘의 업무 보고서 작성 중...")
        report = await run_daily_scout()
        await _send(bot, report)
    except Exception as e:
        logger.error(f"Daily report failed: {e}")


LEARNING_PROMPT = """다음은 방금 완료한 작업과 결과입니다.

작업: {task}
결과 요약: {result}

이 작업에서 사용자가 자주 원할 만한 패턴, 선호도, 반복 가능한 교훈을 1-2줄로 뽑아주세요.
없으면 "없음"만 답하세요. 마크다운 금지, 한 줄로.
"""


async def process_task_queue(bot: Bot, max_tasks: int = 3) -> int:
    """대기 중인 작업 큐를 우선순위 순으로 처리 + 자동 학습."""
    processed = 0
    for _ in range(max_tasks):
        task = next_task()
        if not task:
            break
        start_task(task["id"])  # Mark immediately — prevents queue_worker double-execution
        try:
            await _send(bot, f"📝 큐 작업 시작 [{task['id']}] {task['priority']}\n{task['text']}")

            async def progress(msg: str):
                await _send(bot, msg)

            result = await run_agent(task["text"], progress_callback=progress)
            complete_task(task["id"], result)
            await _send(bot, f"✅ 큐 작업 완료 [{task['id']}]\n{result[:500]}")

            # 자동 학습 — 비동기로 교훈 추출
            try:
                lesson_prompt = LEARNING_PROMPT.format(
                    task=task["text"][:200], result=result[:500]
                )
                lesson = await run_agent(lesson_prompt)
                lesson = lesson.strip()
                if lesson and "없음" not in lesson and len(lesson) < 300:
                    memory_write("fact", lesson)
            except Exception:
                pass

            processed += 1
        except Exception as e:
            logger.error(f"Queue task {task['id']} failed: {e}")
            complete_task(task["id"], f"오류: {e}")
            await _send(bot, f"⚠️ 작업 실패 [{task['id']}]: {e}")
    return processed


async def run_auto_work(bot: Bot, night_mode: bool = False):
    """스스로 할 일 찾아서 실행. 큐 우선 소화 → 자율 탐색."""
    try:
        queued = await process_task_queue(bot, max_tasks=3 if not night_mode else 10)
        if queued > 0 and not night_mode:
            return

        prompt = NIGHT_PROMPT if night_mode else DAYTIME_PROMPT
        label = "🌙 새벽 심층 작업" if night_mode else "🤖 자율 작업"
        await _send(bot, f"{label} 시작...")

        async def progress(msg: str):
            await _send(bot, msg)

        result = await run_agent(prompt, progress_callback=progress)
        await _send(bot, f"✅ {label} 완료:\n{result}")
    except Exception as e:
        logger.error(f"Auto work failed: {e}")
        await _send(bot, f"⚠️ 작업 오류: {e}")


async def run_checkout(bot: Bot):
    """퇴근 모드 — 하루 정리 + 자율 작업."""
    try:
        await _send(bot, "🏠 퇴근 모드 시작! 오늘 하루 정리하고 할 수 있는 작업 처리할게요...")

        async def progress(msg: str):
            await _send(bot, msg)

        result = await run_agent(CHECKOUT_PROMPT, progress_callback=progress)
        await _send(bot, f"📊 퇴근 보고서:\n{result}")
    except Exception as e:
        await _send(bot, f"⚠️ 퇴근 모드 오류: {e}")


async def run_heartbeat(bot: Bot):
    """HEARTBEAT.md 파일 확인 후 내용 있으면 처리."""
    hb_path = Path(HEARTBEAT_FILE)
    if not hb_path.exists():
        return
    content = hb_path.read_text(encoding="utf-8").strip()
    if not content or content.startswith("# 처리 완료"):
        return
    try:
        await _send(bot, "💓 Heartbeat — 새 요청 감지, 처리 시작...")

        async def progress(msg: str):
            await _send(bot, msg)

        result = await run_agent(HEARTBEAT_PROMPT, progress_callback=progress)
        await _send(bot, f"💓 Heartbeat 완료:\n{result}")
    except Exception as e:
        logger.error(f"Heartbeat failed: {e}")


async def schedule_loop(bot: Bot):
    """매일 정해진 시간에 자동 실행."""
    last_report_date = None
    last_auto_work: dict[int, object] = {}
    last_heartbeat_min = -1

    while True:
        now = datetime.now()
        today = now.date()

        # 매일 오전 9시 — 업무 보고서
        if now.hour == DAILY_HOUR and today != last_report_date:
            await send_daily_report(bot)
            last_report_date = today

        # 오전10, 오후12, 오후6 — 일반 자율 작업
        for hour in AUTO_WORK_HOURS:
            if now.hour == hour and last_auto_work.get(hour) != today:
                await run_auto_work(bot, night_mode=False)
                last_auto_work[hour] = today

        # 새벽 2시 — 심층 자율 작업
        if now.hour == NIGHT_WORK_HOUR and last_auto_work.get(NIGHT_WORK_HOUR) != today:
            await run_auto_work(bot, night_mode=True)
            last_auto_work[NIGHT_WORK_HOUR] = today

        # 30분마다 — HEARTBEAT.md 확인
        current_slot = (now.hour * 60 + now.minute) // 30
        if current_slot != last_heartbeat_min:
            await run_heartbeat(bot)
            last_heartbeat_min = current_slot

        await asyncio.sleep(60)

import os
import asyncio
import logging
from datetime import datetime
from telegram import Bot
from daily_scout import run_daily_scout
from agent_engine import run_agent

logger = logging.getLogger(__name__)

DAILY_HOUR = int(os.getenv("DAILY_REPORT_HOUR", "9"))
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

# 자율 실행 시간대 (매일 이 시간에 스스로 할 일 찾아서 실행)
AUTO_WORK_HOURS = [int(h) for h in os.getenv("AUTO_WORK_HOURS", "10,14").split(",")]

AUTO_TASK_PROMPT = """
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


async def _send(bot: Bot, text: str):
    if not ALLOWED_USER_ID:
        return
    for i in range(0, len(text), 4000):
        await bot.send_message(chat_id=ALLOWED_USER_ID, text=text[i:i+4000])


async def send_daily_report(bot: Bot):
    try:
        await _send(bot, "📋 오늘의 업무 보고서 작성 중...")
        report = await run_daily_scout()
        await _send(bot, report)
        logger.info("Daily report sent.")
    except Exception as e:
        logger.error(f"Daily report failed: {e}")


async def run_auto_work(bot: Bot):
    """스스로 할 일 찾아서 실행."""
    try:
        await _send(bot, "🤖 자율 작업 시작 — 할 일을 스스로 찾아 처리합니다...")

        async def progress(msg: str):
            await _send(bot, msg)

        result = await run_agent(AUTO_TASK_PROMPT, progress_callback=progress)
        await _send(bot, f"✅ 자율 작업 완료:\n{result}")
        logger.info("Auto work completed.")
    except Exception as e:
        logger.error(f"Auto work failed: {e}")
        await _send(bot, f"⚠️ 자율 작업 오류: {e}")


async def schedule_loop(bot: Bot):
    """매일 정해진 시간에 자동 실행."""
    last_report_date = None
    last_auto_work: dict[int, object] = {}

    while True:
        now = datetime.now()
        today = now.date()

        # 매일 DAILY_HOUR시 — 업무 보고서
        if now.hour == DAILY_HOUR and today != last_report_date:
            await send_daily_report(bot)
            last_report_date = today

        # AUTO_WORK_HOURS 시간대 — 자율 작업 실행
        for hour in AUTO_WORK_HOURS:
            if now.hour == hour and last_auto_work.get(hour) != today:
                await run_auto_work(bot)
                last_auto_work[hour] = today

        await asyncio.sleep(60)

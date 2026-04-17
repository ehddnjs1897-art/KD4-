import os
import asyncio
import logging
from datetime import datetime
from telegram import Bot
from daily_scout import run_daily_scout

logger = logging.getLogger(__name__)

DAILY_HOUR = int(os.getenv("DAILY_REPORT_HOUR", "9"))
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))


async def send_daily_report(bot: Bot):
    if not ALLOWED_USER_ID:
        logger.warning("TELEGRAM_ALLOWED_USER_ID not set, skipping daily report.")
        return
    try:
        report = await run_daily_scout()
        chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
        for chunk in chunks:
            await bot.send_message(chat_id=ALLOWED_USER_ID, text=chunk)
        logger.info("Daily report sent.")
    except Exception as e:
        logger.error(f"Daily report failed: {e}")


async def schedule_loop(bot: Bot):
    """매일 DAILY_HOUR시에 보고서 전송."""
    last_sent_date = None
    while True:
        now = datetime.now()
        if now.hour == DAILY_HOUR and now.date() != last_sent_date:
            await send_daily_report(bot)
            last_sent_date = now.date()
        await asyncio.sleep(60)

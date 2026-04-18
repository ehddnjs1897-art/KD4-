import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from telegram_bot import build_app
from scheduler import schedule_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        raise EnvironmentError("TELEGRAM_BOT_TOKEN이 .env에 없습니다.")

    app = build_app()

    async with app:
        await app.start()
        logger.info("텔레그램 봇 시작됨. 폴링 중...")

        bot = app.bot
        scheduler_task = asyncio.create_task(schedule_loop(bot))

        await app.updater.start_polling(drop_pending_updates=True)

        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            scheduler_task.cancel()
            await app.updater.stop()
            await app.stop()
            logger.info("봇 종료됨.")


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from telegram import BotCommand
from telegram_bot import build_app, queue_worker
from scheduler import schedule_loop

BOT_COMMANDS = [
    ("menu", "전체 메뉴"),
    ("do", "단일 에이전트 실행"),
    ("team", "멀티 에이전트 팀"),
    ("report", "오늘 업무 보고"),
    ("checkout", "퇴근 정리"),
    ("task", "작업 큐에 추가"),
    ("tasks", "대기 작업 보기"),
    ("cancel", "작업 취소"),
    ("cleardone", "완료 작업 정리"),
    ("memory", "장기 기억 보기"),
    ("remember", "사실 기억"),
    ("forget", "메모리 초기화"),
    ("screen", "화면 캡처"),
    ("sysinfo", "시스템 정보"),
    ("stop", "현재 작업 중단"),
    ("status", "상태 확인"),
]

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "agent.log", encoding="utf-8"),
    ],
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
        try:
            await bot.set_my_commands([BotCommand(c, d) for c, d in BOT_COMMANDS])
            logger.info("Telegram 명령어 목록 등록됨")
        except Exception as e:
            logger.warning(f"명령어 등록 실패: {e}")

        scheduler_task = asyncio.create_task(schedule_loop(bot))
        worker_task = asyncio.create_task(queue_worker(bot))

        await app.updater.start_polling(drop_pending_updates=True)

        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            scheduler_task.cancel()
            worker_task.cancel()
            await app.updater.stop()
            await app.stop()
            logger.info("봇 종료됨.")


def run_with_recovery():
    """크래시 시 최대 5회, 지수 백오프로 자동 재시작."""
    retry_delay = 5
    max_delay = 300
    attempt = 0
    while True:
        attempt += 1
        try:
            asyncio.run(main())
            break
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            logger.exception(f"[시도 {attempt}] 봇 크래시: {e}")
            if attempt > 20:
                logger.error("20회 연속 실패 — 종료")
                break
            logger.info(f"{retry_delay}초 후 자동 재시작...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)


if __name__ == "__main__":
    run_with_recovery()

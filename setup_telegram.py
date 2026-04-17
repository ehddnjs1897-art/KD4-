"""
봇 토큰이 있으면 Telegram Bot API로 봇 프로필 자동 설정:
- 명령어 메뉴 등록
- 봇 설명 설정
- 봇 이름 설정
"""
import sys
import asyncio
from telegram import Bot, BotCommand


COMMANDS = [
    BotCommand("start",  "봇 시작 및 명령어 안내"),
    BotCommand("do",     "/do <작업> — 단일 에이전트 실행"),
    BotCommand("team",   "/team <작업> — 멀티 에이전트 팀 실행"),
    BotCommand("report", "오늘의 업무 보고서 받기"),
    BotCommand("stop",   "현재 작업 중단"),
    BotCommand("status", "현재 상태 확인"),
]

BOT_NAME        = "Claude 자율 에이전트"
BOT_DESCRIPTION = (
    "맥의 Claude를 원격으로 통제하는 자율 에이전트 봇입니다.\n\n"
    "• /do <작업> — 파일 읽기/쓰기, 코드 실행 등 자율 수행\n"
    "• /team <작업> — 분석→실행→검증 멀티 에이전트 팀\n"
    "• /report — 매일 업무 현황 자동 보고\n"
    "• /stop — 진행 중인 작업 즉시 중단\n\n"
    "텔레그램에서 명령하면 맥의 Claude가 알아서 처리합니다."
)
BOT_SHORT_DESC  = "핸드폰으로 맥 Claude를 자율 통제"


async def configure_bot(token: str):
    bot = Bot(token=token)

    me = await bot.get_me()
    print(f"  봇 확인: @{me.username} ({me.first_name})")

    await bot.set_my_commands(COMMANDS)
    print("  ✅ 명령어 메뉴 등록 완료")

    try:
        await bot.set_my_description(BOT_DESCRIPTION)
        print("  ✅ 봇 설명 설정 완료")
    except Exception:
        pass

    try:
        await bot.set_my_short_description(BOT_SHORT_DESC)
        print("  ✅ 짧은 설명 설정 완료")
    except Exception:
        pass

    print(f"\n  봇 링크: https://t.me/{me.username}")


if __name__ == "__main__":
    token = sys.argv[1] if len(sys.argv) > 1 else ""
    if not token:
        print("Usage: python setup_telegram.py <BOT_TOKEN>")
        sys.exit(1)
    asyncio.run(configure_bot(token))

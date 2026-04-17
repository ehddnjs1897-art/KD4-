"""
텔레그램 봇에게 아무 메시지나 보내면 내 user ID를 자동으로 캡처합니다.
setup.sh 에서 내부적으로 호출됩니다.
"""
import sys
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes


async def _capture(token: str) -> int:
    captured_id = None

    async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        nonlocal captured_id
        captured_id = update.effective_user.id
        name = update.effective_user.first_name or ""
        await update.message.reply_text(
            f"✅ ID 확인됨!\n\n"
            f"이름: {name}\n"
            f"User ID: {captured_id}\n\n"
            "setup.sh 로 돌아가서 계속 진행하세요."
        )

    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.ALL, handler))

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        print("  봇이 대기 중입니다. 텔레그램에서 봇에게 아무 메시지나 보내세요...", flush=True)
        for _ in range(60):
            await asyncio.sleep(1)
            if captured_id:
                break
        await app.updater.stop()
        await app.stop()

    return captured_id or 0


if __name__ == "__main__":
    token = sys.argv[1] if len(sys.argv) > 1 else ""
    if not token:
        print("Usage: python get_my_id.py <BOT_TOKEN>")
        sys.exit(1)
    uid = asyncio.run(_capture(token))
    print(f"CAPTURED_ID={uid}")

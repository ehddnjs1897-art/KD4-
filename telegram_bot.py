import os
import asyncio
import logging
import subprocess
import tempfile
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

from agent_engine import run_agent
from orchestrator import run_orchestrated_task
from daily_scout import run_daily_scout

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))
except ValueError:
    ALLOWED_USER_ID = 0

_active_tasks: dict[int, asyncio.Task] = {}


def _is_allowed(update: Update) -> bool:
    return ALLOWED_USER_ID == 0 or update.effective_user.id == ALLOWED_USER_ID


async def _send_chunks(update: Update, text: str):
    """Telegram has 4096 char limit per message."""
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i+4000])


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    await update.message.reply_text(
        "👋 안녕하세요! 맥 자율 에이전트입니다.\n\n"
        "명령어:\n"
        "/do <작업> — 단일 에이전트로 실행\n"
        "/team <작업> — 멀티 에이전트 팀으로 실행\n"
        "/report — 오늘의 업무 보고\n"
        "/stop — 현재 작업 중단\n"
        "/status — 현재 상태 확인\n\n"
        "또는 그냥 메시지를 보내면 /do와 동일하게 실행됩니다."
    )


async def cmd_do(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    task_text = " ".join(ctx.args) if ctx.args else ""
    if not task_text:
        await update.message.reply_text("사용법: /do <작업 내용>")
        return
    await _run_task(update, task_text, use_team=False)


async def cmd_team(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    task_text = " ".join(ctx.args) if ctx.args else ""
    if not task_text:
        await update.message.reply_text("사용법: /team <작업 내용>")
        return
    await _run_task(update, task_text, use_team=True)


async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    await update.message.reply_text("📋 업무 현황 스캔 중...")
    report = await run_daily_scout()
    await _send_chunks(update, report)


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    uid = update.effective_user.id
    task = _active_tasks.get(uid)
    if task and not task.done():
        task.cancel()
        await update.message.reply_text("⛔ 작업을 중단했습니다.")
    else:
        await update.message.reply_text("현재 실행 중인 작업이 없습니다.")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    uid = update.effective_user.id
    task = _active_tasks.get(uid)
    if task and not task.done():
        await update.message.reply_text("⚙️ 작업 실행 중...")
    else:
        await update.message.reply_text("✅ 대기 중 (작업 없음)")


async def cmd_screen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    await update.message.reply_text("📸 화면 캡처 중...")
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        subprocess.run(["screencapture", "-x", path], check=True, timeout=10)
        with open(path, "rb") as img:
            await update.message.reply_photo(img, caption="🖥 맥 현재 화면")
        os.unlink(path)
    except Exception as e:
        await update.message.reply_text(f"❌ 화면 캡처 실패: {e}")


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    await _run_task(update, update.message.text, use_team=False)


async def _run_task(update: Update, task_text: str, use_team: bool):
    uid = update.effective_user.id

    existing = _active_tasks.get(uid)
    if existing and not existing.done():
        await update.message.reply_text("⚠️ 이미 작업이 실행 중입니다. /stop 으로 중단하세요.")
        return

    mode = "🤝 팀 에이전트" if use_team else "🤖 에이전트"
    await update.message.reply_text(f"{mode} 작업 시작:\n_{task_text}_", parse_mode=ParseMode.MARKDOWN)

    async def progress(msg: str):
        try:
            await update.message.reply_text(msg)
        except Exception:
            pass

    async def _execute():
        try:
            if use_team:
                result = await run_orchestrated_task(task_text, progress_callback=progress)
            else:
                result = await run_agent(task_text, progress_callback=progress)
            await update.message.reply_text(f"✅ 완료:\n{result}")
        except asyncio.CancelledError:
            await update.message.reply_text("⛔ 작업이 취소됐습니다.")
        except Exception as e:
            await update.message.reply_text(f"❌ 오류: {e}")
        finally:
            _active_tasks.pop(uid, None)

    _active_tasks[uid] = asyncio.create_task(_execute())


def build_app() -> Application:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("do", cmd_do))
    app.add_handler(CommandHandler("team", cmd_team))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("screen", cmd_screen))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app

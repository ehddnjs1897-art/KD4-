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
from scheduler import run_checkout
from memory import memory_read, memory_write, _load as memory_load, _save as memory_save
from task_queue import (
    add_task, list_tasks, format_tasks_mobile,
    complete_task, cancel_task, clear_done, next_task,
)

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


MENU_TEXT = (
    "👋 맥 자율 에이전트\n\n"
    "🎯 실행\n"
    "/do <작업> — 단일 에이전트\n"
    "/team <작업> — 멀티 에이전트 팀\n"
    "/report — 오늘 업무 보고\n"
    "/checkout — 퇴근 모드\n\n"
    "📝 작업 큐\n"
    "/task <내용> [priority] — 작업 추가 (urgent/high/normal/low)\n"
    "/tasks — 대기 중 작업 목록\n"
    "/cancel <id> — 작업 취소\n"
    "/cleardone — 완료된 작업 삭제\n\n"
    "🧠 메모리\n"
    "/memory — 저장된 기억 보기\n"
    "/remember <내용> — 사실 기억\n"
    "/forget — 메모리 초기화\n\n"
    "🛠 시스템\n"
    "/screen — 화면 캡처\n"
    "/sysinfo — 배터리/디스크/CPU\n"
    "/stop — 현재 작업 중단\n"
    "/status — 상태 확인\n"
    "/menu — 이 메뉴 다시 보기"
)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    await update.message.reply_text(MENU_TEXT)


async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    await update.message.reply_text(MENU_TEXT)


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


async def cmd_checkout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    await update.message.reply_text("🏠 퇴근 모드 시작! 잠시 후 보고서를 보내드릴게요.")

    async def progress(msg: str):
        try:
            await update.message.reply_text(msg)
        except Exception:
            pass

    async def _execute():
        from telegram import Bot
        bot: Bot = ctx.bot
        from scheduler import run_checkout as _checkout
        await _checkout(bot)

    asyncio.create_task(_execute())


async def cmd_memory(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    await _send_chunks(update, memory_read())


async def cmd_remember(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    text = " ".join(ctx.args) if ctx.args else ""
    if not text:
        await update.message.reply_text("사용법: /remember <기억할 내용>")
        return
    result = memory_write("fact", text)
    await update.message.reply_text(f"🧠 {result}")


async def cmd_forget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    memory_save({"facts": [], "tasks": [], "preferences": {}, "notes": []})
    await update.message.reply_text("🧹 메모리 초기화 완료")


async def cmd_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    if not ctx.args:
        await update.message.reply_text("사용법: /task <내용> [urgent|high|normal|low]")
        return
    priority = "normal"
    args = list(ctx.args)
    if args[-1].lower() in {"urgent", "high", "normal", "low"}:
        priority = args.pop().lower()
    text = " ".join(args)
    tid = add_task(text, priority)
    await update.message.reply_text(f"📝 작업 추가됨 [{tid}] {priority}\n{text}")


async def cmd_tasks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    status = ctx.args[0] if ctx.args else "pending"
    await _send_chunks(update, format_tasks_mobile(status))


async def cmd_cancel_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    if not ctx.args:
        await update.message.reply_text("사용법: /cancel <작업id>")
        return
    tid = ctx.args[0]
    ok = cancel_task(tid)
    await update.message.reply_text(f"🗑 취소 {'완료' if ok else '실패 (id 없음)'}: {tid}")


async def cmd_cleardone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    clear_done()
    await update.message.reply_text("✅ 완료된 작업 전부 정리됨")


async def cmd_sysinfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    from mac_tools import system_info
    await update.message.reply_text(system_info())


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
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("do", cmd_do))
    app.add_handler(CommandHandler("team", cmd_team))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("screen", cmd_screen))
    app.add_handler(CommandHandler("checkout", cmd_checkout))
    app.add_handler(CommandHandler("memory", cmd_memory))
    app.add_handler(CommandHandler("remember", cmd_remember))
    app.add_handler(CommandHandler("forget", cmd_forget))
    app.add_handler(CommandHandler("task", cmd_task))
    app.add_handler(CommandHandler("tasks", cmd_tasks))
    app.add_handler(CommandHandler("cancel", cmd_cancel_task))
    app.add_handler(CommandHandler("cleardone", cmd_cleardone))
    app.add_handler(CommandHandler("sysinfo", cmd_sysinfo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app

from __future__ import annotations
import os
import asyncio
import logging
import subprocess
import tempfile
from typing import Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

from agent_engine import run_agent
from orchestrator import run_orchestrated_task
from daily_scout import run_daily_scout
from scheduler import run_checkout
from memory import memory_read, memory_write, _load as memory_load, _save as memory_save
from sync_engine import sync_all, log_telegram_message
from task_queue import (
    add_task, list_tasks, format_tasks_mobile,
    complete_task, cancel_task, clear_done, next_task, start_task,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _parse_allowed_ids() -> list[int]:
    # TELEGRAM_ALLOWED_USER_IDS=123,456  (신규, 첫 번째 = 관리자)
    # TELEGRAM_ALLOWED_USER_ID=123       (하위 호환)
    raw = os.getenv("TELEGRAM_ALLOWED_USER_IDS") or os.getenv("TELEGRAM_ALLOWED_USER_ID", "")
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids

ALLOWED_IDS: list[int] = _parse_allowed_ids()
ADMIN_ID: int = ALLOWED_IDS[0] if ALLOWED_IDS else 0

# 직원이 사용할 수 없는 관리자 전용 명령
ADMIN_ONLY_CMDS = {"stop", "forget", "checkout", "screen", "sysinfo"}

# Global state for queue worker
_default_chat_id: int = 0
_current_task_info: dict = {}
_current_execution: Optional[asyncio.Task] = None


def _is_allowed(update: Update) -> bool:
    if not ALLOWED_IDS:
        return True
    return update.effective_user.id in ALLOWED_IDS


def _is_admin(update: Update) -> bool:
    return ADMIN_ID == 0 or update.effective_user.id == ADMIN_ID


async def _deny_admin(update: Update):
    await update.message.reply_text("🔒 이 명령은 관리자만 사용할 수 있습니다.")


def _track_chat_id(update: Update):
    global _default_chat_id
    if _default_chat_id == 0 and update.effective_chat:
        _default_chat_id = update.effective_chat.id


async def _send_chunks(update: Update, text: str):
    """Telegram has 4096 char limit per message."""
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i+4000])


def _detect_priority(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["긴급", "urgent", "급해", "당장", "지금당장"]):
        return "urgent"
    if any(k in t for k in ["빨리", "빠르게", "서둘러", "우선", "high"]):
        return "high"
    if any(k in t for k in ["나중에", "여유", "천천히", "low"]):
        return "low"
    return "normal"


MENU_TEXT = (
    "👋 맥 자율 에이전트\n\n"
    "🎯 실행\n"
    "/do <작업> — 에이전트 큐에 추가\n"
    "/team <작업> — 멀티 에이전트 팀 큐에 추가\n"
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
    "/sync — 전체 데이터 동기화\n"
    "/menu — 이 메뉴 다시 보기"
)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    _track_chat_id(update)
    await update.message.reply_text(MENU_TEXT)


async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    _track_chat_id(update)
    await update.message.reply_text(MENU_TEXT)


async def cmd_do(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    task_text = " ".join(ctx.args) if ctx.args else ""
    if not task_text:
        await update.message.reply_text("사용법: /do <작업 내용>")
        return
    log_telegram_message(update.effective_user.id, f"/do {task_text}")
    await _enqueue_task(update, task_text, use_team=False)


async def cmd_team(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    raw = " ".join(ctx.args) if ctx.args else ""
    if not raw:
        await update.message.reply_text("사용법: /team <작업 내용>\n또는: /team 프로젝트명: 작업 내용")
        return
    # Parse optional "프로젝트명: 작업내용" syntax
    project_name = ""
    task_text = raw
    if ":" in raw:
        before, _, after = raw.partition(":")
        before = before.strip()
        after = after.strip()
        # Only treat as project prefix if the part before colon is short (not a URL)
        if after and len(before) <= 30 and " " not in before:
            project_name = before
            task_text = after
    log_telegram_message(update.effective_user.id, f"/team {raw}")
    await _enqueue_task(update, task_text, use_team=True, project_name=project_name)


async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    _track_chat_id(update)
    await update.message.reply_text("📋 업무 현황 스캔 중...")
    report = await run_daily_scout()
    await _send_chunks(update, report)


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    if not _is_admin(update):
        await _deny_admin(update)
        return
    global _current_execution
    if _current_execution and not _current_execution.done():
        _current_execution.cancel()
        await update.message.reply_text("⛔ 현재 작업을 중단했습니다.")
    else:
        await update.message.reply_text("현재 실행 중인 작업이 없습니다.")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    from datetime import datetime
    from memory import _load as mem_load
    from task_queue import _load as tq_load

    lines = [f"📊 에이전트 상태  {datetime.now().strftime('%m-%d %H:%M')}"]

    # 실행 중 작업
    if _current_task_info:
        tid = _current_task_info.get("tid", "?")
        text = _current_task_info.get("text", "")[:50]
        lines.append(f"\n⚙️ 실행 중 [{tid}]: {text}")
    else:
        lines.append("\n💤 실행 중인 작업 없음")

    # 큐 상태
    all_tasks = tq_load()
    pending = [t for t in all_tasks if t["status"] == "pending"]
    done = [t for t in all_tasks if t["status"] == "done"]
    urgent = [t for t in pending if t["priority"] in ("urgent", "high")]
    lines.append(f"📋 대기: {len(pending)}개" + (f"  🔴 긴급/높음: {len(urgent)}개" if urgent else "") +
                 f"  ✅ 완료: {len(done)}개")

    # 메모리 상태
    mem = mem_load()
    facts = len(mem.get("facts", []))
    prefs = len(mem.get("preferences", {}))
    notes = len(mem.get("notes", []))
    lines.append(f"🧠 메모리: 사실 {facts}개 / 설정 {prefs}개 / 메모 {notes}개")

    # 마지막 동기화 시각 (facts에서 태그 탐색)
    last_sync = ""
    for f in reversed(mem.get("facts", [])):
        if "[동기화:" in f.get("text", ""):
            last_sync = f.get("date", "")[:16]
            break
    lines.append(f"🔄 마지막 동기화: {last_sync or '없음'}")

    # 다음 스케줄
    now = datetime.now()
    from scheduler import AUTO_WORK_HOURS, DAILY_HOUR, NIGHT_WORK_HOUR
    future_hours = sorted([h for h in AUTO_WORK_HOURS + [DAILY_HOUR, NIGHT_WORK_HOUR] if h > now.hour])
    next_h = future_hours[0] if future_hours else AUTO_WORK_HOURS[0]
    lines.append(f"⏰ 다음 자율 실행: {next_h:02d}:00")

    await update.message.reply_text("\n".join(lines))


async def cmd_checkout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    if not _is_admin(update):
        await _deny_admin(update)
        return
    _track_chat_id(update)
    await update.message.reply_text("🏠 퇴근 모드 시작! 잠시 후 보고서를 보내드릴게요.")

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
    if not _is_admin(update):
        await _deny_admin(update)
        return
    memory_save({"facts": [], "tasks": [], "preferences": {}, "notes": []})
    await update.message.reply_text("🧹 메모리 초기화 완료")


async def cmd_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    _track_chat_id(update)
    if not ctx.args:
        await update.message.reply_text("사용법: /task <내용> [urgent|high|normal|low]")
        return
    priority = "normal"
    args = list(ctx.args)
    if args[-1].lower() in {"urgent", "high", "normal", "low"}:
        priority = args.pop().lower()
    text = " ".join(args)
    chat_id = update.effective_chat.id
    tid = add_task(text, priority, meta={"chat_id": chat_id, "use_team": False})
    pending = list_tasks("pending")
    pos = next((i + 1 for i, t in enumerate(pending) if t["id"] == tid), len(pending))
    icon = {"urgent": "🔴", "high": "🟠", "normal": "🟡", "low": "🟢"}.get(priority, "🟡")
    await update.message.reply_text(
        f"{icon} 작업 추가됨 [{tid}] ({priority})\n{text}\n📋 대기 순번: {pos}번째"
    )


async def cmd_tasks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    status = ctx.args[0] if ctx.args else "pending"
    await _send_chunks(update, format_tasks_mobile(status))


async def cmd_cancel_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    if not ctx.args:
        await update.message.reply_text("사용법: /cancel <작업id|all>")
        return
    arg = ctx.args[0].lower()
    if arg == "all":
        from task_queue import _load as tq_load, _save as tq_save
        tasks = tq_load()
        removed = [t for t in tasks if t["status"] == "pending"]
        tq_save([t for t in tasks if t["status"] != "pending"])
        await update.message.reply_text(f"🗑 대기 중 작업 {len(removed)}개 전부 취소됨")
        return
    ok = cancel_task(arg)
    await update.message.reply_text(f"🗑 취소 {'완료' if ok else '실패 (id 없음)'}: {arg}")


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    from task_queue import _load as tq_load
    tasks = tq_load()
    done = [t for t in tasks if t["status"] == "done"]
    done.sort(key=lambda t: t.get("completed") or "", reverse=True)
    if not done:
        await update.message.reply_text("📭 완료된 작업 기록 없음")
        return
    lines = []
    for t in done[:15]:
        ts = (t.get("completed") or "")[:16].replace("T", " ")
        mode = "🤝" if t.get("meta", {}).get("use_team") else "🤖"
        lines.append(f"{mode} [{t['id']}] {ts}\n  {t['text'][:60]}")
    await _send_chunks(update, "📜 완료 작업 기록 (최근 15개)\n\n" + "\n".join(lines))


async def cmd_cleardone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    clear_done()
    await update.message.reply_text("✅ 완료된 작업 전부 정리됨")


async def cmd_sysinfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    if not _is_admin(update):
        await _deny_admin(update)
        return
    from mac_tools import system_info
    await update.message.reply_text(system_info())


async def cmd_screen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    if not _is_admin(update):
        await _deny_admin(update)
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


async def cmd_sync(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    _track_chat_id(update)
    await update.message.reply_text("🔄 전체 데이터 동기화 시작...\nClaude 대화 / Telegram / 작업기록 / Notion")

    async def progress(msg: str):
        try:
            await update.message.reply_text(msg)
        except Exception:
            pass

    asyncio.create_task(sync_all(progress_callback=progress))


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    # 모든 메시지 로컬 기록
    log_telegram_message(update.effective_user.id, update.message.text)
    await _enqueue_task(update, update.message.text, use_team=False)


async def _enqueue_task(update: Update, task_text: str, use_team: bool, project_name: str = ""):
    _track_chat_id(update)
    chat_id = update.effective_chat.id
    priority = _detect_priority(task_text)
    meta = {"chat_id": chat_id, "use_team": use_team, "project_name": project_name}
    tid = add_task(task_text, priority, meta)

    pending = list_tasks("pending")
    pos = next((i + 1 for i, t in enumerate(pending) if t["id"] == tid), len(pending))

    icon = {"urgent": "🔴", "high": "🟠", "normal": "🟡", "low": "🟢"}.get(priority, "🟡")
    if pos == 1 and not _current_task_info:
        status_line = "⚡ 즉시 실행됩니다"
    else:
        in_queue = len(pending)
        status_line = f"📋 대기 순번: {pos}번째 (총 {in_queue}개)"

    mode = "🤝 팀" if use_team else "🤖"
    await update.message.reply_text(
        f"{icon}{mode} [{tid}] ({priority})\n{task_text[:100]}\n{status_line}"
    )


async def queue_worker(bot):
    """연속 큐 워커 — 대기 작업을 순서대로 실행."""
    global _current_task_info, _current_execution
    logger.info("큐 워커 시작됨")
    while True:
        try:
            task = next_task()
            if not task:
                await asyncio.sleep(0.5)
                continue

            tid = task["id"]
            text = task["text"]
            meta = task.get("meta", {})
            chat_id = meta.get("chat_id") or _default_chat_id
            use_team = meta.get("use_team", False)

            # Mark as in_progress immediately (no await between next_task and start_task)
            start_task(tid)
            _current_task_info = {"tid": tid, "text": text, "chat_id": chat_id}

            if not chat_id:
                complete_task(tid, "chat_id 없음 — 스킵")
                _current_task_info = {}
                continue

            async def progress(msg: str):
                try:
                    await bot.send_message(chat_id=chat_id, text=msg)
                except Exception:
                    pass

            try:
                pending_count = len(list_tasks("pending"))
                queue_note = f" (대기: {pending_count}개)" if pending_count > 0 else ""
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚙️ 실행 중 [{tid}]{queue_note}:\n{text[:100]}"
                )

                if use_team:
                    project_name = meta.get("project_name", "")
                    coro = run_orchestrated_task(text, progress_callback=progress, project_name=project_name)
                else:
                    coro = run_agent(text, progress_callback=progress)

                _current_execution = asyncio.create_task(coro)
                result = await _current_execution

                complete_task(tid, result[:500])

                remaining = len(list_tasks("pending"))
                footer = f"\n\n📋 남은 대기: {remaining}개" if remaining > 0 else ""
                for i in range(0, min(len(result), 3800), 3800):
                    chunk = result[i:i+3800]
                    suffix = footer if i + 3800 >= len(result) else ""
                    await bot.send_message(chat_id=chat_id, text=f"✅ 완료 [{tid}]:\n{chunk}{suffix}")

            except asyncio.CancelledError:
                complete_task(tid, "사용자 취소")
                try:
                    await bot.send_message(chat_id=chat_id, text=f"⛔ 작업 취소됨 [{tid}]")
                except Exception:
                    pass
            except Exception as e:
                logger.exception(f"큐 워커 작업 실행 오류 [{tid}]: {e}")
                complete_task(tid, f"오류: {str(e)[:200]}")
                try:
                    await bot.send_message(chat_id=chat_id, text=f"❌ 오류 [{tid}]: {e}")
                except Exception:
                    pass
            finally:
                _current_task_info = {}
                _current_execution = None

        except asyncio.CancelledError:
            logger.info("큐 워커 종료됨")
            break
        except Exception as e:
            logger.exception(f"큐 워커 루프 오류: {e}")
            await asyncio.sleep(5)


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
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("cleardone", cmd_cleardone))
    app.add_handler(CommandHandler("sysinfo", cmd_sysinfo))
    app.add_handler(CommandHandler("sync", cmd_sync))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app

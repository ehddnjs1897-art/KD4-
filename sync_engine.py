from __future__ import annotations
import json
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Callable
from agent_engine import run_agent
from memory import memory_write

logger = logging.getLogger(__name__)

TELEGRAM_LOG = Path.home() / ".claude-agent" / "telegram_log.jsonl"


# ─── 데이터 읽기 ───────────────────────────────────────────────


def _extract_text(obj: dict) -> str:
    content = obj.get("content") or obj.get("message", {}).get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text") or block.get("content") or "")
        return " ".join(filter(None, parts))
    return ""


def _read_claude_conversations(max_chars: int = 6000) -> str:
    """~/.claude/projects 의 최근 대화에서 사용자 발언 추출."""
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        return ""
    files = sorted(claude_dir.rglob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    excerpts = []
    for f in files[:30]:
        try:
            for line in f.read_text(errors="replace").strip().split("\n")[-80:]:
                try:
                    obj = json.loads(line)
                    role = obj.get("role") or obj.get("type", "")
                    text = _extract_text(obj)
                    if text and role in ("user", "human"):
                        excerpts.append(f"[사용자] {text[:250]}")
                except Exception:
                    pass
        except Exception:
            pass
    return "\n".join(excerpts[-150:])[:max_chars]


def _read_task_history(days: int = 60) -> str:
    """완료된 task_queue 항목 읽기."""
    try:
        from task_queue import _load as tq_load
        tasks = tq_load()
        lines = []
        for t in tasks:
            if t.get("status") == "done":
                date = (t.get("created") or "")[:10]
                result = (t.get("result") or "")[:100]
                lines.append(f"[{date}] {t['text'][:150]} → {result}")
        return "\n".join(lines[-60:])
    except Exception as e:
        logger.warning(f"task history read failed: {e}")
        return ""


def _read_telegram_log(days: int = 60) -> str:
    """~/.claude-agent/telegram_log.jsonl 읽기."""
    if not TELEGRAM_LOG.exists():
        return ""
    cutoff = datetime.now() - timedelta(days=days)
    lines = []
    try:
        for line in TELEGRAM_LOG.read_text(errors="replace").strip().split("\n"):
            if not line:
                continue
            try:
                obj = json.loads(line)
                ts = datetime.fromisoformat(obj.get("ts", "2000-01-01"))
                if ts >= cutoff:
                    lines.append(f"[{ts.strftime('%m-%d')}] {obj.get('text','')[:150]}")
            except Exception:
                pass
    except Exception:
        pass
    return "\n".join(lines[-100:])


async def _read_notion_content() -> str:
    """Notion 부모 페이지의 텍스트 블록 읽기."""
    token = os.getenv("NOTION_API_KEY", "")
    page_id = os.getenv("NOTION_PARENT_PAGE_ID", "")
    if not token or not page_id:
        return ""
    try:
        import httpx
        headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100",
                headers=headers,
            )
            if resp.status_code != 200:
                return ""
            texts = []
            for block in resp.json().get("results", []):
                bt = block.get("type", "")
                for rt in block.get(bt, {}).get("rich_text", []):
                    t = rt.get("plain_text", "").strip()
                    if t:
                        texts.append(t)
            return "\n".join(texts)[:6000]
    except Exception as e:
        logger.warning(f"Notion read failed: {e}")
        return ""


# ─── 압축 저장 ─────────────────────────────────────────────────

COMPRESS_SYSTEM = (
    "당신은 데이터 압축 전문가입니다. "
    "주어진 원시 데이터에서 자율 에이전트가 미래 작업에 활용할 수 있는 "
    "핵심 컨텍스트만 추출하세요:\n"
    "- 진행 중이거나 반복되는 프로젝트\n"
    "- 사용자(팀)의 선호·습관·규칙\n"
    "- 완료된 중요 작업과 교훈\n"
    "5-10줄로 간결하게. 한국어. 마크다운 금지."
)


async def _compress_and_save(source_name: str, raw: str) -> int:
    """raw 데이터를 요약 후 메모리에 저장. 저장된 글자 수 반환."""
    if not raw or len(raw.strip()) < 50:
        return 0
    prompt = f"다음 [{source_name}] 데이터에서 핵심 업무 컨텍스트를 추출하세요:\n\n{raw[:4500]}"
    summary = await run_agent(prompt=prompt, system=COMPRESS_SYSTEM)
    if summary and len(summary.strip()) > 20:
        tag = f"[동기화:{source_name} {datetime.now().strftime('%Y-%m-%d')}]"
        memory_write("fact", f"{tag}\n{summary}")
        return len(summary)
    return 0


# ─── 마스터 동기화 ─────────────────────────────────────────────


async def sync_all(progress_callback: Optional[Callable] = None) -> str:
    """4개 소스 동기화: Claude대화 / Telegram / 작업기록 / Notion."""
    async def send(msg: str):
        if progress_callback:
            try:
                await progress_callback(msg)
            except Exception:
                pass

    await send("🔄 전체 데이터 동기화 시작...")
    results = []
    loop = asyncio.get_event_loop()

    # 1. Claude Code 대화
    await send("📂 Claude 대화 기록 읽는 중...")
    raw = await loop.run_in_executor(None, _read_claude_conversations)
    n = await _compress_and_save("Claude대화", raw)
    results.append(f"{'✅' if n else '⚪'} Claude 대화: {n}자 동기화" if n else "⚪ Claude 대화: 내용 없음")

    # 2. Telegram 로그
    await send("💬 Telegram 대화 읽는 중...")
    raw = await loop.run_in_executor(None, _read_telegram_log)
    n = await _compress_and_save("Telegram", raw)
    results.append(f"✅ Telegram: {n}자 동기화" if n else "⚪ Telegram: 아직 로그 없음 (대화 쌓이면 자동 반영)")

    # 3. 작업 기록
    await send("📋 완료 작업 기록 읽는 중...")
    raw = await loop.run_in_executor(None, _read_task_history)
    n = await _compress_and_save("작업기록", raw)
    results.append(f"✅ 작업 기록: {n}자 동기화" if n else "⚪ 작업 기록: 완료된 작업 없음")

    # 4. Notion
    if os.getenv("NOTION_API_KEY") and os.getenv("NOTION_PARENT_PAGE_ID"):
        await send("📓 Notion 읽는 중...")
        raw = await _read_notion_content()
        n = await _compress_and_save("Notion", raw)
        results.append(f"✅ Notion: {n}자 동기화" if n else "⚪ Notion: 내용 없음")
    else:
        results.append("⚪ Notion: 미설정")

    report = "\n".join(results)
    await send(f"🎯 동기화 완료!\n\n{report}")
    return report


# ─── Telegram 로그 기록 ────────────────────────────────────────


def log_telegram_message(uid: int, text: str, result: str = ""):
    """모든 Telegram 메시지를 로컬에 기록."""
    try:
        TELEGRAM_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "uid": uid,
            "text": text[:500],
            "result": result[:300],
        }
        with open(TELEGRAM_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

import os
import json
import glob
import time
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime

WORKSPACE = os.path.expanduser(os.getenv("WORKSPACE_DIR", "~"))

SCAN_DIRS = [
    "~/Desktop",
    "~/Documents",
    "~/Downloads",
    "~/.claude/projects",
]

STALE_DAYS = 3
LARGE_DOWNLOAD_MB = 10


def _expanduser(p: str) -> str:
    return os.path.expanduser(p)


def _scan_recent_files() -> list[dict]:
    """최근 수정된 파일들 스캔."""
    now = time.time()
    found = []
    for d in SCAN_DIRS:
        d = _expanduser(d)
        if not os.path.isdir(d):
            continue
        try:
            for root, _, files in os.walk(d):
                # .git 등 숨김 폴더 스킵
                if any(part.startswith(".") and part != ".claude" for part in Path(root).parts[-3:]):
                    continue
                for fname in files[:50]:
                    fpath = os.path.join(root, fname)
                    try:
                        mtime = os.path.getmtime(fpath)
                        age_days = (now - mtime) / 86400
                        size_mb = os.path.getsize(fpath) / (1024 * 1024)
                        found.append({
                            "path": fpath,
                            "name": fname,
                            "age_days": round(age_days, 1),
                            "size_mb": round(size_mb, 2),
                            "dir": d,
                        })
                    except OSError:
                        continue
        except PermissionError:
            continue
    return found


def _scan_claude_conversations() -> list[str]:
    """Claude 대화 기록에서 미완성 항목 탐색."""
    snippets = []
    claude_dir = _expanduser("~/.claude/projects")
    if not os.path.isdir(claude_dir):
        return snippets

    pattern = os.path.join(claude_dir, "**", "*.jsonl")
    files = glob.glob(pattern, recursive=True)
    files.sort(key=os.path.getmtime, reverse=True)

    keywords = ["나중에", "TODO", "todo", "해야", "미완성", "다음에", "나중", "추후", "pending"]

    for fpath in files[:20]:
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-100:]
            for line in lines:
                try:
                    obj = json.loads(line)
                    text = ""
                    if isinstance(obj.get("content"), str):
                        text = obj["content"]
                    elif isinstance(obj.get("content"), list):
                        for block in obj["content"]:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text += block.get("text", "")
                    for kw in keywords:
                        if kw in text:
                            snippet = text[:200].replace("\n", " ")
                            snippets.append(snippet)
                            break
                except (json.JSONDecodeError, KeyError):
                    continue
        except OSError:
            continue

    return snippets[:10]


def _build_context() -> str:
    files = _scan_recent_files()
    conversations = _scan_claude_conversations()

    urgent = [f for f in files if f["age_days"] <= 1]
    stale_downloads = [
        f for f in files
        if "Downloads" in f["dir"] and f["age_days"] >= STALE_DAYS
    ]
    large_files = [f for f in files if f["size_mb"] >= LARGE_DOWNLOAD_MB]

    lines = [f"현재 날짜: {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
    lines.append(f"\n최근 24시간 수정 파일 ({len(urgent)}개):")
    for f in urgent[:15]:
        lines.append(f"  - {f['name']} ({f['age_days']}일 전, {f['size_mb']}MB) @ {f['dir']}")

    lines.append(f"\n다운로드 폴더 오래된 파일 ({len(stale_downloads)}개):")
    for f in stale_downloads[:10]:
        lines.append(f"  - {f['name']} ({f['age_days']}일 경과, {f['size_mb']}MB)")

    lines.append(f"\n용량 큰 파일 ({len(large_files)}개):")
    for f in large_files[:5]:
        lines.append(f"  - {f['name']} ({f['size_mb']}MB)")

    lines.append(f"\nClaude 대화에서 미완성 항목 ({len(conversations)}개):")
    for snippet in conversations:
        lines.append(f"  - {snippet[:150]}")

    return "\n".join(lines)


async def run_daily_scout() -> str:
    """파일/대화 스캔 후 claude CLI로 오늘의 업무 보고서 작성."""
    context = _build_context()

    system = (
        "당신은 사용자의 업무를 파악하고 우선순위를 정리하는 비서입니다. "
        "주어진 파일/대화 정보를 바탕으로 오늘 해야 할 일을 한국어로 보고하세요. "
        "이모지를 사용해 가독성 높게 작성하고, 각 항목에 간단한 이유를 달아주세요."
    )
    prompt = f"다음 정보를 바탕으로 오늘의 업무 보고서를 작성해주세요:\n\n{context}"

    def _call():
        result = subprocess.run(
            ["claude", "-p", prompt, "--system", system, "--output-format", "text"],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout.strip() or result.stderr.strip()

    return await asyncio.get_event_loop().run_in_executor(None, _call)

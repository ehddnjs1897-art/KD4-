import json
import os
import hashlib
from pathlib import Path
from datetime import datetime

MEMORY_FILE = os.path.expanduser("~/.claude-agent/memory.json")


def _load() -> dict:
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"facts": [], "tasks": [], "preferences": {}, "notes": []}


def _save(data: dict):
    Path(MEMORY_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _fact_key(text: str) -> str:
    return hashlib.md5(text[:120].strip().encode()).hexdigest()[:12]


def memory_write(category: str, value: str) -> str:
    mem = _load()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if category == "preference":
        key, _, val = value.partition(":")
        mem["preferences"][key.strip()] = val.strip()
    elif category == "task":
        mem["tasks"].append({"text": value, "date": now, "done": False})
        mem["tasks"] = mem["tasks"][-50:]
    elif category == "note":
        mem["notes"].append({"text": value, "date": now})
        mem["notes"] = mem["notes"][-100:]
    else:
        # Deduplicate facts: skip if near-identical text already exists
        new_key = _fact_key(value)
        existing_keys = {_fact_key(f["text"]) for f in mem["facts"]}
        if new_key in existing_keys:
            return f"메모리 이미 존재 [{category}]: {value[:80]}"
        mem["facts"].append({"text": value, "date": now})
        mem["facts"] = mem["facts"][-200:]
    _save(mem)
    return f"메모리 저장됨 [{category}]: {value[:80]}"


def memory_read() -> str:
    mem = _load()
    lines = [f"메모리 현황 ({datetime.now().strftime('%Y-%m-%d')})"]
    if mem["facts"]:
        lines.append("\n사실/기억:")
        for f in mem["facts"][-10:]:
            lines.append(f"  {f['date'][:10]} {f['text']}")
    if mem["tasks"]:
        pending = [t for t in mem["tasks"] if not t.get("done")]
        if pending:
            lines.append("\n진행 중 작업:")
            for t in pending[-10:]:
                lines.append(f"  {t['date'][:10]} {t['text']}")
    if mem["preferences"]:
        lines.append("\n사용자 설정:")
        for k, v in mem["preferences"].items():
            lines.append(f"  {k}: {v}")
    if mem["notes"]:
        lines.append("\n최근 메모:")
        for n in mem["notes"][-5:]:
            lines.append(f"  {n['date'][:10]} {n['text']}")
    return "\n".join(lines) if len(lines) > 1 else "저장된 메모리 없음"


def get_memory_context() -> str:
    mem = _load()
    parts = []
    if mem["facts"]:
        # Most recent facts first, skip sync tags for agent context
        facts = [f["text"] for f in reversed(mem["facts"]) if "[동기화:" not in f["text"]][:12]
        if facts:
            parts.append("기억: " + " / ".join(facts))
    if mem["preferences"]:
        prefs = [f"{k}={v}" for k, v in mem["preferences"].items()]
        parts.append("설정: " + ", ".join(prefs))
    pending = [t["text"] for t in mem["tasks"] if not t.get("done")]
    if pending:
        parts.append("미완료 작업: " + " / ".join(pending[-5:]))
    return "\n".join(parts)

from __future__ import annotations
import json
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

QUEUE_FILE = os.path.expanduser("~/.claude-agent/tasks.json")

PRIORITY_ORDER = {"urgent": 0, "high": 1, "normal": 2, "low": 3}


def _load() -> list:
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(data: list):
    Path(QUEUE_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_task(text: str, priority: str = "normal", meta: Optional[dict] = None) -> str:
    priority = priority if priority in PRIORITY_ORDER else "normal"
    tasks = _load()
    task = {
        "id": uuid.uuid4().hex[:8],
        "text": text,
        "priority": priority,
        "status": "pending",
        "created": datetime.now().isoformat(timespec="seconds"),
        "completed": None,
        "result": None,
        "meta": meta or {},
    }
    tasks.append(task)
    _save(tasks)
    return task["id"]


def start_task(task_id: str) -> bool:
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id and t["status"] == "pending":
            t["status"] = "in_progress"
            _save(tasks)
            return True
    return False


def list_tasks(status: str = "pending") -> list:
    tasks = _load()
    if status == "all":
        return sorted(tasks, key=lambda t: (PRIORITY_ORDER.get(t["priority"], 2), t["created"]))
    return sorted(
        [t for t in tasks if t["status"] == status],
        key=lambda t: (PRIORITY_ORDER.get(t["priority"], 2), t["created"])
    )


def next_task() -> Optional[dict]:
    pending = list_tasks("pending")
    return pending[0] if pending else None


def complete_task(task_id: str, result: str = "") -> bool:
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "done"
            t["completed"] = datetime.now().isoformat(timespec="seconds")
            t["result"] = result[:500]
            _save(tasks)
            return True
    return False


def cancel_task(task_id: str) -> bool:
    tasks = _load()
    new_tasks = [t for t in tasks if t["id"] != task_id]
    if len(new_tasks) == len(tasks):
        return False
    _save(new_tasks)
    return True


def clear_done():
    tasks = _load()
    _save([t for t in tasks if t["status"] != "done"])


def format_tasks_mobile(status: str = "pending") -> str:
    tasks = list_tasks(status)
    # Always prepend in_progress tasks when viewing pending
    if status == "pending":
        all_tasks = _load()
        in_prog = [t for t in all_tasks if t["status"] == "in_progress"]
        tasks = in_prog + tasks
    if not tasks:
        return "🗒 작업 없음"
    ICONS = {"urgent": "🔴", "high": "🟠", "normal": "🟡", "low": "🟢"}
    STATUS_MARK = {"done": "✅", "in_progress": "⚙️", "pending": "⏳"}
    lines = []
    for t in tasks[:20]:
        icon = ICONS.get(t["priority"], "🟡")
        mark = STATUS_MARK.get(t["status"], "⏳")
        lines.append(f"{icon}{mark} [{t['id']}] {t['text'][:60]}")
    return "\n".join(lines)

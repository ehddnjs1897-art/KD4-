from __future__ import annotations
import asyncio
import logging
import re
from typing import Optional, Callable
from agent_council import run_council
from notion_logger import save_meeting_to_notion

logger = logging.getLogger(__name__)


def _extract_project_name(task: str) -> str:
    """작업 텍스트에서 프로젝트명 추출."""
    patterns = [
        r"프로젝트[:\s]+([^\n,]+)",
        r"project[:\s]+([^\n,]+)",
        r"([^\s/]+)\s*(?:프로젝트|관련|에서)",
    ]
    for p in patterns:
        m = re.search(p, task, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:30]
    # Fallback: first meaningful words
    words = task.strip().split()[:4]
    return " ".join(words)[:30]


async def run_orchestrated_task(
    task: str,
    progress_callback: Optional[Callable] = None,
    project_name: str = "",
) -> str:
    """에이전트 회의 실행 + Notion 회의록 저장."""
    if not project_name:
        project_name = _extract_project_name(task)

    result, transcript = await run_council(
        topic=task,
        project_name=project_name,
        progress_callback=progress_callback,
        max_turns=12,
    )

    # Save to Notion in background
    if transcript:
        async def _save():
            url = await save_meeting_to_notion(project_name, task, transcript, result)
            if url and progress_callback:
                try:
                    await progress_callback(f"📓 회의록 저장됨 → Notion")
                except Exception:
                    pass

        asyncio.create_task(_save())

    return result

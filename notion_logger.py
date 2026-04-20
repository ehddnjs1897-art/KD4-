from __future__ import annotations
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

NOTION_TOKEN = os.getenv("NOTION_API_KEY", "")
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID", "")
NOTION_VERSION = "2022-06-28"

AGENT_EMOJI = {"analyst": "🔵", "executor": "🟠", "validator": "🟢"}
AGENT_LABEL = {"analyst": "분석가", "executor": "실행자", "validator": "검증자"}


def _h(content: str, level: int = 2) -> dict:
    k = f"heading_{level}"
    return {"object": "block", "type": k, k: {
        "rich_text": [{"type": "text", "text": {"content": content[:2000]}}],
        "color": "default",
    }}


def _p(content: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": {
        "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
    }}


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _callout(content: str, emoji: str = "💬", color: str = "gray_background") -> dict:
    return {"object": "block", "type": "callout", "callout": {
        "rich_text": [{"type": "text", "text": {"content": content[:2000]}}],
        "icon": {"type": "emoji", "emoji": emoji},
        "color": color,
    }}


def _quote(content: str) -> dict:
    return {"object": "block", "type": "quote", "quote": {
        "rich_text": [{"type": "text", "text": {"content": content[:2000]}}],
        "color": "default",
    }}


def _build_meeting_blocks(
    project_name: str,
    task: str,
    transcript: list[dict],
    result: str,
    now: datetime,
) -> list[dict]:
    date_str = now.strftime("%Y-%m-%d %H:%M")
    blocks: list[dict] = []

    # Header
    blocks.append(_h(f"📅 {date_str}  |  {project_name or '에이전트 작업'}", 2))
    blocks.append(_callout(f"📌 작업 내용\n{task}", "📌", "blue_background"))

    # Transcript
    blocks.append(_h("🏛 회의 진행", 3))

    turn_colors = {
        "analyst": "blue_background",
        "executor": "orange_background",
        "validator": "green_background",
    }
    for i, turn in enumerate(transcript, 1):
        role = turn["role"]
        emoji = AGENT_EMOJI.get(role, "⚪")
        label = AGENT_LABEL.get(role, role)
        ts = turn.get("timestamp", "")[:16].replace("T", " ")
        color = turn_colors.get(role, "gray_background")

        header_line = f"{emoji} {label}  ({ts})  — 발언 {i}"
        content = f"{header_line}\n\n{turn['message']}"

        # Split long messages
        if len(content) > 1900:
            blocks.append(_callout(content[:1900], emoji, color))
            blocks.append(_quote(content[1900:3800]))
        else:
            blocks.append(_callout(content, emoji, color))

    # Result
    blocks.append(_h("🎯 최종 결과", 3))
    result_chunks = [result[i:i+1900] for i in range(0, min(len(result), 5700), 1900)]
    for chunk in result_chunks:
        blocks.append(_p(chunk))

    blocks.append(_divider())
    return blocks


async def save_meeting_to_notion(
    project_name: str,
    task: str,
    transcript: list[dict],
    result: str,
) -> Optional[str]:
    """회의록을 Notion 'AI 에이전트' 페이지에 날짜순으로 저장."""
    if not NOTION_TOKEN or not NOTION_PARENT_PAGE_ID:
        logger.warning("NOTION_API_KEY 또는 NOTION_PARENT_PAGE_ID 미설정 — Notion 저장 스킵")
        return None

    try:
        import httpx
    except ImportError:
        logger.error("httpx 패키지 없음. pip install httpx")
        return None

    now = datetime.now()
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    blocks = _build_meeting_blocks(project_name, task, transcript, result, now)

    # Append blocks to parent page (max 100 per call)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            for i in range(0, len(blocks), 95):
                batch = blocks[i:i+95]
                resp = await client.patch(
                    f"https://api.notion.com/v1/blocks/{NOTION_PARENT_PAGE_ID}/children",
                    headers=headers,
                    json={"children": batch},
                )
                if resp.status_code != 200:
                    logger.error(f"Notion API {resp.status_code}: {resp.text[:300]}")
                    return None

        page_url = f"https://www.notion.so/{NOTION_PARENT_PAGE_ID.replace('-', '')}"
        logger.info(f"Notion 저장 완료: {page_url}")
        return page_url
    except Exception as e:
        logger.error(f"Notion 저장 실패: {e}")
        return None

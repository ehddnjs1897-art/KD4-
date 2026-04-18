import os
import subprocess
import aiofiles
import glob as glob_module
from pathlib import Path
from memory import memory_read, memory_write
from mac_tools import (
    run_applescript,
    mac_notify,
    mac_say,
    mac_clipboard_read,
    mac_clipboard_write,
    mac_screenshot,
    system_info,
    mac_mail_unread,
    mac_calendar_today,
    mac_open_app,
)

TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or home-relative file path"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write or overwrite a file with given content",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "run_bash",
        "description": "Run a shell command on the Mac and return stdout/stderr. Timeout 60s.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "list_files",
        "description": "List files in a directory (non-recursive by default)",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path"},
                "pattern": {"type": "string", "description": "Glob pattern, e.g. *.py (optional)"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "search_files",
        "description": "Search for text inside files using grep",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory to search in"},
                "query": {"type": "string", "description": "Text or regex to search for"},
                "file_pattern": {"type": "string", "description": "File pattern like *.py (optional)"}
            },
            "required": ["directory", "query"]
        }
    },
    {
        "name": "ask_opus",
        "description": "복잡한 판단이나 전략적 결정이 필요할 때 Opus 4.7에게 자문을 구합니다",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Opus에게 물어볼 질문 또는 상황 설명"}
            },
            "required": ["question"]
        }
    },
    {
        "name": "memory_write",
        "description": "장기 메모리에 정보 저장. 세션 종료 후에도 유지됨. category: fact/task/note/preference",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "fact(사실), task(할일), note(메모), preference(설정)"},
                "value": {"type": "string", "description": "저장할 내용. preference는 '키: 값' 형식"}
            },
            "required": ["category", "value"]
        }
    },
    {
        "name": "memory_read",
        "description": "장기 메모리 전체 읽기 — 사용자 선호, 미완료 작업, 기억된 사실 등",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "browser_open",
        "description": "URL을 열고 페이지 내용 반환 (Playwright 필요)",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "열 URL"},
                "wait_for": {"type": "string", "description": "기다릴 CSS 셀렉터 (optional)"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "mac_notify",
        "description": "맥 데스크톱 알림 표시",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "message": {"type": "string"}
            },
            "required": ["title", "message"]
        }
    },
    {
        "name": "mac_say",
        "description": "맥 내장 TTS로 텍스트 음성 출력 (한국어 음성: Yuna)",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "voice": {"type": "string", "description": "기본 Yuna (한국어)"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "mac_clipboard_read",
        "description": "맥 클립보드 내용 읽기 (pbpaste)",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "mac_clipboard_write",
        "description": "맥 클립보드에 텍스트 복사 (pbcopy)",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"]
        }
    },
    {
        "name": "mac_screenshot",
        "description": "맥 화면 전체 캡처 후 경로 반환",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "저장 경로 (optional)"}},
            "required": []
        }
    },
    {
        "name": "system_info",
        "description": "맥 시스템 정보: 배터리, 디스크, 메모리, CPU 부하, 업타임",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "mac_mail_unread",
        "description": "맥 Mail 앱의 받은 편지함 미확인 메일 개수와 최근 5개 미확인 제목",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "mac_calendar_today",
        "description": "맥 Calendar 앱에서 오늘 일정 가져오기",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "mac_open_app",
        "description": "맥 애플리케이션 열기 (예: 'Safari', 'Calendar', 'Mail')",
        "input_schema": {
            "type": "object",
            "properties": {"app_name": {"type": "string"}},
            "required": ["app_name"]
        }
    },
    {
        "name": "applescript_run",
        "description": "임의 AppleScript 실행 — Mac 앱 전부 제어 가능 (Messages, Notes, Reminders, Safari 등)",
        "input_schema": {
            "type": "object",
            "properties": {"script": {"type": "string"}},
            "required": ["script"]
        }
    },
    {
        "name": "browser_act",
        "description": "브라우저에서 클릭/입력/스크롤 등 동작 순서대로 실행 후 결과 반환",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "시작 URL"},
                "actions": {
                    "type": "array",
                    "description": "실행할 동작 목록",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "description": "click / type / scroll / wait / screenshot"},
                            "selector": {"type": "string"},
                            "text": {"type": "string"},
                            "ms": {"type": "number"}
                        }
                    }
                }
            },
            "required": ["url", "actions"]
        }
    }
]


def _expand(path: str) -> str:
    return os.path.expanduser(path)


async def _browser_open(url: str, wait_for: str = "") -> str:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return "Playwright 미설치. 터미널에서 실행: pip install playwright && playwright install chromium"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=30000)
        if wait_for:
            await page.wait_for_selector(wait_for, timeout=10000)
        text = await page.inner_text("body")
        await browser.close()
        return text[:6000]


async def _browser_act(url: str, actions: list) -> str:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return "Playwright 미설치. 터미널에서 실행: pip install playwright && playwright install chromium"
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=30000)
        for act in actions:
            t = act.get("type", "")
            sel = act.get("selector", "")
            if t == "click":
                await page.click(sel)
                results.append(f"클릭: {sel}")
            elif t == "type":
                await page.fill(sel, act.get("text", ""))
                results.append(f"입력: {sel} = {act.get('text', '')[:30]}")
            elif t == "scroll":
                await page.evaluate("window.scrollBy(0, 500)")
                results.append("스크롤 down")
            elif t == "wait":
                import asyncio
                await asyncio.sleep(act.get("ms", 1000) / 1000)
                results.append(f"대기 {act.get('ms', 1000)}ms")
            elif t == "screenshot":
                path = _expand("~/Desktop/screenshot.png")
                await page.screenshot(path=path)
                results.append(f"스크린샷 저장: {path}")
        final_text = await page.inner_text("body")
        await browser.close()
    return "\n".join(results) + f"\n\n최종 페이지 내용:\n{final_text[:3000]}"


async def execute_tool(name: str, inputs: dict) -> str:
    try:
        if name == "read_file":
            p = _expand(inputs["path"])
            async with aiofiles.open(p, "r", encoding="utf-8", errors="replace") as f:
                content = await f.read()
            return content[:8000] if len(content) > 8000 else content

        elif name == "write_file":
            p = _expand(inputs["path"])
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(p, "w", encoding="utf-8") as f:
                await f.write(inputs["content"])
            return f"Written: {p}"

        elif name == "run_bash":
            result = subprocess.run(
                inputs["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            out = result.stdout[-3000:] if result.stdout else ""
            err = result.stderr[-1000:] if result.stderr else ""
            if err:
                return f"STDOUT:\n{out}\nSTDERR:\n{err}"
            return out or "(no output)"

        elif name == "list_files":
            p = _expand(inputs["path"])
            pattern = inputs.get("pattern", "*")
            matches = glob_module.glob(os.path.join(p, pattern))
            if not matches:
                return "No files found."
            lines = []
            for m in sorted(matches)[:100]:
                size = os.path.getsize(m) if os.path.isfile(m) else 0
                tag = "[DIR]" if os.path.isdir(m) else f"{size:,}B"
                lines.append(f"{tag}  {os.path.basename(m)}")
            return "\n".join(lines)

        elif name == "search_files":
            d = _expand(inputs["directory"])
            q = inputs["query"]
            pat = inputs.get("file_pattern", "")
            include = f"--include='{pat}'" if pat else ""
            cmd = f"grep -rn {include} --max-count=5 '{q}' '{d}' 2>/dev/null | head -50"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return result.stdout or "No matches found."

        elif name == "ask_opus":
            question = inputs["question"]
            opus_prompt = (
                f"Sonnet 에이전트가 자문을 요청했습니다.\n\n"
                f"상황/질문:\n{question}\n\n"
                f"간결하고 명확한 조언을 한국어로 주세요. 마크다운 없이 핵심만."
            )
            result = subprocess.run(
                ["claude", "-p", opus_prompt, "--model", "claude-opus-4-7", "--dangerously-skip-permissions"],
                capture_output=True, text=True, timeout=300
            )
            return f"[Opus 자문]\n{result.stdout.strip()}"

        elif name == "memory_write":
            return memory_write(inputs["category"], inputs["value"])

        elif name == "memory_read":
            return memory_read()

        elif name == "mac_notify":
            return mac_notify(inputs["title"], inputs["message"])

        elif name == "mac_say":
            return mac_say(inputs["text"], inputs.get("voice", "Yuna"))

        elif name == "mac_clipboard_read":
            return mac_clipboard_read()

        elif name == "mac_clipboard_write":
            return mac_clipboard_write(inputs["text"])

        elif name == "mac_screenshot":
            return mac_screenshot(inputs.get("path", ""))

        elif name == "system_info":
            return system_info()

        elif name == "mac_mail_unread":
            return mac_mail_unread()

        elif name == "mac_calendar_today":
            return mac_calendar_today()

        elif name == "mac_open_app":
            return mac_open_app(inputs["app_name"])

        elif name == "applescript_run":
            return run_applescript(inputs["script"])

        elif name == "browser_open":
            return await _browser_open(inputs["url"], inputs.get("wait_for", ""))

        elif name == "browser_act":
            return await _browser_act(inputs["url"], inputs["actions"])

        else:
            return f"Unknown tool: {name}"

    except FileNotFoundError as e:
        return f"File not found: {e}"
    except subprocess.TimeoutExpired:
        return "Command timed out (60s)."
    except Exception as e:
        return f"Tool error: {e}"

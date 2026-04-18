import os
import subprocess
import aiofiles
import glob as glob_module
from pathlib import Path

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
    }
]


def _expand(path: str) -> str:
    return os.path.expanduser(path)


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
                ["claude", "-p", opus_prompt, "--model", "claude-opus-4-7"],
                capture_output=True, text=True, timeout=300
            )
            return f"[Opus 자문]\n{result.stdout.strip()}"

        else:
            return f"Unknown tool: {name}"

    except FileNotFoundError as e:
        return f"File not found: {e}"
    except subprocess.TimeoutExpired:
        return "Command timed out (60s)."
    except Exception as e:
        return f"Tool error: {e}"

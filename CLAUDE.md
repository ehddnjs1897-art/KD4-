# CLAUDE.md

This file provides guidance to Claude Code and other AI assistants working in this repository.

## Repository Overview

**Repository**: `ehddnjs1897-art/KD4-`
**Purpose**: Mac autonomous agent system — control desktop Claude from phone via Telegram. Surpasses OpenClaw with deep Mac integration, adaptive learning, and autonomous task queue processing.

## Codebase Structure

```
KD4-/
├── main.py               # Entry point: bot + scheduler + auto-recovery
├── agent_engine.py       # Core agent loop (Sonnet 4.6 via claude CLI)
├── orchestrator.py       # Multi-agent orchestrator (analyst→executor→validator)
├── telegram_bot.py       # Telegram command handlers (17 commands)
├── daily_scout.py        # File/conversation scanner & daily report
├── scheduler.py          # 30m heartbeat + hourly auto-work + 2am deep work
├── tools.py              # 24+ agent tools (unified registry)
├── mac_tools.py          # Mac-native: AppleScript, clipboard, say, notify, calendar
├── web_search.py         # DuckDuckGo search + URL fetch (no API key)
├── memory.py             # Long-term memory (~/.claude-agent/memory.json)
├── task_queue.py         # Priority queue (~/.claude-agent/tasks.json)
├── agents/
│   ├── analyst.py        # Analyst system prompt
│   ├── executor.py       # Executor system prompt
│   └── validator.py      # Validator system prompt
├── requirements.txt
├── .env.example
├── start.sh              # Auto-installs playwright chromium on first run
└── setup_autostart.sh    # launchd autostart
```

## Development Workflows

- **Install**: `pip install -r requirements.txt && playwright install chromium`
- **Run locally**: `bash start.sh`
- **Autostart**: `bash setup_autostart.sh`
- **Logs**: `tail -f logs/agent.log`
- **Stop all instances**: `pkill -f "python3 main.py"`

## Environment Variables

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `TELEGRAM_ALLOWED_USER_ID` | Your Telegram user ID (security) |
| `WORKSPACE_DIR` | Root dir for daily scout (default: `~`) |
| `DAILY_REPORT_HOUR` | Hour for daily report (default: `9`) |
| `AUTO_WORK_HOURS` | Comma-separated hours for auto-work (default: `8,10,12,14,16,18,20,22`) |
| `NIGHT_WORK_HOUR` | Hour for deep overnight work (default: `2`) |

## Telegram Commands

**Execution**
- `/do <task>` — single agent (Sonnet 4.6, Opus 4.7 advisor available)
- `/team <task>` — analyst → executor → validator with retry
- `/report` — scan files/conversations & daily report
- `/checkout` — end-of-day wrap-up

**Task Queue (persistent)**
- `/task <text> [urgent|high|normal|low]`
- `/tasks [pending|done|all]`
- `/cancel <id>`, `/cleardone`

**Memory (persistent)**
- `/memory`, `/remember <fact>`, `/forget`

**System**
- `/screen`, `/sysinfo`, `/stop`, `/status`, `/menu`

## Architecture

1. **agent_engine.py** — ReAct loop: Claude CLI subprocess with `<tool_call>` XML parsing. Auto-injects long-term memory context.
2. **tools.py** — 24+ tools. File I/O, bash, AppleScript, browser (Playwright), clipboard, screenshot, vision (`see_screen`), web search, memory, Opus advisor.
3. **scheduler.py** — `schedule_loop` checks: 30m heartbeat → queue → timed auto-work → daily report.
4. **task_queue.py + memory.py** — JSON persistence in `~/.claude-agent/`.
5. **main.py** — `run_with_recovery()` auto-restarts on crash (exp backoff, max 20 attempts).

## Autonomous Behaviors

- **Every 30 minutes**: scan `HEARTBEAT.md` for user-written requests
- **Every scheduled hour**: process task queue first, then scan for pending work
- **2 AM**: deep work — process up to 10 queued tasks, scan filesystem
- **After each task**: extract lessons → auto-save to memory
- **9 AM**: daily report with scanned file context

## Git & Branch Conventions

- Never commit to `main`
- Current Claude branch: `claude/dev-status-report-Sm5Dx`
- Push with: `git push -u origin <branch-name>`

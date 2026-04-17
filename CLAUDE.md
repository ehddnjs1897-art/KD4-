# CLAUDE.md

This file provides guidance to Claude Code and other AI assistants working in this repository.

## Repository Overview

**Repository**: `ehddnjs1897-art/KD4-`
**Purpose**: Mac autonomous agent system — control desktop Claude from phone via Telegram

## Codebase Structure

```
KD4-/
├── main.py               # Entry point: starts Telegram bot + scheduler
├── agent_engine.py       # Core autonomous agent loop (Anthropic SDK)
├── orchestrator.py       # Multi-agent orchestrator (analyst→executor→validator)
├── telegram_bot.py       # Telegram bot command handlers
├── daily_scout.py        # Proactive file/conversation scanner & daily report
├── scheduler.py          # Daily report scheduler (runs inside main loop)
├── tools.py              # Agent tools: read_file, write_file, run_bash, list_files, search_files
├── agents/
│   ├── analyst.py        # Analyst agent system prompt
│   ├── executor.py       # Executor agent system prompt
│   └── validator.py      # Validator agent system prompt
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── start.sh              # One-click startup script (creates venv, installs deps)
└── setup_autostart.sh    # Mac launchd autostart setup
```

## Development Workflows

- **Install dependencies**: `pip install -r requirements.txt`
- **Run locally**: `bash start.sh` (handles venv + deps automatically)
- **Setup Mac autostart**: `bash setup_autostart.sh`
- **View logs**: `tail -f logs/agent.log`

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From @BotFather on Telegram |
| `TELEGRAM_ALLOWED_USER_ID` | Your Telegram user ID (security) |
| `ANTHROPIC_API_KEY` | From console.anthropic.com |
| `CLAUDE_MODEL` | Default: `claude-opus-4-7` |
| `WORKSPACE_DIR` | Root dir for daily scout (default: `~`) |
| `DAILY_REPORT_HOUR` | Hour for daily report (default: `9`) |

## Architecture

1. **agent_engine.py** — autonomous agent loop using Anthropic SDK tool_use
2. **orchestrator.py** — multi-agent: analyst → executor → validator with retry
3. **telegram_bot.py** — `/do`, `/team`, `/report`, `/stop`, `/status` commands
4. **daily_scout.py** — scans `~/Desktop`, `~/Documents`, `~/Downloads`, `~/.claude/projects`

## Git & Branch Conventions

- Never commit to `main`
- Current Claude branch: `claude/dev-status-report-Sm5Dx`
- Push with: `git push -u origin <branch-name>`

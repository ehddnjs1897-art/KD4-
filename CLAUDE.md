# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) and other AI
assistants when working with this repository.

## Repository Status

- **Repository**: `ehddnjs1897-art/KD4-`
- **Project**: Numberblocks Tetris Game (넘버블럭스 테트리스)
- **Language / stack**: HTML / CSS / vanilla JavaScript
- **Build system**: None (static files, open `index.html` in browser)
- **Tests**: none

## Codebase Structure

- `index.html` — Entry point, game page structure
- `style.css` — All styling including responsive mobile layout
- `game.js` — Game logic (board, pieces, controls, rendering)

## Development Workflows

- **Run the app locally**: Open `index.html` in a browser (no server needed)

## Git & Branch Conventions

These conventions are enforced by the environment this repository runs in and
must be followed by AI sessions:

- **Never commit directly to `main`.** All work happens on feature branches.
- **Claude sessions use the branch named in the session brief.** For this
  repository the current Claude branch is
  `claude/add-claude-documentation-wN4sX`. Future sessions may be assigned a
  different branch — always use the one specified in the session, and create
  it locally if it does not yet exist.
- **Push with upstream tracking**: `git push -u origin <branch-name>`.
- **Retry transient push/fetch failures** with exponential backoff (2s, 4s,
  8s, 16s), up to 4 attempts. Do not retry on non-network errors.
- **Do not force-push** to shared branches, and never force-push to `main`.
- **Do not skip hooks** (`--no-verify`, `--no-gpg-sign`, etc.) unless the user
  explicitly asks for it. Fix the underlying issue instead.
- **Create new commits rather than amending.** If a pre-commit hook fails,
  the commit did not happen — fix the issue, re-stage, and create a new
  commit (do not `--amend`).
- **Do not open a pull request unless the user explicitly asks for one.**

### Commit messages

Until the project establishes its own style, keep commit messages:

- Short imperative subject line (≤ 72 chars), e.g. `Add initial scaffold`
- Optional body explaining _why_ the change was made, not _what_ (the diff
  shows the what)

## GitHub Integration

AI sessions in this repository interact with GitHub **only** through the
GitHub MCP tools (prefixed `mcp__github__`). The `gh` CLI is not available.
Scope is restricted to `ehddnjs1897-art/kd4-` — do not attempt to read from
or write to any other repository.

Be conservative with GitHub side effects:

- Do not post PR comments unless a reply is genuinely necessary.
- Do not create issues or PRs without explicit user instruction.
- Never force-push to `main` even if asked; warn the user instead.

## Coding Conventions

- Vanilla JavaScript (no frameworks/bundlers)
- camelCase for functions and variables, UPPER_SNAKE for constants
- Game state is module-level variables in `game.js`
- Canvas 2D API for all rendering

## Things Not To Do

These rules apply to every AI session in this repository, including
bootstrapping ones:

- Do not create files unless they are necessary for the requested task.
- Do not add README.md or other docs files unless the user asks.
- Do not add backwards-compatibility shims, feature flags, or fallback code
  for scenarios that cannot actually occur.
- Do not add error handling or input validation at internal boundaries —
  only at true system boundaries (user input, external APIs).
- Do not leave `// removed`, `// old`, or similar tombstone comments after
  deleting code. Just delete it.
- Do not add docstrings, type annotations, or comments to code you did not
  change.
- Do not refactor code that is adjacent to, but not part of, the task.

## When This File Is Out Of Date

If you, as an AI assistant, start a task in this repository and find that the
actual code no longer matches this document — for example, source files exist
but the "Codebase Structure" section is still the placeholder — **update this
file as part of your change**. Keeping `CLAUDE.md` accurate is part of every
task that materially changes the codebase, not a separate chore.

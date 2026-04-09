# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) and other AI
assistants when working with this repository.

## Repository Status

**This repository is currently uninitialized.** At the time this document was
written, the repository contains no source code, no commit history, and no
configuration files — only the `.git` directory and this `CLAUDE.md`.

- **Repository**: `ehddnjs1897-art/KD4-`
- **Default working branch for Claude**: `claude/add-claude-documentation-wN4sX`
- **Language / stack**: not yet chosen
- **Build system**: not yet chosen
- **Tests**: none

Because the project has not been scaffolded, there is no existing architecture,
module layout, or set of conventions to describe. Sections below that would
normally document the stack (build, test, lint, entry points, etc.) are
intentionally left as placeholders. **Update this file as soon as the project
is scaffolded** so future AI sessions have accurate guidance.

## For the First Contributor / First AI Session

When the project gets its first real commits, the agent doing that work should:

1. Decide the language and tooling with the user (do not guess).
2. Add a minimal but runnable scaffold (entry point, dependency manifest,
   README).
3. Immediately update this `CLAUDE.md` with the actual structure, commands,
   and conventions — do not leave the placeholder text in place once real code
   exists.
4. Commit the scaffold and the updated `CLAUDE.md` together.

Do not invent a stack, framework, or directory layout in order to fill this
file out. If you are unsure what the project is supposed to be, ask the user
first.

## Codebase Structure

_No source tree yet._ Once the project is scaffolded, document:

- Top-level directories and what each one is for
- Where the entry point lives
- How modules are organized (by feature, by layer, etc.)
- Where tests live relative to the code they cover
- Any generated / vendored directories that should be ignored

## Development Workflows

_No tooling configured yet._ Once chosen, document the exact commands here so
AI assistants can run them without guessing. Typical entries:

- **Install dependencies**: _TBD_
- **Run the app locally**: _TBD_
- **Run tests**: _TBD_
- **Run a single test**: _TBD_
- **Lint**: _TBD_
- **Format**: _TBD_
- **Type-check**: _TBD_
- **Build / package**: _TBD_

Prefer documenting one canonical command per task. If there are multiple ways
to run something, pick the one contributors are expected to use.

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

## Coding Conventions (to be filled in)

Once code exists, document here:

- Naming conventions (files, types, functions, constants)
- Import ordering / module boundaries
- Error-handling style
- Logging style
- Any project-specific idioms that an AI should match rather than "improve"

Until then, a Claude session adding first code to this repository should
default to the idiomatic style of whatever language is chosen, and should
**not** introduce speculative abstractions, config layers, or helper
utilities beyond what the immediate task needs.

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

# Conclaw -- Implementation Tracker

> Shared tracking document for all contributors (Harsh, Satvik, and collaborators).
> Update this file with every significant commit so everyone stays aligned.

---

## Contributors

| Name | GitHub | Role |
|------|--------|------|
| Satvik | @Satvik13o7 | Frontend TUI, LLM client, session system, CLI framework |
| Harsh Azad | btech10440.21@bitmesra.ac.in | Memory system (flat-file), context loader, CONCLAW.md, packaging |

---

## Architecture Overview

```
conclaw/
  src/conclaw/
    cli/            # Rich TUI app, components, themes       (Satvik)
    commands/       # Slash command registry + builtins       (Satvik + Harsh)
    config/         # Config loader, defaults                 (Satvik + Harsh)
    llm/            # Azure OpenAI client, prompts            (Satvik)
    session/        # Session manager, metadata               (Satvik)
    storage/        # Conversation JSONL, paths, memory tool  (Satvik + Harsh)
      context_loader.py  # CONCLAW.md + rules + auto-memory loader
      memory_tool.py     # Claude-style memory tool (view/create/edit/delete/rename)
      auto_memory.py     # Auto-memory writer (MEMORY.md + topic files)
      paths.py           # All path resolution (global, project, memory)
      conversation.py    # Append-only JSONL conversation log
  pyproject.toml      # Package metadata and deps             (Both)
  PRD.md              # Full product requirements             (Satvik)
  environment_CLI_level.md  # Backend-specific PRD            (Harsh)
  track.md            # This file                             (Both)
```

---

## Change Log

### 2026-03-25 -- Harsh (Initial backend scaffold)

- Created `pyproject.toml` (setuptools), `docker-compose.yml`, and flat backend modules:
  `db.py`, `memory.py`, `agent.py`, `safety.py`, `fs_ops.py`, `cli.py`, `config.py`.
- Created `environment_CLI_level.md` (backend PRD).
- Installed Python 3.12, psycopg, openai, pytest on dev machine.

### 2026-03-25 -- Satvik (Frontend TUI + new project structure)

- Switched build system to `hatchling`.
- Added rich TUI (`cli/app.py`), header banner, output area, themes (dark/light).
- Added Azure OpenAI LLM client with streaming, retry, and Key Vault fallback.
- Added session manager with JSONL conversation log.
- Added slash command registry: `/help`, `/exit`, `/clear`, `/files`, `/model`,
  `/history`, `/sessions`, `/config`, `/cost`.
- Added config loader with TOML support and environment overrides.
- Added `.env.example`, `.gitignore`.

### 2026-03-25 -- Harsh (Backend integration into new architecture)

- Pulled Satvik's changes and analyzed PRD.md + new codebase structure.
- Migrated flat backend files into `src/conclaw/backend/` sub-package:
  `db.py`, `memory.py`, `decision.py`, `safety.py`, `fs_ops.py`.
- Refactored backend modules to accept DSN parameter from unified config
  instead of old standalone `AppConfig` class.
- Added `backend.dsn`, `backend.db_mode`, `backend.filesystem_permission`
  to `config/defaults.py`.
- Added `psycopg[binary]` to project dependencies in `pyproject.toml`.
- Registered 3 new slash commands in `commands/builtins.py`:
  - `/db up` -- start Docker PostgreSQL container.
  - `/db init` -- create schema (memory_entries + decision_log tables).
  - `/memory set|get|list|delete` -- CRUD on persistent memory via Postgres.
  - `/decisions [limit]` -- view recent decision log entries.
- Removed old superseded flat files (`agent.py`, `cli.py`, `config.py`, `db.py`,
  `fs_ops.py`, `memory.py`, `safety.py`).
- Created `track.md` (this file).

### 2026-03-25 -- Harsh (Switch to Claude-style flat-file memory)

- **Removed entire PostgreSQL backend** (`backend/` package, `docker-compose.yml`,
  `psycopg` dependency). No database needed anymore.
- **New storage/context_loader.py**: walks directory tree to load CONCLAW.md files
  (project + user + ancestor), `.conclaw/rules/*.md`, and auto-memory MEMORY.md
  (first 200 lines). Supports `@path` imports (max depth 5).
- **New storage/memory_tool.py**: client-side memory tool matching Claude's spec.
  Commands: `view`, `create`, `str_replace`, `insert`, `delete`, `rename`.
  All ops restricted to `~/.conclaw/projects/<project>/memory/` with path
  traversal protection. Includes OpenAI function-calling tool definition.
- **New storage/auto_memory.py**: auto-memory writer. Conclaw saves notes for
  itself as plain `.md` files. MEMORY.md entrypoint + topic files.
- **Updated storage/paths.py**: added `auto_memory_dir()`, `memory_entrypoint()`,
  `project_rules_dir()`, `user_rules_dir()`, `_project_key()` (git-root hash).
- **Updated commands/builtins.py**: replaced `/db`, `/memory` (PG), `/decisions`
  with new `/memory` (lists loaded files, shows auto-memory status/path) and
  `/init` (generates starter CONCLAW.md).
- **Updated cli/app.py**: injects loaded instructions into LLM context at startup.
- **Updated llm/client.py**: added `inject_context()` method.
- **Updated config/defaults.py**: replaced `backend` section with `memory`
  (`auto_memory_enabled: true`).

---

## What Is Done (Implementation Status)

| Area | Status | Owner |
|------|--------|-------|
| Project scaffolding | Done | Both |
| Rich TUI (header, output, themes) | Done | Satvik |
| Azure OpenAI LLM client (stream + non-stream) | Done | Satvik |
| Slash command framework | Done | Satvik |
| Session management (create, close, list, JSONL log) | Done | Satvik |
| Config system (TOML + env overrides + defaults) | Done | Satvik |
| PostgreSQL schema + Docker Compose | Done | Harsh |
| Persistent memory CRUD (backend) | Done | Harsh |
| Decision logging (backend) | Done | Harsh |
| Safety layer (full_access / prompt modes) | Done | Harsh |
| CONCLAW.md loader (ancestor walk + @imports + rules) | Done | Harsh |
| Auto-memory system (MEMORY.md + topic files) | Done | Harsh |
| Memory tool (view/create/str_replace/insert/delete/rename) | Done | Harsh |
| /memory slash command (list files, status, dir path) | Done | Harsh |
| /init slash command (generate starter CONCLAW.md) | Done | Harsh |
| Context injection into LLM at session start | Done | Harsh |

---

## What Is Next (Pending)

| Area | Priority | Owner | PRD Section |
|------|----------|-------|-------------|
| Agent loop (plan-generate-review-execute-observe) | High | TBD | 4.2.1 |
| Code generation engine (python-docx, openpyxl) | High | TBD | 4.3 |
| Sandboxed code execution with timeout | High | TBD | 4.3.3 |
| Word document inspector | Medium | TBD | 4.4.1 |
| Excel file inspector | Medium | TBD | 4.4.2 |
| Session resume (`--resume <id>`) | Medium | TBD | 4.5.4 |
| CONCLAW.md project context injection | Medium | TBD | 4.5.5 |
| `/undo`, `/diff`, `/inspect`, `/run` slash commands | Medium | TBD | 4.6 |
| Developer account system (auth, vault, sync) | Low | TBD | 4.7 |
| Safety hardening v2 (path policies, sensitive file detection) | Low | Harsh | env PRD 10 |
| PyPI packaging + `pipx install conclaw` | Low | TBD | 6.2 |

---

## Conventions

- **Branch**: `main` (direct push for now; switch to feature branches when needed).
- **Build**: `hatchling` (pyproject.toml).
- **Config**: `~/.conclaw/config.toml` (global), `.conclaw/project.json` (per-project).
- **Backend DSN**: Comes from `config["backend"]["dsn"]`.
- **LLM**: Azure OpenAI via `openai` SDK; env var `AZURE_OPENAI_KEY`.
- **Python**: >=3.11.
- **Commit style**: Short imperative summary line, then detail paragraph.

---

## How to Run

```bash
git clone https://github.com/Satvik13o7/conclaw.git
cd conclaw
pip install -e .

# Set your API key
set AZURE_OPENAI_KEY=your_key_here    # Windows
export AZURE_OPENAI_KEY=your_key_here # Linux/macOS

# Create project instructions (optional)
conclaw
/init           # generates CONCLAW.md in cwd

# Inside the TUI:
/memory         # see loaded CONCLAW.md files, rules, auto-memory
/help           # all slash commands

# Memory persists as flat markdown files:
# ~/.conclaw/projects/<project>/memory/MEMORY.md   (auto-memory entrypoint)
# ./CONCLAW.md                                      (project instructions)
# ~/.conclaw/CONCLAW.md                             (user instructions)
# .conclaw/rules/*.md                               (project rules)
```

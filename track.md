# Conclaw -- Implementation Tracker

> Shared tracking document for all contributors (Harsh, Satvik, and collaborators).
> Update this file with every significant commit so everyone stays aligned.

---

## Contributors

| Name | GitHub | Role |
|------|--------|------|
| Satvik | @Satvik13o7 | Frontend TUI, LLM client, session system, CLI framework |
| Harsh Azad | btech10440.21@bitmesra.ac.in | Backend (PostgreSQL persistence, memory, decisions, safety, fs), packaging |

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
    storage/        # Conversation JSONL, paths               (Satvik)
    backend/        # PostgreSQL memory, decision log, safety (Harsh)
  docker-compose.yml  # One-command local Postgres bootstrap  (Harsh)
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

### 2026-03-25 -- Harsh (Auto-discover DB + agent tools)

- Added `discover_and_connect()` in `backend/db.py`: auto-scans localhost
  ports 5432/5433, creates `conclaw` database if missing, initialises schema.
- Added `/db connect` slash command so users can connect with one command.
- Created `backend/tools.py`: defines OpenAI-compatible tool schemas
  (`db_connect`, `memory_set`, `memory_get`, `memory_list`, `memory_delete`,
  `log_decision`) and `ToolExecutor` class so the orchestrator agent can
  call these as function-calling tools.

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
| Slash commands for backend (/db, /memory, /decisions) | Done | Harsh |
| Backend integrated into unified config | Done | Harsh |
| Auto-discover localhost PostgreSQL (/db connect) | Done | Harsh |
| Agent-callable tools (ToolExecutor + TOOL_DEFINITIONS) | Done | Harsh |

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
pip install -e ".[dev]"

# Set your API key
set AZURE_OPENAI_KEY=your_key_here    # Windows
export AZURE_OPENAI_KEY=your_key_here # Linux/macOS

# Launch
conclaw

# Inside the TUI:
/db up          # start Docker Postgres
/db init        # create tables
/memory set global project_name conclaw
/memory list global
/decisions
```

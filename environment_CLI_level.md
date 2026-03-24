# Conclaw Environment CLI Level PRD

## 1. Product Overview
Conclaw is a Python CLI package that provides persistent memory via local PostgreSQL, GPT-5.0-driven decision support, and filesystem operations with configurable safety controls.  
It must work for users who install a local PostgreSQL instance or prefer Docker-managed PostgreSQL, and persist data on the user’s laptop.

## 2. Goals
- Provide reliable persistent memory for CLI workflows.
- Make setup simple for users (`pip install` + `conclaw init`).
- Support both DB modes:
  - system PostgreSQL
  - Docker-managed PostgreSQL
- Default to full filesystem access mode (as requested), with safety-layer modes available for later hardening.
- Route decisions through `gpt-5.0` (or configured model) with memory context.

## 3. Non-Goals (Current Scope)
- Cloud-hosted memory backend.
- Multi-tenant server deployment.
- Enterprise IAM/RBAC integration.
- GUI application.

## 4. Target Users
- Developers using CLI agents/automation locally.
- Power users who want persistent local task context.
- Teams cloning the repo and running the package with laptop-local persistence.

## 5. Core Use Cases
1. User initializes CLI and DB in minutes.
2. User stores and retrieves key-value memory by scope.
3. User asks CLI to make a decision using GPT-5.0 + saved memory context.
4. User reads/writes local files under chosen permission mode.
5. User clones package and reuses the same workflow on another laptop with local persistence.

## 6. Functional Requirements

### FR-1 Initialization
- `conclaw init` stores local config under `~/.conclaw/config.json`.
- Config fields:
  - `db_mode` (`system_or_docker`, `system`, `docker`)
  - `dsn`
  - `model_name` (default `gpt-5.0`)
  - `filesystem_permission` (default `full_access`)
  - `safety_layer`

### FR-2 Database Modes
- `conclaw db up` launches Docker PostgreSQL (`docker compose up -d`) when Docker mode is used.
- `conclaw db init` creates required schema.
- System PostgreSQL mode must work with user-provided DSN.

### FR-3 Persistent Memory
- Provide CRUD-like operations for scoped key-value memory:
  - `conclaw memory set --scope ... --key ... --value ...`
  - `conclaw memory get --scope ... --key ...`
  - `conclaw memory list --scope ... --limit ...`
- Data persists in PostgreSQL across sessions/restarts.

### FR-4 Decision Engine
- `conclaw decide --scope ... --task ...` sends task + memory context to GPT model.
- Default model is `gpt-5.0`.
- If API key/model client unavailable, provide deterministic offline fallback response.
- Every decision is logged in DB (`decision_log` table).

### FR-5 Filesystem Access and Safety
- `conclaw fs read --path ...`
- `conclaw fs write --path ... --content ...`
- Permission modes:
  - `full_access` (default)
  - `prompt_session`
  - `prompt_sensitive`
- Safety layer must be pluggable so stricter controls can be added later.

### FR-6 Packaging and Clone Experience
- Package is installable via Python packaging (`pyproject.toml`).
- Repo clone + install should be sufficient for first run.
- Persistent state uses laptop-local resources:
  - Postgres data directory/volume
  - user config path (`~/.conclaw`)

## 7. Non-Functional Requirements
- **Reliability:** DB operations should be transactional and safe under retries.
- **Performance:** memory read/list and decision context assembly should be fast for typical local usage (<1s excluding network model call).
- **Portability:** works on Windows/macOS/Linux with Python 3.10+.
- **Security baseline:** no secrets hardcoded; model key taken from environment variable.
- **Observability:** decision and key operations are auditable via DB logs.

## 8. Data Model

### memory_entries
- `id` (PK)
- `scope` (TEXT, indexed via unique composite)
- `memory_key` (TEXT)
- `memory_value` (TEXT)
- `created_at`, `updated_at`
- Unique constraint: `(scope, memory_key)`

### decision_log
- `id` (PK)
- `task` (TEXT)
- `decision` (TEXT)
- `model_name` (TEXT)
- `created_at`

## 9. CLI Command Surface (MVP)
- `conclaw init [--db-mode ...] [--dsn ...] [--model ...] [--filesystem-permission ...]`
- `conclaw db up`
- `conclaw db init`
- `conclaw memory set/get/list`
- `conclaw decide`
- `conclaw fs read/write`

## 10. Safety and Risk Controls
- **Default (requested):** `full_access`.
- **Later-stage protection layer roadmap:**
  1. Path allowlist/denylist
  2. Sensitive file pattern detection (`.env`, keys, credentials)
  3. Action policy engine (read/write/delete thresholds)
  4. Optional dry-run mode for decision-to-action flows
  5. Signed action logs for auditability

## 11. Packaging and Distribution Requirements
- Python package metadata in `pyproject.toml`.
- Runtime dependencies:
  - `psycopg[binary]`
  - `openai`
- Optional dev dependency:
  - `pytest`
- Docker compose file included for one-command local Postgres bootstrap.

## 12. Acceptance Criteria
1. Fresh user can clone repo, install package, initialize config, and start DB.
2. User can set/get/list memory with persistence across CLI restarts.
3. User can run `decide` and see memory-informed output + decision log entry.
4. Filesystem commands work in `full_access` and respect prompt modes.
5. Project package can be installed and command `conclaw` is exposed.

## 13. Milestones
- **M1 (Current):** Core CLI + PostgreSQL persistence + decision logging + fs modes.
- **M2:** Safety hardening layer v1 (path policies + sensitive file guardrails).
- **M3:** Advanced policy/risk scoring + richer observability.

## 14. Open Items
- Finalize policy for destructive file actions (`delete`, recursive writes).
- Confirm minimum supported Docker version.
- Add migration strategy for schema evolution.

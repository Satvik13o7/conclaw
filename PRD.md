# Conclaw - Product Requirements Document

## 1. Overview

Conclaw is a CLI-based agentic system that automates Microsoft Word and Excel file operations through natural language. Users describe what they want done to their documents, and Conclaw generates and executes Python (or VBA) code that calls the appropriate Word/Excel APIs to fulfill the request. The interface is a rich terminal UI inspired by tools like Claude Code and Droid, complete with session tracking, model info, and comprehensive logging.

---

## 2. Problem Statement

Editing Word and Excel files programmatically requires knowledge of libraries like `python-docx`, `openpyxl`, `xlsxwriter`, or VBA macros. Non-developers and even developers waste significant time looking up APIs, writing boilerplate, and debugging document manipulation scripts. Conclaw eliminates this friction by acting as an intelligent agent that translates natural-language instructions into executable code, runs it, and presents the results -- all from the terminal.

---

## 3. Target Users

| Persona | Description |
|---|---|
| **Power Users / Analysts** | People who work with large volumes of Word/Excel files and need batch processing, formatting, or data extraction without writing code manually. |
| **Developers** | Engineers who need quick document automation without memorizing library APIs. |
| **Data Teams** | Teams that need to generate reports, populate templates, or transform spreadsheet data programmatically. |
| **IT / Ops** | Staff who need repeatable, auditable document workflows from the command line. |

---

## 4. Core Features

### 4.1 CLI Frontend (Terminal UI)

A rich, interactive terminal interface that serves as the primary interaction surface.

#### 4.1.1 Header / Status Bar

| Element | Description |
|---|---|
| **Product Name** | "conclaw" rendered prominently (styled/colored ASCII text). |
| **Model Name** | The LLM model currently in use (e.g., `gpt-4o`, `claude-sonnet-4`, `llama-3`). |
| **Session Timer** | Elapsed time since the session started, displayed as `HH:MM:SS`, updated in real-time. |
| **Current Time** | Local wall-clock time, updated every second. |
| **Working Directory** | The directory Conclaw was launched from. |
| **Active File(s)** | The document(s) currently being operated on, if any. |
| **Account** | Logged-in user email and plan badge (e.g., `dev@example.com [Pro]`), or `anonymous` if not logged in. |

#### 4.1.2 Input Area

- A multi-line input prompt (like a REPL) where the user types natural-language queries or commands.
- Supports standard line-editing (arrow keys, home/end, history via up/down).
- Slash-commands for meta-operations (see Section 4.6).

#### 4.1.3 Output Area

- Streaming display of agent responses (thought process, generated code, execution results).
- Syntax-highlighted code blocks for generated Python/VBA.
- Collapsible/expandable sections for verbose output (e.g., full code, stack traces).
- Status indicators: spinner while agent is thinking, checkmarks on success, X on failure.

#### 4.1.4 Session Summary Footer

- Token usage (prompt tokens / completion tokens / total).
- Cost estimate (if applicable, based on model pricing).
- Number of tool calls / code executions in the session.

---

### 4.2 Agent System (LLM Core)

The brain of Conclaw. An agentic loop that takes user instructions, reasons about them, generates code, executes it, observes results, and iterates.

#### 4.2.1 Agent Loop

```
User Query
    |
    v
[Plan] -- LLM reasons about the task, identifies target file(s), decides approach
    |
    v
[Generate Code] -- LLM writes Python or VBA code using document APIs
    |
    v
[Review] -- Agent self-reviews the code for correctness and safety
    |
    v
[Execute] -- Code is run in a sandboxed subprocess
    |
    v
[Observe] -- Agent inspects stdout, stderr, file changes, exceptions
    |
    v
[Respond] -- Agent summarizes what happened and presents results
    |
    v
[Iterate?] -- If the result is wrong or incomplete, loop back to [Plan]
```

#### 4.2.2 LLM Provider Support

| Provider | Models |
|---|---|
| OpenAI | gpt-4o, gpt-4o-mini, o1, o3 |
| Anthropic | claude-sonnet-4, claude-opus-4 |
| Local (Ollama) | llama-3, codellama, mistral, etc. |
| Custom | Any OpenAI-compatible API endpoint |

Configuration via environment variables or a `.conclaw/config.toml` file.

#### 4.2.3 System Prompt Design

The system prompt instructs the LLM to:
- Always generate executable Python (preferred) or VBA code.
- Use `python-docx` for Word `.docx` files.
- Use `openpyxl` for reading/writing Excel `.xlsx` files.
- Use `xlsxwriter` when creating new Excel files from scratch.
- Use `python-pptx` for PowerPoint files (future scope).
- Use `win32com.client` (COM automation) when the user explicitly requests VBA or when the task requires features only available through COM (e.g., running macros, PDF export on Windows).
- Never delete or overwrite the original file without explicit user confirmation.
- Always create backups before destructive operations.
- Return structured output the agent can parse (success/failure, file paths, summaries).

#### 4.2.4 Context Management

- **File Awareness**: Before generating code, the agent reads and summarizes the target file's structure (headings, table count, sheet names, row/column counts, etc.).
- **Conversation Memory**: Full conversation history is maintained within a session. Long conversations are summarized to stay within context limits.
- **Tool Results**: stdout/stderr from code execution are fed back into the conversation as tool-call results.

---

### 4.3 Code Generation Engine

#### 4.3.1 Python Code Generation (Primary)

The default mode. Conclaw generates Python scripts that use:

| Library | Use Case |
|---|---|
| `python-docx` | Read/write/modify `.docx` files (paragraphs, tables, styles, headers, footers, images). |
| `openpyxl` | Read/write/modify `.xlsx` files (cells, formulas, charts, formatting, sheets). |
| `xlsxwriter` | Create new `.xlsx` files with complex formatting, charts, and data validation. |
| `pandas` | Data manipulation before writing to Excel (pivot, filter, aggregate). |
| `Pillow` | Image handling for insertion into documents. |
| `python-pptx` | PowerPoint automation (future scope). |

#### 4.3.2 VBA Code Generation (Secondary)

When the user requests VBA or the task requires COM-specific features:

- Generate `.vbs` scripts or inline VBA macro code.
- Execute via `win32com.client` on Windows or provide the VBA code for the user to paste into the macro editor.
- Clearly label VBA output and warn about platform limitations (Windows-only for COM).

#### 4.3.3 Code Safety and Sandboxing

- All generated code runs in a **subprocess** with:
  - A timeout (configurable, default 60 seconds).
  - No network access (unless explicitly allowed by the user).
  - File system access limited to the working directory and explicitly specified paths.
- Before execution, the agent performs a **self-review** checking for:
  - Unintended file deletions.
  - Writes outside the working directory.
  - Suspicious imports (e.g., `os.system`, `subprocess`, `shutil.rmtree`).
- **User confirmation** is required before executing code that:
  - Modifies or deletes existing files.
  - Writes to paths outside the current directory.
  - Uses network or system calls.

---

### 4.4 File Operations

#### 4.4.1 Word Document Operations

| Operation | Description |
|---|---|
| **Read/Inspect** | Extract text, list headings, count pages/paragraphs, describe structure. |
| **Edit Text** | Find and replace, insert/delete paragraphs, modify specific sections. |
| **Formatting** | Apply styles, change fonts, set alignment, adjust spacing. |
| **Tables** | Create, modify, populate, format tables. |
| **Headers/Footers** | Add/edit headers, footers, page numbers. |
| **Images** | Insert, resize, reposition images. |
| **Merge** | Combine multiple Word documents into one. |
| **Convert** | Export to PDF (via COM on Windows, or libreoffice CLI). |
| **Templates** | Populate a template document with provided data. |
| **Mail Merge** | Generate multiple documents from a template + data source (Excel/CSV). |

#### 4.4.2 Excel Spreadsheet Operations

| Operation | Description |
|---|---|
| **Read/Inspect** | List sheets, describe schema, preview data, count rows/columns. |
| **Edit Cells** | Write values, formulas, or data ranges to specific cells/sheets. |
| **Formatting** | Apply cell styles, conditional formatting, number formats, column widths. |
| **Charts** | Create bar, line, pie, scatter charts from data ranges. |
| **Pivot-like** | Summarize, group, aggregate data (via pandas + openpyxl). |
| **Data Validation** | Add dropdowns, input restrictions, custom validation rules. |
| **Filtering/Sorting** | Filter rows by criteria, sort by columns. |
| **Multiple Sheets** | Create, rename, delete, copy, reorder sheets. |
| **Cross-file** | Copy data between Excel files, merge workbooks. |
| **CSV Import/Export** | Read CSV into Excel, export sheets as CSV. |
| **Formulas** | Insert Excel formulas, named ranges, array formulas. |

---

### 4.5 Storage System, Sessions, and Logging

Conclaw uses a **local-first, flat-file storage model** inspired by Claude Code -- no embedded database (no SQLite, no Postgres). All state is stored as human-readable JSON, JSONL, TOML, and Markdown files on disk. This ensures zero external dependencies, easy inspection/debugging, portability, and no migration headaches.

#### 4.5.1 Storage Layout (Claude Code-Style)

Conclaw uses two storage scopes, mirroring how Claude Code splits between `~/.claude/` (global) and per-project state:

**Global storage** -- `~/.conclaw/` (user-level, shared across all projects):

```
~/.conclaw/
    config.toml                     # Global settings (model, provider, theme, etc.)
    auth.json                       # Account credentials (JWT refresh token, encrypted)
    vault.key                       # Device-bound encryption key for API key vault
    credentials.enc                 # Encrypted API keys (Fernet, keyed by vault.key)
    settings.json                   # User preferences (synced with account if logged in)
    conclaw.log                     # Global aggregate log file
    sessions/
        index.jsonl                 # Session index -- one line per session for fast listing
                                    # {id, project_path, started_at, summary, status}
        <session-id>/
            session.json            # Session metadata (start/end time, model, cwd, status)
            conversation.jsonl      # Full chat history (append-only, one JSON obj per line)
                                    # Each line: {role, content, timestamp, tokens, tool_calls}
            code/                   # Generated code, numbered sequentially
                001_edit_word.py
                002_format_excel.py
            backups/                # Auto-backups of files before modification
                report.docx.bak
            logs/
                execution.log       # stdout/stderr from each code execution
                conclaw.log         # Session-level agent log
```

**Project-scoped storage** -- `.conclaw/` in the project/working directory (like Claude Code's `CLAUDE.md`):

```
<project-dir>/
    .conclaw/
        CONCLAW.md                  # Project-level instructions/context (user-editable)
                                    # Automatically injected into the system prompt.
                                    # Similar to CLAUDE.md -- users can write rules like:
                                    # "Always use openpyxl, never xlsxwriter"
                                    # "Default output dir is ./reports/"
        project.json                # Project-specific settings (overrides global config)
                                    # {default_files, preferred_libraries, custom_prompts}
        templates/                  # Project-local document templates
            invoice_template.docx
            monthly_report.xlsx
```

#### 4.5.2 Storage Design Principles

| Principle | Implementation |
|---|---|
| **No database** | All storage is flat files -- JSON, JSONL, TOML, Markdown. Human-readable and `cat`-able. |
| **Append-only conversation log** | `conversation.jsonl` is append-only (one JSON object per line). Never rewritten mid-session. Safe against crashes -- partial writes lose at most one line. |
| **Session index for fast lookup** | `sessions/index.jsonl` is a lightweight index so `conclaw` doesn't need to scan every session directory to list recent sessions. Updated on session create/close. |
| **Project context via CONCLAW.md** | Like Claude Code's `CLAUDE.md`, this file lets users define persistent project-level instructions that are auto-injected into every agent prompt for that project. |
| **Secrets never in plaintext** | API keys encrypted at rest via `cryptography` Fernet. Auth tokens stored with restrictive file permissions (`600`). |
| **Portable** | The entire `~/.conclaw/` directory can be copied to another machine (minus `vault.key` which is device-bound). |
| **Inspectable** | Users can `cat`, `jq`, or `grep` any file to debug or audit agent behavior. No opaque binary blobs. |

#### 4.5.3 Conversation JSONL Format

Each line in `conversation.jsonl` is a self-contained JSON object:

```jsonl
{"role":"user","content":"Add a title to report.docx","timestamp":"2026-03-25T14:32:01Z","tokens":12}
{"role":"assistant","content":"I'll inspect report.docx first...","timestamp":"2026-03-25T14:32:03Z","tokens":45,"tool_calls":[{"type":"inspect","file":"report.docx"}]}
{"role":"tool","name":"inspect","content":"{\"paragraphs\":5,\"tables\":0}","timestamp":"2026-03-25T14:32:04Z"}
{"role":"assistant","content":"Generating code to add the title...","timestamp":"2026-03-25T14:32:05Z","tokens":120,"code_ref":"001_add_title.py"}
{"role":"tool","name":"execute","content":"{\"exit_code\":0,\"stdout\":\"Title added.\"}","timestamp":"2026-03-25T14:32:06Z"}
{"role":"assistant","content":"Done. Title 'Q4 Report' added to report.docx.","timestamp":"2026-03-25T14:32:06Z","tokens":30}
```

#### 4.5.4 Session Management

- Each `conclaw` invocation starts a new session with a UUID.
- Session metadata (`session.json`) is written on start and updated on close.
- The session index (`sessions/index.jsonl`) is appended with one line per session.
- **Resume**: `conclaw --resume <session-id>` or `conclaw --resume last` reloads conversation history into the LLM context.
- **List**: `conclaw sessions` or `/sessions` lists recent sessions from the index file.
- **Prune**: `conclaw sessions prune --older-than 30d` cleans up old session directories.

#### 4.5.5 CONCLAW.md (Project Context File)

Placed at `.conclaw/CONCLAW.md` in any project directory. Automatically detected and injected into the system prompt when `conclaw` is launched from that directory.

Example:
```markdown
# Project Rules

- All generated Excel files must use the `openpyxl` library, never `xlsxwriter`.
- Default output directory is `./output/`. Create it if it doesn't exist.
- Always preserve existing formatting when editing Word documents.
- Template files are in `.conclaw/templates/` -- prefer them over creating from scratch.
- Currency values must use the format `$#,##0.00`.
```

This is the Conclaw equivalent of Claude Code's `CLAUDE.md` -- a way for users to encode persistent, project-specific instructions without repeating them every session.

#### 4.5.6 Logging

All activity is logged at multiple levels:

| Log Level | What is Logged |
|---|---|
| **INFO** | User queries, agent responses (summarized), code execution start/end, file operations. |
| **DEBUG** | Full LLM request/response payloads, generated code, execution stdout/stderr, file diffs. |
| **WARN** | Sandbox violations caught, code review flags, retries. |
| **ERROR** | Execution failures, LLM API errors, file I/O errors. |

- Session logs: `~/.conclaw/sessions/<session-id>/logs/conclaw.log`
- Global log: `~/.conclaw/conclaw.log` (aggregates across sessions).
- Log level configurable via `--log-level` flag or `config.toml`.

#### 4.5.7 Activity Log (User-Facing)

A structured, human-readable activity log displayed in the TUI and saved to disk:

```
[12:34:01] User: "Add a table of contents to report.docx"
[12:34:03] Agent: Planning -- inspecting report.docx structure
[12:34:05] Agent: Reading file -- found 12 headings across 3 levels
[12:34:07] Agent: Generating code -- python-docx script to insert TOC
[12:34:08] Agent: Code review -- PASS (no dangerous operations)
[12:34:08] Agent: Executing -- 001_add_toc.py
[12:34:09] Agent: Success -- TOC added to report.docx (backup at backups/report.docx.bak)
[12:34:09] Cost: 1,234 tokens | $0.002 | 8.2s elapsed
```

---

### 4.6 Slash Commands

Built-in commands available in the REPL:

| Command | Description |
|---|---|
| `/help` | Show all available commands and usage tips. |
| `/model <name>` | Switch the active LLM model. |
| `/files` | List files in the working directory. |
| `/inspect <file>` | Show structure/summary of a Word or Excel file without modifying it. |
| `/history` | Show conversation history for the current session. |
| `/sessions` | List recent sessions with timestamps and summaries. |
| `/resume <id>` | Resume a previous session. |
| `/export` | Export the current session's conversation and code to a markdown file. |
| `/config` | Show or edit configuration. |
| `/cost` | Show token usage and cost for the current session. |
| `/clear` | Clear the screen. |
| `/undo` | Restore the last modified file from its backup. |
| `/diff <file>` | Show a diff of the file before and after the last modification. |
| `/run <file.py>` | Manually run a Python script in the sandbox. |
| `/exit` or `/quit` | End the session. |

---

### 4.7 Developer Account System

Conclaw provides an account system that ties usage, sessions, preferences, and API key management to a persistent developer identity. Accounts can be used locally (offline-only) or synced to a Conclaw cloud backend for cross-machine access, team features, and usage analytics.

#### 4.7.1 Account Types

| Tier | Description | Limits |
|---|---|---|
| **Anonymous (No Account)** | Default mode. All data is local-only. No login required. Uses user-supplied API keys. | Unlimited local usage. No sync, no cloud features. |
| **Free** | Registered developer account. Enables session sync, usage dashboard, and community model presets. | 500 LLM requests/month via Conclaw proxy (or unlimited with own API keys). 5 GB session storage. |
| **Pro** | Paid individual plan. Higher limits, priority model routing, advanced analytics. | 10,000 LLM requests/month via Conclaw proxy. 50 GB session storage. Priority support. |
| **Team** | Organization plan. Shared templates, centralized billing, team usage dashboards. | Custom limits. Shared template library. Admin controls. Audit logs. |

#### 4.7.2 Registration and Authentication

- **Registration**: `conclaw auth register` -- prompts for email and password (or OAuth via GitHub/Google).
- **Login**: `conclaw auth login` -- authenticates and stores a refresh token locally at `~/.conclaw/auth.json`.
- **Logout**: `conclaw auth logout` -- clears local credentials.
- **Token Refresh**: Tokens auto-refresh silently. If the refresh token expires, the user is prompted to re-login on next session start.
- **Passwordless Option**: Magic-link login via email for users who prefer not to manage passwords.

```
$ conclaw auth login
  Email: dev@example.com
  Password: ********
  Authenticated as dev@example.com (Pro plan)
  Token stored at ~/.conclaw/auth.json
```

#### 4.7.3 Developer Profile

Each account has a profile stored locally and (optionally) synced to the cloud:

```json
{
  "id": "usr_abc123",
  "email": "dev@example.com",
  "display_name": "Jane Dev",
  "plan": "pro",
  "created_at": "2026-01-15T10:30:00Z",
  "preferences": {
    "default_model": "claude-sonnet-4",
    "default_provider": "anthropic",
    "theme": "dark",
    "confirm_before_write": true,
    "auto_backup": true
  },
  "api_keys": {
    "openai": "encrypted::<vault-ref>",
    "anthropic": "encrypted::<vault-ref>"
  },
  "usage": {
    "current_period_start": "2026-03-01T00:00:00Z",
    "requests_used": 1247,
    "requests_limit": 10000,
    "tokens_used": 2450000,
    "storage_used_mb": 312
  }
}
```

#### 4.7.4 API Key Management

- **BYOK (Bring Your Own Key)**: Users can store their own API keys, which are encrypted at rest using a device-bound key (`~/.conclaw/vault.key`) and never transmitted to the Conclaw backend.
- **Conclaw Proxy**: Free and Pro users can optionally route LLM requests through the Conclaw API proxy, which handles API key management server-side. The user never sees or manages raw API keys in this mode.
- **Key Rotation**: `conclaw auth keys rotate <provider>` generates a reminder or triggers rotation for proxy-managed keys.
- **Key Priority**: If both a user-supplied key and the Conclaw proxy are available, user-supplied keys take precedence (configurable).

```
$ conclaw auth keys add openai
  Paste your OpenAI API key: sk-...
  Key encrypted and stored in local vault.

$ conclaw auth keys list
  Provider    Source     Status
  openai      local      Active
  anthropic   proxy      Active (Pro plan)
```

#### 4.7.5 Session Sync (Cloud)

- Logged-in users can sync sessions to the Conclaw cloud for cross-machine access.
- Sync is **opt-in** and **selective** -- users choose which sessions to sync.
- Synced data: `session.json`, `conversation.jsonl`, generated code. File backups are **not** synced (too large, contains user data).
- Conflict resolution: last-write-wins with a warning if the same session was modified on two machines.
- Slash command: `/sync` pushes the current session. `/sync pull <id>` pulls a remote session.
- All synced data is encrypted in transit (TLS) and at rest (AES-256).

#### 4.7.6 Usage Dashboard

Available via `conclaw auth usage` or `/usage` slash command:

```
$ conclaw auth usage

  Plan: Pro | Period: Mar 1 - Mar 31, 2026

  LLM Requests:   1,247 / 10,000  [============--------] 12.5%
  Tokens Used:    2.45M
  Est. Cost:      $18.40 (proxy) | $0.00 (BYOK)
  Sessions:       34 this period
  Storage:        312 MB / 50 GB

  Top Models:
    claude-sonnet-4    682 requests  (54.7%)
    gpt-4o             401 requests  (32.2%)
    llama-3 (local)    164 requests  (13.1%)
```

#### 4.7.7 Team Features (Team Plan)

- **Shared Template Library**: Team members can publish and consume document templates (Word/Excel) via `conclaw templates publish <file>` and `conclaw templates pull <name>`.
- **Centralized Billing**: A team admin manages API key allocation and spending limits per member.
- **Usage Audit Logs**: Admins can view aggregated usage across all team members -- who ran what, when, token costs.
- **Role-Based Access**: `admin` (full control), `member` (standard usage), `viewer` (read-only dashboard access).

#### 4.7.8 Account-Related Slash Commands

| Command | Description |
|---|---|
| `/account` | Show current account info (email, plan, usage summary). |
| `/usage` | Show detailed usage dashboard for the current billing period. |
| `/sync` | Push current session to cloud. |
| `/sync pull <id>` | Pull a synced session from cloud. |
| `/keys` | List configured API keys and their status. |
| `/upgrade` | Show plan comparison and open upgrade URL. |

#### 4.7.9 Account-Related CLI Commands

| Command | Description |
|---|---|
| `conclaw auth register` | Create a new developer account. |
| `conclaw auth login` | Authenticate with email/password or OAuth. |
| `conclaw auth logout` | Clear local credentials. |
| `conclaw auth status` | Show current auth state and plan info. |
| `conclaw auth keys add <provider>` | Store an API key in the encrypted local vault. |
| `conclaw auth keys list` | List all configured API keys. |
| `conclaw auth keys remove <provider>` | Remove a stored API key. |
| `conclaw auth keys rotate <provider>` | Rotate/update an API key. |
| `conclaw auth usage` | Show usage dashboard. |
| `conclaw auth upgrade` | Open the plan upgrade page. |

#### 4.7.10 Security and Privacy

- **Local-first**: All account data is usable offline. Cloud sync is optional.
- **Encryption at rest**: API keys encrypted with a device-bound key via `cryptography` (Fernet). The vault key never leaves the device.
- **Encryption in transit**: All cloud communication over TLS 1.3.
- **No telemetry without consent**: Anonymous users are never tracked. Logged-in users can opt out of usage analytics.
- **Data deletion**: `conclaw auth delete-account` wipes all cloud data and local credentials. Sessions on disk are preserved (user's choice to delete).
- **GDPR/Privacy**: Users can export all their cloud data via `conclaw auth export-data`.

---

## 5. Configuration

### 5.1 Config File

Location: `~/.conclaw/config.toml`

```toml
[llm]
provider = "openai"             # openai | anthropic | ollama | custom
model = "gpt-4o"                # Default model
api_key_env = "OPENAI_API_KEY"  # Env var name holding the API key
base_url = ""                   # Custom endpoint (for ollama or proxies)
temperature = 0.2               # Lower = more deterministic code generation
max_tokens = 4096               # Max tokens per LLM response

[execution]
timeout = 60                    # Code execution timeout in seconds
sandbox = true                  # Enable sandboxed execution
auto_backup = true              # Backup files before modification
confirm_before_write = true     # Ask user before modifying files

[ui]
theme = "dark"                  # dark | light | auto
show_code = true                # Show generated code in the TUI
show_tokens = true              # Show token usage
show_cost = true                # Show cost estimates
stream = true                   # Stream LLM responses

[logging]
level = "INFO"                  # DEBUG | INFO | WARN | ERROR
file = "~/.conclaw/conclaw.log"

[account]
sync_sessions = false           # Auto-sync sessions to cloud
key_source = "local"            # local (BYOK) | proxy (Conclaw-managed)
telemetry = false               # Opt-in anonymous usage analytics
```

### 5.2 Environment Variables

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `CONCLAW_MODEL` | Override default model |
| `CONCLAW_LOG_LEVEL` | Override log level |
| `CONCLAW_CONFIG` | Custom config file path |
| `CONCLAW_API_URL` | Conclaw backend API URL (for account/sync features) |
| `CONCLAW_NO_ACCOUNT` | Set to `1` to disable all account/cloud features |

---

## 6. Technical Architecture

### 6.1 High-Level Architecture

```
+-------------------------------------------------------------+
|                        CLI Frontend                          |
|  (Rich TUI: prompt, output, status bar, session info)        |
+-------------------------------------------------------------+
        |                                          ^
        | User input                               | Formatted output
        v                                          |
+-------------------------------------------------------------+
|                        Agent Core                            |
|  (Agentic loop: plan -> generate -> review -> execute)       |
|  - Conversation manager                                      |
|  - Context builder (file inspection, history)                |
|  - Code generator (Python / VBA)                             |
|  - Code reviewer (safety checks)                             |
+-------------------------------------------------------------+
        |                |                         |
        | LLM API calls  | Code execution          | Account ops
        v                v                         v
+----------------+ +---------------------+ +-------------------------+
| LLM Providers  | | Execution Sandbox   | | Account & Auth Layer    |
| - OpenAI       | | - subprocess with   | | - Developer profile     |
| - Anthropic    | |   timeout/isolation | | - Encrypted key vault   |
| - Ollama       | | - File I/O monitor  | | - Session sync (cloud)  |
| - Custom       | | - Backup management | | - Usage tracking        |
| - Conclaw      | +---------------------+ | - Team management       |
|   Proxy (acct) |            |            +-------------------------+
+----------------+            v                         |
                   +-------------------------+          |
                   |   Document Libraries    |          v
                   |  - python-docx          |  +-------------------+
                   |  - openpyxl             |  | Conclaw Backend   |
                   |  - xlsxwriter           |  | (Cloud, Optional) |
                   |  - pandas               |  | - Auth service    |
                   |  - win32com (VBA/COM)   |  | - Session store   |
                   +-------------------------+  | - Usage metering  |
                              |                 | - Team mgmt       |
                              v                 | - LLM proxy       |
                   +-------------------------+  +-------------------+
                   |   Target Files          |
                   |  - .docx / .doc         |
                   |  - .xlsx / .xls / .csv  |
                   +-------------------------+
```

### 6.2 Tech Stack

| Component | Technology |
|---|---|
| **Language** | Python 3.11+ |
| **CLI Framework** | `textual` or `rich` + `prompt_toolkit` |
| **LLM Client** | `litellm` (unified interface to all providers) |
| **Word Processing** | `python-docx`, `win32com.client` (Windows) |
| **Excel Processing** | `openpyxl`, `xlsxwriter`, `pandas` |
| **Code Execution** | `subprocess` with resource limits |
| **Configuration** | `tomli` / `tomli-w` for TOML parsing |
| **Logging** | Python `logging` module with `rich` handler |
| **Session Storage** | JSON/JSONL files on disk |
| **Account/Auth** | `httpx` (async HTTP client), `cryptography` (Fernet encryption for vault), JWT tokens |
| **Packaging** | `pyproject.toml` with `hatchling` or `setuptools` |
| **Distribution** | PyPI package + `pipx install conclaw` |

### 6.3 Project Structure

```
conclaw/
    pyproject.toml
    README.md
    src/
        conclaw/
            __init__.py
            __main__.py          # Entry point: `python -m conclaw`
            cli/
                __init__.py
                app.py           # Main TUI application
                components/      # TUI widgets (header, input, output, status bar)
                    __init__.py
                    header.py
                    input_area.py
                    output_area.py
                    status_bar.py
                themes/
                    __init__.py
                    dark.py
                    light.py
            agent/
                __init__.py
                loop.py          # Main agent loop (plan-generate-execute-observe)
                planner.py       # Task planning and decomposition
                generator.py     # Code generation (Python & VBA)
                reviewer.py      # Code safety review
                context.py       # Context builder (file inspection, history mgmt)
            llm/
                __init__.py
                client.py        # Unified LLM client (wraps litellm)
                providers.py     # Provider-specific config and helpers
                prompts.py       # System prompts and prompt templates
            executor/
                __init__.py
                sandbox.py       # Sandboxed code execution
                monitor.py       # File I/O monitoring
                backup.py        # Automatic backup management
            documents/
                __init__.py
                word.py          # Word document inspection and helpers
                excel.py         # Excel file inspection and helpers
                detect.py        # File type detection
            storage/
                __init__.py
                paths.py         # Resolve global (~/.conclaw/) and project (.conclaw/) paths
                session_index.py # Read/write sessions/index.jsonl
                conversation.py  # Append-only JSONL conversation log reader/writer
                project_context.py  # Load and inject CONCLAW.md into prompts
            session/
                __init__.py
                manager.py       # Session create/save/resume/list/prune
                history.py       # Conversation history management
            config/
                __init__.py
                loader.py        # Config file loading and validation
                defaults.py      # Default configuration values
            logging/
                __init__.py
                setup.py         # Logging configuration
                activity.py      # User-facing activity log
            account/
                __init__.py
                auth.py          # Registration, login, logout, token refresh
                profile.py       # Developer profile management
                vault.py         # Encrypted API key storage (Fernet)
                sync.py          # Session sync to/from Conclaw cloud
                usage.py         # Usage tracking and dashboard rendering
                teams.py         # Team plan features (shared templates, admin)
                api_client.py    # HTTP client for Conclaw backend API
            commands/
                __init__.py
                registry.py      # Slash command registration
                builtins.py      # Built-in slash command implementations
    tests/
        __init__.py
        test_agent/
        test_cli/
        test_executor/
        test_documents/
        test_session/
        test_commands/
        test_account/
        fixtures/               # Sample .docx and .xlsx files for testing
```

---

## 7. User Flows

### 7.1 First Run

```
$ pip install conclaw   (or: pipx install conclaw)
$ conclaw

  ██████╗ ██████╗ ███╗   ██╗ ██████╗██╗      █████╗ ██╗    ██╗
 ██╔════╝██╔═══██╗████╗  ██║██╔════╝██║     ██╔══██╗██║    ██║
 ██║     ██║   ██║██╔██╗ ██║██║     ██║     ███████║██║ █╗ ██║
 ██║     ██║   ██║██║╚██╗██║██║     ██║     ██╔══██║██║███╗██║
 ╚██████╗╚██████╔╝██║ ╚████║╚██████╗███████╗██║  ██║╚███╔███╔╝
  ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝

 Model: gpt-4o | Session: abc-123 | Time: 14:32:05 | Elapsed: 00:00:00
 Account: anonymous

 No API key found. Run `conclaw auth register` for a free account with
 managed API access, or set OPENAI_API_KEY for bring-your-own-key mode.
```

### 7.2 Typical Word Editing Session

```
> Add a title "Q4 Report" with Heading 1 style, then add a 3-column table
  with headers: Metric, Q3, Q4 to report.docx

 [Planning] Inspecting report.docx...
 [Context] report.docx: 5 paragraphs, 0 tables, 2 images
 [Generating] Python script using python-docx
 [Code]
    from docx import Document
    doc = Document('report.docx')
    doc.add_heading('Q4 Report', level=1)
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    for i, header in enumerate(['Metric', 'Q3', 'Q4']):
        table.rows[0].cells[i].text = header
    doc.save('report.docx')
 [Review] PASS -- modifies report.docx (backup will be created)
 [Confirm] Modify report.docx? [Y/n] y
 [Executing] 001_add_title_table.py
 [Success] Title and table added to report.docx
            Backup saved to ~/.conclaw/sessions/abc-123/backups/report.docx.bak

 1,847 tokens | $0.003 | 4.1s
```

### 7.3 Typical Excel Session

```
> Read sales.xlsx and create a bar chart of revenue by month on a new sheet
  called "Charts"

 [Planning] Inspecting sales.xlsx...
 [Context] sales.xlsx: 3 sheets [Sales, Costs, Summary], Sales has 120 rows x 5 cols
           Columns: Month, Product, Units, Revenue, Region
 [Generating] Python script using openpyxl
 [Code]
    import openpyxl
    from openpyxl.chart import BarChart, Reference
    wb = openpyxl.load_workbook('sales.xlsx')
    ws = wb['Sales']
    # ... (aggregation and chart code)
    wb.save('sales.xlsx')
 [Review] PASS
 [Confirm] Modify sales.xlsx? [Y/n] y
 [Executing] 001_create_chart.py
 [Success] Bar chart created on new "Charts" sheet in sales.xlsx

 2,103 tokens | $0.004 | 5.7s
```

---

## 8. Non-Functional Requirements

### 8.1 Performance

- LLM response streaming must begin within 2 seconds of sending the request.
- Code execution must complete within the configured timeout (default 60s).
- TUI must remain responsive during LLM streaming and code execution (async).
- Session load/resume must complete in under 1 second.

### 8.2 Security

- API keys are never logged or displayed in the TUI.
- Generated code is reviewed for dangerous operations before execution.
- File modifications require explicit user confirmation (configurable).
- Automatic backups before any destructive operation.
- Sandboxed execution prevents unintended system access.

### 8.3 Reliability

- Graceful handling of LLM API failures (retry with exponential backoff, max 3 retries).
- If code execution fails, the agent should analyze the error and retry with a fix (max 3 iterations).
- Session state is persisted after every interaction so no work is lost on crash.
- Backup restoration via `/undo` must always work.

### 8.4 Compatibility

- **OS**: Windows 10+, macOS 12+, Linux (Ubuntu 20.04+).
- **Python**: 3.11+.
- **File formats**: `.docx`, `.xlsx`, `.xls` (read-only via openpyxl), `.csv`.
- **VBA/COM**: Windows only (via `win32com`). Graceful fallback message on other OS.

### 8.5 Accessibility

- TUI must work in standard terminal emulators (Windows Terminal, iTerm2, GNOME Terminal).
- No hard dependency on mouse -- fully keyboard navigable.
- Color themes must have sufficient contrast (WCAG AA).

---

## 9. Milestones and Phases

### Phase 1: Foundation (Weeks 1-3)

- [ ] Project scaffolding (`pyproject.toml`, src layout, CI).
- [ ] Config system (`config.toml` loading, env vars, defaults).
- [ ] LLM client integration via `litellm` (OpenAI + Anthropic).
- [ ] Basic agent loop (single-turn: query -> generate code -> execute -> respond).
- [ ] Sandboxed Python execution with timeout.
- [ ] Minimal CLI (plain `rich` console, no full TUI yet).

### Phase 2: Document Intelligence (Weeks 4-5)

- [ ] Word document inspector (`python-docx` based structure analysis).
- [ ] Excel file inspector (`openpyxl` based schema/data preview).
- [ ] File-aware context injection into LLM prompts.
- [ ] Automatic backup system.
- [ ] Code safety reviewer.

### Phase 3: Full TUI (Weeks 6-7)

- [ ] Rich terminal UI with `textual` or `rich` + `prompt_toolkit`.
- [ ] Header with model name, session timer, clock.
- [ ] Streaming output with syntax highlighting.
- [ ] Slash command system.
- [ ] Input history and multi-line editing.

### Phase 4: Session and Logging (Week 8)

- [ ] Session persistence (create, save, list, resume).
- [ ] Conversation history management with context windowing.
- [ ] Structured activity log (TUI + file).
- [ ] Multi-level logging (DEBUG through ERROR).
- [ ] Token counting and cost estimation.

### Phase 5: Developer Account System (Weeks 9-10)

- [ ] Local account creation, login/logout, JWT token management.
- [ ] Encrypted API key vault (`cryptography` Fernet).
- [ ] BYOK key storage and retrieval.
- [ ] Conclaw proxy integration (route LLM calls through backend for managed-key users).
- [ ] Usage tracking and `/usage` dashboard.
- [ ] Session sync to cloud (opt-in, selective push/pull).
- [ ] `conclaw auth` CLI subcommands (register, login, logout, keys, usage).
- [ ] Account-related slash commands (`/account`, `/usage`, `/sync`, `/keys`).

### Phase 6: Advanced Features (Weeks 11-12)

- [ ] Multi-turn agentic loop (retry on failure, iterative refinement).
- [ ] VBA code generation and COM execution (Windows).
- [ ] Batch operations (process multiple files).
- [ ] Mail merge (Word template + Excel data source).
- [ ] `/undo` and `/diff` commands.
- [ ] Cross-file operations (copy data between workbooks).
- [ ] Team plan features (shared templates, centralized billing, audit logs).

### Phase 7: Polish and Release (Weeks 13-14)

- [ ] Comprehensive test suite (unit + integration with fixture files).
- [ ] Error handling hardening.
- [ ] Documentation (README, usage guide, examples).
- [ ] PyPI packaging and `pipx install conclaw` support.
- [ ] Performance profiling and optimization.
- [ ] Beta release.

---

## 10. Success Metrics

| Metric | Target |
|---|---|
| **Task Success Rate** | >85% of single-turn document tasks completed without manual intervention. |
| **Code Execution Safety** | 0 incidents of unintended file deletion or data loss in production use. |
| **Time to First Result** | <10 seconds from user query to visible result for typical operations. |
| **Session Reliability** | 0 data loss from crashes (sessions always recoverable). |
| **User Satisfaction** | Positive feedback from >80% of beta testers. |

---

## 11. Open Questions and Future Scope

| Item | Status |
|---|---|
| PowerPoint (`.pptx`) support via `python-pptx` | Future scope (Phase 7+) |
| Google Docs/Sheets integration | Future scope -- requires OAuth |
| Plugin system for custom document processors | Under consideration |
| Web UI option (browser-based frontend) | Under consideration |
| Multi-agent collaboration (e.g., one agent reads, another writes) | Future scope |
| Voice input (speech-to-text for queries) | Future scope |
| PDF generation and editing | Future scope |

---

## 12. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LLM generates incorrect code that corrupts files | High | Automatic backups, code review step, user confirmation before writes. |
| API rate limiting or downtime | Medium | Retry logic, support for multiple providers, local model fallback (Ollama). |
| Complex formatting lost during programmatic editing | Medium | Inspect-before-edit step, warn user about formatting limitations. |
| VBA/COM only works on Windows | Low | Clear platform detection and messaging; Python-based alternatives for cross-platform. |
| Large files causing slow execution or memory issues | Medium | File size checks, streaming reads for large Excel files, warn user. |
| Account credential theft or vault compromise | High | Device-bound encryption key, Fernet symmetric encryption, no plaintext keys on disk, token expiry and rotation. |
| Cloud backend downtime blocking local usage | Medium | Local-first architecture -- all core features work offline. Cloud features degrade gracefully with cached profile data. |

from __future__ import annotations
import os
from pathlib import Path
from typing import TYPE_CHECKING

from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from conclaw.cli.app import AppContext

from conclaw.commands.registry import CommandRegistry


def register_builtins(registry: CommandRegistry) -> None:
    registry.register("help", "Show all available commands", cmd_help)
    registry.register("exit", "End the session", cmd_exit)
    registry.register("quit", "End the session", cmd_exit)
    registry.register("clear", "Clear the screen", cmd_clear)
    registry.register("files", "List files in the working directory", cmd_files)
    registry.register("model", "Show or switch the active LLM model", cmd_model)
    registry.register("history", "Show conversation history", cmd_history)
    registry.register("sessions", "List recent sessions", cmd_sessions)
    registry.register("config", "Show current configuration", cmd_config)
    registry.register("cost", "Show token usage and cost", cmd_cost)
    registry.register("db", "Database ops: /db connect | /db up | /db init", cmd_db)
    registry.register("memory", "Memory ops: /memory set|get|list|delete", cmd_memory)
    registry.register("decisions", "Show recent decision log entries", cmd_decisions)


def cmd_help(ctx: AppContext, args: list[str]) -> None:
    table = Table(title="Slash Commands", border_style="dim", title_style="bold cyan")
    table.add_column("Command", style="slash.command", no_wrap=True)
    table.add_column("Description", style="slash.description")
    for name, cmd in ctx.registry.all().items():
        if name == "quit":
            continue
        table.add_row(f"/{cmd.name}", cmd.description)
    ctx.console.print(table)
    ctx.console.print()


def cmd_exit(ctx: AppContext, args: list[str]) -> None:
    ctx.session.close()
    ctx.console.print(" Session closed. Goodbye!", style="info")
    ctx.running = False


def cmd_clear(ctx: AppContext, args: list[str]) -> None:
    ctx.console.clear()
    from conclaw.cli.components.header import print_banner, print_status_bar
    print_banner(ctx.console)
    print_status_bar(
        ctx.console,
        model=ctx.config["llm"]["model"],
        session_id=ctx.session.id,
        started_at=ctx.session.started_at,
        cwd=str(Path.cwd()),
    )


def cmd_files(ctx: AppContext, args: list[str]) -> None:
    target = Path(args[0]) if args else Path.cwd()
    if not target.exists():
        ctx.console.print(f" [error]Path not found: {target}[/error]")
        return
    entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    table = Table(border_style="dim", show_header=True)
    table.add_column("Name", style="white")
    table.add_column("Type", style="dim")
    table.add_column("Size", style="dim", justify="right")
    for entry in entries:
        if entry.name.startswith("."):
            continue
        kind = "DIR" if entry.is_dir() else entry.suffix or "FILE"
        size = ""
        if entry.is_file():
            size_bytes = entry.stat().st_size
            if size_bytes < 1024:
                size = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size = f"{size_bytes / 1024:.1f} KB"
            else:
                size = f"{size_bytes / (1024 * 1024):.1f} MB"
        table.add_row(entry.name, kind, size)
    ctx.console.print(table)
    ctx.console.print()


def cmd_model(ctx: AppContext, args: list[str]) -> None:
    if args:
        old = ctx.config["llm"]["model"]
        ctx.config["llm"]["model"] = args[0]
        ctx.console.print(f" Model switched: {old} -> {args[0]}", style="success")
    else:
        ctx.console.print(
            f" Current model: [info.value]{ctx.config['llm']['model']}[/info.value]"
        )
    ctx.console.print()


def cmd_history(ctx: AppContext, args: list[str]) -> None:
    entries = ctx.session.conversation.read_all()
    if not entries:
        ctx.console.print(" No conversation history yet.", style="info")
        ctx.console.print()
        return
    for entry in entries:
        ts = entry.get("timestamp", "")
        if ts:
            ts = ts[11:19]
        role = entry["role"]
        content = entry.get("content", "")
        preview = content[:120] + ("..." if len(content) > 120 else "")
        role_style = "bold green" if role == "user" else "bold cyan"
        line = Text()
        line.append(f"[{ts}] ", style="timestamp")
        line.append(f"{role}: ", style=role_style)
        line.append(preview, style="info")
        ctx.console.print(line)
    ctx.console.print()


def cmd_sessions(ctx: AppContext, args: list[str]) -> None:
    from conclaw.session.manager import Session
    limit = int(args[0]) if args else 10
    sessions = Session.list_recent(limit)
    if not sessions:
        ctx.console.print(" No sessions found.", style="info")
        ctx.console.print()
        return
    table = Table(title="Recent Sessions", border_style="dim", title_style="bold cyan")
    table.add_column("ID", style="info.value", no_wrap=True)
    table.add_column("Started", style="dim")
    table.add_column("Directory", style="dim")
    table.add_column("Status", style="dim")
    for s in reversed(sessions):
        started = s.get("started_at", "")[:19].replace("T", " ")
        table.add_row(s["id"], started, s.get("cwd", ""), s.get("status", ""))
    ctx.console.print(table)
    ctx.console.print()


def cmd_config(ctx: AppContext, args: list[str]) -> None:
    from rich.tree import Tree
    tree = Tree("[bold]Configuration[/bold]")
    for section, values in ctx.config.items():
        branch = tree.add(f"[bold cyan]{section}[/bold cyan]")
        if isinstance(values, dict):
            for k, v in values.items():
                display_v = v
                if "key" in k.lower() and isinstance(v, str) and len(v) > 4:
                    display_v = v[:4] + "****"
                branch.add(f"{k} = [info.value]{display_v}[/info.value]")
        else:
            branch.add(f"[info.value]{values}[/info.value]")
    ctx.console.print(tree)
    ctx.console.print()


def cmd_cost(ctx: AppContext, args: list[str]) -> None:
    s = ctx.session
    total = s.tokens_in + s.tokens_out
    ctx.console.print(f" Tokens in:     [info.value]{s.tokens_in:,}[/info.value]")
    ctx.console.print(f" Tokens out:    [info.value]{s.tokens_out:,}[/info.value]")
    ctx.console.print(f" Total tokens:  [info.value]{total:,}[/info.value]")
    ctx.console.print(f" Tool calls:    [info.value]{s.tool_calls}[/info.value]")
    ctx.console.print()


# ---------------------------------------------------------------------------
# Backend: PostgreSQL memory, decision log, and database management
# ---------------------------------------------------------------------------

def _backend_dsn(ctx: AppContext) -> str:
    return ctx.config.get("backend", {}).get(
        "dsn", "postgresql://conclaw:conclaw@localhost:5433/conclaw"
    )


def cmd_db(ctx: AppContext, args: list[str]) -> None:
    if not args:
        ctx.console.print(
            " Usage: /db connect  -- auto-discover localhost PostgreSQL\n"
            "        /db up       -- start Docker PostgreSQL container\n"
            "        /db init     -- create schema on current DSN",
            style="warning",
        )
        return

    sub = args[0]

    if sub == "connect":
        try:
            from conclaw.backend.db import discover_and_connect
            dsn = discover_and_connect()
            ctx.config.setdefault("backend", {})["dsn"] = dsn
            ctx.console.print(
                f" Connected to localhost PostgreSQL. DSN: [info.value]{dsn}[/info.value]",
                style="success",
            )
        except Exception as e:
            ctx.console.print(f" [error]Auto-connect failed: {e}[/error]")
    elif sub == "up":
        try:
            from conclaw.backend.db import docker_up
            docker_up()
            ctx.console.print(" PostgreSQL container started on port 5433.", style="success")
        except Exception as e:
            ctx.console.print(f" [error]Docker up failed: {e}[/error]")
    elif sub == "init":
        dsn = _backend_dsn(ctx)
        try:
            from conclaw.backend.db import init_db
            init_db(dsn)
            ctx.console.print(" Database schema initialized.", style="success")
        except Exception as e:
            ctx.console.print(f" [error]DB init failed: {e}[/error]")
    else:
        ctx.console.print(f" Unknown sub-command: {sub}. Use /db connect, /db up, or /db init.", style="warning")
    ctx.console.print()


def cmd_memory(ctx: AppContext, args: list[str]) -> None:
    if not args:
        ctx.console.print(
            " Usage: /memory set <scope> <key> <value>\n"
            "        /memory get <scope> <key>\n"
            "        /memory list [scope] [limit]\n"
            "        /memory delete <scope> <key>",
            style="warning",
        )
        return

    dsn = _backend_dsn(ctx)
    sub = args[0]

    if sub == "set" and len(args) >= 4:
        from conclaw.backend.memory import upsert
        scope, key, value = args[1], args[2], " ".join(args[3:])
        try:
            upsert(dsn, scope, key, value)
            ctx.console.print(f" Memory updated: [{scope}] {key}", style="success")
        except Exception as e:
            ctx.console.print(f" [error]Memory set failed: {e}[/error]")

    elif sub == "get" and len(args) >= 3:
        from conclaw.backend.memory import get
        scope, key = args[1], args[2]
        try:
            value = get(dsn, scope, key)
            if value is not None:
                ctx.console.print(f" [{scope}] {key} = [info.value]{value}[/info.value]")
            else:
                ctx.console.print(f" [{scope}] {key}: (not found)", style="warning")
        except Exception as e:
            ctx.console.print(f" [error]Memory get failed: {e}[/error]")

    elif sub == "list":
        from conclaw.backend.memory import list_entries
        scope = args[1] if len(args) > 1 else "global"
        limit = int(args[2]) if len(args) > 2 else 20
        try:
            rows = list_entries(dsn, scope, limit)
            if not rows:
                ctx.console.print(f" No entries in scope '{scope}'.", style="info")
            else:
                table = Table(title=f"Memory [{scope}]", border_style="dim", title_style="bold cyan")
                table.add_column("Key", style="info.value")
                table.add_column("Value", style="info")
                for k, v in rows:
                    table.add_row(k, v[:80])
                ctx.console.print(table)
        except Exception as e:
            ctx.console.print(f" [error]Memory list failed: {e}[/error]")

    elif sub == "delete" and len(args) >= 3:
        from conclaw.backend.memory import delete
        scope, key = args[1], args[2]
        try:
            deleted = delete(dsn, scope, key)
            if deleted:
                ctx.console.print(f" Deleted: [{scope}] {key}", style="success")
            else:
                ctx.console.print(f" Not found: [{scope}] {key}", style="warning")
        except Exception as e:
            ctx.console.print(f" [error]Memory delete failed: {e}[/error]")
    else:
        ctx.console.print(" Invalid usage. Type /memory for help.", style="warning")
    ctx.console.print()


def cmd_decisions(ctx: AppContext, args: list[str]) -> None:
    from conclaw.backend.decision import recent_decisions
    dsn = _backend_dsn(ctx)
    limit = int(args[0]) if args else 10
    try:
        rows = recent_decisions(dsn, limit)
        if not rows:
            ctx.console.print(" No decisions logged yet.", style="info")
        else:
            table = Table(title="Recent Decisions", border_style="dim", title_style="bold cyan")
            table.add_column("ID", style="dim")
            table.add_column("Task", style="info.value")
            table.add_column("Decision", style="info")
            table.add_column("Model", style="dim")
            table.add_column("Time", style="dim")
            for r in rows:
                table.add_row(str(r["id"]), r["task"][:50], r["decision"], r["model"], r["created_at"][:19])
            ctx.console.print(table)
    except Exception as e:
        ctx.console.print(f" [error]Decision log query failed: {e}[/error]")
    ctx.console.print()

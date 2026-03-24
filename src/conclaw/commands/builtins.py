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
    registry.register("memory", "Browse loaded instructions, auto-memory, and toggle settings", cmd_memory)
    registry.register("init", "Generate a starter CONCLAW.md for this project", cmd_init)


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
# Memory: flat-file markdown storage (Claude Code style)
# ---------------------------------------------------------------------------

def cmd_memory(ctx: AppContext, args: list[str]) -> None:
    from conclaw.storage.context_loader import list_loaded_files
    from conclaw.storage.paths import auto_memory_dir

    ctx.console.print(" [bold cyan]Loaded instruction files[/bold cyan]")
    files = list_loaded_files()
    if not files:
        ctx.console.print("  (none)", style="dim")
    else:
        table = Table(border_style="dim", show_header=True)
        table.add_column("Type", style="dim")
        table.add_column("Scope", style="dim")
        table.add_column("Path", style="info")
        for f in files:
            table.add_row(f["type"], f["scope"], f["path"])
        ctx.console.print(table)

    ctx.console.print()
    auto_enabled = ctx.config.get("memory", {}).get("auto_memory_enabled", True)
    status = "[info.value]ON[/info.value]" if auto_enabled else "[warning]OFF[/warning]"
    ctx.console.print(f" Auto-memory: {status}")
    ctx.console.print(f" Memory dir:  [info]{auto_memory_dir()}[/info]")
    ctx.console.print()
    ctx.console.print(
        " Tip: edit any file above directly, or ask Conclaw to remember something.",
        style="dim",
    )
    ctx.console.print()


def cmd_init(ctx: AppContext, args: list[str]) -> None:
    target = Path.cwd() / "CONCLAW.md"
    if target.exists():
        ctx.console.print(
            f" CONCLAW.md already exists at {target}. Edit it directly or delete to regenerate.",
            style="warning",
        )
        ctx.console.print()
        return
    template = (
        "# Project Instructions\n\n"
        "<!-- Conclaw reads this file at the start of every session. -->\n"
        "<!-- Write project-specific rules, conventions, and context here. -->\n\n"
        "## Build & Test\n\n"
        "- (add your build commands here)\n\n"
        "## Coding Standards\n\n"
        "- (add your coding conventions here)\n\n"
        "## Architecture Notes\n\n"
        "- (describe your project structure here)\n"
    )
    target.write_text(template, encoding="utf-8")
    ctx.console.print(f" Created {target}", style="success")
    ctx.console.print(" Edit this file to give Conclaw persistent project context.", style="info")
    ctx.console.print()

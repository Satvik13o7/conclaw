from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text

from conclaw.cli.components.header import print_banner, print_status_bar, _supports_unicode
from conclaw.cli.components.output_area import (
    print_assistant_message,
    print_error,
    print_user_message,
)
from conclaw.cli.themes.dark import DARK_THEME
from conclaw.cli.themes.light import LIGHT_THEME
from conclaw.commands.builtins import register_builtins
from conclaw.commands.registry import CommandRegistry
from conclaw.config.loader import load_config
from conclaw.llm.client import LLMClient
from conclaw.session.manager import Session
from conclaw.storage.paths import global_dir


@dataclass
class AppContext:
    console: Console
    config: dict
    session: Session
    registry: CommandRegistry
    llm: LLMClient | None = None
    running: bool = True


def _ensure_utf8() -> None:
    if sys.platform == "win32":
        os.system("")
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _get_prompt_session() -> PromptSession:
    history_file = global_dir() / "input_history"
    return PromptSession(history=FileHistory(str(history_file)))


def _build_console(config: dict) -> Console:
    theme_name = config.get("ui", {}).get("theme", "dark")
    theme = DARK_THEME if theme_name == "dark" else LIGHT_THEME
    return Console(theme=theme, force_terminal=True)


def _init_llm(config: dict, console: Console) -> LLMClient | None:
    try:
        client = LLMClient(config["llm"])
        client._get_api_key()
        return client
    except RuntimeError as e:
        console.print(f" [warning]![/warning] {e}")
        console.print(
            " Chat will echo messages until an API key is configured.\n",
            style="info",
        )
        return None


def _stream_response(ctx: AppContext, user_input: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    header = Text()
    header.append(f"[{ts}] ", style="timestamp")
    header.append("Conclaw", style="bold cyan")
    ctx.console.print(header)

    collected: list[str] = []

    try:
        with Live("", console=ctx.console, refresh_per_second=12, vertical_overflow="visible") as live:
            def on_chunk(text: str) -> None:
                collected.append(text)
                live.update(Markdown("".join(collected)))

            result = ctx.llm.chat_stream(user_input, on_chunk=on_chunk)
    except Exception as e:
        print_error(ctx.console, f"LLM error: {e}")
        return

    ctx.session.conversation.append(
        "assistant", result.content,
        tokens_in=result.tokens_in, tokens_out=result.tokens_out,
    )
    ctx.session.tokens_in += result.tokens_in
    ctx.session.tokens_out += result.tokens_out

    if ctx.config["ui"].get("show_tokens"):
        ctx.console.print(
            f" [token.count]{result.tokens_in + result.tokens_out:,} tokens "
            f"({result.tokens_in:,} in / {result.tokens_out:,} out)[/token.count]"
        )
    ctx.console.print()


def _non_stream_response(ctx: AppContext, user_input: str) -> None:
    try:
        content, tokens_in, tokens_out = ctx.llm.chat(user_input)
    except Exception as e:
        print_error(ctx.console, f"LLM error: {e}")
        return

    print_assistant_message(ctx.console, content)
    ctx.session.conversation.append("assistant", content,
                                     tokens_in=tokens_in, tokens_out=tokens_out)
    ctx.session.tokens_in += tokens_in
    ctx.session.tokens_out += tokens_out

    if ctx.config["ui"].get("show_tokens"):
        ctx.console.print(
            f" [token.count]{tokens_in + tokens_out:,} tokens "
            f"({tokens_in:,} in / {tokens_out:,} out)[/token.count]"
        )
        ctx.console.print()


def main() -> None:
    _ensure_utf8()
    config = load_config()
    console = _build_console(config)
    session = Session()
    registry = CommandRegistry()
    register_builtins(registry)
    llm = _init_llm(config, console)

    # Load CONCLAW.md + rules + auto-memory into LLM context
    from conclaw.storage.context_loader import load_all_instructions
    from conclaw.storage.auto_memory import ensure_entrypoint, is_enabled as mem_enabled
    instructions = load_all_instructions()
    if instructions and llm is not None:
        llm.inject_context(instructions)
    if mem_enabled(config):
        ensure_entrypoint()

    ctx = AppContext(
        console=console,
        config=config,
        session=session,
        registry=registry,
        llm=llm,
    )

    print_banner(console)
    print_status_bar(
        console,
        model=config["llm"]["model"],
        session_id=session.id,
        started_at=session.started_at,
        cwd=str(Path.cwd()),
    )

    prompt_session = _get_prompt_session()
    prompt_char = "> " if not _supports_unicode() else "\u276f "

    while ctx.running:
        try:
            user_input = prompt_session.prompt(
                HTML(f"<ansigreen><b>{prompt_char}</b></ansigreen>")
            )
        except (EOFError, KeyboardInterrupt):
            console.print()
            session.close()
            console.print(" Session closed. Goodbye!", style="info")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.startswith("/"):
            handled = registry.execute(ctx, user_input)
            if not handled:
                console.print(
                    f" Unknown command: {user_input.split()[0]}. "
                    "Type /help for available commands.",
                    style="warning",
                )
            continue

        session.conversation.append("user", user_input)
        print_user_message(console, user_input)

        if ctx.llm is None:
            print_assistant_message(
                console,
                "No API key configured. Set `AZURE_OPENAI_KEY` in your "
                "environment or `.env` file, then restart conclaw.",
            )
            continue

        if config["ui"].get("stream", True):
            _stream_response(ctx, user_input)
        else:
            _non_stream_response(ctx, user_input)


if __name__ == "__main__":
    main()

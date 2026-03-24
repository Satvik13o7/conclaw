import sys
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.markdown import Markdown


def _icon(unicode_char: str, fallback: str) -> str:
    try:
        encoding = sys.stdout.encoding or ""
        if encoding.lower().replace("-", "") in ("utf8", "utf16", "utf32"):
            return unicode_char
    except Exception:
        pass
    return fallback


def print_user_message(console: Console, message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    header = Text()
    header.append(f"[{ts}] ", style="timestamp")
    header.append("You", style="bold green")
    console.print(header)
    console.print(f" {message}", style="user.message")
    console.print()


def print_assistant_message(console: Console, message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    header = Text()
    header.append(f"[{ts}] ", style="timestamp")
    header.append("Conclaw", style="bold cyan")
    console.print(header)
    console.print(Markdown(message), style="assistant.message")
    console.print()


def print_thinking(console: Console, message: str) -> None:
    console.print(f" {message}", style="assistant.thinking")


def print_code_block(console: Console, code: str, language: str = "python") -> None:
    syntax = Syntax(code, language, theme="monokai", line_numbers=True, padding=1)
    console.print(Panel(syntax, title=f"[bold]{language}[/bold]", border_style="dim"))
    console.print()


def print_success(console: Console, message: str) -> None:
    icon = _icon("\u2713", "+")
    console.print(f" [success]{icon}[/success] {message}")
    console.print()


def print_error(console: Console, message: str) -> None:
    icon = _icon("\u2717", "X")
    console.print(f" [error]{icon}[/error] {message}")
    console.print()


def print_warning(console: Console, message: str) -> None:
    console.print(f" [warning]![/warning] {message}")
    console.print()


def print_divider(console: Console) -> None:
    console.rule(style="divider")

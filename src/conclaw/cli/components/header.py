import sys
from datetime import datetime, timedelta
from rich.console import Console
from rich.text import Text


BANNER_UNICODE = r"""
  ██████╗ ██████╗ ███╗   ██╗ ██████╗██╗      █████╗ ██╗    ██╗
 ██╔════╝██╔═══██╗████╗  ██║██╔════╝██║     ██╔══██╗██║    ██║
 ██║     ██║   ██║██╔██╗ ██║██║     ██║     ███████║██║ █╗ ██║
 ██║     ██║   ██║██║╚██╗██║██║     ██║     ██╔══██║██║███╗██║
 ╚██████╗╚██████╔╝██║ ╚████║╚██████╗███████╗██║  ██║╚███╔███╔╝
  ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
"""

BANNER_ASCII = r"""
   ____  ___  _   _  ____  _        _  __        __
  / ___|/ _ \| \ | |/ ___|| |      / \\ \      / /
 | |   | | | |  \| | |    | |     / _ \\ \ /\ / /
 | |___| |_| | |\  | |___ | |___ / ___ \\ V  V /
  \____|\___/|_| \_|\____||_____/_/   \_\\_/\_/
"""


def _supports_unicode() -> bool:
    try:
        encoding = sys.stdout.encoding or ""
        return encoding.lower().replace("-", "") in ("utf8", "utf16", "utf32")
    except Exception:
        return False


def print_banner(console: Console) -> None:
    banner = BANNER_UNICODE if _supports_unicode() else BANNER_ASCII
    console.print(banner, style="banner", highlight=False)


def print_status_bar(
    console: Console,
    *,
    model: str,
    session_id: str,
    started_at: datetime,
    cwd: str,
    account: str = "anonymous",
) -> None:
    now = datetime.now(started_at.tzinfo)
    elapsed = now - started_at
    elapsed_str = str(timedelta(seconds=int(elapsed.total_seconds())))
    time_str = now.strftime("%H:%M:%S")

    bar = Text()
    bar.append(" Model: ", style="info.label")
    bar.append(model, style="info.value")
    bar.append("  |  ", style="info.separator")
    bar.append("Session: ", style="info.label")
    bar.append(session_id, style="info.value")
    bar.append("  |  ", style="info.separator")
    bar.append("Time: ", style="info.label")
    bar.append(time_str, style="info.value")
    bar.append("  |  ", style="info.separator")
    bar.append("Elapsed: ", style="info.label")
    bar.append(elapsed_str, style="info.value")
    bar.append("  |  ", style="info.separator")
    bar.append("Account: ", style="info.label")
    bar.append(account, style="info.value")

    console.print(bar)

    cwd_line = Text()
    cwd_line.append(" cwd: ", style="info.label")
    cwd_line.append(cwd, style="info")
    console.print(cwd_line)
    console.print()

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from conclaw.cli.app import AppContext


@dataclass
class SlashCommand:
    name: str
    description: str
    handler: Callable[[AppContext, list[str]], None]


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, SlashCommand] = {}

    def register(self, name: str, description: str, handler: Callable) -> None:
        self._commands[name] = SlashCommand(
            name=name, description=description, handler=handler
        )

    def get(self, name: str) -> SlashCommand | None:
        return self._commands.get(name)

    def all(self) -> dict[str, SlashCommand]:
        return dict(self._commands)

    def execute(self, ctx: AppContext, raw_input: str) -> bool:
        parts = raw_input.strip().split(maxsplit=1)
        name = parts[0].lstrip("/")
        args = parts[1].split() if len(parts) > 1 else []
        cmd = self.get(name)
        if cmd is None:
            return False
        cmd.handler(ctx, args)
        return True

from __future__ import annotations

from pathlib import Path

from conclaw.safety import SafetyLayer


def read_file(path: str, safety: SafetyLayer) -> str:
    target = Path(path).expanduser().resolve()
    safety.ensure_allowed("read", target)
    return target.read_text(encoding="utf-8")


def write_file(path: str, content: str, safety: SafetyLayer) -> None:
    target = Path(path).expanduser().resolve()
    safety.ensure_allowed("write", target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

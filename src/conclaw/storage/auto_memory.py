"""Auto-memory: Conclaw writes notes for itself across sessions.

Mirrors Claude Code's auto memory:
- MEMORY.md is the entrypoint (kept concise, <200 lines)
- Topic files (debugging.md, patterns.md, etc.) for detailed notes
- All files are plain markdown, human-editable
"""
from __future__ import annotations

from pathlib import Path

from conclaw.storage.paths import auto_memory_dir, memory_entrypoint


def is_enabled(config: dict) -> bool:
    return config.get("memory", {}).get("auto_memory_enabled", True)


def ensure_entrypoint() -> Path:
    """Create MEMORY.md if it does not exist."""
    mem = memory_entrypoint()
    if not mem.exists():
        mem.write_text(
            "# Conclaw Auto-Memory\n\n"
            "This file is managed by Conclaw. It stores learnings across sessions.\n"
            "Edit or delete any entry freely.\n\n",
            encoding="utf-8",
        )
    return mem


def append_to_memory(note: str, topic: str | None = None) -> str:
    """Append a note to MEMORY.md or a topic file. Returns the file path written."""
    mem_dir = auto_memory_dir()
    if topic:
        target = mem_dir / f"{topic}.md"
        if not target.exists():
            target.write_text(f"# {topic}\n\n", encoding="utf-8")
    else:
        target = ensure_entrypoint()
    with open(target, "a", encoding="utf-8") as f:
        f.write(f"\n{note}\n")
    return str(target)


def read_memory() -> str:
    """Read MEMORY.md (first 200 lines) for injection into context."""
    mem = memory_entrypoint()
    if not mem.exists():
        return ""
    lines = mem.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[:200])


def list_topic_files() -> list[str]:
    """List all topic files in the auto-memory directory."""
    mem_dir = auto_memory_dir()
    return [f.name for f in sorted(mem_dir.glob("*.md")) if f.name != "MEMORY.md"]

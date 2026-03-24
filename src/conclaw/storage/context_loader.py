"""Load CONCLAW.md files and .conclaw/rules/ into session context.

Mirrors Claude Code's CLAUDE.md loading:
- Walk up from cwd to root, collecting CONCLAW.md files
- Load .conclaw/rules/*.md from project and user dirs
- Load auto-memory MEMORY.md (first 200 lines)
- Support @path imports (max depth 5)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from conclaw.storage.paths import (
    global_dir,
    project_context_file,
    project_rules_dir,
    user_rules_dir,
    memory_entrypoint,
)

_IMPORT_RE = re.compile(r"^@(.+)$", re.MULTILINE)
_MAX_IMPORT_DEPTH = 5
_MEMORY_LINE_LIMIT = 200


def _read_with_imports(path: Path, depth: int = 0) -> str:
    if depth > _MAX_IMPORT_DEPTH or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    def _replace(m: re.Match) -> str:
        import_path = m.group(1).strip()
        if import_path.startswith("~"):
            resolved = Path(import_path).expanduser()
        else:
            resolved = (path.parent / import_path).resolve()
        return _read_with_imports(resolved, depth + 1)
    return _IMPORT_RE.sub(_replace, text)


def _collect_conclaw_md_files() -> List[Path]:
    """Walk from cwd up to root collecting CONCLAW.md files."""
    files: list[Path] = []
    current = Path.cwd().resolve()
    while True:
        for candidate in [current / "CONCLAW.md", current / ".conclaw" / "CONCLAW.md"]:
            if candidate.is_file():
                files.append(candidate)
        parent = current.parent
        if parent == current:
            break
        current = parent
    # User-level
    user_md = global_dir() / "CONCLAW.md"
    if user_md.is_file():
        files.append(user_md)
    files.reverse()  # broader scope first
    return files


def _collect_rules(rules_dir: Path) -> List[Path]:
    if not rules_dir.is_dir():
        return []
    return sorted(rules_dir.rglob("*.md"))


def load_all_instructions() -> str:
    """Return the full instruction context to inject into the system prompt."""
    sections: list[str] = []

    # 1. CONCLAW.md files (ancestor walk)
    for md_file in _collect_conclaw_md_files():
        content = _read_with_imports(md_file)
        if content.strip():
            sections.append(f"# Instructions from {md_file}\n\n{content}")

    # 2. User-level rules
    for rule_file in _collect_rules(user_rules_dir()):
        content = _read_with_imports(rule_file)
        if content.strip():
            sections.append(f"# User rule: {rule_file.name}\n\n{content}")

    # 3. Project rules
    for rule_file in _collect_rules(project_rules_dir()):
        content = _read_with_imports(rule_file)
        if content.strip():
            sections.append(f"# Project rule: {rule_file.name}\n\n{content}")

    # 4. Auto-memory MEMORY.md (first 200 lines)
    mem_file = memory_entrypoint()
    if mem_file.is_file():
        lines = mem_file.read_text(encoding="utf-8", errors="replace").splitlines()
        truncated = "\n".join(lines[:_MEMORY_LINE_LIMIT])
        if truncated.strip():
            sections.append(f"# Auto-memory\n\n{truncated}")

    return "\n\n---\n\n".join(sections)


def list_loaded_files() -> List[dict]:
    """Return metadata about all loaded instruction files for /memory command."""
    result: list[dict] = []
    for md_file in _collect_conclaw_md_files():
        result.append({"type": "CONCLAW.md", "path": str(md_file), "scope": "project/ancestor"})
    for rule_file in _collect_rules(user_rules_dir()):
        result.append({"type": "rule", "path": str(rule_file), "scope": "user"})
    for rule_file in _collect_rules(project_rules_dir()):
        result.append({"type": "rule", "path": str(rule_file), "scope": "project"})
    mem_file = memory_entrypoint()
    if mem_file.is_file():
        result.append({"type": "auto-memory", "path": str(mem_file), "scope": "project"})
    for topic in sorted(mem_file.parent.glob("*.md")):
        if topic.name != "MEMORY.md":
            result.append({"type": "auto-memory-topic", "path": str(topic), "scope": "project"})
    return result

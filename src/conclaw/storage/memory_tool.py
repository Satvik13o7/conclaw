"""Client-side memory tool matching Claude's memory tool spec.

All operations are restricted to the auto-memory directory.
Commands: view, create, str_replace, insert, delete, rename.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Optional

from conclaw.storage.paths import auto_memory_dir


def _resolve_safe(path_str: str) -> Path:
    """Resolve a /memories/... path to the actual filesystem path, with traversal protection."""
    mem_dir = auto_memory_dir()
    clean = path_str.replace("\\", "/")
    if clean.startswith("/memories"):
        clean = clean[len("/memories"):]
    clean = clean.lstrip("/")
    if not clean:
        return mem_dir
    resolved = (mem_dir / clean).resolve()
    if not str(resolved).startswith(str(mem_dir.resolve())):
        raise PermissionError(f"Path traversal blocked: {path_str}")
    return resolved


def _human_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes}"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}K"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}M"


def _view_dir(target: Path) -> str:
    lines = []
    for root, dirs, files in os.walk(target):
        root_path = Path(root)
        depth = len(root_path.relative_to(target).parts)
        if depth > 2:
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]
        for name in sorted(dirs) + sorted(files):
            entry = root_path / name
            if name.startswith("."):
                continue
            size = _human_size(entry.stat().st_size) if entry.is_file() else "4.0K"
            rel = entry.relative_to(auto_memory_dir())
            lines.append(f"{size}\t/memories/{rel}")
    total_size = _human_size(sum(f.stat().st_size for f in target.rglob("*") if f.is_file()))
    header = f"Here're the files and directories up to 2 levels deep in /memories, excluding hidden items and node_modules:\n{total_size}\t/memories"
    return header + ("\n" + "\n".join(lines) if lines else "")


def _view_file(target: Path, view_range: Optional[list[int]] = None) -> str:
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) > 999_999:
        return f"File /memories/{target.relative_to(auto_memory_dir())} exceeds maximum line limit of 999,999 lines."
    if view_range:
        start, end = view_range[0], view_range[1]
        lines = lines[start - 1:end]
        offset = start
    else:
        offset = 1
    numbered = "\n".join(f"{i + offset:6d}\t{line}" for i, line in enumerate(lines))
    rel = target.relative_to(auto_memory_dir())
    return f"Here's the content of /memories/{rel} with line numbers:\n{numbered}"


def execute(command: str, **kwargs: Any) -> str:
    try:
        if command == "view":
            target = _resolve_safe(kwargs["path"])
            if not target.exists():
                return f"The path {kwargs['path']} does not exist. Please provide a valid path."
            if target.is_dir():
                return _view_dir(target)
            return _view_file(target, kwargs.get("view_range"))

        elif command == "create":
            target = _resolve_safe(kwargs["path"])
            if target.exists():
                return f"Error: File {kwargs['path']} already exists"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(kwargs["file_text"], encoding="utf-8")
            return f"File created successfully at: {kwargs['path']}"

        elif command == "str_replace":
            target = _resolve_safe(kwargs["path"])
            if not target.is_file():
                return f"Error: The path {kwargs['path']} does not exist. Please provide a valid path."
            text = target.read_text(encoding="utf-8", errors="replace")
            old_str = kwargs["old_str"]
            new_str = kwargs["new_str"]
            occurrences = text.count(old_str)
            if occurrences == 0:
                return f"No replacement was performed, old_str `{old_str}` did not appear verbatim in {kwargs['path']}."
            if occurrences > 1:
                lines = text.splitlines()
                line_nums = [i + 1 for i, line in enumerate(lines) if old_str in line]
                return f"No replacement was performed. Multiple occurrences of old_str `{old_str}` in lines: {line_nums}. Please ensure it is unique"
            text = text.replace(old_str, new_str, 1)
            target.write_text(text, encoding="utf-8")
            return "The memory file has been edited."

        elif command == "insert":
            target = _resolve_safe(kwargs["path"])
            if not target.is_file():
                return f"Error: The path {kwargs['path']} does not exist"
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
            insert_line = kwargs["insert_line"]
            if insert_line < 0 or insert_line > len(lines):
                return f"Error: Invalid `insert_line` parameter: {insert_line}. It should be within the range of lines of the file: [0, {len(lines)}]"
            new_lines = kwargs["insert_text"].splitlines()
            lines[insert_line:insert_line] = new_lines
            target.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return f"The file {kwargs['path']} has been edited."

        elif command == "delete":
            target = _resolve_safe(kwargs["path"])
            if not target.exists():
                return f"Error: The path {kwargs['path']} does not exist"
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            return f"Successfully deleted {kwargs['path']}"

        elif command == "rename":
            old_target = _resolve_safe(kwargs["old_path"])
            new_target = _resolve_safe(kwargs["new_path"])
            if not old_target.exists():
                return f"Error: The path {kwargs['old_path']} does not exist"
            if new_target.exists():
                return f"Error: The destination {kwargs['new_path']} already exists"
            new_target.parent.mkdir(parents=True, exist_ok=True)
            old_target.rename(new_target)
            return f"Successfully renamed {kwargs['old_path']} to {kwargs['new_path']}"

        else:
            return f"Unknown command: {command}"

    except PermissionError as e:
        return str(e)
    except Exception as e:
        return f"Error: {e}"


# OpenAI function-calling tool definition for the orchestrator agent
MEMORY_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "memory",
        "description": (
            "Store and retrieve information across conversations. "
            "All operations are scoped to the /memories directory. "
            "Commands: view, create, str_replace, insert, delete, rename."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "enum": ["view", "create", "str_replace", "insert", "delete", "rename"],
                },
                "path": {"type": "string", "description": "Path within /memories/"},
                "file_text": {"type": "string", "description": "Content for create command"},
                "old_str": {"type": "string", "description": "Text to find for str_replace"},
                "new_str": {"type": "string", "description": "Replacement text for str_replace"},
                "insert_line": {"type": "integer", "description": "Line number for insert (0-indexed)"},
                "insert_text": {"type": "string", "description": "Text to insert"},
                "old_path": {"type": "string", "description": "Source path for rename"},
                "new_path": {"type": "string", "description": "Destination path for rename"},
                "view_range": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Optional [start, end] line range for view",
                },
            },
            "required": ["command"],
        },
    },
}

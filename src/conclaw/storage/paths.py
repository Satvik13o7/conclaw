from pathlib import Path
import hashlib


def global_dir() -> Path:
    path = Path.home() / ".conclaw"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sessions_dir() -> Path:
    path = global_dir() / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def session_dir(session_id: str) -> Path:
    path = sessions_dir() / session_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_dir() -> Path:
    return Path.cwd() / ".conclaw"


def project_context_file() -> Path:
    return project_dir() / "CONCLAW.md"


def project_rules_dir() -> Path:
    return project_dir() / "rules"


def user_rules_dir() -> Path:
    path = global_dir() / "rules"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _project_key() -> str:
    """Derive a stable key from the git root or cwd."""
    cwd = Path.cwd().resolve()
    git_dir = cwd
    while git_dir != git_dir.parent:
        if (git_dir / ".git").exists():
            break
        git_dir = git_dir.parent
    else:
        git_dir = cwd
    return hashlib.sha1(str(git_dir).encode()).hexdigest()[:12]


def auto_memory_dir() -> Path:
    """Per-project auto-memory directory: ~/.conclaw/projects/<key>/memory/"""
    path = global_dir() / "projects" / _project_key() / "memory"
    path.mkdir(parents=True, exist_ok=True)
    return path


def memory_entrypoint() -> Path:
    """MEMORY.md inside the auto-memory directory."""
    return auto_memory_dir() / "MEMORY.md"

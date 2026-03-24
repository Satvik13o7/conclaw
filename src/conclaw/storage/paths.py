from pathlib import Path


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

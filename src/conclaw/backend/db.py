from __future__ import annotations

import subprocess
from contextlib import contextmanager
from pathlib import Path

try:
    import psycopg
except ImportError:
    psycopg = None


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS memory_entries (
    id BIGSERIAL PRIMARY KEY,
    scope TEXT NOT NULL,
    memory_key TEXT NOT NULL,
    memory_value TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(scope, memory_key)
);

CREATE TABLE IF NOT EXISTS decision_log (
    id BIGSERIAL PRIMARY KEY,
    task TEXT NOT NULL,
    decision TEXT NOT NULL,
    model_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def _require_psycopg() -> None:
    if psycopg is None:
        raise RuntimeError("psycopg is required. Install with: pip install 'psycopg[binary]'")


@contextmanager
def get_connection(dsn: str):
    _require_psycopg()
    with psycopg.connect(dsn) as conn:
        yield conn


def init_db(dsn: str) -> None:
    with get_connection(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            conn.commit()


def docker_up(compose_path: Path | None = None) -> None:
    if compose_path is None:
        compose_path = Path(__file__).resolve().parents[3] / "docker-compose.yml"
    subprocess.run(
        ["docker", "compose", "-f", str(compose_path), "up", "-d"],
        check=True,
    )

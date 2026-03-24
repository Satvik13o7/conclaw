from __future__ import annotations

import logging
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

try:
    import psycopg
except ImportError:
    psycopg = None

logger = logging.getLogger(__name__)

DB_NAME = "conclaw"

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

CANDIDATE_DSNS = [
    "postgresql://postgres:postgres@localhost:5432/conclaw",
    "postgresql://postgres@localhost:5432/conclaw",
    "postgresql://conclaw:conclaw@localhost:5433/conclaw",
    "postgresql://conclaw:conclaw@localhost:5432/conclaw",
]

ADMIN_DSNS = [
    ("postgresql://postgres:postgres@localhost:5432/postgres", 5432),
    ("postgresql://postgres@localhost:5432/postgres", 5432),
    ("postgresql://postgres:postgres@localhost:5433/postgres", 5433),
]


def _require_psycopg() -> None:
    if psycopg is None:
        raise RuntimeError("psycopg is required. Install with: pip install 'psycopg[binary]'")


@contextmanager
def get_connection(dsn: str):
    _require_psycopg()
    with psycopg.connect(dsn) as conn:
        yield conn


def _try_connect(dsn: str) -> bool:
    _require_psycopg()
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def _ensure_database_exists(admin_dsn: str) -> bool:
    _require_psycopg()
    try:
        with psycopg.connect(admin_dsn, connect_timeout=3, autocommit=True) as conn:
            row = conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,)
            ).fetchone()
            if not row:
                conn.execute(f'CREATE DATABASE "{DB_NAME}"')
                logger.info("Created database '%s'.", DB_NAME)
        return True
    except Exception as exc:
        logger.debug("Could not ensure DB via %s: %s", admin_dsn, exc)
        return False


def discover_and_connect() -> str:
    """Auto-discover a running localhost PostgreSQL, create the conclaw DB and
    schema if needed, and return the working DSN."""
    _require_psycopg()

    for dsn in CANDIDATE_DSNS:
        if _try_connect(dsn):
            logger.info("Connected to existing conclaw DB at %s", dsn)
            init_db(dsn)
            return dsn

    for admin_dsn, port in ADMIN_DSNS:
        if _ensure_database_exists(admin_dsn):
            target_dsn = admin_dsn.rsplit("/", 1)[0] + f"/{DB_NAME}"
            if _try_connect(target_dsn):
                init_db(target_dsn)
                logger.info("Auto-provisioned conclaw DB at %s", target_dsn)
                return target_dsn

    raise RuntimeError(
        "No running PostgreSQL found on localhost (tried ports 5432, 5433). "
        "Install PostgreSQL, start the service, or run /db up for Docker mode."
    )


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

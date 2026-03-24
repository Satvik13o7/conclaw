from __future__ import annotations

from contextlib import contextmanager

from conclaw.config import AppConfig

try:
    import psycopg
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("psycopg is required. Install with: pip install 'psycopg[binary]'") from exc


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


@contextmanager
def get_connection(config: AppConfig):
    with psycopg.connect(config.dsn) as conn:
        yield conn


def init_db(config: AppConfig) -> None:
    with get_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            conn.commit()

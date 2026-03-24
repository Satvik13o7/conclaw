from __future__ import annotations

from typing import List, Optional, Tuple

from conclaw.config import AppConfig
from conclaw.db import get_connection


def upsert_memory(config: AppConfig, scope: str, key: str, value: str) -> None:
    sql = """
    INSERT INTO memory_entries (scope, memory_key, memory_value)
    VALUES (%s, %s, %s)
    ON CONFLICT (scope, memory_key)
    DO UPDATE SET
      memory_value = EXCLUDED.memory_value,
      updated_at = NOW();
    """
    with get_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (scope, key, value))
            conn.commit()


def get_memory(config: AppConfig, scope: str, key: str) -> Optional[str]:
    sql = "SELECT memory_value FROM memory_entries WHERE scope = %s AND memory_key = %s;"
    with get_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (scope, key))
            row = cur.fetchone()
            return row[0] if row else None


def list_memory(config: AppConfig, scope: str, limit: int = 20) -> List[Tuple[str, str]]:
    sql = """
    SELECT memory_key, memory_value
    FROM memory_entries
    WHERE scope = %s
    ORDER BY updated_at DESC
    LIMIT %s;
    """
    with get_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (scope, limit))
            rows = cur.fetchall()
            return [(r[0], r[1]) for r in rows]

from __future__ import annotations

from conclaw.backend.db import get_connection
from conclaw.backend.memory import list_entries


def memory_context(dsn: str, scope: str) -> str:
    rows = list_entries(dsn, scope=scope, limit=20)
    if not rows:
        return "No memory entries."
    return "\n".join([f"- {k}: {v}" for k, v in rows])


def log_decision(dsn: str, task: str, decision: str, model_name: str) -> None:
    sql = """
    INSERT INTO decision_log (task, decision, model_name)
    VALUES (%s, %s, %s);
    """
    with get_connection(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (task, decision, model_name))
            conn.commit()


def recent_decisions(dsn: str, limit: int = 10) -> list[dict]:
    sql = """
    SELECT id, task, decision, model_name, created_at
    FROM decision_log
    ORDER BY created_at DESC
    LIMIT %s;
    """
    with get_connection(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "task": r[1],
                    "decision": r[2][:120],
                    "model": r[3],
                    "created_at": str(r[4]),
                }
                for r in rows
            ]

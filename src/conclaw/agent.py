from __future__ import annotations

import os
from typing import Optional

from conclaw.config import AppConfig
from conclaw.db import get_connection
from conclaw.memory import list_memory

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore


def _memory_context(config: AppConfig, scope: str) -> str:
    rows = list_memory(config, scope=scope, limit=20)
    if not rows:
        return "No memory entries."
    return "\n".join([f"- {k}: {v}" for k, v in rows])


def decide(config: AppConfig, scope: str, task: str) -> str:
    memory_blob = _memory_context(config, scope)
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or OpenAI is None:
        decision = (
            f"[offline-decision] Task: {task}\n"
            f"Scope: {scope}\n"
            f"Memory:\n{memory_blob}\n"
            "Set OPENAI_API_KEY and install openai for GPT-5.0 decisions."
        )
        _log_decision(config, task, decision)
        return decision

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=config.model_name,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a CLI decision engine with filesystem authority. "
                    "Prioritize safety, deterministic steps, and clear actions."
                ),
            },
            {
                "role": "user",
                "content": f"Task:\n{task}\n\nMemory Context:\n{memory_blob}",
            },
        ],
    )
    decision = response.output_text.strip()
    _log_decision(config, task, decision)
    return decision


def _log_decision(config: AppConfig, task: str, decision: str) -> None:
    sql = """
    INSERT INTO decision_log (task, decision, model_name)
    VALUES (%s, %s, %s);
    """
    with get_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (task, decision, config.model_name))
            conn.commit()

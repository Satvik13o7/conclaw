"""Tools callable by the orchestrator agent for database/memory operations."""
from __future__ import annotations

from typing import Any

from conclaw.backend.db import discover_and_connect, init_db
from conclaw.backend.memory import upsert, get, list_entries, delete
from conclaw.backend.decision import log_decision, memory_context


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "db_connect",
            "description": (
                "Auto-discover and connect to a localhost PostgreSQL instance. "
                "Creates the conclaw database and schema if they do not exist. "
                "Returns the working DSN string."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_set",
            "description": "Store a key-value pair in persistent memory under a scope.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "description": "Memory scope (e.g. global, project)"},
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["scope", "key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_get",
            "description": "Retrieve a value from persistent memory by scope and key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string"},
                    "key": {"type": "string"},
                },
                "required": ["scope", "key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_list",
            "description": "List recent memory entries for a scope.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "default": "global"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_delete",
            "description": "Delete a memory entry by scope and key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string"},
                    "key": {"type": "string"},
                },
                "required": ["scope", "key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_decision",
            "description": "Log a decision made by the agent into the decision_log table.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "decision": {"type": "string"},
                    "model_name": {"type": "string"},
                },
                "required": ["task", "decision", "model_name"],
            },
        },
    },
]


class ToolExecutor:
    """Executes backend tool calls from the orchestrator agent."""

    def __init__(self, dsn: str | None = None):
        self._dsn = dsn

    @property
    def dsn(self) -> str | None:
        return self._dsn

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        try:
            if tool_name == "db_connect":
                self._dsn = discover_and_connect()
                return f"Connected. DSN: {self._dsn}"

            if self._dsn is None:
                return "Error: Not connected to a database. Call db_connect first."

            if tool_name == "memory_set":
                upsert(self._dsn, arguments["scope"], arguments["key"], arguments["value"])
                return f"Stored [{arguments['scope']}] {arguments['key']}"

            if tool_name == "memory_get":
                value = get(self._dsn, arguments["scope"], arguments["key"])
                if value is not None:
                    return value
                return "(not found)"

            if tool_name == "memory_list":
                scope = arguments.get("scope", "global")
                limit = arguments.get("limit", 20)
                rows = list_entries(self._dsn, scope, limit)
                if not rows:
                    return f"No entries in scope '{scope}'."
                return "\n".join(f"{k}={v}" for k, v in rows)

            if tool_name == "memory_delete":
                deleted = delete(self._dsn, arguments["scope"], arguments["key"])
                return "Deleted." if deleted else "Not found."

            if tool_name == "log_decision":
                log_decision(
                    self._dsn,
                    arguments["task"],
                    arguments["decision"],
                    arguments["model_name"],
                )
                return "Decision logged."

            return f"Unknown tool: {tool_name}"
        except Exception as exc:
            return f"Tool error: {exc}"

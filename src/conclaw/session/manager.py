import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from conclaw.storage.paths import session_dir, sessions_dir
from conclaw.storage.conversation import ConversationLog


class Session:
    def __init__(self, session_id: str | None = None):
        self.id = session_id or uuid.uuid4().hex[:12]
        self.started_at = datetime.now(timezone.utc)
        self._dir = session_dir(self.id)
        self.conversation = ConversationLog(self._dir / "conversation.jsonl")
        self.tokens_in = 0
        self.tokens_out = 0
        self.tool_calls = 0
        self._write_metadata()

    @property
    def dir(self) -> Path:
        return self._dir

    def _write_metadata(self) -> None:
        meta = {
            "id": self.id,
            "started_at": self.started_at.isoformat(),
            "cwd": str(Path.cwd()),
            "status": "active",
        }
        with open(self._dir / "session.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        self._append_index()

    def _append_index(self) -> None:
        index_path = sessions_dir() / "index.jsonl"
        entry = {
            "id": self.id,
            "started_at": self.started_at.isoformat(),
            "cwd": str(Path.cwd()),
            "status": "active",
        }
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def close(self) -> None:
        meta_path = self._dir / "session.json"
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["status"] = "closed"
        meta["ended_at"] = datetime.now(timezone.utc).isoformat()
        meta["tokens_in"] = self.tokens_in
        meta["tokens_out"] = self.tokens_out
        meta["tool_calls"] = self.tool_calls
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    @staticmethod
    def list_recent(limit: int = 10) -> list[dict]:
        index_path = sessions_dir() / "index.jsonl"
        if not index_path.exists():
            return []
        entries = []
        with open(index_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries[-limit:]

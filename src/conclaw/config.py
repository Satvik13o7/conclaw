from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


CONFIG_DIR = Path.home() / ".conclaw"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class AppConfig:
    db_mode: str = "system_or_docker"
    dsn: str = "postgresql://conclaw:conclaw@localhost:5433/conclaw"
    model_name: str = "gpt-5.0"
    filesystem_permission: str = "full_access"
    safety_layer: str = "baseline"

    @classmethod
    def load(cls) -> "AppConfig":
        if not CONFIG_FILE.exists():
            return cls()
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return cls(**data)

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

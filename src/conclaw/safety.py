from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SafetyLayer:
    permission_mode: str = "full_access"
    _session_allowed: bool = field(default=False, init=False)

    def ensure_allowed(self, action: str, target: Path) -> None:
        if self.permission_mode == "full_access":
            return

        if self.permission_mode == "prompt_session":
            if not self._session_allowed:
                response = input(
                    "Grant filesystem access for this session? [y/N]: "
                ).strip().lower()
                self._session_allowed = response in {"y", "yes"}
            if self._session_allowed:
                return
            raise PermissionError("Filesystem access denied for this session.")

        if self.permission_mode == "prompt_sensitive":
            sensitive = action in {"write", "delete"}
            if sensitive:
                response = input(
                    f"Allow {action} on {target}? [y/N]: "
                ).strip().lower()
                if response in {"y", "yes"}:
                    return
                raise PermissionError(f"Denied {action} on {target}")
            return

        raise ValueError(f"Unknown permission mode: {self.permission_mode}")

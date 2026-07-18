from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nexusops_agent.config import Settings


class ModelRegistry:
    def __init__(self, path: Path | None = None) -> None:
        settings = Settings.from_env()
        self.path = path or settings.config_dir / "model_registry.json"
        self._data = json.loads(self.path.read_text(encoding="utf-8"))

    @property
    def version(self) -> str:
        return str(self._data["version"])

    def role(self, role_name: str) -> dict[str, Any]:
        try:
            return dict(self._data["roles"][role_name])
        except KeyError as exc:
            raise KeyError(f"Unknown model role: {role_name}") from exc

    def select(self, role_name: str, *, use_fallback: bool = False) -> str | None:
        role = self.role(role_name)
        if role.get("primary_engine") == "DETERMINISTIC" and not use_fallback:
            return None
        key = "fallback_model" if use_fallback else "primary_model"
        model = role.get(key)
        if model is None and use_fallback:
            model = role.get("fallback_model")
        return str(model) if model else None

    def assert_critic_diversity(self) -> None:
        credit = self.role("credit_agent")["primary_model"]
        critic = self.role("mandatory_critic")["primary_model"]
        if credit == critic:
            raise ValueError("Mandatory critic must use a different model family from Credit Agent")

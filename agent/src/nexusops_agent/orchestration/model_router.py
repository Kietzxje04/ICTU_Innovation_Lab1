from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from nexusops_agent.config import Settings


class ModelRegistry:
    ENV_OVERRIDES = {
        "planner": "NEXUSOPS_PLANNER_FALLBACK_MODEL",
        "product_agent": "NEXUSOPS_PRODUCT_MODEL",
        "credit_agent": "NEXUSOPS_CREDIT_MODEL",
        "compliance_agent": "NEXUSOPS_COMPLIANCE_MODEL",
        "mandatory_critic": "NEXUSOPS_CRITIC_MODEL",
        "escalation_reasoner": "NEXUSOPS_ESCALATION_MODEL",
        "vision_document_extractor": "NEXUSOPS_VISION_MODEL",
        "embedding": "NEXUSOPS_EMBEDDING_MODEL",
        "reranker": "NEXUSOPS_RERANKER_MODEL",
    }
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
        if not use_fallback:
            override = os.getenv(self.ENV_OVERRIDES.get(role_name, ""))
            if override:
                return override
        key = "fallback_model" if use_fallback else "primary_model"
        model = role.get(key)
        if model is None and use_fallback:
            model = role.get("fallback_model")
        return str(model) if model else None

    def candidates(self, role_name: str) -> list[str]:
        values = [self.select(role_name), self.select(role_name, use_fallback=True)]
        return list(dict.fromkeys(value for value in values if value))

    def assert_critic_diversity(self) -> None:
        credit = self.role("credit_agent")["primary_model"]
        critic = self.role("mandatory_critic")["primary_model"]
        if credit == critic:
            raise ValueError("Mandatory critic must use a different model family from Credit Agent")

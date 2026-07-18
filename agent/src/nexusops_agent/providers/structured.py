from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from nexusops_agent.orchestration.model_router import ModelRegistry

from .fpt_factory import FptAiFactoryClient


T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class LiveInvocation:
    result: BaseModel
    model: str
    usage: dict[str, Any]


class FptStructuredReasoner:
    def __init__(self, client: FptAiFactoryClient, registry: ModelRegistry | None = None, prompts_dir: Path | None = None) -> None:
        self.client = client
        self.registry = registry or ModelRegistry()
        self.prompts_dir = prompts_dir or self.registry.path.parent.parent / "prompts"

    def prompt(self, name: str) -> str:
        return (self.prompts_dir / f"{name}.md").read_text(encoding="utf-8").strip()

    @staticmethod
    def _content(response: dict[str, Any]) -> str:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("Chat response missing choices")
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise ValueError("Chat response missing content")
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        return text

    def invoke(self, role: str, prompt_name: str, payload: dict[str, Any], output_schema: type[T]) -> LiveInvocation:
        schema_instruction = json.dumps(output_schema.model_json_schema(), ensure_ascii=False)
        messages = [
            {"role": "system", "content": f"{self.prompt(prompt_name)}\nReturn one JSON object matching this schema exactly: {schema_instruction}"},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
        ]
        role_config = self.registry.role(role)
        errors: list[Exception] = []
        for model in self.registry.candidates(role):
            try:
                response = self.client.chat_completion(
                    model=model,
                    messages=messages,
                    temperature=float(role_config.get("temperature", 0.0)),
                    max_tokens=min(int(role_config.get("max_tokens", 1200)), 1200),
                    response_format={"type": "json_object"},
                )
                result = output_schema.model_validate(json.loads(self._content(response)))
                return LiveInvocation(result=result, model=model, usage=dict(response.get("usage") or {}))
            except Exception as exc:
                errors.append(exc)
        last = errors[-1] if errors else RuntimeError(f"No live model configured for role {role}")
        raise RuntimeError(f"All live models failed for role {role}: {type(last).__name__}") from last

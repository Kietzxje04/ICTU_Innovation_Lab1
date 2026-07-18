from __future__ import annotations

from typing import Protocol


class StructuredModelClient(Protocol):
    def invoke(self, *, system_prompt: str, payload: dict[str, object], output_schema: type) -> object: ...


class LlmNodeNotConfigured(RuntimeError):
    pass


def invoke_structured(client: StructuredModelClient | None, *, system_prompt: str, payload: dict[str, object], output_schema: type) -> object:
    if client is None:
        raise LlmNodeNotConfigured("No local/cloud model adapter configured")
    return client.invoke(system_prompt=system_prompt, payload=payload, output_schema=output_schema)

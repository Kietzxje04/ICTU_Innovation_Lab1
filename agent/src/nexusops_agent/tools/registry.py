from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    handler: Callable[..., Any]
    read_only: bool = True


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def invoke(self, name: str, **kwargs: object) -> object:
        try:
            tool = self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Tool not allowlisted: {name}") from exc
        return tool.handler(**kwargs)

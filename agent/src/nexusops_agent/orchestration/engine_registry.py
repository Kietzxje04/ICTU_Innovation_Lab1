from dataclasses import dataclass

from nexusops_agent.contracts.enums import EngineKind


@dataclass(frozen=True)
class EngineDefinition:
    name: str
    kind: EngineKind
    model: str | None = None
    enabled: bool = True


class EngineRegistry:
    def __init__(self) -> None:
        self._engines: dict[str, EngineDefinition] = {}

    def register(self, engine: EngineDefinition) -> None:
        if engine.name in self._engines:
            raise ValueError(f"Engine already registered: {engine.name}")
        self._engines[engine.name] = engine

    def get(self, name: str) -> EngineDefinition:
        try:
            return self._engines[name]
        except KeyError as exc:
            raise KeyError(f"Unknown engine: {name}") from exc

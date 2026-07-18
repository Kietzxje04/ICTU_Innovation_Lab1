from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from nexusops_agent.providers.fpt_factory import FptAiFactoryClient


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass
class FptEmbeddingProvider:
    client: FptAiFactoryClient
    model: str = "Vietnamese_Embedding"

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings(model=self.model, inputs=texts)
        data = response.get("data")
        if not isinstance(data, list):
            raise ValueError("Embedding response missing data list")
        ordered = sorted(data, key=lambda item: int(item.get("index", 0)))
        vectors = [item.get("embedding") for item in ordered]
        if any(not isinstance(vector, list) for vector in vectors):
            raise ValueError("Embedding response contains invalid vector")
        return vectors

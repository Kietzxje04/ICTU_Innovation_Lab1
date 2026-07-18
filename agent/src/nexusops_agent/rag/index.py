from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from nexusops_agent.contracts.evidence import EvidenceChunk

from .namespace_router import Namespace, namespace_for


@dataclass(frozen=True)
class IndexManifest:
    version: str
    source_file: str
    source_sha256: str
    total_chunks: int
    namespace_counts: dict[str, int]
    searchable_default_chunks: int
    quarantined_chunks: int
    embedding_model: str
    reranker_model: str

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class VectorRecord:
    chunk: EvidenceChunk
    vector: list[float]


class InMemoryVectorIndex:
    """Small test/demo index; production adapter can target Chroma/FAISS."""

    def __init__(self, records: list[VectorRecord]) -> None:
        self.records = records

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if len(left) != len(right) or not left:
            raise ValueError("Vector dimensions must match and be non-empty")
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        return 0.0 if left_norm == 0 or right_norm == 0 else dot / (left_norm * right_norm)

    def search(self, query_vector: list[float], namespaces: set[Namespace], top_k: int = 20) -> list[tuple[EvidenceChunk, float]]:
        scored = [
            (record.chunk, self._cosine(query_vector, record.vector))
            for record in self.records
            if namespace_for(record.chunk) in namespaces
        ]
        return sorted(scored, key=lambda item: (-item[1], item[0].chunk_id))[:top_k]

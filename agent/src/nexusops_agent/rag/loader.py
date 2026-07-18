from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from nexusops_agent.config import Settings
from nexusops_agent.contracts.evidence import EvidenceChunk


class RagCorpus:
    """Read-only access to the normalized legal corpus."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Settings.from_env().rag_data_path
        self._chunks: list[EvidenceChunk] | None = None

    def load(self) -> list[EvidenceChunk]:
        if self._chunks is None:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                raise ValueError("RAG corpus root must be a list")
            self._chunks = [EvidenceChunk.model_validate(item) for item in raw]
            ids = [item.chunk_id for item in self._chunks]
            if len(ids) != len(set(ids)):
                raise ValueError("Duplicate chunk_id detected")
        return list(self._chunks)

    def by_id(self) -> dict[str, EvidenceChunk]:
        return {item.chunk_id: item for item in self.load()}

    def inventory(self) -> dict[str, object]:
        chunks = self.load()
        return {
            "total": len(chunks),
            "quality": dict(Counter(item.quality.status for item in chunks)),
            "domain": dict(Counter(item.domain for item in chunks)),
            "synthetic": sum(item.is_synthetic for item in chunks),
        }

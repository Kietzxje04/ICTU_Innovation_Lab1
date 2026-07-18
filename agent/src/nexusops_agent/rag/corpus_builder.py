from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from nexusops_agent.contracts.evidence import EvidenceChunk

from .registry import DocumentRegistry


CorpusBucket = Literal["accepted", "quarantine", "rejected"]


class CorpusBuildManifest(BaseModel):
    version: str
    source_sha256: str
    registry_sha256: str
    total_chunks: int
    accepted_chunks: int
    quarantined_chunks: int
    rejected_chunks: int
    output_sha256: dict[str, str]


@dataclass(frozen=True)
class CorpusBuildResult:
    accepted: list[EvidenceChunk]
    quarantine: list[EvidenceChunk]
    rejected: list[EvidenceChunk]
    manifest: CorpusBuildManifest


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _jsonl(chunks: list[EvidenceChunk]) -> bytes:
    rows = [
        json.dumps(chunk.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for chunk in sorted(chunks, key=lambda item: item.chunk_id)
    ]
    return (("\n".join(rows) + "\n") if rows else "").encode("utf-8")


class CorpusBuilder:
    """Deterministically route normalized chunks into searchable and review buckets."""

    def __init__(self, registry: DocumentRegistry) -> None:
        self.registry = registry

    def bucket_for(self, chunk: EvidenceChunk) -> CorpusBucket:
        if chunk.quality.status == "REJECTED":
            return "rejected"
        entry = self.registry.get(chunk.document_id)
        if entry is None:
            return "quarantine"
        if entry.verification_status == "REJECTED":
            return "rejected"
        if chunk.quality.status == "REVIEW_REQUIRED":
            return "quarantine"
        if chunk.quality.status == "DEMO_ONLY":
            return "accepted" if entry.verification_status == "DEMO_ONLY" else "quarantine"
        return "accepted" if entry.is_verified_for_search else "quarantine"

    def build(self, chunks: list[EvidenceChunk], *, source_bytes: bytes, registry_bytes: bytes) -> CorpusBuildResult:
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        content_hashes = [chunk.content_hash for chunk in chunks]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("Duplicate chunk_id detected during corpus build")
        if len(content_hashes) != len(set(content_hashes)):
            raise ValueError("Duplicate content_hash detected during corpus build")
        buckets: dict[CorpusBucket, list[EvidenceChunk]] = {
            "accepted": [],
            "quarantine": [],
            "rejected": [],
        }
        for chunk in chunks:
            buckets[self.bucket_for(chunk)].append(chunk)
        rendered = {name: _jsonl(items) for name, items in buckets.items()}
        manifest = CorpusBuildManifest(
            version="rag-v2-gated-jsonl",
            source_sha256=_sha256(source_bytes),
            registry_sha256=_sha256(registry_bytes),
            total_chunks=len(chunks),
            accepted_chunks=len(buckets["accepted"]),
            quarantined_chunks=len(buckets["quarantine"]),
            rejected_chunks=len(buckets["rejected"]),
            output_sha256={name: _sha256(data) for name, data in rendered.items()},
        )
        return CorpusBuildResult(
            accepted=sorted(buckets["accepted"], key=lambda item: item.chunk_id),
            quarantine=sorted(buckets["quarantine"], key=lambda item: item.chunk_id),
            rejected=sorted(buckets["rejected"], key=lambda item: item.chunk_id),
            manifest=manifest,
        )

    def write(self, result: CorpusBuildResult, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        payloads = {
            "accepted.jsonl": _jsonl(result.accepted),
            "quarantine.jsonl": _jsonl(result.quarantine),
            "rejected.jsonl": _jsonl(result.rejected),
        }
        for filename, data in payloads.items():
            (output_dir / filename).write_bytes(data)
        (output_dir / "manifest.json").write_text(
            json.dumps(result.manifest.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

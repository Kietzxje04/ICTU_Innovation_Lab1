from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field

from nexusops_agent.contracts.evidence import EvidenceChunk

from .registry import DocumentRegistry


class QualityGateIssue(BaseModel):
    severity: Literal["ERROR", "WARNING"]
    code: str
    document_id: str | None = None
    chunk_id: str | None = None
    detail: str


class QualityGateReport(BaseModel):
    total_documents: int
    total_chunks: int
    searchable_documents: int
    searchable_chunks: int
    quarantined_chunks: int
    rejected_chunks: int
    chunk_quality_counts: dict[str, int] = Field(default_factory=dict)
    chunk_warning_counts: dict[str, int] = Field(default_factory=dict)
    errors: int
    warnings: int
    issue_counts: dict[str, int] = Field(default_factory=dict)
    issues: list[QualityGateIssue] = Field(default_factory=list)

    @property
    def ready_for_build(self) -> bool:
        return self.errors == 0


class LegalCorpusQualityGate:
    """Fail-closed document and chunk checks before indexing a legal corpus."""

    def __init__(self, registry: DocumentRegistry) -> None:
        self.registry = registry

    def audit(self, chunks: list[EvidenceChunk]) -> QualityGateReport:
        issues: list[QualityGateIssue] = []
        seen_chunk_ids: set[str] = set()
        seen_hashes: set[str] = set()
        chunk_quality_counts = Counter(chunk.quality.status for chunk in chunks)
        chunk_warning_counts = Counter(
            warning
            for chunk in chunks
            for warning in chunk.quality.warnings
        )

        for chunk in chunks:
            if chunk.chunk_id in seen_chunk_ids:
                issues.append(self._chunk_error(chunk, "DUPLICATE_CHUNK_ID", "chunk_id is not unique"))
            seen_chunk_ids.add(chunk.chunk_id)
            if chunk.content_hash in seen_hashes:
                issues.append(self._chunk_error(chunk, "DUPLICATE_CONTENT_HASH", "content_hash is not unique"))
            seen_hashes.add(chunk.content_hash)

            entry = self.registry.get(chunk.document_id)
            if entry is None:
                issues.append(self._chunk_error(chunk, "DOCUMENT_NOT_REGISTERED", "document_id is absent from the registry"))
                continue

            allowed_numbers = {entry.canonical_document_number, *entry.observed_document_numbers}
            if chunk.document_number not in allowed_numbers:
                issues.append(
                    self._chunk_error(
                        chunk,
                        "UNRECOGNIZED_DOCUMENT_NUMBER",
                        f"chunk document_number={chunk.document_number!r} is not registered",
                    )
                )

            if chunk.domain != entry.domain:
                issues.append(
                    self._chunk_error(
                        chunk,
                        "DOCUMENT_DOMAIN_MISMATCH",
                        f"chunk domain={chunk.domain!r}; registry domain={entry.domain!r}",
                    )
                )

        for entry in self.registry.entries:
            if entry.verification_status not in {"VERIFIED", "DEMO_ONLY"}:
                issues.append(
                    QualityGateIssue(
                        severity="ERROR",
                        code=f"DOCUMENT_{entry.verification_status}",
                        document_id=entry.document_id,
                        detail="document cannot enter the searchable corpus until document-level review is complete",
                    )
                )
            if entry.is_official and not entry.source_url:
                issues.append(
                    QualityGateIssue(
                        severity="ERROR",
                        code="OFFICIAL_SOURCE_URL_MISSING",
                        document_id=entry.document_id,
                        detail="official legal document has no authoritative source URL",
                    )
                )
            if entry.is_official and not entry.source_hash:
                issues.append(
                    QualityGateIssue(
                        severity="ERROR",
                        code="OFFICIAL_SOURCE_HASH_MISSING",
                        document_id=entry.document_id,
                        detail="official legal document has no immutable source hash",
                    )
                )
            if entry.is_official and entry.validity_status != "VERIFIED_ACTIVE":
                issues.append(
                    QualityGateIssue(
                        severity="ERROR",
                        code="OFFICIAL_VALIDITY_NOT_VERIFIED",
                        document_id=entry.document_id,
                        detail=f"validity_status={entry.validity_status!r}",
                    )
                )

        counts = Counter(issue.code for issue in issues)
        errors = sum(issue.severity == "ERROR" for issue in issues)
        warnings = len(issues) - errors
        searchable_chunks = sum(
            chunk.quality.status in {"ACCEPTED", "DEMO_ONLY"}
            and (entry := self.registry.get(chunk.document_id)) is not None
            and entry.is_verified_for_search
            for chunk in chunks
        )
        return QualityGateReport(
            total_documents=len(self.registry.entries),
            total_chunks=len(chunks),
            searchable_documents=sum(entry.is_verified_for_search for entry in self.registry.entries),
            searchable_chunks=searchable_chunks,
            quarantined_chunks=chunk_quality_counts["REVIEW_REQUIRED"],
            rejected_chunks=chunk_quality_counts["REJECTED"],
            chunk_quality_counts=dict(sorted(chunk_quality_counts.items())),
            chunk_warning_counts=dict(sorted(chunk_warning_counts.items())),
            errors=errors,
            warnings=warnings,
            issue_counts=dict(sorted(counts.items())),
            issues=issues,
        )

    @staticmethod
    def _chunk_error(chunk: EvidenceChunk, code: str, detail: str) -> QualityGateIssue:
        return QualityGateIssue(
            severity="ERROR",
            code=code,
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            detail=detail,
        )

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class QualityInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: Literal["ACCEPTED", "REVIEW_REQUIRED", "DEMO_ONLY", "REJECTED"]
    warnings: list[str] = Field(default_factory=list)


class EvidenceChunk(BaseModel):
    model_config = ConfigDict(extra="allow")

    chunk_id: str
    document_id: str
    document_number: str
    filename_document_number: str | None = None
    document_title: str | None = None
    domain: str
    source_type: str
    source_authority: str
    validity_status: str
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    page_or_part: int | None = None
    title: str | None = None
    content: str
    citation_text: str
    content_hash: str
    is_synthetic: bool = False
    synthetic_disclaimer: str | None = None
    embedding_text: str
    quality: QualityInfo
    provenance: dict[str, Any] = Field(default_factory=dict)


class CitationClaim(BaseModel):
    claim_id: str
    chunk_id: str
    quote: str
    claim_type: str = "EXPLANATORY"


class ValidationResult(BaseModel):
    status: Literal[
        "VALID",
        "WARNING_DEMO_ONLY",
        "REVIEW_REQUIRED",
        "STALE_OR_UNVERIFIED",
        "INVALID_QUOTE",
        "INVALID_HASH",
        "INVALID_AUTHORITY",
        "ABSTAIN_NO_EVIDENCE",
    ]
    reasons: list[str] = Field(default_factory=list)

from __future__ import annotations

import hashlib
import re
import unicodedata

from nexusops_agent.contracts.evidence import CitationClaim, EvidenceChunk, ValidationResult


def _content_hash(content: str) -> str:
    normalized = unicodedata.normalize("NFC", content)
    normalized = re.sub(r"\s+", " ", normalized).casefold().strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class CitationValidator:
    def __init__(self, chunks: dict[str, EvidenceChunk]) -> None:
        self.chunks = chunks

    def validate(self, claim: CitationClaim) -> ValidationResult:
        chunk = self.chunks.get(claim.chunk_id)
        if chunk is None:
            return ValidationResult(status="ABSTAIN_NO_EVIDENCE", reasons=["CHUNK_NOT_FOUND"])
        if _content_hash(chunk.content) != chunk.content_hash:
            return ValidationResult(status="INVALID_HASH", reasons=["CONTENT_HASH_MISMATCH"])
        if claim.quote not in chunk.content:
            return ValidationResult(status="INVALID_QUOTE", reasons=["QUOTE_NOT_EXACT_SUBSTRING"])
        if chunk.quality.status == "REVIEW_REQUIRED":
            return ValidationResult(status="REVIEW_REQUIRED", reasons=chunk.quality.warnings)
        if chunk.quality.status == "DEMO_ONLY" or chunk.is_synthetic:
            if not chunk.synthetic_disclaimer:
                return ValidationResult(status="INVALID_AUTHORITY", reasons=["SYNTHETIC_DISCLAIMER_MISSING"])
            return ValidationResult(status="WARNING_DEMO_ONLY", reasons=[chunk.synthetic_disclaimer])
        if chunk.validity_status != "VERIFIED_ACTIVE":
            return ValidationResult(status="STALE_OR_UNVERIFIED", reasons=[chunk.validity_status])
        return ValidationResult(status="VALID")

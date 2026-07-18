from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DocumentVerificationStatus = Literal[
    "VERIFIED",
    "PENDING_SOURCE_VERIFICATION",
    "IDENTITY_CONFLICT",
    "INCOMPLETE_SOURCE",
    "DEMO_ONLY",
    "REJECTED",
]


class DocumentRegistryEntry(BaseModel):
    """Document-level source of truth used before chunks become searchable."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    canonical_document_number: str
    observed_document_numbers: list[str] = Field(default_factory=list)
    document_title: str
    document_type: str
    issuer: str
    domain: str
    source_type: str
    source_authority: str
    source_url: str | None = None
    source_hash: str | None = None
    issue_date: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    validity_status: str = "UNVERIFIED"
    verification_status: DocumentVerificationStatus
    notes: list[str] = Field(default_factory=list)

    @property
    def is_official(self) -> bool:
        return self.source_type == "OFFICIAL_LEGAL"

    @property
    def is_verified_for_search(self) -> bool:
        if self.verification_status == "DEMO_ONLY":
            return True
        return (
            self.verification_status == "VERIFIED"
            and bool(self.source_url)
            and bool(self.source_hash)
            and self.validity_status == "VERIFIED_ACTIVE"
        )


class DocumentRegistry:
    def __init__(self, entries: list[DocumentRegistryEntry]) -> None:
        ids = [entry.document_id for entry in entries]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate document_id detected in registry")
        self.entries = list(entries)
        self._by_id = {entry.document_id: entry for entry in entries}

    @classmethod
    def load(cls, path: Path) -> "DocumentRegistry":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Document registry root must be a list")
        return cls([DocumentRegistryEntry.model_validate(item) for item in raw])

    def get(self, document_id: str) -> DocumentRegistryEntry | None:
        return self._by_id.get(document_id)

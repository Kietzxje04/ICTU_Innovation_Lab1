import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.contracts.evidence import EvidenceChunk
from nexusops_agent.rag.quality_gate import LegalCorpusQualityGate
from nexusops_agent.rag.registry import DocumentRegistry, DocumentRegistryEntry


def chunk(**updates: object) -> EvidenceChunk:
    raw = {
        "chunk_id": "DOC-1-DIEU-1",
        "document_id": "DOC-1",
        "document_number": "01/2026/TT-TEST",
        "document_title": "Test document",
        "filename_document_number": "01/2026/TT-TEST",
        "domain": "LENDING_REGULATION",
        "source_type": "OFFICIAL_LEGAL",
        "source_authority": "L1",
        "validity_status": "VERIFIED_ACTIVE",
        "article": "Điều 1",
        "content": "Điều 1. Nội dung kiểm thử.",
        "citation_text": "[01/2026/TT-TEST, Điều 1]",
        "content_hash": "hash-1",
        "embedding_text": "01/2026/TT-TEST Điều 1 Nội dung kiểm thử",
        "quality": {"status": "ACCEPTED", "warnings": []},
    }
    raw.update(updates)
    return EvidenceChunk.model_validate(raw)


def registry_entry(**updates: object) -> DocumentRegistryEntry:
    raw = {
        "document_id": "DOC-1",
        "canonical_document_number": "01/2026/TT-TEST",
        "observed_document_numbers": ["01/2026/TT-TEST"],
        "document_title": "Test document",
        "document_type": "TT",
        "issuer": "TEST_ISSUER",
        "domain": "LENDING_REGULATION",
        "source_type": "OFFICIAL_LEGAL",
        "source_authority": "L1",
        "source_url": "https://example.test/legal/01-2026",
        "source_hash": "sha256:source",
        "validity_status": "VERIFIED_ACTIVE",
        "verification_status": "VERIFIED",
    }
    raw.update(updates)
    return DocumentRegistryEntry.model_validate(raw)


class DocumentRegistryTest(unittest.TestCase):
    def test_load_rejects_duplicate_document_ids(self) -> None:
        payload = [registry_entry().model_dump(mode="json"), registry_entry().model_dump(mode="json")]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate document_id"):
                DocumentRegistry.load(path)

    def test_verified_document_passes_gate(self) -> None:
        report = LegalCorpusQualityGate(DocumentRegistry([registry_entry()])).audit([chunk()])
        self.assertTrue(report.ready_for_build)
        self.assertEqual(1, report.searchable_documents)
        self.assertEqual(1, report.searchable_chunks)
        self.assertEqual({"ACCEPTED": 1}, report.chunk_quality_counts)
        self.assertEqual({}, report.issue_counts)

    def test_unverified_official_document_fails_closed(self) -> None:
        entry = registry_entry(
            source_url=None,
            source_hash=None,
            validity_status="UNVERIFIED",
            verification_status="IDENTITY_CONFLICT",
        )
        report = LegalCorpusQualityGate(DocumentRegistry([entry])).audit([chunk()])
        self.assertFalse(report.ready_for_build)
        self.assertIn("DOCUMENT_IDENTITY_CONFLICT", report.issue_counts)
        self.assertIn("OFFICIAL_SOURCE_URL_MISSING", report.issue_counts)
        self.assertIn("OFFICIAL_SOURCE_HASH_MISSING", report.issue_counts)
        self.assertIn("OFFICIAL_VALIDITY_NOT_VERIFIED", report.issue_counts)

    def test_unregistered_chunk_is_rejected(self) -> None:
        report = LegalCorpusQualityGate(DocumentRegistry([])).audit([chunk()])
        self.assertEqual(1, report.issue_counts["DOCUMENT_NOT_REGISTERED"])


if __name__ == "__main__":
    unittest.main()

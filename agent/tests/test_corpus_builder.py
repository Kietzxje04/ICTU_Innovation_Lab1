import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.contracts.evidence import EvidenceChunk
from nexusops_agent.rag.corpus_builder import CorpusBuilder
from nexusops_agent.rag.registry import DocumentRegistry, DocumentRegistryEntry


def entry(document_id: str, *, verified: bool = True, demo: bool = False) -> DocumentRegistryEntry:
    return DocumentRegistryEntry.model_validate({
        "document_id": document_id,
        "canonical_document_number": document_id,
        "observed_document_numbers": [document_id],
        "document_title": document_id,
        "document_type": "DEMO" if demo else "TT",
        "issuer": "TEST",
        "domain": "INTERNAL_POLICY" if demo else "LENDING_REGULATION",
        "source_type": "SYNTHETIC_INTERNAL_POLICY" if demo else "OFFICIAL_LEGAL",
        "source_authority": "L3" if demo else "L1",
        "source_url": None if demo else "https://example.test/source",
        "source_hash": None if demo else "sha256:source",
        "validity_status": "UNVERIFIED" if demo else "VERIFIED_ACTIVE",
        "verification_status": "DEMO_ONLY" if demo else "VERIFIED" if verified else "PENDING_SOURCE_VERIFICATION",
    })


def chunk(chunk_id: str, document_id: str, status: str = "ACCEPTED") -> EvidenceChunk:
    return EvidenceChunk.model_validate({
        "chunk_id": chunk_id,
        "document_id": document_id,
        "document_number": document_id,
        "domain": "INTERNAL_POLICY" if document_id == "DEMO" else "LENDING_REGULATION",
        "source_type": "SYNTHETIC_INTERNAL_POLICY" if document_id == "DEMO" else "OFFICIAL_LEGAL",
        "source_authority": "L3" if document_id == "DEMO" else "L1",
        "validity_status": "UNVERIFIED" if document_id == "DEMO" else "VERIFIED_ACTIVE",
        "content": f"Content {chunk_id}",
        "citation_text": f"[{document_id}]",
        "content_hash": f"hash-{chunk_id}",
        "embedding_text": f"Embedding {chunk_id}",
        "is_synthetic": document_id == "DEMO",
        "synthetic_disclaimer": "DEMO ONLY" if document_id == "DEMO" else None,
        "quality": {"status": status, "warnings": []},
    })


class CorpusBuilderTest(unittest.TestCase):
    def test_routes_only_verified_or_demo_chunks_to_accepted(self) -> None:
        registry = DocumentRegistry([entry("VERIFIED"), entry("PENDING", verified=False), entry("DEMO", demo=True)])
        builder = CorpusBuilder(registry)
        result = builder.build([
            chunk("a", "VERIFIED"),
            chunk("b", "PENDING"),
            chunk("c", "VERIFIED", "REVIEW_REQUIRED"),
            chunk("d", "DEMO", "DEMO_ONLY"),
            chunk("e", "UNKNOWN"),
        ], source_bytes=b"source", registry_bytes=b"registry")
        self.assertEqual(["a", "d"], [item.chunk_id for item in result.accepted])
        self.assertEqual(["b", "c", "e"], [item.chunk_id for item in result.quarantine])
        self.assertEqual([], result.rejected)

    def test_build_and_output_are_deterministic(self) -> None:
        builder = CorpusBuilder(DocumentRegistry([entry("VERIFIED")]))
        first = builder.build([chunk("b", "VERIFIED"), chunk("a", "VERIFIED")], source_bytes=b"s", registry_bytes=b"r")
        second = builder.build([chunk("a", "VERIFIED"), chunk("b", "VERIFIED")], source_bytes=b"s", registry_bytes=b"r")
        self.assertEqual(first.manifest, second.manifest)
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            builder.write(first, Path(left))
            builder.write(second, Path(right))
            for filename in ["accepted.jsonl", "quarantine.jsonl", "rejected.jsonl", "manifest.json"]:
                self.assertEqual((Path(left) / filename).read_bytes(), (Path(right) / filename).read_bytes())

    def test_duplicate_ids_and_hashes_fail_the_build(self) -> None:
        builder = CorpusBuilder(DocumentRegistry([entry("VERIFIED")]))
        with self.assertRaisesRegex(ValueError, "Duplicate chunk_id"):
            builder.build([chunk("a", "VERIFIED"), chunk("a", "VERIFIED")], source_bytes=b"s", registry_bytes=b"r")
        duplicate_hash = chunk("b", "VERIFIED").model_copy(update={"content_hash": "hash-a"})
        with self.assertRaisesRegex(ValueError, "Duplicate content_hash"):
            builder.build([chunk("a", "VERIFIED"), duplicate_hash], source_bytes=b"s", registry_bytes=b"r")


if __name__ == "__main__":
    unittest.main()

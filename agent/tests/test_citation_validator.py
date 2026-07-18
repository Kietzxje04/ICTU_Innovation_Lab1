import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.contracts.evidence import CitationClaim
from nexusops_agent.rag.citation_validator import CitationValidator
from nexusops_agent.rag.loader import RagCorpus


class CitationValidatorTest(unittest.TestCase):
    def setUp(self) -> None:
        corpus = RagCorpus(ROOT / "final_rag_data_normalized_v1.json")
        self.chunks = corpus.by_id()
        self.validator = CitationValidator(self.chunks)

    def test_exact_quote_never_becomes_valid_when_unverified(self) -> None:
        chunk = next(item for item in self.chunks.values() if item.quality.status == "ACCEPTED")
        claim = CitationClaim(claim_id="C1", chunk_id=chunk.chunk_id, quote=chunk.content[:80])
        result = self.validator.validate(claim)
        self.assertEqual("STALE_OR_UNVERIFIED", result.status)

    def test_wrong_quote_is_rejected(self) -> None:
        chunk = next(iter(self.chunks.values()))
        claim = CitationClaim(claim_id="C2", chunk_id=chunk.chunk_id, quote="QUOTE KHÔNG TỒN TẠI")
        result = self.validator.validate(claim)
        self.assertEqual("INVALID_QUOTE", result.status)


if __name__ == "__main__":
    unittest.main()

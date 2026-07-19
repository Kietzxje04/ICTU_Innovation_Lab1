import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.evaluation.retrieval import RetrievalCase, RetrievalEvaluator
from nexusops_agent.rag.corpus_builder import CorpusBuilder
from nexusops_agent.rag.loader import RagCorpus
from nexusops_agent.rag.migration import CorpusMetadataMigrator
from nexusops_agent.rag.pipeline import RetrievalPipeline
from nexusops_agent.rag.registry import DocumentRegistry
from nexusops_agent.rag.retriever import HybridLiteRetriever


class RagMigrationEvaluationTest(unittest.TestCase):
    def test_current_corpus_builds_and_retrieves_both_demo_products(self) -> None:
        source_path = ROOT / "final_rag_data_normalized_v1.json"
        registry_path = ROOT / "configs" / "rag" / "document_registry.json"
        chunks, migration = CorpusMetadataMigrator().migrate(RagCorpus(source_path).load())
        self.assertGreaterEqual(migration.product_tag_counts["CORPORATE_OVERDRAFT"], 1)
        self.assertGreaterEqual(migration.product_tag_counts["WORKING_CAPITAL"], 1)
        builder = CorpusBuilder(DocumentRegistry.load(registry_path))
        result = builder.build(chunks, source_bytes=source_path.read_bytes(), registry_bytes=registry_path.read_bytes())
        self.assertEqual(2, len(result.accepted))
        self.assertEqual(238, len(result.quarantine))
        with tempfile.TemporaryDirectory() as directory:
            builder.write(result, Path(directory))
            pipeline = RetrievalPipeline(HybridLiteRetriever(RagCorpus.from_generated(Path(directory))))
            report = RetrievalEvaluator(pipeline).evaluate([
                RetrievalCase(
                    case_id="od", agent_id="PRODUCT_AGENT", query="điều kiện cấp thấu chi doanh nghiệp",
                    product="CORPORATE_OVERDRAFT", expected_chunk_ids=["shb_sme_policy_2026-f5e370ef82792900"],
                ),
                RetrievalCase(
                    case_id="wc", agent_id="PRODUCT_AGENT", query="điều kiện vay vốn lưu động doanh nghiệp",
                    product="WORKING_CAPITAL", expected_chunk_ids=["shb_sme_policy_2026-891a26254a536aff"],
                ),
            ])
            self.assertEqual(2, report.passed)
            self.assertEqual(1.0, report.recall_at_k)


if __name__ == "__main__":
    unittest.main()

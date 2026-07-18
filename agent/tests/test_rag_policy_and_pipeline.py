import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.rag.loader import RagCorpus
from nexusops_agent.rag.namespace_router import Namespace
from nexusops_agent.rag.pipeline import RetrievalPipeline
from nexusops_agent.rag.policy import policy_for
from nexusops_agent.rag.retriever import HybridLiteRetriever


class RagPolicyTest(unittest.TestCase):
    def test_agent_namespace_allowlist(self) -> None:
        compliance = policy_for("COMPLIANCE_AGENT")
        self.assertEqual(frozenset({Namespace.LEGAL_AML}), compliance.namespaces)
        credit = policy_for("CREDIT_AGENT")
        self.assertIn(Namespace.LEGAL_LENDING, credit.namespaces)
        self.assertIn(Namespace.DEMO_INTERNAL_POLICY, credit.namespaces)
        reviewer = policy_for("DATA_REVIEWER")
        self.assertTrue(reviewer.allow_review_required)

    def test_sparse_aml_routing_and_demo_retrieval(self) -> None:
        corpus = RagCorpus(ROOT / "final_rag_data_normalized_v1.json")
        pipeline = RetrievalPipeline(HybridLiteRetriever(corpus))
        compliance_hits = pipeline.retrieve(agent_id="COMPLIANCE_AGENT", query="giao dịch đáng ngờ", top_k=3)
        self.assertTrue(compliance_hits)
        self.assertTrue(all(hit.namespace == Namespace.LEGAL_AML for hit in compliance_hits))
        credit_hits = pipeline.retrieve(agent_id="CREDIT_AGENT", query="điều kiện cấp thấu chi", top_k=3)
        self.assertTrue(credit_hits)
        self.assertTrue(all(hit.namespace == Namespace.DEMO_INTERNAL_POLICY for hit in credit_hits))


if __name__ == "__main__":
    unittest.main()

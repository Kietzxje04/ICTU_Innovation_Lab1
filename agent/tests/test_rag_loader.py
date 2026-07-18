import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.rag.loader import RagCorpus
from nexusops_agent.rag.namespace_router import Namespace, namespace_for


class RagLoaderTest(unittest.TestCase):
    def test_inventory_and_namespaces(self) -> None:
        corpus = RagCorpus(ROOT / "final_rag_data_normalized_v1.json")
        chunks = corpus.load()
        self.assertEqual(240, len(chunks))
        self.assertEqual(240, len({chunk.chunk_id for chunk in chunks}))
        namespaces = {namespace_for(chunk) for chunk in chunks}
        self.assertIn(Namespace.QUARANTINE, namespaces)
        self.assertIn(Namespace.DEMO_INTERNAL_POLICY, namespaces)


if __name__ == "__main__":
    unittest.main()

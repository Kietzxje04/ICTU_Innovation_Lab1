import sys
import json
import tempfile
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

    def test_generated_jsonl_excludes_quarantine_by_default(self) -> None:
        source = json.loads((ROOT / "final_rag_data_normalized_v1.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory)
            (generated / "accepted.jsonl").write_text(json.dumps(source[0], ensure_ascii=False) + "\n", encoding="utf-8")
            (generated / "quarantine.jsonl").write_text(json.dumps(source[1], ensure_ascii=False) + "\n", encoding="utf-8")
            self.assertEqual(1, len(RagCorpus.from_generated(generated).load()))
            self.assertEqual(2, len(RagCorpus.from_generated(generated, include_quarantine=True).load()))


if __name__ == "__main__":
    unittest.main()

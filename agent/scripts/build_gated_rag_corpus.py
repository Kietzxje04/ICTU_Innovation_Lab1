from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.rag.corpus_builder import CorpusBuilder
from nexusops_agent.rag.loader import RagCorpus
from nexusops_agent.rag.migration import CorpusMetadataMigrator
from nexusops_agent.rag.registry import DocumentRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="Build gated JSONL corpora from normalized legal RAG data")
    parser.add_argument("--corpus", type=Path, default=ROOT / "final_rag_data_normalized_v1.json")
    parser.add_argument("--registry", type=Path, default=ROOT / "configs" / "rag" / "document_registry.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runtime" / "rag" / "generated")
    args = parser.parse_args()

    source_bytes = args.corpus.read_bytes()
    registry_bytes = args.registry.read_bytes()
    registry = DocumentRegistry.load(args.registry)
    builder = CorpusBuilder(registry)
    chunks, migration = CorpusMetadataMigrator().migrate(RagCorpus(args.corpus).load())
    result = builder.build(chunks, source_bytes=source_bytes, registry_bytes=registry_bytes)
    builder.write(result, args.output_dir)
    print(args.output_dir.resolve())
    print(result.manifest.model_dump(mode="json"))
    print(migration.model_dump(mode="json"))


if __name__ == "__main__":
    main()

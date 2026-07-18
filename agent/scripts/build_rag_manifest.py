from __future__ import annotations

import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.config import Settings
from nexusops_agent.rag.index import IndexManifest
from nexusops_agent.rag.loader import RagCorpus
from nexusops_agent.rag.namespace_router import Namespace, namespace_for


def main() -> None:
    settings = Settings.from_env()
    corpus = RagCorpus(settings.rag_data_path)
    chunks = corpus.load()
    namespace_counts = {namespace.value: 0 for namespace in Namespace}
    for chunk in chunks:
        namespace_counts[namespace_for(chunk).value] += 1
    source_bytes = settings.rag_data_path.read_bytes()
    manifest = IndexManifest(
        version="rag-v1-structural",
        source_file=str(settings.rag_data_path.resolve()),
        source_sha256=hashlib.sha256(source_bytes).hexdigest().upper(),
        total_chunks=len(chunks),
        namespace_counts=namespace_counts,
        searchable_default_chunks=sum(
            chunk.quality.status in {"ACCEPTED", "DEMO_ONLY"} for chunk in chunks
        ),
        quarantined_chunks=sum(chunk.quality.status == "REVIEW_REQUIRED" for chunk in chunks),
        embedding_model="Vietnamese_Embedding",
        reranker_model="bge-reranker-v2-m3",
    )
    output = settings.runtime_dir / "indexes" / "rag-v1-manifest.json"
    manifest.write(output)
    print(output.resolve())
    print(manifest.model_dump() if hasattr(manifest, "model_dump") else manifest.__dict__)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.rag.loader import RagCorpus
from nexusops_agent.rag.quality_gate import LegalCorpusQualityGate
from nexusops_agent.rag.registry import DocumentRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit legal RAG data against the document registry")
    parser.add_argument("--corpus", type=Path, default=ROOT / "final_rag_data_normalized_v1.json")
    parser.add_argument("--registry", type=Path, default=ROOT / "configs" / "rag" / "document_registry.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true", help="exit non-zero when the corpus fails the quality gate")
    args = parser.parse_args()

    registry = DocumentRegistry.load(args.registry)
    report = LegalCorpusQualityGate(registry).audit(RagCorpus(args.corpus).load())
    rendered = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    if args.strict and not report.ready_for_build:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

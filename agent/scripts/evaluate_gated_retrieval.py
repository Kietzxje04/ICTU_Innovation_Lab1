from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.evaluation.retrieval import RetrievalCase, RetrievalEvaluator
from nexusops_agent.rag.loader import RagCorpus
from nexusops_agent.rag.pipeline import RetrievalPipeline
from nexusops_agent.rag.retriever import HybridLiteRetriever


def main() -> None:
    generated = ROOT / "runtime" / "rag" / "generated"
    corpus = RagCorpus.from_generated(generated)
    evaluator = RetrievalEvaluator(RetrievalPipeline(HybridLiteRetriever(corpus)))
    report = evaluator.evaluate([
        RetrievalCase(
            case_id="corporate-overdraft-demo-evidence",
            agent_id="PRODUCT_AGENT",
            query="điều kiện cấp thấu chi doanh nghiệp",
            product="CORPORATE_OVERDRAFT",
            topics={"ELIGIBILITY"},
            expected_chunk_ids=["shb_sme_policy_2026-f5e370ef82792900"],
        ),
        RetrievalCase(
            case_id="working-capital-demo-evidence",
            agent_id="PRODUCT_AGENT",
            query="điều kiện vay vốn lưu động doanh nghiệp",
            product="WORKING_CAPITAL",
            topics={"ELIGIBILITY"},
            expected_chunk_ids=["shb_sme_policy_2026-891a26254a536aff"],
        ),
    ])
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
    if report.passed != report.total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

from __future__ import annotations

from pydantic import BaseModel, Field

from nexusops_agent.rag.pipeline import RetrievalPipeline


class RetrievalCase(BaseModel):
    case_id: str
    agent_id: str
    query: str
    expected_chunk_ids: list[str]
    product: str | None = None
    topics: set[str] = Field(default_factory=set)


class RetrievalEvaluationReport(BaseModel):
    total: int
    passed: int
    recall_at_k: float
    results: list[dict[str, object]]


class RetrievalEvaluator:
    def __init__(self, pipeline: RetrievalPipeline) -> None:
        self.pipeline = pipeline

    def evaluate(self, cases: list[RetrievalCase], *, top_k: int = 5) -> RetrievalEvaluationReport:
        results: list[dict[str, object]] = []
        for case in cases:
            hits = self.pipeline.retrieve(
                agent_id=case.agent_id,
                query=case.query,
                top_k=top_k,
                product=case.product,
                topics=case.topics,
            )
            actual = [hit.chunk.chunk_id for hit in hits]
            passed = any(chunk_id in actual for chunk_id in case.expected_chunk_ids)
            results.append({"case_id": case.case_id, "passed": passed, "actual_chunk_ids": actual})
        passed_count = sum(bool(result["passed"]) for result in results)
        return RetrievalEvaluationReport(
            total=len(cases),
            passed=passed_count,
            recall_at_k=passed_count / len(cases) if cases else 1.0,
            results=results,
        )

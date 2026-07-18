from __future__ import annotations

from nexusops_agent.contracts.evidence import CitationClaim
from nexusops_agent.contracts.state import AgentArtifact, WorkflowState
from nexusops_agent.nodes.readiness_rules import ReadinessRuleEngine
from nexusops_agent.rag.pipeline import RetrievalPipeline

from .base import BaseAgent


def _claims_from_hits(agent_id: str, hits: list[object]) -> list[CitationClaim]:
    claims: list[CitationClaim] = []
    for index, hit in enumerate(hits):
        chunk = hit.chunk
        claims.append(
            CitationClaim(
                claim_id=f"{agent_id}-CLAIM-{index + 1}",
                chunk_id=chunk.chunk_id,
                quote=chunk.content[: min(320, len(chunk.content))],
                claim_type="POLICY_GROUNDING",
            )
        )
    return claims


class ProductAgent(BaseAgent):
    agent_id = "PRODUCT_AGENT"
    engine = "DETERMINISTIC_PLUS_RAG"

    def __init__(self, retrieval: RetrievalPipeline | None = None, demo_mode: bool = True) -> None:
        self.retrieval = retrieval
        self.demo_mode = demo_mode

    def run(self, state: WorkflowState) -> AgentArtifact:
        hits = []
        if self.retrieval is not None:
            query = "điều kiện cấp thấu chi doanh nghiệp" if state.case.product == "CORPORATE_OVERDRAFT" else "điều kiện vay vốn lưu động doanh nghiệp"
            hits = self.retrieval.retrieve(agent_id=self.agent_id, query=query, demo_mode=self.demo_mode)
        warnings = ["NO_PRODUCT_EVIDENCE"] if not hits else []
        if any(hit.chunk.is_synthetic for hit in hits):
            warnings.append("SYNTHETIC_DEMO_POLICY_NOT_OFFICIAL")
        return AgentArtifact(
            agent_id=self.agent_id,
            engine=self.engine,
            status="WARNING" if warnings else "PASS",
            summary=f"Product route: {state.case.product}; evidence={len(hits)}",
            claims=_claims_from_hits(self.agent_id, hits),
            warnings=warnings,
            raw={"evidence_chunk_ids": [hit.chunk.chunk_id for hit in hits]},
        )


class CreditAgent(BaseAgent):
    agent_id = "CREDIT_AGENT"
    engine = "DETERMINISTIC_RULES_WITH_OPTIONAL_REASONER"

    def __init__(self, rule_engine: ReadinessRuleEngine | None = None) -> None:
        self.rule_engine = rule_engine or ReadinessRuleEngine()

    def run(self, state: WorkflowState) -> AgentArtifact:
        assessment = self.rule_engine.assess(state.case)
        status_map = {
            "READY_FOR_HUMAN_REVIEW": "PASS",
            "NEEDS_MORE_EVIDENCE": "REVIEW_REQUIRED",
            "BLOCKED_OUT_OF_SCOPE": "BLOCKED",
        }
        return AgentArtifact(
            agent_id=self.agent_id,
            engine=self.engine,
            status=status_map[assessment.status],
            summary=f"Credit readiness={assessment.status}",
            metrics=assessment.metrics,
            warnings=assessment.warnings + [result.reason_code for result in assessment.rule_results if result.status != "PASS"],
            proposed_actions=["HUMAN_CREDIT_REVIEW"] if assessment.status != "BLOCKED_OUT_OF_SCOPE" else [],
            raw=assessment.model_dump(mode="json"),
        )


class ComplianceAgent(BaseAgent):
    agent_id = "COMPLIANCE_AGENT"
    engine = "RULES_PLUS_AML_RAG"

    def __init__(self, retrieval: RetrievalPipeline | None = None) -> None:
        self.retrieval = retrieval

    def run(self, state: WorkflowState) -> AgentArtifact:
        flags = state.case.kyc_aml_flags
        if not flags:
            return AgentArtifact(
                agent_id=self.agent_id,
                engine=self.engine,
                status="PASS",
                summary="No KYC/AML trigger; compliance retrieval skipped",
                raw={"retrieval_skipped": True},
            )
        hits = []
        if self.retrieval is not None:
            hits = self.retrieval.retrieve(
                agent_id=self.agent_id,
                query=" ".join(flags) + " phòng chống rửa tiền giao dịch đáng ngờ",
                demo_mode=False,
            )
        warnings = list(flags)
        if not hits:
            warnings.append("NO_ACCEPTED_AML_EVIDENCE")
        return AgentArtifact(
            agent_id=self.agent_id,
            engine=self.engine,
            status="REVIEW_REQUIRED",
            summary=f"Compliance trigger requires human review; evidence={len(hits)}",
            claims=_claims_from_hits(self.agent_id, hits),
            warnings=warnings,
            proposed_actions=["CREATE_COMPLIANCE_REVIEW_TASK"],
            raw={"evidence_chunk_ids": [hit.chunk.chunk_id for hit in hits]},
        )

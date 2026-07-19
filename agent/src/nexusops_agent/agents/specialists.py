from __future__ import annotations

from nexusops_agent.contracts.evidence import CitationClaim
from nexusops_agent.contracts.live import LiveAgentNarrative
from nexusops_agent.contracts.state import AgentArtifact, WorkflowState
from nexusops_agent.nodes.readiness_rules import ReadinessRuleEngine
from nexusops_agent.rag.pipeline import RetrievalPipeline
from nexusops_agent.providers.structured import FptStructuredReasoner

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

    def __init__(self, retrieval: RetrievalPipeline | None = None, demo_mode: bool = True, reasoner: FptStructuredReasoner | None = None) -> None:
        self.retrieval = retrieval
        self.demo_mode = demo_mode
        self.reasoner = reasoner

    def run(self, state: WorkflowState) -> AgentArtifact:
        hits = []
        if self.retrieval is not None:
            query = "điều kiện cấp thấu chi doanh nghiệp" if state.case.product == "CORPORATE_OVERDRAFT" else "điều kiện vay vốn lưu động doanh nghiệp"
            hits = self.retrieval.retrieve(
                agent_id=self.agent_id,
                query=query,
                demo_mode=self.demo_mode,
                product=state.case.product.value,
                topics={"ELIGIBILITY", "REQUIRED_DOCUMENTS"},
            )
        warnings = ["NO_PRODUCT_EVIDENCE"] if not hits else []
        if any(hit.chunk.is_synthetic for hit in hits):
            warnings.append("SYNTHETIC_DEMO_POLICY_NOT_OFFICIAL")
        summary = f"Product route: {state.case.product}; evidence={len(hits)}"
        raw = {"evidence_chunk_ids": [hit.chunk.chunk_id for hit in hits]}
        engine = self.engine
        if self.reasoner is not None:
            try:
                invocation = self.reasoner.invoke(
                    "product_agent", "product_agent",
                    {"product": state.case.product.value, "requested_amount": state.case.requested_amount,
                     "relationship_months": state.case.relationship_months, "submitted_documents": state.case.submitted_documents,
                     "required_documents": state.case.required_documents,
                     "evidence": [{"chunk_id": hit.chunk.chunk_id, "content": hit.chunk.content[:900]} for hit in hits],
                     "boundary": "Readiness only; never approve, reject, price or set a limit."},
                    LiveAgentNarrative,
                )
                live = invocation.result
                summary = live.summary
                raw.update({"live_model": invocation.model, "live_reasoning": live.model_dump(mode="json"), "live_usage": invocation.usage})
                engine = "FPT_AI_FACTORY_PLUS_RAG"
            except Exception as exc:
                warnings.append(f"LIVE_AI_UNAVAILABLE:PRODUCT_AGENT:{type(exc).__name__}")
                raw["live_error_type"] = type(exc).__name__
                engine = "DETERMINISTIC_RAG_FALLBACK"
        return AgentArtifact(
            agent_id=self.agent_id,
            engine=engine,
            status="WARNING" if warnings else "PASS",
            summary=summary,
            claims=_claims_from_hits(self.agent_id, hits),
            warnings=warnings,
            raw=raw,
        )


class CreditAgent(BaseAgent):
    agent_id = "CREDIT_AGENT"
    engine = "DETERMINISTIC_RULES_WITH_OPTIONAL_REASONER"

    def __init__(self, rule_engine: ReadinessRuleEngine | None = None, reasoner: FptStructuredReasoner | None = None) -> None:
        self.rule_engine = rule_engine or ReadinessRuleEngine()
        self.reasoner = reasoner

    def run(self, state: WorkflowState) -> AgentArtifact:
        assessment = self.rule_engine.assess(state.case)
        status_map = {
            "READY_FOR_HUMAN_REVIEW": "PASS",
            "NEEDS_MORE_EVIDENCE": "REVIEW_REQUIRED",
            "BLOCKED_OUT_OF_SCOPE": "BLOCKED",
        }
        summary = f"Credit readiness={assessment.status}"
        raw = assessment.model_dump(mode="json")
        engine = self.engine
        warnings = assessment.warnings + [result.reason_code for result in assessment.rule_results if result.status != "PASS"]
        if self.reasoner is not None:
            try:
                invocation = self.reasoner.invoke(
                    "credit_agent", "credit_agent",
                    {"deterministic_assessment": raw,
                     "boundary": "The deterministic status and rule results are authoritative. Explain only; never approve, reject, price or set a limit."},
                    LiveAgentNarrative,
                )
                live = invocation.result
                summary = live.summary
                raw = {**raw, "live_model": invocation.model, "live_reasoning": live.model_dump(mode="json"), "live_usage": invocation.usage}
                engine = "DETERMINISTIC_RULES_PLUS_FPT_AI"
            except Exception as exc:
                warnings.append(f"LIVE_AI_UNAVAILABLE:CREDIT_AGENT:{type(exc).__name__}")
                raw["live_error_type"] = type(exc).__name__
                engine = "DETERMINISTIC_RULES_LIVE_FALLBACK"
        return AgentArtifact(
            agent_id=self.agent_id,
            engine=engine,
            status=status_map[assessment.status],
            summary=summary,
            metrics=assessment.metrics,
            warnings=warnings,
            proposed_actions=["HUMAN_CREDIT_REVIEW"] if assessment.status != "BLOCKED_OUT_OF_SCOPE" else [],
            raw=raw,
        )


class ComplianceAgent(BaseAgent):
    agent_id = "COMPLIANCE_AGENT"
    engine = "RULES_PLUS_AML_RAG"

    def __init__(self, retrieval: RetrievalPipeline | None = None, reasoner: FptStructuredReasoner | None = None) -> None:
        self.retrieval = retrieval
        self.reasoner = reasoner

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
        summary = f"Compliance trigger requires human review; evidence={len(hits)}"
        raw = {"evidence_chunk_ids": [hit.chunk.chunk_id for hit in hits]}
        engine = self.engine
        if self.reasoner is not None:
            try:
                invocation = self.reasoner.invoke(
                    "compliance_agent", "compliance_agent",
                    {"kyc_aml_flags": flags,
                     "evidence": [{"chunk_id": hit.chunk.chunk_id, "content": hit.chunk.content[:900]} for hit in hits],
                     "boundary": "Compliance review only; do not infer credit approval or rejection."},
                    LiveAgentNarrative,
                )
                live = invocation.result
                summary = live.summary
                raw.update({"live_model": invocation.model, "live_reasoning": live.model_dump(mode="json"), "live_usage": invocation.usage})
                engine = "FPT_AI_FACTORY_PLUS_AML_RAG"
            except Exception as exc:
                warnings.append(f"LIVE_AI_UNAVAILABLE:COMPLIANCE_AGENT:{type(exc).__name__}")
                raw["live_error_type"] = type(exc).__name__
                engine = "RULES_PLUS_AML_RAG_LIVE_FALLBACK"
        return AgentArtifact(
            agent_id=self.agent_id,
            engine=engine,
            status="REVIEW_REQUIRED",
            summary=summary,
            claims=_claims_from_hits(self.agent_id, hits),
            warnings=warnings,
            proposed_actions=["CREATE_COMPLIANCE_REVIEW_TASK"],
            raw=raw,
        )

from __future__ import annotations

from typing import Callable

from nexusops_agent.agents.critic import MandatoryCriticAgent
from nexusops_agent.agents.planner import PlannerAgent
from nexusops_agent.agents.specialists import ComplianceAgent, CreditAgent, ProductAgent
from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.state import AgentArtifact, WorkflowState
from nexusops_agent.nodes.deterministic import document_completeness, existing_customer_gate, financial_tax_gap
from nexusops_agent.nodes.readiness_rules import ReadinessRuleEngine, financial_metrics
from nexusops_agent.observability.events import NodeRunEvent
from nexusops_agent.orchestration.router import route_case
from nexusops_agent.rag.citation_validator import CitationValidator
from nexusops_agent.rag.loader import RagCorpus
from nexusops_agent.rag.pipeline import RetrievalPipeline
from nexusops_agent.rag.retriever import HybridLiteRetriever


class AgentWorkflowRunner:
    """Typed sequential baseline with the same node contracts as LangGraph.

    This runner is used by unit tests and as a deterministic fallback when the
    LangGraph optional dependency is unavailable.
    """

    def __init__(
        self,
        *,
        corpus: RagCorpus | None = None,
        retrieval: RetrievalPipeline | None = None,
        rule_engine: ReadinessRuleEngine | None = None,
    ) -> None:
        self.corpus = corpus or RagCorpus()
        self.retrieval = retrieval or RetrievalPipeline(HybridLiteRetriever(self.corpus))
        self.rule_engine = rule_engine or ReadinessRuleEngine()
        self.citation_validator = CitationValidator(self.corpus.by_id())
        self.product_agent = ProductAgent(self.retrieval, demo_mode=True)
        self.credit_agent = CreditAgent(self.rule_engine)
        self.compliance_agent = ComplianceAgent(self.retrieval)
        self.critic_agent = MandatoryCriticAgent()

    @staticmethod
    def _record(state: WorkflowState, node_id: str, status: str, artifact: AgentArtifact | None = None) -> None:
        event = NodeRunEvent(
            case_id=state.case.case_id,
            node_id=node_id,
            status=status,
            engine=artifact.engine if artifact else "DETERMINISTIC",
            output_summary={
                "artifact_status": artifact.status,
                "summary": artifact.summary,
            } if artifact else {},
        )
        state.trace.append(event.model_dump(mode="json"))

    @staticmethod
    def _simple_artifact(node_id: str, status: str, summary: str, **raw: object) -> AgentArtifact:
        return AgentArtifact(
            agent_id=node_id,
            engine="DETERMINISTIC",
            status=status,
            summary=summary,
            raw=raw,
        )

    def execute_node(self, state: WorkflowState, node_id: str) -> AgentArtifact:
        handlers: dict[str, Callable[[], AgentArtifact]] = {
            "EXISTING_CUSTOMER_GATE": lambda: self._existing_customer(state),
            "PRODUCT_AGENT": lambda: self.product_agent.run(state),
            "DOCUMENT_COMPLETENESS": lambda: self._completeness(state),
            "ACCOUNT_TURNOVER": lambda: self._account_turnover(state),
            "FINANCIAL_METRICS": lambda: self._financial_metrics(state),
            "TAX_CONSISTENCY": lambda: self._tax_consistency(state),
            "CREDIT_AGENT": lambda: self.credit_agent.run(state),
            "COMPLIANCE_AGENT": lambda: self.compliance_agent.run(state),
            "READINESS_RULE_ENGINE": lambda: self._readiness_result(state),
            "MANDATORY_CRITIC": lambda: self.critic_agent.run(state),
            "CITATION_VALIDATOR": lambda: self._validate_citations(state),
            "POLICY_GATE": lambda: self._policy_gate(state),
        }
        if node_id not in handlers:
            raise KeyError(f"No workflow node handler: {node_id}")
        self._record(state, node_id, "RUNNING")
        try:
            artifact = handlers[node_id]()
            state.artifacts[node_id] = artifact
            self._record(state, node_id, "SUCCEEDED", artifact)
            return artifact
        except Exception:
            self._record(state, node_id, "FAILED")
            raise

    def run(self, case: CaseContext) -> WorkflowState:
        state = WorkflowState(case=case)
        planner = PlannerAgent().run(state)
        state.artifacts[planner.agent_id] = planner
        self._record(state, planner.agent_id, "SUCCEEDED", planner)
        route = route_case(case)
        state.route = route.nodes
        for node_id in route.nodes:
            self.execute_node(state, node_id)
        self._finalize(state)
        return state

    def _existing_customer(self, state: WorkflowState) -> AgentArtifact:
        passed, reason = existing_customer_gate(state.case)
        return self._simple_artifact(
            "EXISTING_CUSTOMER_GATE",
            "PASS" if passed else "BLOCKED",
            reason,
            passed=passed,
        )

    def _completeness(self, state: WorkflowState) -> AgentArtifact:
        assessment = self.rule_engine.assess(state.case)
        return self._simple_artifact(
            "DOCUMENT_COMPLETENESS",
            "PASS" if not assessment.missing_documents else "REVIEW_REQUIRED",
            f"missing={len(assessment.missing_documents)}",
            missing_documents=assessment.missing_documents,
        )

    def _account_turnover(self, state: WorkflowState) -> AgentArtifact:
        value = state.case.twelve_month_account_turnover
        return self._simple_artifact(
            "ACCOUNT_TURNOVER",
            "PASS" if value is not None else "REVIEW_REQUIRED",
            "Account turnover loaded" if value is not None else "Account turnover missing",
            twelve_month_account_turnover=value,
        )

    def _financial_metrics(self, state: WorkflowState) -> AgentArtifact:
        metrics = financial_metrics(state.case)
        return AgentArtifact(
            agent_id="FINANCIAL_METRICS",
            engine="DETERMINISTIC",
            status="PASS" if metrics else "REVIEW_REQUIRED",
            summary=f"Calculated {len(metrics)} financial metrics",
            metrics=metrics,
        )

    def _tax_consistency(self, state: WorkflowState) -> AgentArtifact:
        gap = financial_tax_gap(state.case)
        status = "REVIEW_REQUIRED" if gap is None or gap > 0.10 else "PASS"
        return AgentArtifact(
            agent_id="TAX_CONSISTENCY",
            engine="DETERMINISTIC",
            status=status,
            summary="Tax gap unavailable" if gap is None else f"tax_revenue_gap={gap:.4f}",
            metrics={"tax_revenue_gap": gap} if gap is not None else {},
            warnings=["FINANCIAL_TAX_MISMATCH"] if gap is not None and gap > 0.10 else [],
        )

    def _readiness_result(self, state: WorkflowState) -> AgentArtifact:
        credit = state.artifacts.get("CREDIT_AGENT")
        return self._simple_artifact(
            "READINESS_RULE_ENGINE",
            credit.status if credit else "REVIEW_REQUIRED",
            credit.summary if credit else "Credit artifact missing",
        )

    def _validate_citations(self, state: WorkflowState) -> AgentArtifact:
        statuses: list[str] = []
        for artifact in state.artifacts.values():
            for claim in artifact.claims:
                result = self.citation_validator.validate(claim)
                state.citation_results[claim.claim_id] = result
                statuses.append(result.status)
        invalid = {"REVIEW_REQUIRED", "STALE_OR_UNVERIFIED", "INVALID_QUOTE", "INVALID_HASH", "INVALID_AUTHORITY", "ABSTAIN_NO_EVIDENCE"}
        has_invalid = any(status in invalid for status in statuses)
        return self._simple_artifact(
            "CITATION_VALIDATOR",
            "REVIEW_REQUIRED" if has_invalid else "PASS",
            f"validated={len(statuses)}",
            statuses=statuses,
        )

    def _policy_gate(self, state: WorkflowState) -> AgentArtifact:
        return self._simple_artifact(
            "POLICY_GATE",
            "PASS",
            "No external write executed; human authority retained",
            external_write_allowed=False,
        )

    @staticmethod
    def _finalize(state: WorkflowState) -> None:
        if state.artifacts.get("EXISTING_CUSTOMER_GATE", AgentArtifact(agent_id="x", engine="x", status="BLOCKED", summary="x")).status == "BLOCKED":
            state.final_status = "BLOCKED"
            return
        unresolved = any(
            artifact.status in {"BLOCKED", "REVIEW_REQUIRED"}
            for name, artifact in state.artifacts.items()
            if name not in {"POLICY_GATE"}
        )
        state.final_status = "NEEDS_MORE_EVIDENCE" if unresolved or state.critic_verdict != "PASS" else "READY_FOR_HUMAN_REVIEW"

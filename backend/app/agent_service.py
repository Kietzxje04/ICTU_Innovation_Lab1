from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nexusops_agent.agents import ComplianceAgent, CreditAgent, MandatoryCriticAgent, PlannerAgent, ProductAgent
from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.evidence import CitationClaim
from nexusops_agent.contracts.state import AgentArtifact, WorkflowState
from nexusops_agent.nodes.deterministic import document_completeness, financial_tax_gap
from nexusops_agent.observability.events import NodeRunEvent
from nexusops_agent.rag import CitationValidator, HybridLiteRetriever, RagCorpus
from nexusops_agent.rag.namespace_router import Namespace
from nexusops_agent.tools.mock_banking import get_account_turnover


class AgentService:
    """Backend adapter around the read-only NexusOps Agent Layer."""

    def __init__(self, corpus: RagCorpus | None = None) -> None:
        self.corpus = corpus or RagCorpus()
        self.retriever = HybridLiteRetriever(self.corpus)
        self.validator = CitationValidator(self.corpus.by_id())
        self._agents: dict[str, Callable[[WorkflowState], AgentArtifact]] = {
            "PRODUCT_AGENT": ProductAgent().run,
            "CREDIT_AGENT": CreditAgent().run,
            "COMPLIANCE_AGENT": ComplianceAgent().run,
            "MANDATORY_CRITIC": MandatoryCriticAgent().run,
        }

    def health(self) -> dict[str, Any]:
        inventory = self.corpus.inventory()
        return {
            "status": "ok",
            "package": "nexusops-agent",
            "mode": "deterministic",
            "rag_records": inventory["total"],
        }

    def rag_inventory(self) -> dict[str, object]:
        return self.corpus.inventory()

    def run(self, case: CaseContext) -> WorkflowState:
        state = WorkflowState(case=case)
        planner = PlannerAgent().run(state)
        state.artifacts[planner.agent_id] = planner
        self._trace(state, planner.agent_id, planner)

        for node_id in state.route:
            try:
                artifact = self._run_node(node_id, state)
                state.artifacts[node_id] = artifact
                self._trace(state, node_id, artifact)
            except Exception as exc:
                event = NodeRunEvent(
                    case_id=case.case_id,
                    node_id=node_id,
                    status="FAILED",
                    engine="BACKEND_AGENT_ADAPTER",
                    output_summary={"error": type(exc).__name__, "message": str(exc)},
                )
                state.trace.append(event.model_dump(mode="json"))
                raise
        return state

    def _run_node(self, node_id: str, state: WorkflowState) -> AgentArtifact:
        if node_id in self._agents:
            return self._agents[node_id](state)
        handlers: dict[str, Callable[[WorkflowState], AgentArtifact]] = {
            "EXISTING_CUSTOMER_GATE": self._existing_customer_gate,
            "DOCUMENT_COMPLETENESS": self._document_completeness,
            "ACCOUNT_TURNOVER": self._account_turnover,
            "FINANCIAL_METRICS": self._financial_metrics,
            "TAX_CONSISTENCY": self._tax_consistency,
            "READINESS_RULE_ENGINE": self._readiness_rule_engine,
            "CITATION_VALIDATOR": self._citation_validation,
            "POLICY_GATE": self._policy_gate,
        }
        try:
            return handlers[node_id](state)
        except KeyError as exc:
            raise ValueError(f"Unsupported routed node: {node_id}") from exc

    @staticmethod
    def _trace(state: WorkflowState, node_id: str, artifact: AgentArtifact) -> None:
        event = NodeRunEvent(
            case_id=state.case.case_id,
            node_id=node_id,
            status="SUCCEEDED",
            engine=artifact.engine,
            output_summary={"artifact_status": artifact.status, "warnings": artifact.warnings},
        )
        state.trace.append(event.model_dump(mode="json"))

    @staticmethod
    def _existing_customer_gate(state: WorkflowState) -> AgentArtifact:
        allowed = state.case.existing_customer
        return AgentArtifact(
            agent_id="EXISTING_CUSTOMER_GATE",
            engine="DETERMINISTIC",
            status="PASS" if allowed else "BLOCKED",
            summary="Existing customer eligibility evaluated",
            warnings=[] if allowed else ["NEW_TO_BANK_OUT_OF_SCOPE"],
        )

    @staticmethod
    def _document_completeness(state: WorkflowState) -> AgentArtifact:
        result = document_completeness(state.case)
        missing = list(result["missing"])
        return AgentArtifact(
            agent_id="DOCUMENT_COMPLETENESS",
            engine="DETERMINISTIC",
            status="PASS" if result["complete"] else "REVIEW_REQUIRED",
            summary=f"Document completeness={result['ratio']}",
            metrics={"completeness_ratio": float(result["ratio"])},
            warnings=[f"MISSING_DOCUMENT:{name}" for name in missing],
            proposed_actions=["REQUEST_MISSING_DOCUMENTS"] if missing else [],
            raw=result,
        )

    @staticmethod
    def _account_turnover(state: WorkflowState) -> AgentArtifact:
        snapshot = get_account_turnover(state.case.customer_id)
        turnover = float(snapshot["twelve_month_turnover"])
        return AgentArtifact(
            agent_id="ACCOUNT_TURNOVER",
            engine="DETERMINISTIC_TOOL",
            status="PASS",
            summary="Account turnover loaded from allowlisted mock tool",
            metrics={"twelve_month_turnover": turnover},
            raw=snapshot,
        )

    @staticmethod
    def _financial_metrics(state: WorkflowState) -> AgentArtifact:
        case = state.case
        profits = case.pretax_profit_last_2_years
        average_profit = sum(profits) / len(profits) if profits else 0.0
        requested_to_revenue = case.requested_amount / case.annual_revenue if case.annual_revenue else 0.0
        warnings: list[str] = []
        if not case.annual_revenue:
            warnings.append("ANNUAL_REVENUE_MISSING")
        if not profits:
            warnings.append("PRETAX_PROFIT_HISTORY_MISSING")
        return AgentArtifact(
            agent_id="FINANCIAL_METRICS",
            engine="DETERMINISTIC",
            status="REVIEW_REQUIRED" if warnings else "PASS",
            summary="Financial readiness metrics calculated by code",
            metrics={
                "annual_revenue": float(case.annual_revenue or 0),
                "average_pretax_profit": float(average_profit),
                "requested_to_revenue": round(float(requested_to_revenue), 6),
            },
            warnings=warnings,
        )

    @staticmethod
    def _tax_consistency(state: WorkflowState) -> AgentArtifact:
        gap = financial_tax_gap(state.case)
        material = gap is not None and gap > 0.10
        warnings = ["FINANCIAL_TAX_MISMATCH"] if material else []
        if gap is None:
            warnings.append("TAX_COMPARISON_DATA_MISSING")
        return AgentArtifact(
            agent_id="TAX_CONSISTENCY",
            engine="DETERMINISTIC",
            status="REVIEW_REQUIRED" if warnings else "PASS",
            summary="Financial and tax revenue reconciled by code",
            metrics={} if gap is None else {"revenue_tax_gap": round(gap, 6)},
            warnings=warnings,
            proposed_actions=["CREATE_TAX_RECONCILIATION_TASK"] if material else [],
        )

    @staticmethod
    def _readiness_rule_engine(state: WorkflowState) -> AgentArtifact:
        warnings: list[str] = []
        actions: list[str] = []
        if state.case.cic_bad_debt:
            warnings.append("CIC_BAD_DEBT")
            actions.append("CREATE_CREDIT_REVIEW_TASK")
        if state.case.kyc_aml_flags:
            warnings.extend(state.case.kyc_aml_flags)
            actions.append("CREATE_COMPLIANCE_REVIEW_TASK")
        for artifact in state.artifacts.values():
            warnings.extend(artifact.warnings)
            actions.extend(artifact.proposed_actions)
        status = "BLOCKED" if not state.case.existing_customer else "REVIEW_REQUIRED" if warnings else "PASS"
        return AgentArtifact(
            agent_id="READINESS_RULE_ENGINE",
            engine="DETERMINISTIC",
            status=status,
            summary="Readiness outcome assembled from typed artifacts",
            warnings=list(dict.fromkeys(warnings)),
            proposed_actions=list(dict.fromkeys(actions)),
        )

    def _citation_validation(self, state: WorkflowState) -> AgentArtifact:
        query = "điều kiện cho vay vốn lưu động doanh nghiệp hồ sơ tín dụng"
        namespaces = {Namespace.LEGAL_LENDING, Namespace.DEMO_INTERNAL_POLICY}
        if state.case.kyc_aml_flags:
            query += " phòng chống rửa tiền nhận biết khách hàng"
            namespaces.add(Namespace.LEGAL_AML)
        hits = self.retriever.search(query, namespaces, top_k=4)
        claims: list[CitationClaim] = []
        warnings: list[str] = []
        for index, hit in enumerate(hits, start=1):
            quote = hit.chunk.content[: min(240, len(hit.chunk.content))]
            claim = CitationClaim(
                claim_id=f"{state.case.case_id}-claim-{index}",
                chunk_id=hit.chunk.chunk_id,
                quote=quote,
                claim_type="SUPPORTING_EVIDENCE",
            )
            claims.append(claim)
            result = self.validator.validate(claim)
            state.citation_results[claim.claim_id] = result
            if result.status not in {"VALID", "WARNING_DEMO_ONLY"}:
                warnings.append(f"{claim.chunk_id}:{result.status}")
        if not claims:
            warnings.append("ABSTAIN_NO_EVIDENCE")
        return AgentArtifact(
            agent_id="CITATION_VALIDATOR",
            engine="DETERMINISTIC_RAG",
            status="PASS" if claims and not warnings else "REVIEW_REQUIRED",
            summary=f"Validated {len(claims)} evidence claims",
            claims=claims,
            warnings=warnings,
            raw={"retrieved": len(hits), "namespaces": sorted(item.value for item in namespaces)},
        )

    @staticmethod
    def _policy_gate(state: WorkflowState) -> AgentArtifact:
        citation = state.artifacts.get("CITATION_VALIDATOR")
        if not state.case.existing_customer or state.case.cic_bad_debt:
            final_status = "BLOCKED"
        elif state.critic_verdict != "PASS" or citation is None or citation.status != "PASS":
            final_status = "NEEDS_MORE_EVIDENCE"
        else:
            final_status = "READY_FOR_HUMAN_REVIEW"
        state.final_status = final_status
        return AgentArtifact(
            agent_id="POLICY_GATE",
            engine="DETERMINISTIC",
            status="BLOCKED" if final_status == "BLOCKED" else "REVIEW_REQUIRED" if final_status == "NEEDS_MORE_EVIDENCE" else "PASS",
            summary=f"Policy gate final status={final_status}",
            warnings=[] if final_status == "READY_FOR_HUMAN_REVIEW" else [final_status],
        )

from __future__ import annotations

from nexusops_agent.contracts.state import AgentArtifact, WorkflowState

from .base import BaseAgent


class ProductAgent(BaseAgent):
    agent_id = "PRODUCT_AGENT"
    engine = "LOCAL_LLM_OR_DETERMINISTIC"

    def run(self, state: WorkflowState) -> AgentArtifact:
        return AgentArtifact(agent_id=self.agent_id, engine=self.engine, status="PASS", summary=f"Selected product: {state.case.product}")


class CreditAgent(BaseAgent):
    agent_id = "CREDIT_AGENT"
    engine = "DETERMINISTIC_PLUS_CLOUD_REASONING"

    def run(self, state: WorkflowState) -> AgentArtifact:
        return AgentArtifact(agent_id=self.agent_id, engine=self.engine, status="REVIEW_REQUIRED", summary="Credit readiness requires deterministic metrics and human review")


class ComplianceAgent(BaseAgent):
    agent_id = "COMPLIANCE_AGENT"
    engine = "RULES_PLUS_RAG"

    def run(self, state: WorkflowState) -> AgentArtifact:
        flags = state.case.kyc_aml_flags
        return AgentArtifact(
            agent_id=self.agent_id,
            engine=self.engine,
            status="REVIEW_REQUIRED" if flags else "PASS",
            summary="Compliance route evaluated",
            warnings=flags,
        )

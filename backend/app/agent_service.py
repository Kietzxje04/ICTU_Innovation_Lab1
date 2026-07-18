from __future__ import annotations

from typing import Any

from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.hitl import AgentResolutionPackage
from nexusops_agent.contracts.state import WorkflowState
from nexusops_agent.services import AgentService as NexusAgentService


class AgentService:
    """Backend adapter for the pulled ``nexusops-agent`` package.

    The backend never calls individual providers or banking systems.  It owns
    persistence and API projection, while the agent package owns routing,
    deterministic nodes, evidence validation, Critic and bounded rework.
    ``run`` returns the typed WorkflowState because the backend must persist
    node artifacts/events for the frontend workbench.
    """

    def __init__(self) -> None:
        self.runtime = NexusAgentService()
        self.corpus = self.runtime.runner.corpus

    def health(self) -> dict[str, Any]:
        inventory = self.corpus.inventory()
        return {
            "status": "ok",
            "package": "nexusops-agent",
            "mode": "live" if self.runtime.runner.settings.live_ai_enabled else "deterministic",
            "runtime": "AgentWorkflowRunner",
            "provider": "FPT_AI_FACTORY" if self.runtime.runner.settings.live_ai_enabled else None,
            "api_key_configured": bool(self.runtime.runner.settings.fpt_ai_api_key),
            "demo_mode": self.runtime.runner.settings.demo_mode,
            "rag_records": inventory["total"],
            "workflow_support": ["CORPORATE_OVERDRAFT", "WORKING_CAPITAL"],
            "external_write_executed": False,
        }

    def rag_inventory(self) -> dict[str, object]:
        return self.corpus.inventory()

    def run(self, case: CaseContext) -> WorkflowState:
        state = self.runtime.runner.run(case)
        if state.critic_verdict == "REVISE":
            self.runtime.rework.apply_once(
                state,
                lambda: self.runtime.runner.execute_node(state, "MANDATORY_CRITIC"),
            )
            self.runtime.runner._finalize(state)
        return state

    def start(self, case: CaseContext) -> WorkflowState:
        return self.runtime.runner.start(case)

    def run_node(self, state: WorkflowState, node_id: str) -> WorkflowState:
        self.runtime.runner.execute_node(state, node_id)
        return state

    def finish(self, state: WorkflowState) -> WorkflowState:
        if state.critic_verdict == "REVISE":
            self.runtime.rework.apply_once(
                state,
                lambda: self.runtime.runner.execute_node(state, "MANDATORY_CRITIC"),
            )
        self.runtime.runner._finalize(state)
        return state

    def run_case(self, case: CaseContext) -> AgentResolutionPackage:
        return self.runtime.run_case(case)

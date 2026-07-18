from nexusops_agent.contracts.state import AgentArtifact, WorkflowState

from .base import BaseAgent


class MandatoryCriticAgent(BaseAgent):
    agent_id = "MANDATORY_CRITIC"
    engine = "CLOUD_LLM_STRUCTURED"

    def run(self, state: WorkflowState) -> AgentArtifact:
        unresolved = [name for name, artifact in state.artifacts.items() if artifact.status in {"BLOCKED", "REVIEW_REQUIRED"}]
        verdict = "REVISE" if unresolved else "PASS"
        state.critic_verdict = verdict
        return AgentArtifact(
            agent_id=self.agent_id,
            engine=self.engine,
            status="REVIEW_REQUIRED" if unresolved else "PASS",
            summary=f"Critic verdict={verdict}",
            warnings=[f"UNRESOLVED:{name}" for name in unresolved],
        )

from nexusops_agent.contracts.state import AgentArtifact, WorkflowState
from nexusops_agent.orchestration.router import route_case

from .base import BaseAgent


class PlannerAgent(BaseAgent):
    agent_id = "PLANNER_AGENT"
    engine = "DETERMINISTIC"

    def run(self, state: WorkflowState) -> AgentArtifact:
        decision = route_case(state.case)
        state.route = decision.nodes
        return AgentArtifact(
            agent_id=self.agent_id,
            engine=self.engine,
            status="WARNING" if decision.hardness else "PASS",
            summary=f"Routed {len(decision.nodes)} nodes; hardness={decision.hardness}",
            warnings=decision.reasons,
            raw=decision.model_dump(),
        )

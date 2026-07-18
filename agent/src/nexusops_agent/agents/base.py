from __future__ import annotations

from abc import ABC, abstractmethod

from nexusops_agent.contracts.state import AgentArtifact, WorkflowState


class BaseAgent(ABC):
    agent_id: str
    engine: str

    @abstractmethod
    def run(self, state: WorkflowState) -> AgentArtifact:
        """Return a typed artifact; never mutate operational systems directly."""
        raise NotImplementedError

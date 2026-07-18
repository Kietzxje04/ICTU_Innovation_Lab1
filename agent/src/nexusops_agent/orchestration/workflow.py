from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


MANDATORY_NODES = {"MANDATORY_CRITIC", "CITATION_VALIDATOR", "READINESS_RULE_ENGINE", "POLICY_GATE"}
MANDATORY_TAIL = ["MANDATORY_CRITIC", "CITATION_VALIDATOR", "READINESS_RULE_ENGINE", "POLICY_GATE"]


class WorkflowDefinition(BaseModel):
    workflow_id: str
    version: str
    product: str
    nodes: list[str] = Field(min_length=1)
    max_rework: int = Field(default=1, ge=0, le=1)

    def validate_safety(self) -> None:
        missing = MANDATORY_NODES - set(self.nodes)
        if missing:
            raise ValueError(f"Workflow missing mandatory nodes: {sorted(missing)}")
        if self.nodes[-4:] != MANDATORY_TAIL:
            raise ValueError(f"Workflow must end with {MANDATORY_TAIL}")


def load_workflow(path: Path) -> WorkflowDefinition:
    workflow = WorkflowDefinition.model_validate(json.loads(path.read_text(encoding="utf-8")))
    workflow.validate_safety()
    return workflow

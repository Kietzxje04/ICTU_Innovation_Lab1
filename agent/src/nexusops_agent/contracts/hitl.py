from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CriticFinding(BaseModel):
    finding_id: str
    finding_type: Literal[
        "UNSUPPORTED_CLAIM",
        "UNRESOLVED_ARTIFACT",
        "INVALID_CITATION",
        "UNSAFE_ACTION",
        "OUT_OF_SCOPE",
    ]
    target_id: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    reason: str
    required_action: str


class HumanReviewTask(BaseModel):
    task_type: Literal["CREDIT_REVIEW", "COMPLIANCE_REVIEW", "DATA_REVIEW", "OUT_OF_SCOPE_REVIEW"]
    case_id: str
    priority: Literal["NORMAL", "HIGH", "CRITICAL"] = "NORMAL"
    reason_codes: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class ProposedAction(BaseModel):
    action_type: str
    payload: dict[str, Any]
    risk: Literal["LOW", "MEDIUM", "HIGH"]
    requires_human_approval: bool = True


class AgentResolutionPackage(BaseModel):
    case_id: str
    final_status: str
    critic_verdict: str
    route: list[str]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    human_tasks: list[HumanReviewTask] = Field(default_factory=list)
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    external_write_executed: bool = False
    trace: list[dict[str, Any]] = Field(default_factory=list)

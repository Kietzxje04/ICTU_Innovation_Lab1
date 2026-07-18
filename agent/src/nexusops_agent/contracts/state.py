from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .case import CaseContext
from .evidence import CitationClaim, ValidationResult


class AgentArtifact(BaseModel):
    agent_id: str
    engine: str
    status: Literal["PASS", "WARNING", "BLOCKED", "REVIEW_REQUIRED"]
    summary: str
    claims: list[CitationClaim] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    proposed_actions: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class WorkflowState(BaseModel):
    case: CaseContext
    route: list[str] = Field(default_factory=list)
    artifacts: dict[str, AgentArtifact] = Field(default_factory=dict)
    citation_results: dict[str, ValidationResult] = Field(default_factory=dict)
    critic_verdict: Literal["PENDING", "PASS", "REVISE", "ESCALATE"] = "PENDING"
    final_status: Literal["IN_PROGRESS", "READY_FOR_HUMAN_REVIEW", "NEEDS_MORE_EVIDENCE", "BLOCKED"] = "IN_PROGRESS"
    trace: list[dict[str, Any]] = Field(default_factory=list)

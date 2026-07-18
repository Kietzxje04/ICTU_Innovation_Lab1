from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RuleResult(BaseModel):
    rule_id: str
    status: Literal["PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"]
    actual: Any = None
    expected: str
    reason_code: str
    source: Literal["DETERMINISTIC", "SYNTHETIC_DEMO_POLICY"] = "DETERMINISTIC"


class ReadinessAssessment(BaseModel):
    product: str
    status: Literal["READY_FOR_HUMAN_REVIEW", "NEEDS_MORE_EVIDENCE", "BLOCKED_OUT_OF_SCOPE"]
    rule_results: list[RuleResult] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    missing_documents: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

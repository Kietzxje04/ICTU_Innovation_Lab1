from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiError(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiResponse(BaseModel):
    data: Any = None
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


AgentState = Literal["done", "running", "required", "optional"]
CompanyStatus = Literal["Đã xác minh", "Đang chờ rà soát", "Từ chối", "Chấp nhận"]
RiskLevel = Literal["Thấp", "Trung bình", "Cao"]


class AgentView(BaseModel):
    name: str
    state: AgentState
    confidence: int = Field(ge=0, le=100)
    result: str


class Company(BaseModel):
    """Compatibility projection consumed by the current React frontend."""

    model_config = ConfigDict(extra="forbid")

    id: str
    code: str
    name: str
    shortName: str
    owner: str
    amount: str
    purpose: str
    sla: str
    submitted: str
    agent: str
    score: int
    status: CompanyStatus
    risk: RiskLevel
    issue: str
    recommendation: str
    consensus: list[str]
    objections: list[str]
    agents: list[AgentView]


class AssessmentRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    case_id: str
    input_hash: str
    workflow_id: str
    workflow_version: str
    status: str
    route: list[str]
    critic_verdict: str
    final_status: str
    error_code: str | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


class ProposedAction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    run_id: str
    type: str
    payload: dict[str, Any]
    payload_hash: str
    status: Literal["PENDING_APPROVAL", "APPROVED", "REJECTED", "SUCCEEDED"]
    created_by: str
    approved_by: str | None = None
    decided_at: datetime | None = None


class ApprovalRequest(BaseModel):
    approved_payload_hash: str
    reason: str | None = None


class RejectionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class LoginRequest(BaseModel):
    username: str
    password: str


class TransferRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    target_user_id: str | None = None


class LoanApprovalRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class ExecutionRecord(BaseModel):
    action_id: str
    external_ref: str | None
    status: Literal["NOT_STARTED", "SUCCEEDED"]
    idempotency_key: str | None
    executed_at: datetime | None


class ResolutionPackage(BaseModel):
    case: Company
    run: AssessmentRun
    primary_outcome: str
    blockers: list[str]
    routes: list[str]
    reason_codes: list[str]
    eligible_actions: list[str]
    proposed_action: ProposedAction

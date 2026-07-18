from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


AgentState = Literal["done", "running", "required", "optional"]
CompanyStatus = Literal["Đã xác minh", "Đang chờ rà soát", "Từ chối", "Chấp nhận"]
RiskLevel = Literal["Thấp", "Trung bình", "Cao"]


class Agent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    state: AgentState
    confidence: int
    result: str


class Company(BaseModel):
    """API contract intentionally mirrors frontend/src/data.ts."""

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
    agents: list[Agent]


class ApiResponse(BaseModel):
    data: object
    meta: dict[str, object] | None = None


ActionStatus = Literal["PENDING_APPROVAL", "APPROVED", "REJECTED", "SUCCEEDED"]


class ProposedAction(BaseModel):
    id: str
    case_id: str
    type: str
    payload: dict[str, object]
    payload_hash: str
    status: ActionStatus
    created_by: str
    approved_by: str | None = None
    decided_at: datetime | None = None


class ApprovalRequest(BaseModel):
    approved_payload_hash: str
    reason: str | None = None


class RejectionRequest(BaseModel):
    reason: str


class ExecutionRecord(BaseModel):
    action_id: str
    external_ref: str | None
    status: Literal["NOT_STARTED", "SUCCEEDED"]
    idempotency_key: str | None
    executed_at: datetime | None


class ResolutionPackage(BaseModel):
    case: Company
    primary_outcome: str
    blockers: list[str]
    routes: list[str]
    reason_codes: list[str]
    eligible_actions: list[str]
    proposed_action: ProposedAction

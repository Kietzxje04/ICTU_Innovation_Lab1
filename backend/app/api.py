from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from nexusops_agent.contracts.state import WorkflowState

from .agent_service import AgentService
from .config import get_settings
from .database import engine, get_session
from .dependencies import get_action_service, get_agent_service, get_assessment_service, get_resolution_service
from .exceptions import DomainError
from .repositories import AssessmentRepository, CaseRepository, run_schema
from .schemas import ApiResponse, ApprovalRequest, RejectionRequest, LoginRequest, LoanApprovalRequest, TransferRequest
from .services import ActionService, AssessmentService, ResolutionService, company_projection
from .readiness_schemas import CreateReadinessCase
from .readiness_service import ReadinessService
from .dependencies import get_readiness_service
from .auth import CurrentUser, create_session, current_user, verify_password
from .approval_service import LoanApprovalService
from .models import RoleRecord, UserRecord


router = APIRouter()


class WorkflowStepRequest(BaseModel):
    state: WorkflowState


def response(request: Request, data: object, **meta: object) -> ApiResponse:
    return ApiResponse(
        data=data,
        meta={"request_id": getattr(request.state, "request_id", "unknown"), "api": "single-backend", **meta},
    )


@router.post("/api/auth/login", response_model=ApiResponse)
def login(request: Request, body: LoginRequest, session: Session = Depends(get_session)) -> ApiResponse:
    user = session.scalar(select(UserRecord).where(UserRecord.username == body.username))
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise DomainError(401, "INVALID_CREDENTIALS", "Tên đăng nhập hoặc mật khẩu không đúng")
    role = session.get(RoleRecord, user.role_id)
    token, expires = create_session(session, user)
    return response(request, {"access_token": token, "token_type": "bearer", "expires_at": expires.isoformat(), "user": {"user_id": user.user_id, "username": user.username, "full_name": user.full_name, "email": user.email, "role_id": user.role_id, "role_name": role.name if role else user.role_id, "approval_limit": role.approval_limit if role else None, "permissions": role.permissions if role else []}})


@router.get("/api/auth/me", response_model=ApiResponse)
def me(request: Request, user: CurrentUser = Depends(current_user)) -> ApiResponse:
    return response(request, {"user_id": user.record.user_id, "username": user.record.username, "full_name": user.record.full_name, "email": user.record.email, "role_id": user.role.role_id, "role_name": user.role.name, "approval_limit": user.role.approval_limit, "permissions": user.role.permissions})


@router.get("/api/cases/{case_id}/loan-approval", response_model=ApiResponse)
def check_loan_approval(request: Request, case_id: str, user: CurrentUser = Depends(current_user), session: Session = Depends(get_session)) -> ApiResponse:
    return response(request, LoanApprovalService(session).check(case_id, user))


@router.post("/api/cases/{case_id}/loan-approval/approve", response_model=ApiResponse)
def approve_loan(request: Request, case_id: str, body: LoanApprovalRequest, user: CurrentUser = Depends(current_user), session: Session = Depends(get_session)) -> ApiResponse:
    return response(request, LoanApprovalService(session).approve(case_id, user, body.reason))


@router.post("/api/cases/{case_id}/loan-approval/transfer", response_model=ApiResponse)
def transfer_loan(request: Request, case_id: str, body: TransferRequest, user: CurrentUser = Depends(current_user), session: Session = Depends(get_session)) -> ApiResponse:
    return response(request, LoanApprovalService(session).transfer(case_id, user, body.reason, body.target_user_id))


@router.get("/health", response_model=ApiResponse)
def health(request: Request, agent: AgentService = Depends(get_agent_service)) -> ApiResponse:
    settings = get_settings()
    return response(
        request,
        {
            "status": "ok",
            "service": "nexusops-backend",
            "database": {
                "dialect": engine.dialect.name,
                "seed_demo_data": settings.seed_demo_data,
            },
            "agent": agent.health(),
        },
    )


@router.get("/api/agent/health", response_model=ApiResponse)
def agent_health(request: Request, agent: AgentService = Depends(get_agent_service)) -> ApiResponse:
    return response(request, agent.health())


@router.get("/api/agent/rag/inventory", response_model=ApiResponse)
def rag_inventory(request: Request, agent: AgentService = Depends(get_agent_service)) -> ApiResponse:
    return response(request, agent.rag_inventory())


@router.get("/api/cases", response_model=ApiResponse)
def list_cases(
    request: Request,
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> ApiResponse:
    records = CaseRepository(session).list(q, status)
    runs = AssessmentRepository(session)
    items = []
    for record in records:
        latest = runs.latest(record.case_id)
        loaded = runs.get(latest.run_id) if latest else None
        items.append(company_projection(record, loaded).model_dump())
    return response(request, items, total=len(records))


@router.get("/api/readiness/cases", response_model=ApiResponse)
def list_readiness_cases(
    request: Request,
    q: str | None = Query(default=None),
    product: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    readiness: ReadinessService = Depends(get_readiness_service),
) -> ApiResponse:
    items, total = readiness.list_page(q=q, product=product, status=status, limit=limit, offset=offset)
    return response(request, [item.model_dump(mode="json") for item in items], total=total, limit=limit, offset=offset)


@router.post("/api/readiness/cases", response_model=ApiResponse, status_code=201)
def create_readiness_case(
    request: Request,
    body: CreateReadinessCase,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    readiness: ReadinessService = Depends(get_readiness_service),
) -> ApiResponse:
    item = readiness.create(body, idempotency_key)
    return response(request, item.model_dump(mode="json"), case_id=item.id)


@router.get("/api/readiness/cases/{case_id}", response_model=ApiResponse)
def get_readiness_case(
    request: Request,
    case_id: str,
    readiness: ReadinessService = Depends(get_readiness_service),
) -> ApiResponse:
    item = readiness.get(case_id)
    return response(request, item.model_dump(mode="json"))


@router.get("/api/cases/{case_id}", response_model=ApiResponse)
def get_case(request: Request, case_id: str, session: Session = Depends(get_session)) -> ApiResponse:
    record = CaseRepository(session).get(case_id)
    if record is None:
        raise DomainError(404, "CASE_NOT_FOUND", "Case not found")
    runs = AssessmentRepository(session)
    latest = runs.latest(case_id)
    loaded = runs.get(latest.run_id) if latest else None
    return response(request, company_projection(record, loaded).model_dump())


@router.post("/api/cases/{case_id}/assessment-runs", response_model=ApiResponse)
def create_assessment_run(
    request: Request,
    case_id: str,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    assessments: AssessmentService = Depends(get_assessment_service),
) -> ApiResponse:
    record = assessments.run(case_id, idempotency_key)
    return response(request, run_schema(record).model_dump(mode="json"), run_id=record.run_id)


@router.post("/api/cases/{case_id}/assessment-runs/rerun", response_model=ApiResponse)
def rerun_assessment(
    request: Request,
    case_id: str,
    assessments: AssessmentService = Depends(get_assessment_service),
) -> ApiResponse:
    record = assessments.run(case_id, f"rerun-{uuid4().hex}")
    return response(request, run_schema(record).model_dump(mode="json"), run_id=record.run_id)


@router.post("/api/cases/{case_id}/workflow-runs", response_model=ApiResponse)
def start_workflow_run(
    request: Request,
    case_id: str,
    assessments: AssessmentService = Depends(get_assessment_service),
) -> ApiResponse:
    record, state = assessments.start_stepwise(case_id, f"stepwise-{uuid4().hex}")
    return response(request, {"run_id": record.run_id, "state": state.model_dump(mode="json")}, run_id=record.run_id)


@router.post("/api/cases/{case_id}/workflow-runs/{run_id}/nodes/{node_id}", response_model=ApiResponse)
def execute_workflow_node(
    request: Request,
    case_id: str,
    run_id: str,
    node_id: str,
    body: WorkflowStepRequest,
    assessments: AssessmentService = Depends(get_assessment_service),
) -> ApiResponse:
    record, state = assessments.execute_step(case_id, run_id, body.state, node_id)
    return response(
        request,
        {"run_id": record.run_id, "run_status": record.status, "node": node_id, "state": state.model_dump(mode="json")},
        run_id=record.run_id,
        node=node_id,
    )


@router.get("/api/cases/{case_id}/assessment-runs", response_model=ApiResponse)
def list_assessment_runs(
    request: Request,
    case_id: str,
    session: Session = Depends(get_session),
) -> ApiResponse:
    if CaseRepository(session).get(case_id) is None:
        raise DomainError(404, "CASE_NOT_FOUND", "Case not found")
    records = AssessmentRepository(session).list(case_id)
    return response(request, [run_schema(record).model_dump(mode="json") for record in records], total=len(records))


@router.get("/api/cases/{case_id}/assessment-runs/{run_id}", response_model=ApiResponse)
def get_assessment_run(
    request: Request,
    case_id: str,
    run_id: str,
    assessments: AssessmentService = Depends(get_assessment_service),
) -> ApiResponse:
    record = assessments.get(case_id, run_id)
    return response(request, run_schema(record).model_dump(mode="json"))


@router.get("/api/cases/{case_id}/assessment-runs/{run_id}/artifacts", response_model=ApiResponse)
def get_artifacts(
    request: Request,
    case_id: str,
    run_id: str,
    assessments: AssessmentService = Depends(get_assessment_service),
) -> ApiResponse:
    record = assessments.get(case_id, run_id)
    items = [
        {
            "artifact_id": artifact.artifact_id,
            "run_id": artifact.run_id,
            "agent_id": artifact.agent_id,
            "engine": artifact.engine,
            "status": artifact.status,
            "summary": artifact.summary,
            "claims": artifact.claims,
            "metrics": artifact.metrics,
            "warnings": artifact.warnings,
            "proposed_actions": artifact.proposed_actions,
            "raw": artifact.raw,
        }
        for artifact in record.artifacts
    ]
    return response(request, items, total=len(items))


@router.get("/api/cases/{case_id}/assessment-runs/{run_id}/events", response_model=ApiResponse)
def get_run_events(
    request: Request,
    case_id: str,
    run_id: str,
    assessments: AssessmentService = Depends(get_assessment_service),
) -> ApiResponse:
    record = assessments.get(case_id, run_id)
    return response(request, [
        {
            "event_id": event.event_id,
            "case_id": event.case_id,
            "run_id": event.run_id,
            "node_id": event.node_id,
            "status": event.status,
            "engine": event.engine,
            "input_summary": event.input_summary,
            "output_summary": event.output_summary,
            "timestamp": event.timestamp,
        }
        for event in record.events
    ], total=len(record.events))


@router.get("/api/cases/{case_id}/events", response_model=ApiResponse)
def get_case_events(
    request: Request,
    case_id: str,
    resolution: ResolutionService = Depends(get_resolution_service),
) -> ApiResponse:
    package = resolution.get(case_id)
    record = resolution.assessments.get(case_id, package.run.run_id)
    items = [
        {
            "event_id": event.event_id,
            "case_id": event.case_id,
            "run_id": event.run_id,
            "node_id": event.node_id,
            "status": event.status,
            "engine": event.engine,
            "input_summary": event.input_summary,
            "output_summary": event.output_summary,
            "timestamp": event.timestamp,
        }
        for event in record.events
    ]
    return response(request, items, total=len(items))


@router.get("/api/cases/{case_id}/resolution-package", response_model=ApiResponse)
def get_resolution_package(
    request: Request,
    case_id: str,
    run_id: str | None = Query(default=None),
    resolution: ResolutionService = Depends(get_resolution_service),
) -> ApiResponse:
    package = resolution.get(case_id, run_id)
    return response(request, package.model_dump(mode="json"))


@router.get("/api/cases/{case_id}/actions", response_model=ApiResponse)
def list_actions(
    request: Request,
    case_id: str,
    actions: ActionService = Depends(get_action_service),
) -> ApiResponse:
    items = actions.list(case_id)
    return response(request, [item.model_dump(mode="json") for item in items], total=len(items))


@router.post("/api/cases/{case_id}/actions/{action_id}/approve", response_model=ApiResponse)
def approve_action(
    request: Request,
    case_id: str,
    action_id: str,
    body: ApprovalRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    x_user_id: str = Header(default="demo-approver"),
    x_role: str = Header(default="viewer"),
    actions: ActionService = Depends(get_action_service),
) -> ApiResponse:
    item = actions.approve(case_id, action_id, body.approved_payload_hash, x_user_id, x_role, idempotency_key, body.reason)
    return response(request, item.model_dump(mode="json"))


@router.post("/api/cases/{case_id}/actions/{action_id}/reject", response_model=ApiResponse)
def reject_action(
    request: Request,
    case_id: str,
    action_id: str,
    body: RejectionRequest,
    x_user_id: str = Header(default="demo-approver"),
    x_role: str = Header(default="viewer"),
    actions: ActionService = Depends(get_action_service),
) -> ApiResponse:
    item = actions.reject(case_id, action_id, x_user_id, x_role, body.reason)
    return response(request, item.model_dump(mode="json"))


@router.get("/api/cases/{case_id}/actions/{action_id}/execution", response_model=ApiResponse)
def get_execution(
    request: Request,
    case_id: str,
    action_id: str,
    actions: ActionService = Depends(get_action_service),
) -> ApiResponse:
    return response(request, actions.execution(case_id, action_id).model_dump(mode="json"))

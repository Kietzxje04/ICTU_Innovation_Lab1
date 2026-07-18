from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from .agent_service import AgentService
from .database import get_session
from .dependencies import get_action_service, get_agent_service, get_assessment_service, get_resolution_service
from .exceptions import DomainError
from .repositories import AssessmentRepository, CaseRepository, run_schema
from .schemas import ApiResponse, ApprovalRequest, RejectionRequest
from .services import ActionService, AssessmentService, ResolutionService, company_projection
from .readiness_schemas import CreateReadinessCase
from .readiness_service import ReadinessService
from .dependencies import get_readiness_service


router = APIRouter()


def response(request: Request, data: object, **meta: object) -> ApiResponse:
    return ApiResponse(
        data=data,
        meta={"request_id": getattr(request.state, "request_id", "unknown"), "api": "single-backend", **meta},
    )


@router.get("/health", response_model=ApiResponse)
def health(request: Request, agent: AgentService = Depends(get_agent_service)) -> ApiResponse:
    return response(request, {"status": "ok", "service": "nexusops-backend", "agent": agent.health()})


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
    readiness: ReadinessService = Depends(get_readiness_service),
) -> ApiResponse:
    items = readiness.list(q=q, product=product, status=status)
    return response(request, [item.model_dump(mode="json") for item in items], total=len(items))


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

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.nodes.readiness_rules import ReadinessRuleEngine
from nexusops_agent.orchestration.router import route_case
from nexusops_agent.tools.mock_banking import (
    get_account_turnover,
    get_cic_snapshot,
    get_customer_snapshot,
    get_kyc_aml_snapshot,
)
from sqlalchemy.orm import Session

from .agent_service import AgentService
from .database import get_session
from .dependencies import (
    get_action_service,
    get_agent_service,
    get_readiness_service,
    get_resolution_service,
)
from .readiness_schemas import CreateReadinessCase
from .readiness_service import ReadinessService
from .schemas import ApiResponse, ApprovalRequest, RejectionRequest
from .services import ActionService, ResolutionService
from .v3_schemas import MockActionRequest, RoutePreviewRequest, SignatureValidationRequest, WorkflowCreate
from .v3_services import EvaluationService, MockActionService, WorkflowRegistryService


router = APIRouter()


@router.get("/api/v3/products", response_model=ApiResponse)
def list_products(request: Request) -> ApiResponse:
    engine = ReadinessRuleEngine()
    items = []
    for product in ("CORPORATE_OVERDRAFT", "WORKING_CAPITAL"):
        pack = engine.product_definition(product)
        items.append({
            "product": product,
            "purpose": pack.get("purpose"),
            "facility_type": pack.get("facility_type"),
            "customer_relationship": pack.get("customer_relationship"),
            "currency": pack.get("currency", "VND"),
            "required_documents": pack.get("required_documents", []),
            "policy_source": pack.get("policy_source"),
            "synthetic": bool(pack.get("synthetic", True)),
        })
    return response(request, items, total=len(items), source="agent-config")


@router.get("/api/v3/products/{product}/intake-schema", response_model=ApiResponse)
def product_intake_schema(request: Request, product: str) -> ApiResponse:
    if product not in {"CORPORATE_OVERDRAFT", "WORKING_CAPITAL"}:
        raise HTTPException(status_code=404, detail={"code": "PRODUCT_NOT_FOUND", "message": "Product not found"})
    pack = ReadinessRuleEngine().product_definition(product)
    overdraft_fields = [
        {"name": "account_history_months", "type": "integer", "required": True},
        {"name": "twelve_month_credit_turnover", "type": "number", "required": True},
        {"name": "average_monthly_credit_inflow", "type": "number", "required": False},
        {"name": "turnover_stability_ratio", "type": "number", "required": False},
        {"name": "expected_utilization_ratio", "type": "number", "required": False},
        {"name": "negative_balance_days", "type": "integer", "required": False},
        {"name": "cleanup_days", "type": "integer", "required": False},
        {"name": "overdraft_purpose", "type": "string", "required": True},
    ]
    working_capital_fields = [
        {"name": "loan_purpose", "type": "string", "required": True},
        {"name": "collateral_ratio", "type": "number", "required": True},
    ]
    return response(request, {
        "product": product,
        "required_documents": pack.get("required_documents", []),
        "fields": overdraft_fields if product == "CORPORATE_OVERDRAFT" else working_capital_fields,
        "rules": pack.get("rules", []),
        "synthetic": bool(pack.get("synthetic", True)),
    }, source="agent-config")


@router.post("/api/v3/cases/preview-route", response_model=ApiResponse)
def preview_case_route(request: Request, body: RoutePreviewRequest) -> ApiResponse:
    context = ReadinessRuleEngine().canonical_case(body.context)
    decision = route_case(context)
    return response(request, {
        "product": context.product.value,
        "required_documents": context.required_documents,
        "route": decision.nodes,
        "hardness": decision.hardness,
        "reasons": decision.reasons,
    }, source="agent-router")


def response(request: Request, data: object, **meta: object) -> ApiResponse:
    return ApiResponse(
        data=data,
        meta={"request_id": getattr(request.state, "request_id", "unknown"), "api": "single-backend", **meta},
    )


# Agent package handoff API -------------------------------------------------


@router.post("/api/v1/agent/runs", response_model=ApiResponse)
def run_agent(
    request: Request,
    body: CaseContext,
    agent: AgentService = Depends(get_agent_service),
) -> ApiResponse:
    package = agent.run_case(body)
    return response(request, package.model_dump(mode="json"), persisted=False)


@router.get("/api/v1/agent/runs/{case_id}", response_model=ApiResponse)
def get_agent_run(
    request: Request,
    case_id: str,
    run_id: str | None = Query(default=None),
    resolution: ResolutionService = Depends(get_resolution_service),
) -> ApiResponse:
    package = resolution.get(case_id, run_id)
    return response(request, package.model_dump(mode="json"), persisted=True)


@router.get("/api/v1/agent/runs/{case_id}/events", response_model=ApiResponse)
def get_agent_run_events(
    request: Request,
    case_id: str,
    resolution: ResolutionService = Depends(get_resolution_service),
) -> ApiResponse:
    package = resolution.get(case_id)
    run = resolution.assessments.get(case_id, package.run.run_id)
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
        for event in run.events
    ]
    return response(request, items, total=len(items))


# V3 case/readiness API aliases --------------------------------------------


@router.get("/api/v3/cases", response_model=ApiResponse)
def list_v3_cases(
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


@router.post("/api/v3/cases", response_model=ApiResponse, status_code=201)
def create_v3_case(
    request: Request,
    body: CreateReadinessCase,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    readiness: ReadinessService = Depends(get_readiness_service),
) -> ApiResponse:
    item = readiness.create(body, idempotency_key)
    return response(request, item.model_dump(mode="json"), case_id=item.id)


@router.get("/api/v3/cases/{case_id}", response_model=ApiResponse)
def get_v3_case(
    request: Request,
    case_id: str,
    readiness: ReadinessService = Depends(get_readiness_service),
) -> ApiResponse:
    item = readiness.get(case_id)
    return response(request, item.model_dump(mode="json"))


@router.get("/api/v3/cases/{case_id}/readiness-package", response_model=ApiResponse)
def get_v3_readiness_package(
    request: Request,
    case_id: str,
    run_id: str | None = Query(default=None),
    resolution: ResolutionService = Depends(get_resolution_service),
) -> ApiResponse:
    package = resolution.get(case_id, run_id)
    return response(request, package.model_dump(mode="json"))


@router.get("/api/v3/cases/{case_id}/node-runs", response_model=ApiResponse)
def get_v3_node_runs(
    request: Request,
    case_id: str,
    resolution: ResolutionService = Depends(get_resolution_service),
) -> ApiResponse:
    package = resolution.get(case_id)
    run = resolution.assessments.get(case_id, package.run.run_id)
    artifacts = {artifact.agent_id: artifact for artifact in run.artifacts}
    items = []
    for event in run.events:
        artifact = artifacts.get(event.node_id)
        items.append(
            {
                "node_id": event.node_id,
                "run_id": event.run_id,
                "status": event.status,
                "engine": event.engine,
                "timestamp": event.timestamp,
                "summary": artifact.summary if artifact else event.output_summary,
                "artifact_status": artifact.status if artifact else None,
                "metrics": artifact.metrics if artifact else {},
                "warnings": artifact.warnings if artifact else [],
            }
        )
    return response(request, items, total=len(items))


@router.get("/api/v3/cases/{case_id}/events", response_model=ApiResponse)
def get_v3_events(
    request: Request,
    case_id: str,
    resolution: ResolutionService = Depends(get_resolution_service),
) -> ApiResponse:
    return get_agent_run_events(request, case_id, resolution)


@router.get("/api/v3/cases/{case_id}/actions", response_model=ApiResponse)
def get_v3_actions(
    request: Request,
    case_id: str,
    actions: ActionService = Depends(get_action_service),
) -> ApiResponse:
    items = actions.list(case_id)
    return response(request, [item.model_dump(mode="json") for item in items], total=len(items))


@router.post("/api/v3/cases/{case_id}/actions/{action_id}/approve", response_model=ApiResponse)
def approve_v3_action(
    request: Request,
    case_id: str,
    action_id: str,
    body: ApprovalRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    x_user_id: str = Header(default="demo-approver"),
    x_role: str = Header(default="viewer"),
    actions: ActionService = Depends(get_action_service),
) -> ApiResponse:
    item = actions.approve(
        case_id,
        action_id,
        body.approved_payload_hash,
        x_user_id,
        x_role,
        idempotency_key,
        body.reason,
    )
    return response(request, item.model_dump(mode="json"))


@router.post("/api/v3/cases/{case_id}/actions/{action_id}/reject", response_model=ApiResponse)
def reject_v3_action(
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


@router.get("/api/v3/cases/{case_id}/actions/{action_id}/execution", response_model=ApiResponse)
def get_v3_execution(
    request: Request,
    case_id: str,
    action_id: str,
    actions: ActionService = Depends(get_action_service),
) -> ApiResponse:
    return response(request, actions.execution(case_id, action_id).model_dump(mode="json"))


# Workflow registry and evaluation -----------------------------------------


@router.get("/api/v3/workflows", response_model=ApiResponse)
def list_workflows(request: Request, session: Session = Depends(get_session)) -> ApiResponse:
    items = WorkflowRegistryService(session).list()
    return response(request, [item.model_dump(mode="json") for item in items], total=len(items))


@router.post("/api/v3/workflows", response_model=ApiResponse, status_code=201)
def create_workflow(
    request: Request,
    body: WorkflowCreate,
    x_user_id: str = Header(default="workflow-designer"),
    session: Session = Depends(get_session),
) -> ApiResponse:
    item = WorkflowRegistryService(session).create(body, x_user_id)
    return response(request, item.model_dump(mode="json"))


@router.post("/api/v3/workflows/{workflow_id}/validate", response_model=ApiResponse)
def validate_workflow(request: Request, workflow_id: str, session: Session = Depends(get_session)) -> ApiResponse:
    item = WorkflowRegistryService(session).validate(workflow_id)
    return response(request, item.model_dump(mode="json"), valid=not item.validation_errors)


@router.post("/api/v3/workflows/{workflow_id}/publish", response_model=ApiResponse)
def publish_workflow(request: Request, workflow_id: str, session: Session = Depends(get_session)) -> ApiResponse:
    item = WorkflowRegistryService(session).publish(workflow_id)
    return response(request, item.model_dump(mode="json"))


@router.get("/api/v3/workflows/{workflow_id}/versions", response_model=ApiResponse)
def workflow_versions(request: Request, workflow_id: str, session: Session = Depends(get_session)) -> ApiResponse:
    items = WorkflowRegistryService(session).versions(workflow_id)
    return response(request, [item.model_dump(mode="json") for item in items], total=len(items))


@router.post("/api/v3/evaluations/run", response_model=ApiResponse, status_code=201)
def run_evaluation(request: Request, session: Session = Depends(get_session)) -> ApiResponse:
    record = EvaluationService(session).run()
    return response(
        request,
        {"run_id": record.run_id, "status": record.status, **record.report},
    )


@router.get("/api/v3/evaluations/{run_id}", response_model=ApiResponse)
def get_evaluation(request: Request, run_id: str, session: Session = Depends(get_session)) -> ApiResponse:
    record = EvaluationService(session).get(run_id)
    return response(request, {"run_id": record.run_id, "status": record.status, **record.report})


# Allowlisted mock operational APIs ----------------------------------------


@router.get("/mock/customer/{customer_id}", response_model=ApiResponse)
def mock_customer(request: Request, customer_id: str) -> ApiResponse:
    return response(request, get_customer_snapshot(customer_id))


@router.get("/mock/accounts/{customer_id}/turnover", response_model=ApiResponse)
def mock_turnover(request: Request, customer_id: str) -> ApiResponse:
    return response(request, get_account_turnover(customer_id))


@router.get("/mock/cic/{customer_id}", response_model=ApiResponse)
def mock_cic(request: Request, customer_id: str) -> ApiResponse:
    return response(request, get_cic_snapshot(customer_id))


@router.get("/mock/kyc-aml/{customer_id}", response_model=ApiResponse)
def mock_kyc_aml(request: Request, customer_id: str) -> ApiResponse:
    return response(request, get_kyc_aml_snapshot(customer_id))


@router.post("/mock/signature/validate", response_model=ApiResponse)
def mock_signature(request: Request, body: SignatureValidationRequest) -> ApiResponse:
    if body.signature_present is False:
        status = "INVALID"
        reasons = ["SIGNATURE_MISSING"]
    elif body.signature_present is None:
        status = "UNKNOWN"
        reasons = ["SIGNATURE_METADATA_MISSING"]
    elif body.certificate_valid is False or body.digest_matches is False:
        status = "INVALID"
        reasons = [
            reason
            for condition, reason in (
                (body.certificate_valid is False, "CERTIFICATE_INVALID"),
                (body.digest_matches is False, "DIGEST_MISMATCH"),
            )
            if condition
        ]
    elif body.certificate_valid is None or body.digest_matches is None:
        status = "UNKNOWN"
        reasons = ["SIGNATURE_VALIDATION_INCOMPLETE"]
    else:
        status = "VALID"
        reasons = []
    return response(request, {"document_id": body.document_id, "status": status, "reasons": reasons})


def execute_mock_action(
    request: Request,
    action_type: str,
    body: MockActionRequest,
    idempotency_key: str,
    approved_by: str,
    session: Session,
) -> ApiResponse:
    record = MockActionService(session).execute(
        action_type=action_type,
        case_id=body.case_id,
        payload=body.payload,
        idempotency_key=idempotency_key,
        approved_by=approved_by,
    )
    return response(
        request,
        {
            "external_ref": record.external_ref,
            "idempotency_key": record.idempotency_key,
            "action_type": record.action_type,
            "case_id": record.case_id,
            "status": record.status,
            "approved_by": record.approved_by,
            "created_at": record.created_at,
        },
    )


@router.post("/mock-los/draft-intake", response_model=ApiResponse)
def mock_los(
    request: Request,
    body: MockActionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    approved_by: str = Header(alias="X-Approved-By"),
    session: Session = Depends(get_session),
) -> ApiResponse:
    return execute_mock_action(request, "CREATE_DRAFT_LOS_INTAKE", body, idempotency_key, approved_by, session)


@router.post("/mock-dms/document-request", response_model=ApiResponse)
def mock_dms(
    request: Request,
    body: MockActionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    approved_by: str = Header(alias="X-Approved-By"),
    session: Session = Depends(get_session),
) -> ApiResponse:
    return execute_mock_action(request, "REQUEST_MISSING_DOCUMENTS", body, idempotency_key, approved_by, session)


@router.post("/mock-bpm/financial-review-task", response_model=ApiResponse)
def mock_bpm(
    request: Request,
    body: MockActionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    approved_by: str = Header(alias="X-Approved-By"),
    session: Session = Depends(get_session),
) -> ApiResponse:
    return execute_mock_action(request, "CREATE_FINANCIAL_REVIEW_TASK", body, idempotency_key, approved_by, session)


@router.post("/mock-grc/compliance-review-task", response_model=ApiResponse)
def mock_grc(
    request: Request,
    body: MockActionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    approved_by: str = Header(alias="X-Approved-By"),
    session: Session = Depends(get_session),
) -> ApiResponse:
    return execute_mock_action(request, "CREATE_COMPLIANCE_REVIEW_TASK", body, idempotency_key, approved_by, session)


@router.get("/mock/actions/{external_ref}", response_model=ApiResponse)
def get_mock_action(request: Request, external_ref: str, session: Session = Depends(get_session)) -> ApiResponse:
    record = MockActionService(session).get(external_ref)
    return response(
        request,
        {
            "external_ref": record.external_ref,
            "idempotency_key": record.idempotency_key,
            "action_type": record.action_type,
            "case_id": record.case_id,
            "payload": record.payload,
            "status": record.status,
            "approved_by": record.approved_by,
            "created_at": record.created_at,
        },
    )

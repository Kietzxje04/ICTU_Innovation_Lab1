import os

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .actions import approve_action, build_resolution_package, get_execution, get_or_create_action, reject_action
from .schemas import ApiResponse, ApprovalRequest, RejectionRequest
from .seed import COMPANIES


app = FastAPI(title="NexusOps AI Backend", version="0.1.0")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", response_model=ApiResponse)
def health() -> ApiResponse:
    return ApiResponse(data={"status": "ok", "service": "nexusops-backend"})


@app.get("/api/v1/cases", response_model=ApiResponse)
def list_cases(
    q: str | None = Query(default=None, description="Search by company name or case code"),
    status: str | None = Query(default=None),
) -> ApiResponse:
    items = COMPANIES
    if q:
        needle = q.casefold()
        items = [item for item in items if needle in f"{item.name} {item.code}".casefold()]
    if status and status != "Tất cả":
        items = [item for item in items if item.status == status]
    return ApiResponse(data=items, meta={"total": len(items)})


@app.get("/api/v1/cases/{case_id}", response_model=ApiResponse)
def get_case(case_id: str) -> ApiResponse:
    case = next((item for item in COMPANIES if item.id == case_id), None)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})
    return ApiResponse(data=case)


@app.get("/api/v1/cases/{case_id}/resolution-package", response_model=ApiResponse)
def get_resolution_package(case_id: str) -> ApiResponse:
    case = next((item for item in COMPANIES if item.id == case_id), None)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})
    return ApiResponse(data=build_resolution_package(case))


def _get_case_or_404(case_id: str):
    case = next((item for item in COMPANIES if item.id == case_id), None)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})
    return case


def _require_approver(x_role: str = Header(default="viewer")) -> None:
    if x_role not in {"approver", "manager", "credit_officer"}:
        raise HTTPException(status_code=403, detail={"code": "INSUFFICIENT_ROLE", "message": "Approver role is required"})


@app.get("/api/v1/cases/{case_id}/actions", response_model=ApiResponse)
def list_actions(case_id: str) -> ApiResponse:
    case = _get_case_or_404(case_id)
    return ApiResponse(data=[get_or_create_action(case)], meta={"total": 1})


@app.post("/api/v1/cases/{case_id}/actions/{action_id}/approve", response_model=ApiResponse)
def approve_case_action(
    case_id: str,
    action_id: str,
    body: ApprovalRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    x_user_id: str = Header(default="demo-approver"),
    x_role: str = Header(default="viewer"),
) -> ApiResponse:
    _require_approver(x_role)
    action = get_or_create_action(_get_case_or_404(case_id))
    if action.id != action_id:
        raise HTTPException(status_code=404, detail={"code": "ACTION_NOT_FOUND", "message": "Action not found"})
    return ApiResponse(data=approve_action(action, approved_payload_hash=body.approved_payload_hash, user_id=x_user_id, idempotency_key=idempotency_key))


@app.post("/api/v1/cases/{case_id}/actions/{action_id}/reject", response_model=ApiResponse)
def reject_case_action(
    case_id: str,
    action_id: str,
    body: RejectionRequest,
    x_user_id: str = Header(default="demo-approver"),
    x_role: str = Header(default="viewer"),
) -> ApiResponse:
    _require_approver(x_role)
    action = get_or_create_action(_get_case_or_404(case_id))
    if action.id != action_id:
        raise HTTPException(status_code=404, detail={"code": "ACTION_NOT_FOUND", "message": "Action not found"})
    return ApiResponse(data=reject_action(action, user_id=x_user_id))


@app.get("/api/v1/cases/{case_id}/actions/{action_id}/execution", response_model=ApiResponse)
def get_action_execution(case_id: str, action_id: str) -> ApiResponse:
    action = get_or_create_action(_get_case_or_404(case_id))
    if action.id != action_id:
        raise HTTPException(status_code=404, detail={"code": "ACTION_NOT_FOUND", "message": "Action not found"})
    return ApiResponse(data=get_execution(action.id))

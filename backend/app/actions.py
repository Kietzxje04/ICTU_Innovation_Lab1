import hashlib
import json
from datetime import datetime, timezone

from fastapi import HTTPException

from .schemas import Company, ExecutionRecord, ProposedAction, ResolutionPackage


OUTCOMES: dict[str, tuple[str, list[str], list[str], str]] = {
    "toan-cau": (
        "TAX_RECONCILIATION_REQUIRED",
        ["MATERIAL_REVENUE_GAP"],
        ["TAX_REVIEW", "CREDIT_REVIEW"],
        "CREATE_TAX_RECONCILIATION_TASK",
    ),
    "hung-phat": (
        "READY_FOR_HUMAN_REVIEW",
        [],
        ["CREDIT_OFFICER_REVIEW"],
        "CREATE_DRAFT_REVIEW_PACKAGE",
    ),
    "sai-gon": (
        "CREDIT_EXCEPTION_REVIEW",
        ["LOW_DSCR", "HIGH_LEVERAGE"],
        ["CREDIT_REVIEW", "STRUCTURING_REVIEW"],
        "CREATE_CREDIT_REVIEW_TASK",
    ),
    "le-gia": (
        "DOCUMENT_REQUIRED",
        ["MISSING_RECEIVABLES_REPORT"],
        ["OPERATIONS", "RELATIONSHIP_MANAGER"],
        "REQUEST_MISSING_DOCUMENTS",
    ),
}

_actions: dict[str, ProposedAction] = {}
_executions: dict[str, ExecutionRecord] = {}


def _hash_payload(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_or_create_action(company: Company) -> ProposedAction:
    action_id = f"act-{company.id}"
    if action_id in _actions:
        return _actions[action_id]

    _, _, _, action_type = OUTCOMES[company.id]
    payload: dict[str, object] = {
        "case_id": company.id,
        "case_code": company.code,
        "customer_name": company.name,
        "action_type": action_type,
        "owner": company.owner,
    }
    action = ProposedAction(
        id=action_id,
        case_id=company.id,
        type=action_type,
        payload=payload,
        payload_hash=_hash_payload(payload),
        status="PENDING_APPROVAL",
        created_by="nexusops-system",
    )
    _actions[action_id] = action
    _executions[action_id] = ExecutionRecord(
        action_id=action_id,
        external_ref=None,
        status="NOT_STARTED",
        idempotency_key=None,
        executed_at=None,
    )
    return action


def build_resolution_package(company: Company) -> ResolutionPackage:
    outcome, blockers, routes, action_type = OUTCOMES[company.id]
    return ResolutionPackage(
        case=company,
        primary_outcome=outcome,
        blockers=blockers,
        routes=routes,
        reason_codes=blockers or ["NO_UNRESOLVED_BLOCKER"],
        eligible_actions=[action_type],
        proposed_action=get_or_create_action(company),
    )


def approve_action(
    action: ProposedAction,
    *,
    approved_payload_hash: str,
    user_id: str,
    idempotency_key: str,
) -> ProposedAction:
    if action.status in {"APPROVED", "SUCCEEDED"}:
        return action
    if action.status == "REJECTED":
        raise HTTPException(status_code=409, detail={"code": "ACTION_ALREADY_REJECTED", "message": "Action was rejected"})
    if approved_payload_hash != action.payload_hash:
        raise HTTPException(status_code=409, detail={"code": "PAYLOAD_HASH_MISMATCH", "message": "Action payload has changed"})

    now = datetime.now(timezone.utc)
    action.status = "SUCCEEDED"
    action.approved_by = user_id
    action.decided_at = now
    _executions[action.id] = ExecutionRecord(
        action_id=action.id,
        external_ref=f"mock-{action.id}",
        status="SUCCEEDED",
        idempotency_key=idempotency_key,
        executed_at=now,
    )
    return action


def reject_action(action: ProposedAction, *, user_id: str) -> ProposedAction:
    if action.status == "REJECTED":
        return action
    if action.status in {"APPROVED", "SUCCEEDED"}:
        raise HTTPException(status_code=409, detail={"code": "ACTION_ALREADY_EXECUTED", "message": "Executed action cannot be rejected"})
    action.status = "REJECTED"
    action.approved_by = user_id
    action.decided_at = datetime.now(timezone.utc)
    return action


def get_execution(action_id: str) -> ExecutionRecord:
    return _executions[action_id]
